from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.database import async_session_factory
from app.models.item import Item, ItemCategory, ItemCondition, ItemStatus
from app.models.request import DonationRequest, RequestStatus
from app.models.user import User, UserRole
from app.schemas.item import ItemCreate, ItemUpdate
from app.services import auth_service, item_service


async def create_db_user(email: str, role: UserRole = UserRole.donor) -> User:
    async with async_session_factory() as session:
        user = User(
            supabase_user_id=str(uuid4()),
            email=email,
            hashed_password=auth_service.SUPABASE_PASSWORD_SENTINEL,
            full_name="Test Item Service User",
            role=role,
            preferred_categories=[],
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def create_db_item(donor: User, title: str, status: ItemStatus = ItemStatus.available, lat: float | None = None, lng: float | None = None) -> Item:
    async with async_session_factory() as session:
        item = Item(
            donor_id=donor.id,
            title=title,
            description="Description",
            category="books",
            condition="good",
            quantity=1,
            status=status,
            location=item_service.point_from_coordinates(lat, lng),
            city="Bengaluru",
            pincode="560001",
        )
        session.add(item)
        await session.commit()
        await session.refresh(item)
        return item


async def create_db_request(item: Item, requester: User, status: RequestStatus = RequestStatus.pending) -> DonationRequest:
    async with async_session_factory() as session:
        req = DonationRequest(
            item_id=item.id,
            requester_id=requester.id,
            message="Request message",
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
async def test_get_item_not_found_raises_404():
    async with async_session_factory() as db:
        with pytest.raises(HTTPException) as exc_info:
            await item_service.get_item(db, -999)
        assert exc_info.value.status_code == 404
        assert "Item not found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_ensure_item_owner_permission_denied():
    email1 = f"user1-{uuid4().hex}@example.com"
    email2 = f"user2-{uuid4().hex}@example.com"
    user1 = await create_db_user(email1)
    user2 = await create_db_user(email2)
    item = await create_db_item(user1, "Some Title")

    try:
        with pytest.raises(HTTPException) as exc_info:
            item_service.ensure_item_owner(item, user2)
        assert exc_info.value.status_code == 403
        assert "Only the item owner can modify it" in exc_info.value.detail
    finally:
        await cleanup_db(email1, email2)


@pytest.mark.asyncio
async def test_create_item_success():
    email = f"donor-{uuid4().hex}@example.com"
    donor = await create_db_user(email)
    item_in = ItemCreate(
        title="Valid title",
        description="Valid description",
        category=ItemCategory.books,
        condition=ItemCondition.good,
        quantity=2,
        city="Bengaluru",
        pincode="560001",
        lat=12.9716,
        lng=77.5946,
    )

    try:
        async with async_session_factory() as db:
            item = await item_service.create_item(db, donor, item_in)
            assert item.id is not None
            assert item.title == "Valid title"
            assert item.status == ItemStatus.available
            assert item.location is not None
    finally:
        await cleanup_db(email)


@pytest.mark.asyncio
async def test_update_item_lat_lng_validation():
    email = f"donor-{uuid4().hex}@example.com"
    donor = await create_db_user(email)
    item = await create_db_item(donor, "Test Item")

    try:
        async with async_session_factory() as db:
            # 1. Mismatch: latitude set but longitude is None
            update_mismatch = ItemUpdate(lat=12.9716)
            with pytest.raises(HTTPException) as exc_info:
                await item_service.update_item(db, item.id, donor, update_mismatch)
            assert exc_info.value.status_code == 422
            assert "Both lat and lng are required" in exc_info.value.detail

            # 2. Correct update
            update_correct = ItemUpdate(lat=12.9716, lng=77.5946, title="Updated Title")
            updated = await item_service.update_item(db, item.id, donor, update_correct)
            assert updated.title == "Updated Title"
            assert updated.location is not None
    finally:
        await cleanup_db(email)


@pytest.mark.asyncio
async def test_remove_item_success():
    email_donor = f"donor-{uuid4().hex}@example.com"
    email_recip = f"recip-{uuid4().hex}@example.com"
    donor = await create_db_user(email_donor, UserRole.donor)
    recip = await create_db_user(email_recip, UserRole.recipient)
    item = await create_db_item(donor, "Target Item")
    req_pending = await create_db_request(item, recip, RequestStatus.pending)
    req_approved = await create_db_request(item, recip, RequestStatus.approved)

    try:
        async with async_session_factory() as db:
            removed = await item_service.remove_item(db, item.id, donor)
            assert removed.status == ItemStatus.removed
            assert removed.removed_at is not None

            # Verify pending request is cancelled, approved request is rejected
            r_pending = await db.get(DonationRequest, req_pending.id)
            assert r_pending.status == RequestStatus.cancelled

            r_approved = await db.get(DonationRequest, req_approved.id)
            assert r_approved.status == RequestStatus.rejected
    finally:
        await cleanup_db(email_donor, email_recip)


@pytest.mark.asyncio
async def test_remove_item_already_removed_raises_409():
    email = f"donor-{uuid4().hex}@example.com"
    donor = await create_db_user(email)
    item_removed = await create_db_item(donor, "Removed Item", status=ItemStatus.removed)

    try:
        async with async_session_factory() as db:
            with pytest.raises(HTTPException) as exc_info:
                await item_service.remove_item(db, item_removed.id, donor)
            assert exc_info.value.status_code == 409
            assert "cannot be removed" in exc_info.value.detail
    finally:
        await cleanup_db(email)


@pytest.mark.asyncio
async def test_list_items_validation_and_filters():
    email_donor = f"donor-{uuid4().hex}@example.com"
    donor = await create_db_user(email_donor)
    # Bengaluru coordinates
    item_blr = await create_db_item(donor, "Blr Item", lat=12.9716, lng=77.5946)
    # Mysore coordinates (~140km away)
    item_mys = await create_db_item(donor, "Mys Item", lat=12.2958, lng=76.6394)

    try:
        async with async_session_factory() as db:
            # 1. mine=True but current_user is None raises 401
            with pytest.raises(HTTPException) as exc_info:
                await item_service.list_items(
                    db,
                    categories=None,
                    status_filter=None,
                    city=None,
                    condition=None,
                    mine=True,
                    current_user=None,
                    lat=None,
                    lng=None,
                    radius_km=None,
                    page=1,
                    page_size=10,
                )
            assert exc_info.value.status_code == 401

            # 2. Radius check - searching within 50km of Bengaluru should find Blr Item but NOT Mys Item
            res = await item_service.list_items(
                db,
                categories=None,
                status_filter=None,
                city=None,
                condition=None,
                mine=False,
                current_user=None,
                lat=12.9716,
                lng=77.5946,
                radius_km=50.0,
                page=1,
                page_size=10,
            )
            assert any(item.id == item_blr.id for item in res.items)
            assert not any(item.id == item_mys.id for item in res.items)

            # 3. Radius check - searching within 200km should find both
            res_wide = await item_service.list_items(
                db,
                categories=None,
                status_filter=None,
                city=None,
                condition=None,
                mine=False,
                current_user=None,
                lat=12.9716,
                lng=77.5946,
                radius_km=200.0,
                page=1,
                page_size=10,
            )
            assert any(item.id == item_blr.id for item in res_wide.items)
            assert any(item.id == item_mys.id for item in res_wide.items)
    finally:
        await cleanup_db(email_donor)
