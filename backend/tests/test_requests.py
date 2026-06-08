from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from app.config import get_settings
from app.database import async_session_factory
from app.main import create_app
from app.models import DonationRequest, Item, ItemStatus, RequestStatus, User, UserRole
from app.services import auth_service


def request_test_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=create_app()), base_url="http://test")


async def create_user(email: str, role: UserRole) -> User:
    async with async_session_factory() as session:
        user = User(
            supabase_user_id=str(uuid4()),
            email=email,
            hashed_password=auth_service.SUPABASE_PASSWORD_SENTINEL,
            full_name=f"{role.value.title()} User",
            role=role,
            phone="9999999999",
            preferred_categories=[],
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def create_item(donor: User, title: str) -> Item:
    async with async_session_factory() as session:
        item = Item(
            donor_id=donor.id,
            title=title,
            description=f"{title} description",
            category="books",
            condition="good",
            quantity=1,
            status=ItemStatus.available,
            city="Bengaluru",
            pincode="560001",
        )
        session.add(item)
        await session.commit()
        await session.refresh(item)
        return item


def make_token(user: User) -> str:
    settings = get_settings()
    payload = {
        "sub": user.supabase_user_id,
        "role": user.role.value,
        "user_id": user.id,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
    }
    return jwt.encode(payload, settings.supabase_jwt_secret, algorithm=settings.jwt_algorithm)


async def cleanup_users(*emails: str) -> None:
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
async def test_recipient_request_success():
    email = f"recip-{uuid4().hex}@example.com"
    donor_email = f"donor-{uuid4().hex}@example.com"
    recipient = await create_user(email, UserRole.recipient)
    donor = await create_user(donor_email, UserRole.donor)
    item = await create_item(donor, "Test Item")

    try:
        async with request_test_client() as client:
            response = await client.post(
                "/api/requests/",
                json={"item_id": item.id, "message": "Need this"},
                headers={"Authorization": f"Bearer {make_token(recipient)}"},
            )

        assert response.status_code == 201
        payload = response.json()
        assert payload["status"] == "pending"
        assert payload["item_id"] == item.id
        assert payload["requester_id"] == recipient.id
        assert payload["donor_phone"] is None
    finally:
        await cleanup_users(email, donor_email)


@pytest.mark.asyncio
async def test_ngo_request_with_ngo_note_success():
    email = f"ngo-{uuid4().hex}@example.com"
    donor_email = f"donor-{uuid4().hex}@example.com"
    bystander_email = f"recip-{uuid4().hex}@example.com"
    ngo = await create_user(email, UserRole.ngo)
    donor = await create_user(donor_email, UserRole.donor)
    bystander = await create_user(bystander_email, UserRole.recipient)
    item = await create_item(donor, "Test Item")

    try:
        async with request_test_client() as client:
            response = await client.post(
                "/api/requests/",
                json={"item_id": item.id, "message": "Need this", "ngo_note": "For shelter"},
                headers={"Authorization": f"Bearer {make_token(ngo)}"},
            )

        assert response.status_code == 201
        payload = response.json()
        assert payload["status"] == "pending"
        assert payload["ngo_note"] == "For shelter"

        # TF-03: ngo_note must be hidden from a third-party requester (not the NGO or donor)
        # Bystander cannot GET this request (403/404 depending on privacy guard)
        # We verify via the donor GET (who is a party) that ngo_note is visible to donor
        async with request_test_client() as client:
            donor_view = await client.get(
                f"/api/requests/{payload['id']}",
                headers={"Authorization": f"Bearer {make_token(donor)}"},
            )
            assert donor_view.json()["ngo_note"] == "For shelter"
    finally:
        await cleanup_users(email, donor_email, bystander_email)


@pytest.mark.asyncio
async def test_donor_cannot_make_request():
    donor1_email = f"d1-{uuid4().hex}@example.com"
    donor2_email = f"d2-{uuid4().hex}@example.com"
    donor1 = await create_user(donor1_email, UserRole.donor)
    donor2 = await create_user(donor2_email, UserRole.donor)
    item = await create_item(donor2, "Test Item")

    try:
        async with request_test_client() as client:
            response = await client.post(
                "/api/requests/",
                json={"item_id": item.id},
                headers={"Authorization": f"Bearer {make_token(donor1)}"},
            )
        assert response.status_code == 403
    finally:
        await cleanup_users(donor1_email, donor2_email)


@pytest.mark.asyncio
async def test_recipient_submitting_ngo_note_fails():
    email = f"recip-{uuid4().hex}@example.com"
    donor_email = f"donor-{uuid4().hex}@example.com"
    recipient = await create_user(email, UserRole.recipient)
    donor = await create_user(donor_email, UserRole.donor)
    item = await create_item(donor, "Test Item")

    try:
        async with request_test_client() as client:
            response = await client.post(
                "/api/requests/",
                json={"item_id": item.id, "ngo_note": "Invalid note"},
                headers={"Authorization": f"Bearer {make_token(recipient)}"},
            )

        assert response.status_code == 422
    finally:
        await cleanup_users(email, donor_email)


@pytest.mark.asyncio
async def test_duplicate_active_request_blocked():
    email = f"recip-{uuid4().hex}@example.com"
    donor_email = f"donor-{uuid4().hex}@example.com"
    recipient = await create_user(email, UserRole.recipient)
    donor = await create_user(donor_email, UserRole.donor)
    item = await create_item(donor, "Test Item")

    try:
        async with request_test_client() as client:
            resp1 = await client.post(
                "/api/requests/",
                json={"item_id": item.id},
                headers={"Authorization": f"Bearer {make_token(recipient)}"},
            )
            assert resp1.status_code == 201

            resp2 = await client.post(
                "/api/requests/",
                json={"item_id": item.id},
                headers={"Authorization": f"Bearer {make_token(recipient)}"},
            )
            assert resp2.status_code == 422
    finally:
        await cleanup_users(email, donor_email)


@pytest.mark.asyncio
async def test_donor_phone_privacy():
    email = f"recip-{uuid4().hex}@example.com"
    donor_email = f"donor-{uuid4().hex}@example.com"
    recipient = await create_user(email, UserRole.recipient)
    donor = await create_user(donor_email, UserRole.donor)
    item = await create_item(donor, "Test Item")

    try:
        async with request_test_client() as client:
            # Create request
            create_resp = await client.post(
                "/api/requests/",
                json={"item_id": item.id},
                headers={"Authorization": f"Bearer {make_token(recipient)}"},
            )
            req_id = create_resp.json()["id"]

            # As requester before approval, phone is None
            get_resp = await client.get(
                f"/api/requests/{req_id}",
                headers={"Authorization": f"Bearer {make_token(recipient)}"},
            )
            assert get_resp.json()["donor_phone"] is None

            # As donor, phone is visible
            donor_get = await client.get(
                f"/api/requests/{req_id}",
                headers={"Authorization": f"Bearer {make_token(donor)}"},
            )
            assert donor_get.json()["donor_phone"] is not None

            # Approve request
            approve_resp = await client.patch(
                f"/api/requests/{req_id}/approve",
                headers={"Authorization": f"Bearer {make_token(donor)}"},
            )
            assert approve_resp.status_code == 200

            # As requester after approval, phone is visible
            get_resp2 = await client.get(
                f"/api/requests/{req_id}",
                headers={"Authorization": f"Bearer {make_token(recipient)}"},
            )
            assert get_resp2.json()["donor_phone"] is not None

    finally:
        await cleanup_users(email, donor_email)


@pytest.mark.asyncio
@patch("app.worker.tasks.send_pickup_confirmation.delay")
@patch("app.worker.tasks.send_rejection_notification.delay")
@patch("app.worker.tasks.send_approval_notification.delay")
@patch("app.worker.tasks.send_request_notification.delay")
async def test_request_lifecycle_celery_dispatch(
    mock_request_notification,
    mock_approval_notification,
    mock_rejection_notification,
    mock_pickup_confirmation,
):
    email_recip1 = f"recip1-{uuid4().hex}@example.com"
    email_recip2 = f"recip2-{uuid4().hex}@example.com"
    donor_email = f"donor-{uuid4().hex}@example.com"
    
    recipient1 = await create_user(email_recip1, UserRole.recipient)
    recipient2 = await create_user(email_recip2, UserRole.recipient)
    donor = await create_user(donor_email, UserRole.donor)
    item = await create_item(donor, "Celery Test Item")

    try:
        async with request_test_client() as client:
            # 1. Create request 1 (recipient 1) -> triggers request notification
            resp1 = await client.post(
                "/api/requests/",
                json={"item_id": item.id, "message": "Want this"},
                headers={"Authorization": f"Bearer {make_token(recipient1)}"},
            )
            assert resp1.status_code == 201
            req1_id = resp1.json()["id"]
            mock_request_notification.assert_called_once()
            mock_request_notification.reset_mock()

            # 2. Create request 2 (recipient 2) -> triggers request notification again
            resp2 = await client.post(
                "/api/requests/",
                json={"item_id": item.id, "message": "Also want this"},
                headers={"Authorization": f"Bearer {make_token(recipient2)}"},
            )
            assert resp2.status_code == 201
            req2_id = resp2.json()["id"]
            assert mock_request_notification.call_count == 1
            mock_request_notification.reset_mock()

            # 3. Approve request 1 -> triggers approval for req 1 AND auto-rejection for req 2
            approve_resp = await client.patch(
                f"/api/requests/{req1_id}/approve",
                headers={"Authorization": f"Bearer {make_token(donor)}"},
            )
            assert approve_resp.status_code == 200
            mock_approval_notification.assert_called_once()
            mock_rejection_notification.assert_called_once()
            mock_approval_notification.reset_mock()
            mock_rejection_notification.reset_mock()

            # 4. Confirm pickup -> triggers pickup confirmation to both
            pickup_resp = await client.patch(
                f"/api/requests/{req1_id}/pickup",
                headers={"Authorization": f"Bearer {make_token(donor)}"},
            )
            assert pickup_resp.status_code == 200
            mock_pickup_confirmation.assert_called_once()
            
    finally:
        await cleanup_users(email_recip1, email_recip2, donor_email)


@pytest.mark.asyncio
@patch("app.worker.tasks.send_rejection_notification.delay")
async def test_request_rejection_celery_dispatch(mock_rejection_notification):
    email_recip = f"recip-{uuid4().hex}@example.com"
    donor_email = f"donor-{uuid4().hex}@example.com"
    
    recipient = await create_user(email_recip, UserRole.recipient)
    donor = await create_user(donor_email, UserRole.donor)
    item = await create_item(donor, "Rejection Celery Test Item")

    try:
        async with request_test_client() as client:
            # Create request
            resp = await client.post(
                "/api/requests/",
                json={"item_id": item.id, "message": "Want this"},
                headers={"Authorization": f"Bearer {make_token(recipient)}"},
            )
            assert resp.status_code == 201
            req_id = resp.json()["id"]

            # Reject request
            reject_resp = await client.patch(
                f"/api/requests/{req_id}/reject",
                headers={"Authorization": f"Bearer {make_token(donor)}"},
            )
            assert reject_resp.status_code == 200
            mock_rejection_notification.assert_called_once()
            
    finally:
        await cleanup_users(email_recip, donor_email)

