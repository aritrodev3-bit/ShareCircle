import pytest
import jwt
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from fastapi import HTTPException
from sqlalchemy import delete
from app.config import get_settings
from app.database import async_session_factory
from app.models.user import User, UserRole
from app.models.item import Item, ItemCategory, ItemCondition, ItemStatus
from app.models.request import DonationRequest, RequestStatus
from app.schemas.user import UserCreate
from app.schemas.item import ItemCreate, ItemUpdate
from app.schemas.request import RequestCreate
from app.services import auth_service, item_service, request_service, analytics_service, matching_service

async def delete_test_data(email: str = None, item_ids: list[int] = None, request_ids: list[int] = None):
    async with async_session_factory() as session:
        if request_ids:
            await session.execute(delete(DonationRequest).where(DonationRequest.id.in_(request_ids)))
        if item_ids:
            await session.execute(delete(Item).where(Item.id.in_(item_ids)))
        await session.commit()
        if email:
            await session.execute(delete(User).where(User.email == email))
        await session.commit()

class FakeAuthClient:
    async def sign_up(self, user):
        return {"user": {"id": str(uuid4())}}
    async def sign_in_with_password(self, email, password):
        return {"access_token": "dummy_token"}

@pytest.mark.asyncio
async def test_auth_service_coverage():
    # Test extract_supabase_user_id invalid responses
    with pytest.raises(HTTPException) as exc:
        auth_service.extract_supabase_user_id({})
    assert exc.value.status_code == 400

    with pytest.raises(HTTPException) as exc:
        auth_service.extract_supabase_user_id({"user": "not-dict"})
    assert exc.value.status_code == 400

    with pytest.raises(HTTPException) as exc:
        auth_service.extract_supabase_user_id({"user": {"id": ""}})
    assert exc.value.status_code == 400

    # Test read_int_claim invalid formats
    assert auth_service.read_int_claim({}, "user_id") is None
    with pytest.raises(HTTPException) as exc:
        auth_service.read_int_claim({"user_id": "abc"}, "user_id")
    assert exc.value.status_code == 401

    email = f"service-test-{uuid4().hex}@example.com"
    async with async_session_factory() as session:
        user_in = UserCreate(email=email, password="password", full_name="Service User", role="recipient")
        user = await auth_service.create_user(session, user_in, FakeAuthClient())
        assert user.email == email

        # Create again should raise 400
        with pytest.raises(HTTPException) as exc:
            await auth_service.create_user(session, user_in, FakeAuthClient())
        assert exc.value.status_code == 400

    await delete_test_data(email=email)

    # Test decode_access_token invalid/expired
    with pytest.raises(HTTPException) as exc:
        auth_service.decode_access_token("garbage")
    assert exc.value.status_code == 401

    expired_payload = {
        "sub": "user-id",
        "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
    }
    settings = get_settings()
    expired_token = jwt.encode(expired_payload, settings.supabase_jwt_secret, algorithm=settings.jwt_algorithm)
    with pytest.raises(HTTPException) as exc:
        auth_service.decode_access_token(expired_token)
    assert exc.value.status_code == 401

    # authenticate_user email not found
    inactive_email = "inactive@example.com"
    async with async_session_factory() as session:
        with pytest.raises(HTTPException) as exc:
            await auth_service.authenticate_user(session, "nonexistent@example.com", "pw")
        assert exc.value.status_code == 401

        # authenticate_user inactive user
        user = User(supabase_user_id=str(uuid4()), email=inactive_email, hashed_password="pw", full_name="Inactive", role=UserRole.recipient, is_active=False)
        session.add(user)
        await session.commit()
        with pytest.raises(HTTPException) as exc:
            await auth_service.authenticate_user(session, inactive_email, "pw")
        assert exc.value.status_code == 401

    await delete_test_data(email=inactive_email)

    # get_user_from_token
    active_email = "active@example.com"
    async with async_session_factory() as session:
        user = User(supabase_user_id=str(uuid4()), email=active_email, hashed_password="pw", full_name="Active", role=UserRole.recipient, is_active=True)
        session.add(user)
        await session.commit()
        await session.refresh(user)

        token = auth_service.create_access_token(user)
        user_from_token = await auth_service.get_user_from_token(session, token)
        assert user_from_token.id == user.id

        # token inactive user
        user.is_active = False
        await session.commit()
        with pytest.raises(HTTPException) as exc:
            await auth_service.get_user_from_token(session, token)
        assert exc.value.status_code == 401

    await delete_test_data(email=active_email)

@pytest.mark.asyncio
async def test_item_service_coverage():
    email_donor = f"donor-{uuid4().hex}@example.com"
    email_recipient = f"rec-{uuid4().hex}@example.com"
    item_id = None
    async with async_session_factory() as session:
        donor = User(supabase_user_id=str(uuid4()), email=email_donor, hashed_password="pw", full_name="Donor", role=UserRole.donor)
        recipient = User(supabase_user_id=str(uuid4()), email=email_recipient, hashed_password="pw", full_name="Recipient", role=UserRole.recipient)
        session.add_all([donor, recipient])
        await session.commit()
        await session.refresh(donor)
        await session.refresh(recipient)

        # Create item
        item_in = ItemCreate(title="Test Item", description="Desc", category="clothing", condition="new", quantity=1, city="City", pincode="123456")
        item = await item_service.create_item(session, donor, item_in)
        item_id = item.id
        assert item.title == "Test Item"

        # get_item not found
        with pytest.raises(HTTPException) as exc:
            await item_service.get_item(session, 999999)
        assert exc.value.status_code == 404

        # ensure_item_owner not owner
        with pytest.raises(HTTPException) as exc:
            item_service.ensure_item_owner(item, recipient)
        assert exc.value.status_code == 403

        # update_item invalid coordinates
        with pytest.raises(HTTPException) as exc:
            await item_service.update_item(session, item.id, donor, ItemUpdate(lat=12.34))
        assert exc.value.status_code == 422

        # list_items unauthorized mine
        with pytest.raises(HTTPException) as exc:
            await item_service.list_items(session, categories=None, status_filter=None, city=None, condition=None, mine=True, current_user=None, lat=None, lng=None, radius_km=None, page=1, page_size=10)
        assert exc.value.status_code == 401

        # remove_item already removed
        item.status = ItemStatus.removed
        await session.commit()
        with pytest.raises(HTTPException) as exc:
            await item_service.remove_item(session, item.id, donor)
        assert exc.value.status_code == 409

    await delete_test_data(item_ids=[item_id])
    await delete_test_data(email=email_donor)
    await delete_test_data(email=email_recipient)

@pytest.mark.asyncio
@patch("app.worker.tasks.send_pickup_confirmation.delay")
@patch("app.worker.tasks.send_rejection_notification.delay")
@patch("app.worker.tasks.send_approval_notification.delay")
@patch("app.worker.tasks.send_request_notification.delay")
async def test_request_service_coverage(
    mock_request_notification,
    mock_approval_notification,
    mock_rejection_notification,
    mock_pickup_confirmation,
):
    email_donor = f"donor-{uuid4().hex}@example.com"
    email_recipient = f"rec-{uuid4().hex}@example.com"
    item_id = None
    req_id = None
    async with async_session_factory() as session:
        donor = User(supabase_user_id=str(uuid4()), email=email_donor, hashed_password="pw", full_name="Donor", role=UserRole.donor)
        recipient = User(supabase_user_id=str(uuid4()), email=email_recipient, hashed_password="pw", full_name="Recipient", role=UserRole.recipient)
        session.add_all([donor, recipient])
        await session.commit()
        await session.refresh(donor)
        await session.refresh(recipient)

        # Create item
        item_in = ItemCreate(title="Test Item", description="Desc", category="clothing", condition="new", quantity=1, city="City", pincode="123456")
        item = await item_service.create_item(session, donor, item_in)
        item_id = item.id

        # create_request item not found
        with pytest.raises(HTTPException) as exc:
            await request_service.create_request(session, recipient, RequestCreate(item_id=999999, message="interested"))
        assert exc.value.status_code == 404

        # create_request donor role restricted
        with pytest.raises(HTTPException) as exc:
            await request_service.create_request(session, donor, RequestCreate(item_id=item.id, message="interested"))
        assert exc.value.status_code == 403

        # create_request request own item (recipient owns item)
        item.donor_id = recipient.id
        await session.commit()
        with pytest.raises(HTTPException) as exc:
            await request_service.create_request(session, recipient, RequestCreate(item_id=item.id, message="interested"))
        assert exc.value.status_code == 422

        # restore donor_id
        item.donor_id = donor.id
        await session.commit()

        # create_request item not available
        item.status = ItemStatus.removed
        await session.commit()
        with pytest.raises(HTTPException) as exc:
            await request_service.create_request(session, recipient, RequestCreate(item_id=item.id, message="interested"))
        assert exc.value.status_code == 422

        # Restore item to available
        item.status = ItemStatus.available
        await session.commit()

        # create_request success
        req = await request_service.create_request(session, recipient, RequestCreate(item_id=item.id, message="interested"))
        req_id = req.id
        assert req.status == RequestStatus.pending

        # get_request not found
        with pytest.raises(HTTPException) as exc:
            await request_service.get_request(session, 999999, recipient)
        assert exc.value.status_code == 404

        # list_incoming_requests only donors
        with pytest.raises(HTTPException) as exc:
            await request_service.list_incoming_requests(session, recipient)
        assert exc.value.status_code == 403

        # reject_request not found
        with pytest.raises(HTTPException) as exc:
            await request_service.reject_request(session, 999999, donor)
        assert exc.value.status_code == 404

        # approve_request not found
        with pytest.raises(HTTPException) as exc:
            await request_service.approve_request(session, 999999, donor)
        assert exc.value.status_code == 404

        # reject_request not authorized
        with pytest.raises(HTTPException) as exc:
            await request_service.reject_request(session, req.id, recipient)
        assert exc.value.status_code == 403

        # cancel_request not authorized
        with pytest.raises(HTTPException) as exc:
            await request_service.cancel_request(session, req.id, donor)
        assert exc.value.status_code == 403

        # reject_request not pending
        req.status = RequestStatus.approved
        await session.commit()
        with pytest.raises(HTTPException) as exc:
            await request_service.reject_request(session, req.id, donor)
        assert exc.value.status_code == 409

        # cancel_request not pending
        with pytest.raises(HTTPException) as exc:
            await request_service.cancel_request(session, req.id, recipient)
        assert exc.value.status_code == 409

        # approve_request item no longer available
        req.status = RequestStatus.pending
        item.status = ItemStatus.reserved
        await session.commit()
        with pytest.raises(HTTPException) as exc:
            await request_service.approve_request(session, req.id, donor)
        assert exc.value.status_code == 409

        # pickup_request not approved
        req.status = RequestStatus.pending
        await session.commit()
        with pytest.raises(HTTPException) as exc:
            await request_service.pickup_request(session, req.id, donor)
        assert exc.value.status_code == 409

    await delete_test_data(request_ids=[req_id])
    await delete_test_data(item_ids=[item_id])
    await delete_test_data(email=email_donor)
    await delete_test_data(email=email_recipient)

@pytest.mark.asyncio
async def test_analytics_matching_coverage():
    async with async_session_factory() as session:
        await analytics_service.get_summary(session)
        await analytics_service.get_category_breakdown(session)
        await analytics_service.get_donation_trend(session)
        await analytics_service.get_top_cities(session)
        await analytics_service.get_platform_activity(session)

        dummy_user = User(supabase_user_id=str(uuid4()), email=f"match-{uuid4().hex}@example.com", hashed_password="pw", full_name="User", role=UserRole.recipient, preferred_categories=[])
        session.add(dummy_user)
        await session.commit()
        await session.refresh(dummy_user)

        await matching_service.get_suggestions(session, dummy_user, lat=None, lng=None)
        await matching_service.get_suggestions(session, dummy_user, lat=12.34, lng=56.78)

        await delete_test_data(email=dummy_user.email)
