from datetime import datetime, timezone
from typing import Sequence

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models.item import Item, ItemStatus
from app.models.request import DonationRequest, RequestStatus
from app.models.user import User, UserRole
from app.schemas.request import RequestCreate, RequestOut


async def _load_request(db: AsyncSession, request_id: int) -> DonationRequest | None:
    """Fetch a DonationRequest with all required relationships eagerly loaded."""
    return await db.scalar(
        select(DonationRequest)
        .options(
            joinedload(DonationRequest.item).joinedload(Item.donor),
            joinedload(DonationRequest.requester),
        )
        .where(DonationRequest.id == request_id)
    )


async def request_to_out(request: DonationRequest, current_user: User) -> RequestOut:
    # Privacy: donor + approved/picked-up requester can see donor phone
    can_see_phone = current_user.id == request.item.donor_id or (
        current_user.id == request.requester_id
        and request.status in (RequestStatus.approved, RequestStatus.picked_up)
    )
    donor_phone = request.item.donor.phone if can_see_phone else None

    # ngo_note visible only to the parties of the request
    ngo_note = request.ngo_note
    if current_user.id != request.item.donor_id and current_user.id != request.requester_id:
        ngo_note = None

    return RequestOut(
        id=request.id,
        item_id=request.item_id,
        requester_id=request.requester_id,
        item_title=request.item.title,
        donor_name=request.item.donor.full_name,
        donor_phone=donor_phone,
        requester_name=request.requester.full_name,
        message=request.message,
        ngo_note=ngo_note,
        status=request.status,
        pickup_scheduled_at=request.pickup_scheduled_at,
        approved_at=request.approved_at,
        picked_up_at=request.picked_up_at,
        cancelled_at=request.cancelled_at,
        created_at=request.created_at,
        updated_at=request.updated_at,
    )


async def create_request(
    db: AsyncSession, current_user: User, request_in: RequestCreate
) -> DonationRequest:
    if current_user.role == UserRole.donor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Donors cannot request items",
        )

    if request_in.ngo_note and current_user.role != UserRole.ngo:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only NGOs can submit an ngo_note",
        )

    item = await db.scalar(
        select(Item).options(selectinload(Item.donor)).where(Item.id == request_in.item_id)
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    if item.donor_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cannot request your own item",
        )

    if item.status != ItemStatus.available:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Item is not available for request",
        )

    existing = await db.scalar(
        select(DonationRequest).where(
            DonationRequest.item_id == item.id,
            DonationRequest.requester_id == current_user.id,
            DonationRequest.status.in_([RequestStatus.pending, RequestStatus.approved]),
        )
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="You already have an active request for this item",
        )

    new_request = DonationRequest(
        item_id=item.id,
        requester_id=current_user.id,
        message=request_in.message,
        ngo_note=request_in.ngo_note,
        status=RequestStatus.pending,
    )
    db.add(new_request)
    await db.commit()

    # Reload with relationships — commit expires all attributes
    loaded = await _load_request(db, new_request.id)
    assert loaded is not None

    # Dispatch email task to notify the donor
    from app.worker.tasks import send_request_notification
    send_request_notification.delay(
        donor_email=loaded.item.donor.email,
        donor_name=loaded.item.donor.full_name,
        requester_name=loaded.requester.full_name,
        item_title=loaded.item.title,
        message=loaded.message or "",
    )

    return loaded


async def approve_request(db: AsyncSession, request_id: int, current_user: User) -> DonationRequest:
    # Transaction note: relies on SQLAlchemy's implicit transaction opened by get_db().
    # The sequence (lock request → lock item → mutate → commit) is atomic within the
    # single session yielded by the FastAPI dependency. If middleware ever introduces a
    # surrounding transaction, this must be revisited with explicit savepoints.
    req = await db.scalar(
        select(DonationRequest)
        .where(DonationRequest.id == request_id)
        .with_for_update()
    )
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")

    # Need item to check ownership — fetch with lock
    item = await db.scalar(
        select(Item).where(Item.id == req.item_id).with_for_update()
    )
    if item.donor_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    if req.status != RequestStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Request is {req.status}, cannot approve",
        )

    if item.status != ItemStatus.available:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Item is no longer available",
        )

    req.status = RequestStatus.approved
    req.approved_at = datetime.now(timezone.utc)
    item.status = ItemStatus.reserved

    # Auto-reject all other pending requests for this item
    other_requests_result = await db.execute(
        select(DonationRequest)
        .options(selectinload(DonationRequest.requester))
        .where(
            DonationRequest.item_id == item.id,
            DonationRequest.id != req.id,
            DonationRequest.status == RequestStatus.pending,
        )
        .with_for_update()
    )
    other_requests = other_requests_result.scalars().all()
    rejected_users = [
        (other.requester.email, other.requester.full_name)
        for other in other_requests
    ]
    for other in other_requests:
        other.status = RequestStatus.rejected

    await db.commit()

    # Reload to get fresh, fully-joined object after commit expiry
    loaded = await _load_request(db, request_id)
    assert loaded is not None

    # Dispatch approval notification to requester
    from app.worker.tasks import send_approval_notification, send_rejection_notification
    send_approval_notification.delay(
        requester_email=loaded.requester.email,
        requester_name=loaded.requester.full_name,
        item_title=loaded.item.title,
        donor_phone=current_user.phone or "not provided",
        pickup_instructions="Contact the donor to arrange pickup.",
    )

    # Dispatch rejection notifications to competing requesters who were auto-rejected
    for r_email, r_name in rejected_users:
        send_rejection_notification.delay(
            requester_email=r_email,
            requester_name=r_name,
            item_title=loaded.item.title,
        )

    return loaded


async def reject_request(db: AsyncSession, request_id: int, current_user: User) -> DonationRequest:
    req = await db.scalar(
        select(DonationRequest).where(DonationRequest.id == request_id)
    )
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")

    item = await db.scalar(select(Item).where(Item.id == req.item_id))
    if item.donor_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    if req.status != RequestStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Request is {req.status}, cannot reject",
        )

    req.status = RequestStatus.rejected
    await db.commit()

    loaded = await _load_request(db, request_id)
    assert loaded is not None

    # Dispatch rejection notification to requester
    from app.worker.tasks import send_rejection_notification
    send_rejection_notification.delay(
        requester_email=loaded.requester.email,
        requester_name=loaded.requester.full_name,
        item_title=loaded.item.title,
    )

    return loaded


async def pickup_request(db: AsyncSession, request_id: int, current_user: User) -> DonationRequest:
    # Transaction note: same implicit-transaction dependency as approve_request.
    # lock request → lock item → mutate both → commit is atomic within the single session.
    req = await db.scalar(
        select(DonationRequest).where(DonationRequest.id == request_id).with_for_update()
    )
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")

    item = await db.scalar(
        select(Item).where(Item.id == req.item_id).with_for_update()
    )
    if item.donor_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    if req.status != RequestStatus.approved:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Request is {req.status}, cannot confirm pickup",
        )

    now = datetime.now(timezone.utc)
    req.status = RequestStatus.picked_up
    req.picked_up_at = now
    item.status = ItemStatus.donated
    item.donated_at = now

    await db.commit()

    loaded = await _load_request(db, request_id)
    assert loaded is not None

    # Dispatch pickup confirmation email to both donor and recipient
    from app.worker.tasks import send_pickup_confirmation
    send_pickup_confirmation.delay(
        donor_email=loaded.item.donor.email,
        donor_name=loaded.item.donor.full_name,
        requester_email=loaded.requester.email,
        requester_name=loaded.requester.full_name,
        item_title=loaded.item.title,
    )

    return loaded


async def cancel_request(db: AsyncSession, request_id: int, current_user: User) -> DonationRequest:
    req = await db.scalar(
        select(DonationRequest).where(DonationRequest.id == request_id)
    )
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")

    if req.requester_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    if req.status != RequestStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Request is {req.status}, cannot cancel",
        )

    req.status = RequestStatus.cancelled
    req.cancelled_at = datetime.now(timezone.utc)
    await db.commit()

    loaded = await _load_request(db, request_id)
    assert loaded is not None
    return loaded


async def get_request(db: AsyncSession, request_id: int, current_user: User) -> DonationRequest:
    req = await _load_request(db, request_id)
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")

    if req.requester_id != current_user.id and req.item.donor_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    return req


async def list_incoming_requests(db: AsyncSession, current_user: User) -> Sequence[DonationRequest]:
    if current_user.role != UserRole.donor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only donors have incoming requests",
        )

    result = await db.scalars(
        select(DonationRequest)
        .options(
            joinedload(DonationRequest.item).joinedload(Item.donor),
            joinedload(DonationRequest.requester),
        )
        .join(Item)
        .where(Item.donor_id == current_user.id)
        .order_by(DonationRequest.created_at.desc())
    )
    return result.all()


async def list_my_requests(db: AsyncSession, current_user: User) -> Sequence[DonationRequest]:
    result = await db.scalars(
        select(DonationRequest)
        .options(
            joinedload(DonationRequest.item).joinedload(Item.donor),
            joinedload(DonationRequest.requester),
        )
        .where(DonationRequest.requester_id == current_user.id)
        .order_by(DonationRequest.created_at.desc())
    )
    return result.all()
