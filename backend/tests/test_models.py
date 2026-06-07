from uuid import uuid4

import pytest
from geoalchemy2.elements import WKTElement
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from app.database import async_session_factory
from app.models import (
    DonationRequest,
    Item,
    ItemCategory,
    ItemCondition,
    ItemStatus,
    RequestStatus,
    User,
    UserRole,
)


@pytest.mark.asyncio
async def test_models_persist_round_trip_and_load_relationships():
    unique_id = uuid4().hex
    donor_email = f"donor-{unique_id}@example.com"
    requester_email = f"requester-{unique_id}@example.com"

    async with async_session_factory() as session:
        donor = User(
            supabase_user_id=str(uuid4()),
            email=donor_email,
            hashed_password="hashed-donor-password",
            full_name="Donor User",
            role=UserRole.donor,
            phone="1111111111",
            preferred_categories=[ItemCategory.books.value],
        )
        requester = User(
            supabase_user_id=str(uuid4()),
            email=requester_email,
            hashed_password="hashed-requester-password",
            full_name="Requester User",
            role=UserRole.recipient,
            preferred_categories=[ItemCategory.clothing.value],
        )
        session.add_all([donor, requester])
        await session.flush()

        item = Item(
            donor_id=donor.id,
            title="Study desk",
            description="A sturdy desk for students.",
            category=ItemCategory.furniture,
            condition=ItemCondition.good,
            quantity=2,
            status=ItemStatus.available,
            location=WKTElement("POINT(77.5946 12.9716)", srid=4326),
            city="Bengaluru",
            pincode="560001",
        )
        session.add(item)
        await session.flush()

        donation_request = DonationRequest(
            item_id=item.id,
            requester_id=requester.id,
            message="This would help our study center.",
            status=RequestStatus.pending,
        )
        session.add(donation_request)
        await session.commit()

    try:
        async with async_session_factory() as session:
            donor_result = await session.execute(
                select(User)
                .where(User.email == donor_email)
                .options(selectinload(User.items))
            )
            persisted_donor = donor_result.scalar_one()

            requester_result = await session.execute(
                select(User)
                .where(User.email == requester_email)
                .options(selectinload(User.requests))
            )
            persisted_requester = requester_result.scalar_one()

            item_result = await session.execute(
                select(Item)
                .where(Item.title == "Study desk")
                .options(selectinload(Item.donor), selectinload(Item.requests))
            )
            persisted_item = item_result.scalar_one()

            request_result = await session.execute(
                select(DonationRequest)
                .where(DonationRequest.item_id == persisted_item.id)
                .options(
                    selectinload(DonationRequest.item),
                    selectinload(DonationRequest.requester),
                )
            )
            persisted_request = request_result.scalar_one()

            assert persisted_donor.items[0].title == "Study desk"
            assert persisted_requester.requests[0].status is RequestStatus.pending
            assert persisted_item.donor.email == donor_email
            assert persisted_item.requests[0].message == "This would help our study center."
            assert persisted_request.item.title == "Study desk"
            assert persisted_request.requester.email == requester_email
            assert persisted_item.created_at.tzinfo is not None
            assert persisted_item.updated_at.tzinfo is not None
            assert persisted_request.created_at.tzinfo is not None
    finally:
        async with async_session_factory() as session:
            donor_ids = select(User.id).where(User.email.in_([donor_email, requester_email]))
            await session.execute(
                delete(DonationRequest).where(DonationRequest.requester_id.in_(donor_ids))
            )
            await session.execute(delete(Item).where(Item.title == "Study desk"))
            await session.execute(delete(User).where(User.email.in_([donor_email, requester_email])))
            await session.commit()


def test_quantity_is_item_metadata_not_request_fulfillment_state():
    item_columns = set(Item.__table__.columns.keys())
    request_columns = set(DonationRequest.__table__.columns.keys())

    assert "quantity" in item_columns
    assert "quantity" not in request_columns
    assert "fulfilled_quantity" not in request_columns
    assert "remaining_quantity" not in item_columns
