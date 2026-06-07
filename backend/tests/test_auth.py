from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from app.config import get_settings
from app.database import async_session_factory
from app.dependencies import require_role
from app.main import create_app
from app.models.user import User, UserRole
from app.schemas.user import UserCreate
from app.services import auth_service


def auth_test_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=create_app()), base_url="http://test")


class FakeSupabaseAuthClient:
    def __init__(self, reject_login: bool = False) -> None:
        self.reject_login = reject_login
        self.signed_up_user_id = str(uuid4())
        self.access_token: str | None = None
        self.sign_up_payloads: list[UserCreate] = []
        self.sign_in_payloads: list[tuple[str, str]] = []

    async def sign_up(self, user: UserCreate) -> dict[str, object]:
        self.sign_up_payloads.append(user)
        return {"user": {"id": self.signed_up_user_id, "email": user.email}}

    async def sign_in_with_password(self, email: str, password: str) -> dict[str, object]:
        self.sign_in_payloads.append((email, password))
        if self.reject_login:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        if self.access_token is None:
            raise HTTPException(status_code=401, detail="Invalid auth response")
        return {"access_token": self.access_token}


async def create_test_user(email: str, role: UserRole = UserRole.recipient, active: bool = True) -> User:
    async with async_session_factory() as session:
        user = User(
            supabase_user_id=str(uuid4()),
            email=email,
            hashed_password=auth_service.SUPABASE_PASSWORD_SENTINEL,
            full_name="Test User",
            role=role,
            preferred_categories=[],
            is_active=active,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def delete_test_users(*emails: str) -> None:
    async with async_session_factory() as session:
        await session.execute(delete(User).where(User.email.in_(emails)))
        await session.commit()


def make_token(user: User, expires_delta: timedelta = timedelta(minutes=30)) -> str:
    settings = get_settings()
    payload = {
        "sub": user.supabase_user_id or user.email,
        "role": user.role.value,
        "user_id": user.id,
        "exp": datetime.now(timezone.utc) + expires_delta,
    }
    return jwt.encode(payload, settings.supabase_jwt_secret, algorithm=settings.jwt_algorithm)


@pytest.mark.asyncio
async def test_register_creates_user_and_delegates_password_to_supabase(monkeypatch):
    email = f"register-{uuid4().hex}@example.com"
    fake_client = FakeSupabaseAuthClient()
    monkeypatch.setattr(auth_service, "create_supabase_auth_client", lambda: fake_client)

    try:
        async with auth_test_client() as client:
            response = await client.post(
                "/api/auth/register",
                json={
                    "email": email,
                    "password": "secure-password",
                    "full_name": "Register User",
                    "role": "donor",
                    "phone": "1234567890",
                },
            )

        assert response.status_code == 201
        assert response.json()["email"] == email
        assert fake_client.sign_up_payloads[0].password == "secure-password"

        async with async_session_factory() as session:
            result = await session.execute(select(User).where(User.email == email))
            user = result.scalar_one()
            assert user.hashed_password == auth_service.SUPABASE_PASSWORD_SENTINEL
            assert user.hashed_password != "secure-password"
            assert user.supabase_user_id == fake_client.signed_up_user_id
            assert user.role is UserRole.donor
    finally:
        await delete_test_users(email)


@pytest.mark.asyncio
async def test_register_duplicate_email_returns_400(monkeypatch):
    email = f"duplicate-{uuid4().hex}@example.com"
    fake_client = FakeSupabaseAuthClient()
    monkeypatch.setattr(auth_service, "create_supabase_auth_client", lambda: fake_client)
    await create_test_user(email)

    try:
        async with auth_test_client() as client:
            response = await client.post(
                "/api/auth/register",
                json={
                    "email": email,
                    "password": "secure-password",
                    "full_name": "Duplicate User",
                    "role": "recipient",
                },
            )

        assert response.status_code == 400
        assert fake_client.sign_up_payloads == []
    finally:
        await delete_test_users(email)


@pytest.mark.asyncio
async def test_login_success_returns_jwt_with_required_claims(monkeypatch):
    email = f"login-{uuid4().hex}@example.com"
    fake_client = FakeSupabaseAuthClient()
    monkeypatch.setattr(auth_service, "create_supabase_auth_client", lambda: fake_client)
    user = await create_test_user(email, role=UserRole.ngo)
    fake_client.access_token = make_token(user)

    try:
        async with auth_test_client() as client:
            response = await client.post(
                "/api/auth/login",
                data={"username": email, "password": "correct-password"},
            )

        assert response.status_code == 200
        token = response.json()["access_token"]
        assert token == fake_client.access_token
        payload = auth_service.decode_access_token(token)
        assert payload["sub"] == user.supabase_user_id
        assert payload["role"] == "ngo"
        assert payload["user_id"] == user.id
        assert "exp" in payload
        assert fake_client.sign_in_payloads == [(email, "correct-password")]
    finally:
        await delete_test_users(email)


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401(monkeypatch):
    email = f"wrong-password-{uuid4().hex}@example.com"
    fake_client = FakeSupabaseAuthClient(reject_login=True)
    monkeypatch.setattr(auth_service, "create_supabase_auth_client", lambda: fake_client)
    await create_test_user(email)

    try:
        async with auth_test_client() as client:
            response = await client.post(
                "/api/auth/login",
                data={"username": email, "password": "wrong-password"},
            )

        assert response.status_code == 401
    finally:
        await delete_test_users(email)


@pytest.mark.asyncio
async def test_me_with_valid_token_returns_current_user():
    email = f"me-{uuid4().hex}@example.com"
    user = await create_test_user(email, role=UserRole.admin)
    token = make_token(user)

    try:
        async with auth_test_client() as client:
            response = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 200
        assert response.json()["email"] == email
        assert response.json()["role"] == "admin"
    finally:
        await delete_test_users(email)


@pytest.mark.asyncio
async def test_me_with_invalid_token_returns_401():
    async with auth_test_client() as client:
        response = await client.get("/api/auth/me", headers={"Authorization": "Bearer invalid-token"})

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_with_expired_token_returns_401():
    email = f"expired-{uuid4().hex}@example.com"
    user = await create_test_user(email)
    token = make_token(user, expires_delta=timedelta(minutes=-1))

    try:
        async with auth_test_client() as client:
            response = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 401
    finally:
        await delete_test_users(email)


@pytest.mark.asyncio
async def test_inactive_user_token_returns_401():
    email = f"inactive-{uuid4().hex}@example.com"
    user = await create_test_user(email, active=False)
    token = make_token(user)

    try:
        async with auth_test_client() as client:
            response = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 401
    finally:
        await delete_test_users(email)


@pytest.mark.asyncio
async def test_preferences_update_persists_valid_categories():
    email = f"preferences-{uuid4().hex}@example.com"
    user = await create_test_user(email)
    token = make_token(user)

    try:
        async with auth_test_client() as client:
            response = await client.patch(
                "/api/auth/me/preferences",
                json={"preferred_categories": ["books", "medical"]},
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 200
        assert response.json()["preferred_categories"] == ["books", "medical"]

        async with async_session_factory() as session:
            result = await session.execute(select(User).where(User.email == email))
            persisted_user = result.scalar_one()
            assert persisted_user.preferred_categories == ["books", "medical"]
    finally:
        await delete_test_users(email)


@pytest.mark.asyncio
async def test_require_role_allows_matching_role_and_rejects_mismatch():
    email = f"role-guard-{uuid4().hex}@example.com"
    user = await create_test_user(email, role=UserRole.donor)
    donor_guard = require_role(UserRole.donor)
    admin_guard = require_role(UserRole.admin)

    try:
        assert await donor_guard(user) is user
        with pytest.raises(HTTPException) as exc_info:
            await admin_guard(user)
        assert exc_info.value.status_code == 403
    finally:
        await delete_test_users(email)
