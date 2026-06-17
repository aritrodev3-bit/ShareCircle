from typing import Annotated

from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.auth import Token
from app.schemas.user import PreferencesUpdate, UserCreate, UserOut, UserUpdate
from app.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(user_create: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]) -> User:
    try:
        return await auth_service.create_user(db, user_create)
    except HTTPException as e:
        raise e
    except Exception as e:
        import logging
        logger = logging.getLogger("app.routers.auth")
        logger.exception("Unexpected error during user registration")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed. Please check your credentials or try again later.",
        )


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


@router.patch("/me", response_model=UserOut)
async def update_profile(
    user_update: UserUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name
    if user_update.role is not None:
        current_user.role = user_update.role
    if user_update.phone is not None:
        current_user.phone = user_update.phone

    await db.commit()
    await db.refresh(current_user)
    return current_user
