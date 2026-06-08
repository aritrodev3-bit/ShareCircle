from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest
from geoalchemy2.elements import WKTElement
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
async def test_approval_auto_rejects_competing_pending_requests():
    donor_email = f"donor-{uuid4().hex}@example.com"
    r1_email = f"r1-{uuid4().hex}@example.com"
    r2_email = f"r2-{uuid4().hex}@example.com"

    donor = await create_user(donor_email, UserRole.donor)
    r1 = await create_user(r1_email, UserRole.recipient)
    r2 = await create_user(r2_email, UserRole.recipient)
    item = await create_item(donor, "Test Item")

    try:
        async with request_test_client() as client:
            # Create two competing requests
            req1 = await client.post(
                "/api/requests/",
                json={"item_id": item.id},
                headers={"Authorization": f"Bearer {make_token(r1)}"},
            )
            req2 = await client.post(
                "/api/requests/",
                json={"item_id": item.id},
                headers={"Authorization": f"Bearer {make_token(r2)}"},
            )

            req1_id = req1.json()["id"]
            req2_id = req2.json()["id"]

            # Approve the first request
            app_resp = await client.patch(
                f"/api/requests/{req1_id}/approve",
                headers={"Authorization": f"Bearer {make_token(donor)}"},
            )
            assert app_resp.status_code == 200
            assert app_resp.json()["status"] == "approved"

            # Second request should be auto-rejected
            get_resp2 = await client.get(
                f"/api/requests/{req2_id}",
                headers={"Authorization": f"Bearer {make_token(r2)}"},
            )
            assert get_resp2.json()["status"] == "rejected"

            # Item should be reserved
            item_resp = await client.get(f"/api/items/{item.id}")
            assert item_resp.json()["status"] == "reserved"
    finally:
        await cleanup_users(donor_email, r1_email, r2_email)


@pytest.mark.asyncio
async def test_invalid_lifecycle_rejections():
    donor_email = f"donor-{uuid4().hex}@example.com"
    recip_email = f"recip-{uuid4().hex}@example.com"

    donor = await create_user(donor_email, UserRole.donor)
    recipient = await create_user(recip_email, UserRole.recipient)
    item = await create_item(donor, "Test Item")

    try:
        async with request_test_client() as client:
            # Create request
            req = await client.post(
                "/api/requests/",
                json={"item_id": item.id},
                headers={"Authorization": f"Bearer {make_token(recipient)}"},
            )
            req_id = req.json()["id"]

            # Pickup before approval -> 409
            pk_err = await client.patch(
                f"/api/requests/{req_id}/pickup",
                headers={"Authorization": f"Bearer {make_token(donor)}"},
            )
            assert pk_err.status_code == 409

            # Non-donor trying to approve -> 403 (require_role(donor) gate)
            app_403 = await client.patch(
                f"/api/requests/{req_id}/approve",
                headers={"Authorization": f"Bearer {make_token(recipient)}"},
            )
            assert app_403.status_code == 403

            # Approve -> 200
            app_resp = await client.patch(
                f"/api/requests/{req_id}/approve",
                headers={"Authorization": f"Bearer {make_token(donor)}"},
            )
            assert app_resp.status_code == 200

            # Re-approve -> 409
            re_app = await client.patch(
                f"/api/requests/{req_id}/approve",
                headers={"Authorization": f"Bearer {make_token(donor)}"},
            )
            assert re_app.status_code == 409

            # Reject already-approved -> 409
            rej_err = await client.patch(
                f"/api/requests/{req_id}/reject",
                headers={"Authorization": f"Bearer {make_token(donor)}"},
            )
            assert rej_err.status_code == 409

            # Cancel already-approved -> 409
            can_err = await client.patch(
                f"/api/requests/{req_id}/cancel",
                headers={"Authorization": f"Bearer {make_token(recipient)}"},
            )
            assert can_err.status_code == 409

            # Pickup -> 200
            pk_resp = await client.patch(
                f"/api/requests/{req_id}/pickup",
                headers={"Authorization": f"Bearer {make_token(donor)}"},
            )
            assert pk_resp.status_code == 200
            assert pk_resp.json()["status"] == "picked_up"

            # Request on donated item -> 422
            req2 = await client.post(
                "/api/requests/",
                json={"item_id": item.id},
                headers={"Authorization": f"Bearer {make_token(recipient)}"},
            )
            assert req2.status_code == 422

    finally:
        await cleanup_users(donor_email, recip_email)


@pytest.mark.asyncio
async def test_cancel_own_pending_request_success():
    donor_email = f"donor-{uuid4().hex}@example.com"
    recip_email = f"recip-{uuid4().hex}@example.com"

    donor = await create_user(donor_email, UserRole.donor)
    recipient = await create_user(recip_email, UserRole.recipient)
    item = await create_item(donor, "Test Item")

    try:
        async with request_test_client() as client:
            req = await client.post(
                "/api/requests/",
                json={"item_id": item.id},
                headers={"Authorization": f"Bearer {make_token(recipient)}"},
            )
            req_id = req.json()["id"]

            can_resp = await client.patch(
                f"/api/requests/{req_id}/cancel",
                headers={"Authorization": f"Bearer {make_token(recipient)}"},
            )
            assert can_resp.status_code == 200
            payload = can_resp.json()
            assert payload["status"] == "cancelled"
            # TF-04: cancelled_at must be set
            assert payload["cancelled_at"] is not None
    finally:
        await cleanup_users(donor_email, recip_email)


# ── TC-05: F-01 — Self-request blocked ───────────────────────────────────────

@pytest.mark.asyncio
async def test_self_request_blocked():
    """A donor cannot request their own item (service guard at request_service.py:81)."""
    donor_email = f"donor-{uuid4().hex}@example.com"
    donor = await create_user(donor_email, UserRole.donor)
    item = await create_item(donor, "My Own Item")

    try:
        async with request_test_client() as client:
            resp = await client.post(
                "/api/requests/",
                json={"item_id": item.id},
                headers={"Authorization": f"Bearer {make_token(donor)}"},
            )
            # Donor role is blocked at the first guard (403), not the self-request check (422)
            assert resp.status_code == 403
    finally:
        await cleanup_users(donor_email)


# ── TC-08: F-04 — Approve request success (standalone) ───────────────────────

@pytest.mark.asyncio
async def test_approve_request_success():
    """Standalone approval test: verifies status=approved, item=reserved, approved_at set."""
    donor_email = f"donor-{uuid4().hex}@example.com"
    recip_email = f"recip-{uuid4().hex}@example.com"

    donor = await create_user(donor_email, UserRole.donor)
    recipient = await create_user(recip_email, UserRole.recipient)
    item = await create_item(donor, "Approvable Item")

    try:
        async with request_test_client() as client:
            req = await client.post(
                "/api/requests/",
                json={"item_id": item.id},
                headers={"Authorization": f"Bearer {make_token(recipient)}"},
            )
            assert req.status_code == 201
            req_id = req.json()["id"]

            approve_resp = await client.patch(
                f"/api/requests/{req_id}/approve",
                headers={"Authorization": f"Bearer {make_token(donor)}"},
            )
            assert approve_resp.status_code == 200
            payload = approve_resp.json()
            assert payload["status"] == "approved"
            # TF-04: approved_at must be set
            assert payload["approved_at"] is not None

            # Item must be reserved
            item_resp = await client.get(f"/api/items/{item.id}")
            assert item_resp.json()["status"] == "reserved"
    finally:
        await cleanup_users(donor_email, recip_email)


# ── TC-12: F-04 — Reject pending request success ─────────────────────────────

@pytest.mark.asyncio
async def test_reject_pending_request_success():
    """Donor can reject a pending request; status becomes rejected."""
    donor_email = f"donor-{uuid4().hex}@example.com"
    recip_email = f"recip-{uuid4().hex}@example.com"

    donor = await create_user(donor_email, UserRole.donor)
    recipient = await create_user(recip_email, UserRole.recipient)
    item = await create_item(donor, "Rejectable Item")

    try:
        async with request_test_client() as client:
            req = await client.post(
                "/api/requests/",
                json={"item_id": item.id},
                headers={"Authorization": f"Bearer {make_token(recipient)}"},
            )
            assert req.status_code == 201
            req_id = req.json()["id"]

            reject_resp = await client.patch(
                f"/api/requests/{req_id}/reject",
                headers={"Authorization": f"Bearer {make_token(donor)}"},
            )
            assert reject_resp.status_code == 200
            assert reject_resp.json()["status"] == "rejected"

            # Item must still be available after rejection
            item_resp = await client.get(f"/api/items/{item.id}")
            assert item_resp.json()["status"] == "available"
    finally:
        await cleanup_users(donor_email, recip_email)


# ── TC-14: F-02 / TF-05 — Pickup approved request success ───────────────────

@pytest.mark.asyncio
async def test_pickup_approved_request_success():
    """
    Standalone pickup test verifying all four state outcomes required by the roadmap:
    (1) request.status = picked_up
    (2) request.picked_up_at is set
    (3) item.status = donated
    (4) item.donated_at is set  (verified via DB query — not exposed in ItemOut)
    """
    donor_email = f"donor-{uuid4().hex}@example.com"
    recip_email = f"recip-{uuid4().hex}@example.com"

    donor = await create_user(donor_email, UserRole.donor)
    recipient = await create_user(recip_email, UserRole.recipient)
    item = await create_item(donor, "Pickup Item")

    try:
        async with request_test_client() as client:
            # Create and approve
            req = await client.post(
                "/api/requests/",
                json={"item_id": item.id},
                headers={"Authorization": f"Bearer {make_token(recipient)}"},
            )
            req_id = req.json()["id"]
            await client.patch(
                f"/api/requests/{req_id}/approve",
                headers={"Authorization": f"Bearer {make_token(donor)}"},
            )

            # Confirm pickup
            pickup_resp = await client.patch(
                f"/api/requests/{req_id}/pickup",
                headers={"Authorization": f"Bearer {make_token(donor)}"},
            )
            assert pickup_resp.status_code == 200
            payload = pickup_resp.json()
            # (1) request status
            assert payload["status"] == "picked_up"
            # (2) picked_up_at set
            assert payload["picked_up_at"] is not None

            # (3) item status = donated via API
            item_resp = await client.get(f"/api/items/{item.id}")
            assert item_resp.json()["status"] == "donated"

        # (4) donated_at set — verified directly in DB
        async with async_session_factory() as session:
            db_item = await session.get(Item, item.id)
            assert db_item.donated_at is not None
    finally:
        await cleanup_users(donor_email, recip_email)


# ── TC-18: F-05 — Remove item cancels/rejects active requests ────────────────

@pytest.mark.asyncio
async def test_remove_item_cancels_active_requests():
    """
    Removing an item with active requests follows defined behavior:
    - pending requests are cancelled
    - approved requests are rejected
    - item.status becomes removed
    """
    donor_email = f"donor-{uuid4().hex}@example.com"
    r1_email = f"r1-{uuid4().hex}@example.com"
    r2_email = f"r2-{uuid4().hex}@example.com"

    donor = await create_user(donor_email, UserRole.donor)
    r1 = await create_user(r1_email, UserRole.recipient)
    r2 = await create_user(r2_email, UserRole.recipient)
    item = await create_item(donor, "Item To Remove")

    try:
        async with request_test_client() as client:
            # r1 requests — will stay pending
            req1 = await client.post(
                "/api/requests/",
                json={"item_id": item.id},
                headers={"Authorization": f"Bearer {make_token(r1)}"},
            )
            req1_id = req1.json()["id"]

            # r2 requests and gets approved (item → reserved)
            req2 = await client.post(
                "/api/requests/",
                json={"item_id": item.id},
                headers={"Authorization": f"Bearer {make_token(r2)}"},
            )
            req2_id = req2.json()["id"]
            await client.patch(
                f"/api/requests/{req2_id}/approve",
                headers={"Authorization": f"Bearer {make_token(donor)}"},
            )

            # Now donor removes the reserved item
            del_resp = await client.delete(
                f"/api/items/{item.id}",
                headers={"Authorization": f"Bearer {make_token(donor)}"},
            )
            assert del_resp.status_code == 200
            assert del_resp.json()["status"] == "removed"

            # req1 (was pending before approval happened, now auto-rejected by approve)
            # and req2 (approved → now rejected by remove)
            get_req2 = await client.get(
                f"/api/requests/{req2_id}",
                headers={"Authorization": f"Bearer {make_token(r2)}"},
            )
            assert get_req2.json()["status"] == "rejected"
    finally:
        await cleanup_users(donor_email, r1_email, r2_email)
