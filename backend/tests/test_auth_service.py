from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

import jwt
import pytest
from fastapi import HTTPException
from sqlalchemy import delete, select

from app.config import get_settings
from app.database import async_session_factory
from app.models.user import User, UserRole
from app.models.item import ItemCategory
from app.schemas.user import UserCreate
from app.services import auth_service


class MockAuthClient:
    def __init__(self, signup_response=None, signin_response=None, fail_signup=False, fail_signin=False):
        self.signup_response = signup_response
        self.signin_response = signin_response
        self.fail_signup = fail_signup
        self.fail_signin = fail_signin

    async def sign_up(self, user: UserCreate) -> dict:
        if self.fail_signup:
            raise HTTPException(status_code=400, detail="Supabase registration failed")
        return self.signup_response or {"user": {"id": str(uuid4()), "email": user.email}}

    async def sign_in_with_password(self, email: str, password: str) -> dict:
        if self.fail_signin:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        return self.signin_response or {"access_token": "mock-token"}


async def create_db_user(email: str, role: UserRole = UserRole.recipient, active: bool = True, supabase_user_id: str | None = "DEFAULT") -> User:
    if supabase_user_id == "DEFAULT":
        supabase_user_id = str(uuid4())
    async with async_session_factory() as session:
        user = User(
            supabase_user_id=supabase_user_id,
            email=email,
            hashed_password=auth_service.SUPABASE_PASSWORD_SENTINEL,
            full_name="Test Auth Service User",
            role=role,
            preferred_categories=[],
            is_active=active,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def cleanup_db(*emails: str) -> None:
    async with async_session_factory() as session:
        await session.execute(delete(User).where(User.email.in_(emails)))
        await session.commit()


def make_jwt(payload_overrides: dict) -> str:
    settings = get_settings()
    payload = {
        "sub": str(uuid4()),
        "role": "recipient",
        "user_id": 1,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
    }
    payload.update(payload_overrides)
    return jwt.encode(payload, settings.supabase_jwt_secret, algorithm=settings.jwt_algorithm)


@pytest.mark.asyncio
async def test_create_user_success():
    email = f"auth-create-{uuid4().hex}@example.com"
    user_in = UserCreate(
        email=email,
        password="password123",
        full_name="Created User",
        role=UserRole.donor,
        phone="123456",
    )
    sb_id = str(uuid4())
    client = MockAuthClient(signup_response={"user": {"id": sb_id, "email": email}})

    try:
        async with async_session_factory() as db:
            user = await auth_service.create_user(db, user_in, auth_client=client)
            assert user.id is not None
            assert user.email == email
            assert user.supabase_user_id == sb_id
            assert user.role == UserRole.donor
    finally:
        await cleanup_db(email)


@pytest.mark.asyncio
async def test_create_user_duplicate_email_raises_400():
    email = f"auth-dup-{uuid4().hex}@example.com"
    await create_db_user(email)
    user_in = UserCreate(
        email=email,
        password="password123",
        full_name="Created User",
        role=UserRole.donor,
    )
    client = MockAuthClient()

    try:
        async with async_session_factory() as db:
            with pytest.raises(HTTPException) as exc_info:
                await auth_service.create_user(db, user_in, auth_client=client)
            assert exc_info.value.status_code == 400
            assert "Email already registered" in exc_info.value.detail
    finally:
        await cleanup_db(email)


@pytest.mark.asyncio
async def test_create_user_extract_id_errors():
    # 1. User payload not a dict
    with pytest.raises(HTTPException) as exc_info:
        auth_service.extract_supabase_user_id({"user": None})
    assert exc_info.value.status_code == 400

    # 2. Subabase user id missing or not str
    with pytest.raises(HTTPException) as exc_info:
        auth_service.extract_supabase_user_id({"user": {"id": None}})
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_authenticate_user_errors():
    email = f"auth-login-{uuid4().hex}@example.com"
    user = await create_db_user(email, role=UserRole.recipient)

    try:
        async with async_session_factory() as db:
            # 1. Invalid email
            with pytest.raises(HTTPException) as exc_info:
                await auth_service.authenticate_user(db, "nonexistent@example.com", "password")
            assert exc_info.value.status_code == 401
            assert "Invalid email or password" in exc_info.value.detail

            # 2. Inactive user
            inactive_email = f"inactive-login-{uuid4().hex}@example.com"
            await create_db_user(inactive_email, active=False)
            with pytest.raises(HTTPException) as exc_info:
                await auth_service.authenticate_user(db, inactive_email, "password")
            assert exc_info.value.status_code == 401
            assert "Inactive user" in exc_info.value.detail
            await cleanup_db(inactive_email)

            # 3. Invalid auth response (token empty/missing)
            client_invalid = MockAuthClient(signin_response={"access_token": None})
            with pytest.raises(HTTPException) as exc_info:
                await auth_service.authenticate_user(db, email, "password", auth_client=client_invalid)
            assert exc_info.value.status_code == 401
            assert "Invalid auth response" in exc_info.value.detail

            # 4. Token subject mismatch
            token_sub_mismatch = make_jwt({"sub": "wrong-sub", "user_id": user.id, "role": user.role.value})
            client_sub = MockAuthClient(signin_response={"access_token": token_sub_mismatch})
            with pytest.raises(HTTPException) as exc_info:
                await auth_service.authenticate_user(db, email, "password", auth_client=client_sub)
            assert exc_info.value.status_code == 401
            assert "Invalid token" in exc_info.value.detail

            # 5. Token user_id mismatch
            token_user_mismatch = make_jwt({"sub": user.supabase_user_id, "user_id": -99, "role": user.role.value})
            client_user = MockAuthClient(signin_response={"access_token": token_user_mismatch})
            with pytest.raises(HTTPException) as exc_info:
                await auth_service.authenticate_user(db, email, "password", auth_client=client_user)
            assert exc_info.value.status_code == 401

            # 6. Token role mismatch
            token_role_mismatch = make_jwt({"sub": user.supabase_user_id, "user_id": user.id, "role": "donor"})
            client_role = MockAuthClient(signin_response={"access_token": token_role_mismatch})
            with pytest.raises(HTTPException) as exc_info:
                await auth_service.authenticate_user(db, email, "password", auth_client=client_role)
            assert exc_info.value.status_code == 401
    finally:
        await cleanup_db(email)


@pytest.mark.asyncio
async def test_decode_access_token_errors():
    settings = get_settings()

    # 1. Expired token
    expired_token = jwt.encode(
        {"sub": "123", "exp": datetime.now(timezone.utc) - timedelta(minutes=5)},
        settings.supabase_jwt_secret,
        algorithm=settings.jwt_algorithm
    )
    with pytest.raises(HTTPException) as exc_info:
        auth_service.decode_access_token(expired_token)
    assert exc_info.value.status_code == 401
    assert "Token expired" in exc_info.value.detail

    # 2. Invalid token signature
    invalid_token = jwt.encode(
        {"sub": "123"},
        "wrong-secret",
        algorithm=settings.jwt_algorithm
    )
    with pytest.raises(HTTPException) as exc_info:
        auth_service.decode_access_token(invalid_token)
    assert exc_info.value.status_code == 401
    assert "Invalid token" in exc_info.value.detail

    # 3. Missing sub claim
    missing_sub = jwt.encode(
        {"exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        settings.supabase_jwt_secret,
        algorithm=settings.jwt_algorithm
    )
    with pytest.raises(HTTPException) as exc_info:
        auth_service.decode_access_token(missing_sub)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_read_int_claim_exceptions():
    # 1. Non-integer format claim
    payload = {"user_id": "not-an-integer"}
    with pytest.raises(HTTPException) as exc_info:
        auth_service.read_int_claim(payload, "user_id")
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_user_from_token_errors():
    email = f"auth-token-{uuid4().hex}@example.com"
    user = await create_db_user(email, role=UserRole.recipient)

    try:
        async with async_session_factory() as db:
            # 1. Token subject not found in DB
            token_unknown_sub = make_jwt({"sub": "unknown-sub", "user_id": -1})
            with pytest.raises(HTTPException) as exc_info:
                await auth_service.get_user_from_token(db, token_unknown_sub)
            assert exc_info.value.status_code == 401

            # 2. Inactive user from token
            inactive_email = f"inactive-token-{uuid4().hex}@example.com"
            inactive_user = await create_db_user(inactive_email, active=False)
            token_inactive = make_jwt({"sub": inactive_user.supabase_user_id, "user_id": inactive_user.id})
            with pytest.raises(HTTPException) as exc_info:
                await auth_service.get_user_from_token(db, token_inactive)
            assert exc_info.value.status_code == 401
            await cleanup_db(inactive_email)

            # 3. User email as subject success fallback
            email_fallback = f"fallback-{uuid4().hex}@example.com"
            user_fallback = await create_db_user(email_fallback, supabase_user_id=None)
            token_email_sub = make_jwt({"sub": email_fallback, "user_id": user_fallback.id})
            res_user = await auth_service.get_user_from_token(db, token_email_sub)
            assert res_user.id == user_fallback.id
            await cleanup_db(email_fallback)
    finally:
        await cleanup_db(email)


@pytest.mark.asyncio
async def test_update_preferences_success():
    email = f"auth-prefs-{uuid4().hex}@example.com"
    user = await create_db_user(email)

    try:
        async with async_session_factory() as db:
            db.add(user)  # attach to session
            updated = await auth_service.update_preferences(db, user, [ItemCategory.clothing, ItemCategory.books])
            assert updated.preferred_categories == ["clothing", "books"]
    finally:
        await cleanup_db(email)
