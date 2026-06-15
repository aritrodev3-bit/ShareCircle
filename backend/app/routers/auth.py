import base64
import hashlib
import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.auth import Token
from app.schemas.user import PreferencesUpdate, UserCreate, UserOut
from app.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(user_create: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]) -> User:
    return await auth_service.create_user(db, user_create)


@router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Token:
    access_token = await auth_service.authenticate_user(db, form_data.username, form_data.password)
    return Token(access_token=access_token)


@router.get("/me", response_model=UserOut)
async def me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user


@router.patch("/me/preferences", response_model=UserOut)
async def update_my_preferences(
    preferences: PreferencesUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    return await auth_service.update_preferences(db, current_user, preferences.preferred_categories)


@router.get("/login/google")
async def login_google() -> RedirectResponse:
    settings = get_settings()
    code_verifier = secrets.token_urlsafe(64)
    hashed = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = (
        base64.urlsafe_b64encode(hashed)
        .decode("ascii")
        .replace("=", "")
    )

    supabase_auth_url = (
        f"{str(settings.supabase_url).rstrip('/')}/auth/v1/authorize"
        f"?provider=google"
        f"&redirect_to={settings.google_redirect_uri}"
        f"&code_challenge={code_challenge}"
        f"&code_challenge_method=S256"
    )

    redirect_response = RedirectResponse(url=supabase_auth_url)
    redirect_response.set_cookie(
        key="sb-code-verifier",
        value=code_verifier,
        httponly=True,
        secure=settings.environment != "local",
        samesite="lax",
        max_age=600,
    )
    return redirect_response


@router.get("/callback/google")
async def callback_google(
    code: str,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RedirectResponse:
    settings = get_settings()
    code_verifier = request.cookies.get("sb-code-verifier")
    if not code_verifier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing code verifier",
        )

    try:
        result = await auth_service.exchange_google_code(db, code, code_verifier)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Google authentication service error",
        ) from exc

    redirect_response = RedirectResponse(
        url=f"{settings.frontend_oauth_redirect_url}#access_token={result['access_token']}&is_new_user={str(result['is_new_user']).lower()}"
    )
    redirect_response.delete_cookie("sb-code-verifier")
    return redirect_response
