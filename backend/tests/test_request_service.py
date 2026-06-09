from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.database import async_session_factory
from app.models.item import Item, ItemStatus
from app.models.request import DonationRequest, RequestStatus
from app.models.user import User, UserRole
from app.schemas.request import RequestCreate
from app.services import auth_service, request_service


async def create_db_user(email: str, role: UserRole) -> User:
    async with async_session_factory() as session:
        user = User(
            supabase_user_id=str(uuid4()),
            email=email,
            hashed_password=auth_service.SUPABASE_PASSWORD_SENTINEL,
            full_name=f"{role.value.title()} User",
            role=role,
            phone="1234567890",
            preferred_categories=[],
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def create_db_item(donor: User, title: str, status: ItemStatus = ItemStatus.available) -> Item:
    async with async_session_factory() as session:
        item = Item(
            donor_id=donor.id,
            title=title,
            description="Description",
            category="books",
            condition="good",
            quantity=1,
            status=status,
            city="Bengaluru",
            pincode="560001",
        )
        session.add(item)
        await session.commit()
        await session.refresh(item)
        return item


async def create_db_request(item: Item, requester: User, status: RequestStatus = RequestStatus.pending, ngo_note: str | None = None) -> DonationRequest:
    async with async_session_factory() as session:
        req = DonationRequest(
            item_id=item.id,
            requester_id=requester.id,
            message="Request message",
            ngo_note=ngo_note,
            status=status,
        )
        session.add(req)
        await session.commit()
        await session.refresh(req)
        return req


async def cleanup_db(*emails: str) -> None:
    from sqlalchemy import delete
    async with async_session_factory() as session:
        user_ids_result = await session.execute(select(User.id).where(User.email.in_(emails)))
        user_ids = [row[0] for row in user_ids_result.all()]
        if user_ids:
            await session.execute(delete(DonationRequest).where(DonationRequest.requester_id.in_(user_ids)))
            items_result = await session.execute(select(Item.id).where(Item.donor_id.in_(user_ids)))
            item_ids = [row[0] for row in items_result.all()]
            if item_ids:
                await session.execute(delete(DonationRequest).where(DonationRequest.item_id.in_(item_ids)))
            await session.execute(delete(Item).where(Item.donor_id.in_(user_ids)))
            await session.execute(delete(User).where(User.email.in_(emails)))
            await session.commit()


@pytest.mark.asyncio
@patch("app.worker.tasks.send_request_notification.delay")
async def test_create_request_success(mock_notify):
    email_recip = f"recip-{uuid4().hex}@example.com"
    email_donor = f"donor-{uuid4().hex}@example.com"
    recip = await create_db_user(email_recip, UserRole.recipient)
    donor = await create_db_user(email_donor, UserRole.donor)
    item = await create_db_item(donor, "Books")

    try:
        async with async_session_factory() as db:
            req_in = RequestCreate(item_id=item.id, message="Please give me")
            req = await request_service.create_request(db, recip, req_in)
            
            assert req.id is not None
            assert req.item_id == item.id
            assert req.requester_id == recip.id
            assert req.status == RequestStatus.pending
            mock_notify.assert_called_once_with(
                donor_email=donor.email,
                donor_name=donor.full_name,
                requester_name=recip.full_name,
                item_title=item.title,
                message="Please give me",
            )
    finally:
        await cleanup_db(email_recip, email_donor)


@pytest.mark.asyncio
async def test_create_request_donor_raises_403():
    email_donor = f"donor-{uuid4().hex}@example.com"
    donor = await create_db_user(email_donor, UserRole.donor)
    try:
        async with async_session_factory() as db:
            req_in = RequestCreate(item_id=1, message="Please")
            with pytest.raises(HTTPException) as exc_info:
                await request_service.create_request(db, donor, req_in)
            assert exc_info.value.status_code == 403
            assert "Donors cannot request items" in exc_info.value.detail
    finally:
        await cleanup_db(email_donor)


@pytest.mark.asyncio
async def test_create_request_recipient_submitting_ngo_note_raises_422():
    email_recip = f"recip-{uuid4().hex}@example.com"
    recip = await create_db_user(email_recip, UserRole.recipient)
    try:
        async with async_session_factory() as db:
            req_in = RequestCreate(item_id=1, message="Please", ngo_note="Some NGO note")
            with pytest.raises(HTTPException) as exc_info:
                await request_service.create_request(db, recip, req_in)
            assert exc_info.value.status_code == 422
            assert "Only NGOs can submit an ngo_note" in exc_info.value.detail
    finally:
        await cleanup_db(email_recip)


@pytest.mark.asyncio
async def test_create_request_item_not_found_raises_404():
    email_recip = f"ngo-{uuid4().hex}@example.com"
    ngo = await create_db_user(email_recip, UserRole.ngo)
    try:
        async with async_session_factory() as db:
            req_in = RequestCreate(item_id=-999, message="Please")
            with pytest.raises(HTTPException) as exc_info:
                await request_service.create_request(db, ngo, req_in)
            assert exc_info.value.status_code == 404
            assert "Item not found" in exc_info.value.detail
    finally:
        await cleanup_db(email_recip)


@pytest.mark.asyncio
async def test_create_request_self_request_raises_422():
    email_donor = f"donor-{uuid4().hex}@example.com"
    donor = await create_db_user(email_donor, UserRole.ngo)  # Using NGO role to allow requesting, but owning item
    item = await create_db_item(donor, "Books")
    try:
        async with async_session_factory() as db:
            req_in = RequestCreate(item_id=item.id, message="Please")
            with pytest.raises(HTTPException) as exc_info:
                await request_service.create_request(db, donor, req_in)
            assert exc_info.value.status_code == 422
            assert "Cannot request your own item" in exc_info.value.detail
    finally:
        await cleanup_db(email_donor)


@pytest.mark.asyncio
async def test_create_request_item_unavailable_raises_422():
    email_recip = f"recip-{uuid4().hex}@example.com"
    email_donor = f"donor-{uuid4().hex}@example.com"
    recip = await create_db_user(email_recip, UserRole.recipient)
    donor = await create_db_user(email_donor, UserRole.donor)
    item = await create_db_item(donor, "Books", status=ItemStatus.reserved)
    try:
        async with async_session_factory() as db:
            req_in = RequestCreate(item_id=item.id, message="Please")
            with pytest.raises(HTTPException) as exc_info:
                await request_service.create_request(db, recip, req_in)
            assert exc_info.value.status_code == 422
            assert "Item is not available for request" in exc_info.value.detail
    finally:
        await cleanup_db(email_recip, email_donor)


@pytest.mark.asyncio
async def test_create_request_duplicate_active_raises_422():
    email_recip = f"recip-{uuid4().hex}@example.com"
    email_donor = f"donor-{uuid4().hex}@example.com"
    recip = await create_db_user(email_recip, UserRole.recipient)
    donor = await create_db_user(email_donor, UserRole.donor)
    item = await create_db_item(donor, "Books")
    await create_db_request(item, recip, RequestStatus.pending)
    try:
        async with async_session_factory() as db:
            req_in = RequestCreate(item_id=item.id, message="Please")
            with pytest.raises(HTTPException) as exc_info:
                await request_service.create_request(db, recip, req_in)
            assert exc_info.value.status_code == 422
            assert "You already have an active request for this item" in exc_info.value.detail
    finally:
        await cleanup_db(email_recip, email_donor)


@pytest.mark.asyncio
@patch("app.worker.tasks.send_approval_notification.delay")
@patch("app.worker.tasks.send_rejection_notification.delay")
async def test_approve_request_success(mock_reject_notify, mock_approve_notify):
    email_recip1 = f"recip1-{uuid4().hex}@example.com"
    email_recip2 = f"recip2-{uuid4().hex}@example.com"
    email_donor = f"donor-{uuid4().hex}@example.com"
    recip1 = await create_db_user(email_recip1, UserRole.recipient)
    recip2 = await create_db_user(email_recip2, UserRole.recipient)
    donor = await create_db_user(email_donor, UserRole.donor)
    item = await create_db_item(donor, "Books")
    req1 = await create_db_request(item, recip1, RequestStatus.pending)
    req2 = await create_db_request(item, recip2, RequestStatus.pending)

    try:
        async with async_session_factory() as db:
            approved_req = await request_service.approve_request(db, req1.id, donor)
            assert approved_req.status == RequestStatus.approved
            
            # Verify item status changed to reserved
            updated_item = await db.get(Item, item.id)
            assert updated_item.status == ItemStatus.reserved

            # Verify other requests are rejected
            other_req = await db.get(DonationRequest, req2.id)
            assert other_req.status == RequestStatus.rejected

            mock_approve_notify.assert_called_once()
            mock_reject_notify.assert_called_once_with(
                requester_email=recip2.email,
                requester_name=recip2.full_name,
                item_title=item.title,
            )
    finally:
        await cleanup_db(email_recip1, email_recip2, email_donor)


@pytest.mark.asyncio
async def test_approve_request_not_found_raises_404():
    email_donor = f"donor-{uuid4().hex}@example.com"
    donor = await create_db_user(email_donor, UserRole.donor)
    try:
        async with async_session_factory() as db:
            with pytest.raises(HTTPException) as exc_info:
                await request_service.approve_request(db, -999, donor)
            assert exc_info.value.status_code == 404
            assert "Request not found" in exc_info.value.detail
    finally:
        await cleanup_db(email_donor)


@pytest.mark.asyncio
async def test_approve_request_unauthorized_raises_403():
    email_recip = f"recip-{uuid4().hex}@example.com"
    email_donor1 = f"donor1-{uuid4().hex}@example.com"
    email_donor2 = f"donor2-{uuid4().hex}@example.com"
    recip = await create_db_user(email_recip, UserRole.recipient)
    donor1 = await create_db_user(email_donor1, UserRole.donor)
    donor2 = await create_db_user(email_donor2, UserRole.donor)
    item = await create_db_item(donor1, "Books")
    req = await create_db_request(item, recip, RequestStatus.pending)

    try:
        async with async_session_factory() as db:
            with pytest.raises(HTTPException) as exc_info:
                await request_service.approve_request(db, req.id, donor2)
            assert exc_info.value.status_code == 403
            assert "Not authorized" in exc_info.value.detail
    finally:
        await cleanup_db(email_recip, email_donor1, email_donor2)


@pytest.mark.asyncio
async def test_approve_request_not_pending_raises_409():
    email_recip = f"recip-{uuid4().hex}@example.com"
    email_donor = f"donor-{uuid4().hex}@example.com"
    recip = await create_db_user(email_recip, UserRole.recipient)
    donor = await create_db_user(email_donor, UserRole.donor)
    item = await create_db_item(donor, "Books")
    req = await create_db_request(item, recip, RequestStatus.approved)

    try:
        async with async_session_factory() as db:
            with pytest.raises(HTTPException) as exc_info:
                await request_service.approve_request(db, req.id, donor)
            assert exc_info.value.status_code == 409
            assert "cannot approve" in exc_info.value.detail
    finally:
        await cleanup_db(email_recip, email_donor)


@pytest.mark.asyncio
async def test_approve_request_item_unavailable_raises_409():
    email_recip = f"recip-{uuid4().hex}@example.com"
    email_donor = f"donor-{uuid4().hex}@example.com"
    recip = await create_db_user(email_recip, UserRole.recipient)
    donor = await create_db_user(email_donor, UserRole.donor)
    item = await create_db_item(donor, "Books", status=ItemStatus.reserved)
    req = await create_db_request(item, recip, RequestStatus.pending)

    try:
        async with async_session_factory() as db:
            with pytest.raises(HTTPException) as exc_info:
                await request_service.approve_request(db, req.id, donor)
            assert exc_info.value.status_code == 409
            assert "Item is no longer available" in exc_info.value.detail
    finally:
        await cleanup_db(email_recip, email_donor)


@pytest.mark.asyncio
@patch("app.worker.tasks.send_rejection_notification.delay")
async def test_reject_request_success(mock_notify):
    email_recip = f"recip-{uuid4().hex}@example.com"
    email_donor = f"donor-{uuid4().hex}@example.com"
    recip = await create_db_user(email_recip, UserRole.recipient)
    donor = await create_db_user(email_donor, UserRole.donor)
    item = await create_db_item(donor, "Books")
    req = await create_db_request(item, recip, RequestStatus.pending)

    try:
        async with async_session_factory() as db:
            rejected = await request_service.reject_request(db, req.id, donor)
            assert rejected.status == RequestStatus.rejected
            mock_notify.assert_called_once_with(
                requester_email=recip.email,
                requester_name=recip.full_name,
                item_title=item.title,
            )
    finally:
        await cleanup_db(email_recip, email_donor)


@pytest.mark.asyncio
async def test_reject_request_not_found_raises_404():
    email_donor = f"donor-{uuid4().hex}@example.com"
    donor = await create_db_user(email_donor, UserRole.donor)
    try:
        async with async_session_factory() as db:
            with pytest.raises(HTTPException) as exc_info:
                await request_service.reject_request(db, -999, donor)
            assert exc_info.value.status_code == 404
    finally:
        await cleanup_db(email_donor)


@pytest.mark.asyncio
async def test_reject_request_unauthorized_raises_403():
    email_recip = f"recip-{uuid4().hex}@example.com"
    email_donor1 = f"donor1-{uuid4().hex}@example.com"
    email_donor2 = f"donor2-{uuid4().hex}@example.com"
    recip = await create_db_user(email_recip, UserRole.recipient)
    donor1 = await create_db_user(email_donor1, UserRole.donor)
    donor2 = await create_db_user(email_donor2, UserRole.donor)
    item = await create_db_item(donor1, "Books")
    req = await create_db_request(item, recip, RequestStatus.pending)

    try:
        async with async_session_factory() as db:
            with pytest.raises(HTTPException) as exc_info:
                await request_service.reject_request(db, req.id, donor2)
            assert exc_info.value.status_code == 403
    finally:
        await cleanup_db(email_recip, email_donor1, email_donor2)


@pytest.mark.asyncio
async def test_reject_request_not_pending_raises_409():
    email_recip = f"recip-{uuid4().hex}@example.com"
    email_donor = f"donor-{uuid4().hex}@example.com"
    recip = await create_db_user(email_recip, UserRole.recipient)
    donor = await create_db_user(email_donor, UserRole.donor)
    item = await create_db_item(donor, "Books")
    req = await create_db_request(item, recip, RequestStatus.rejected)

    try:
        async with async_session_factory() as db:
            with pytest.raises(HTTPException) as exc_info:
                await request_service.reject_request(db, req.id, donor)
            assert exc_info.value.status_code == 409
    finally:
        await cleanup_db(email_recip, email_donor)


@pytest.mark.asyncio
@patch("app.worker.tasks.send_pickup_confirmation.delay")
async def test_pickup_request_success(mock_notify):
    email_recip = f"recip-{uuid4().hex}@example.com"
    email_donor = f"donor-{uuid4().hex}@example.com"
    recip = await create_db_user(email_recip, UserRole.recipient)
    donor = await create_db_user(email_donor, UserRole.donor)
    item = await create_db_item(donor, "Books", status=ItemStatus.reserved)
    req = await create_db_request(item, recip, RequestStatus.approved)

    try:
        async with async_session_factory() as db:
            picked = await request_service.pickup_request(db, req.id, donor)
            assert picked.status == RequestStatus.picked_up
            assert picked.picked_up_at is not None
            
            # Verify item is donated
            updated_item = await db.get(Item, item.id)
            assert updated_item.status == ItemStatus.donated
            assert updated_item.donated_at is not None

            mock_notify.assert_called_once_with(
                donor_email=donor.email,
                donor_name=donor.full_name,
                requester_email=recip.email,
                requester_name=recip.full_name,
                item_title=item.title,
            )
    finally:
        await cleanup_db(email_recip, email_donor)


@pytest.mark.asyncio
async def test_pickup_request_validation_errors():
    email_recip = f"recip-{uuid4().hex}@example.com"
    email_donor1 = f"donor1-{uuid4().hex}@example.com"
    email_donor2 = f"donor2-{uuid4().hex}@example.com"
    recip = await create_db_user(email_recip, UserRole.recipient)
    donor1 = await create_db_user(email_donor1, UserRole.donor)
    donor2 = await create_db_user(email_donor2, UserRole.donor)
    item = await create_db_item(donor1, "Books")
    req = await create_db_request(item, recip, RequestStatus.pending)

    try:
        async with async_session_factory() as db:
            # 1. Not found
            with pytest.raises(HTTPException) as exc_info:
                await request_service.pickup_request(db, -999, donor1)
            assert exc_info.value.status_code == 404

            # 2. Unauthorized (donor2 is not item owner)
            with pytest.raises(HTTPException) as exc_info:
                await request_service.pickup_request(db, req.id, donor2)
            assert exc_info.value.status_code == 403

            # 3. Not approved status
            with pytest.raises(HTTPException) as exc_info:
                await request_service.pickup_request(db, req.id, donor1)
            assert exc_info.value.status_code == 409
    finally:
        await cleanup_db(email_recip, email_donor1, email_donor2)


@pytest.mark.asyncio
async def test_cancel_request_success():
    email_recip = f"recip-{uuid4().hex}@example.com"
    email_donor = f"donor-{uuid4().hex}@example.com"
    recip = await create_db_user(email_recip, UserRole.recipient)
    donor = await create_db_user(email_donor, UserRole.donor)
    item = await create_db_item(donor, "Books")
    req = await create_db_request(item, recip, RequestStatus.pending)

    try:
        async with async_session_factory() as db:
            cancelled = await request_service.cancel_request(db, req.id, recip)
            assert cancelled.status == RequestStatus.cancelled
            assert cancelled.cancelled_at is not None
    finally:
        await cleanup_db(email_recip, email_donor)


@pytest.mark.asyncio
async def test_cancel_request_validation_errors():
    email_recip1 = f"recip1-{uuid4().hex}@example.com"
    email_recip2 = f"recip2-{uuid4().hex}@example.com"
    email_donor = f"donor-{uuid4().hex}@example.com"
    recip1 = await create_db_user(email_recip1, UserRole.recipient)
    recip2 = await create_db_user(email_recip2, UserRole.recipient)
    donor = await create_db_user(email_donor, UserRole.donor)
    item = await create_db_item(donor, "Books")
    req = await create_db_request(item, recip1, RequestStatus.approved)

    try:
        async with async_session_factory() as db:
            # 1. Not found
            with pytest.raises(HTTPException) as exc_info:
                await request_service.cancel_request(db, -999, recip1)
            assert exc_info.value.status_code == 404

            # 2. Unauthorized
            with pytest.raises(HTTPException) as exc_info:
                await request_service.cancel_request(db, req.id, recip2)
            assert exc_info.value.status_code == 403

            # 3. Not pending
            with pytest.raises(HTTPException) as exc_info:
                await request_service.cancel_request(db, req.id, recip1)
            assert exc_info.value.status_code == 409
    finally:
        await cleanup_db(email_recip1, email_recip2, email_donor)


@pytest.mark.asyncio
async def test_get_request_details():
    email_recip = f"recip-{uuid4().hex}@example.com"
    email_donor = f"donor-{uuid4().hex}@example.com"
    email_bystander = f"bystander-{uuid4().hex}@example.com"
    recip = await create_db_user(email_recip, UserRole.recipient)
    donor = await create_db_user(email_donor, UserRole.donor)
    bystander = await create_db_user(email_bystander, UserRole.recipient)
    item = await create_db_item(donor, "Books")
    req = await create_db_request(item, recip, RequestStatus.pending)

    try:
        async with async_session_factory() as db:
            # 1. Not found
            with pytest.raises(HTTPException) as exc_info:
                await request_service.get_request(db, -999, recip)
            assert exc_info.value.status_code == 404

            # 2. Unauthorized bystander
            with pytest.raises(HTTPException) as exc_info:
                await request_service.get_request(db, req.id, bystander)
            assert exc_info.value.status_code == 403

            # 3. Success for requester
            r = await request_service.get_request(db, req.id, recip)
            assert r.id == req.id

            # 4. Success for donor
            r_donor = await request_service.get_request(db, req.id, donor)
            assert r_donor.id == req.id
    finally:
        await cleanup_db(email_recip, email_donor, email_bystander)


@pytest.mark.asyncio
async def test_list_incoming_and_my_requests():
    email_recip = f"recip-{uuid4().hex}@example.com"
    email_donor = f"donor-{uuid4().hex}@example.com"
    recip = await create_db_user(email_recip, UserRole.recipient)
    donor = await create_db_user(email_donor, UserRole.donor)
    item = await create_db_item(donor, "Books")
    await create_db_request(item, recip, RequestStatus.pending)

    try:
        async with async_session_factory() as db:
            # list my requests (recip)
            my_reqs = await request_service.list_my_requests(db, recip)
            assert len(my_reqs) == 1

            # list incoming requests (donor)
            incoming = await request_service.list_incoming_requests(db, donor)
            assert len(incoming) == 1

            # list incoming as non-donor raises 403
            with pytest.raises(HTTPException) as exc_info:
                await request_service.list_incoming_requests(db, recip)
            assert exc_info.value.status_code == 403
    finally:
        await cleanup_db(email_recip, email_donor)


@pytest.mark.asyncio
async def test_request_to_out_privacy():
    email_recip = f"recip-{uuid4().hex}@example.com"
    email_donor = f"donor-{uuid4().hex}@example.com"
    email_bystander = f"bystander-{uuid4().hex}@example.com"
    recip = await create_db_user(email_recip, UserRole.recipient)
    donor = await create_db_user(email_donor, UserRole.donor)
    bystander = await create_db_user(email_bystander, UserRole.recipient)
    item = await create_db_item(donor, "Books")
    req = await create_db_request(item, recip, RequestStatus.pending, ngo_note="Secret Note")

    try:
        async with async_session_factory() as db:
            # Reload to load relationships
            req_loaded = await request_service.get_request(db, req.id, recip)

            # Bystander view
            out_bystander = await request_service.request_to_out(req_loaded, bystander)
            assert out_bystander.donor_phone is None
            assert out_bystander.ngo_note is None

            # Donor view (sees phone + ngo note)
            out_donor = await request_service.request_to_out(req_loaded, donor)
            assert out_donor.donor_phone == donor.phone
            assert out_donor.ngo_note == "Secret Note"

            # Requester view before approval (sees ngo note, phone is hidden)
            out_recip_pending = await request_service.request_to_out(req_loaded, recip)
            assert out_recip_pending.donor_phone is None
            assert out_recip_pending.ngo_note == "Secret Note"

            # Requester view after approval
            req_loaded.status = RequestStatus.approved
            out_recip_approved = await request_service.request_to_out(req_loaded, recip)
            assert out_recip_approved.donor_phone == donor.phone
    finally:
        await cleanup_db(email_recip, email_donor, email_bystander)
