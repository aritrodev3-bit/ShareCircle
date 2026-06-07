from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import jwt
from fastapi import HTTPException, status
from jwt import ExpiredSignatureError, InvalidTokenError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.item import ItemCategory
from app.models.user import User, UserRole
from app.schemas.user import UserCreate

SUPABASE_PASSWORD_SENTINEL = "supabase_auth_managed"


class SupabaseAuthClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.auth_url = f"{str(settings.supabase_url).rstrip('/')}/auth/v1"
        self.headers = {
            "apikey": settings.supabase_anon_key,
            "Content-Type": "application/json",
        }

    async def sign_up(self, user: UserCreate) -> dict[str, Any]:
        payload = {
            "email": user.email,
            "password": user.password,
            "data": {
                "full_name": user.full_name,
            },
        }
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{self.auth_url}/signup",
                json=payload,
                headers=self.headers,
            )
        if response.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Supabase registration failed",
            )
        return response.json()

    async def sign_in_with_password(self, email: str, password: str) -> dict[str, Any]:
        payload = {"email": email, "password": password}
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{self.auth_url}/token?grant_type=password",
                json=payload,
                headers=self.headers,
            )
        if response.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        return response.json()


def create_supabase_auth_client() -> SupabaseAuthClient:
    return SupabaseAuthClient()


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_supabase_user_id(db: AsyncSession, supabase_user_id: str) -> User | None:
    result = await db.execute(select(User).where(User.supabase_user_id == supabase_user_id))
    return result.scalar_one_or_none()


def extract_supabase_user_id(auth_response: dict[str, Any]) -> str:
    user_payload = auth_response.get("user")
    if not isinstance(user_payload, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Supabase registration response did not include a user",
        )

    supabase_user_id = user_payload.get("id")
    if not isinstance(supabase_user_id, str) or not supabase_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Supabase registration response did not include a user id",
        )
    return supabase_user_id


async def create_user(
    db: AsyncSession,
    user_create: UserCreate,
    auth_client: SupabaseAuthClient | None = None,
) -> User:
    existing_user = await get_user_by_email(db, user_create.email)
    if existing_user is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    client = auth_client or create_supabase_auth_client()
    auth_response = await client.sign_up(user_create)
    supabase_user_id = extract_supabase_user_id(auth_response)

    user = User(
        supabase_user_id=supabase_user_id,
        email=user_create.email,
        hashed_password=SUPABASE_PASSWORD_SENTINEL,
        full_name=user_create.full_name,
        role=user_create.role,
        phone=user_create.phone,
        preferred_categories=[],
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        ) from exc
    await db.refresh(user)
    return user


def create_access_token(user: User) -> str:
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": user.supabase_user_id or user.email,
        "role": user.role.value,
        "user_id": user.id,
        "exp": expires_at,
    }
    return jwt.encode(payload, settings.supabase_jwt_secret, algorithm=settings.jwt_algorithm)


async def authenticate_user(
    db: AsyncSession,
    email: str,
    password: str,
    auth_client: SupabaseAuthClient | None = None,
) -> str:
    user = await get_user_by_email(db, email)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user")

    client = auth_client or create_supabase_auth_client()
    auth_response = await client.sign_in_with_password(email, password)
    access_token = auth_response.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth response")

    payload = decode_access_token(access_token)
    token_subject = payload["sub"]
    if user.supabase_user_id is not None and token_subject != user.supabase_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    token_user_id = read_int_claim(payload, "user_id")
    if token_user_id is not None and token_user_id != user.id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    if "role" in payload and payload["role"] != user.role.value:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return access_token


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except ExpiredSignatureError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired") from exc
    except InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    if "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return payload


def read_int_claim(payload: dict[str, Any], claim_name: str) -> int | None:
    if claim_name not in payload:
        return None
    try:
        return int(payload[claim_name])
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc


async def get_user_from_token(db: AsyncSession, token: str) -> User:
    payload = decode_access_token(token)
    subject = payload["sub"]
    token_user_id = read_int_claim(payload, "user_id")
    user: User | None = None

    if isinstance(subject, str):
        user = await get_user_by_supabase_user_id(db, subject)
        if user is None:
            user = await get_user_by_email(db, subject)

    if user is None and token_user_id is not None:
        user = await get_user_by_id(db, token_user_id)

    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    if user.supabase_user_id is not None and subject != user.supabase_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    if token_user_id is not None and token_user_id != user.id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    if "role" in payload and payload["role"] != user.role.value:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user")
    return user


async def update_preferences(
    db: AsyncSession,
    user: User,
    preferred_categories: list[ItemCategory],
) -> User:
    user.preferred_categories = [category.value for category in preferred_categories]
    await db.commit()
    await db.refresh(user)
    return user
