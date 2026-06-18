from typing import Annotated

from fastapi import APIRouter, Depends, status, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, require_role, get_current_user
from app.models.user import User, UserRole
from app.schemas.request import RequestCreate, RequestOut, RequestApprove
from app.services import request_service

router = APIRouter(prefix="/api/requests", tags=["requests"])


@router.post("", response_model=RequestOut, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=RequestOut, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def create_request(
    request_in: RequestCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RequestOut:
    req = await request_service.create_request(db, current_user, request_in)
    return await request_service.request_to_out(req, current_user)


@router.get("/incoming", response_model=list[RequestOut])
async def list_incoming_requests(
    current_user: Annotated[User, Depends(require_role(UserRole.donor))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[RequestOut]:
    reqs = await request_service.list_incoming_requests(db, current_user)
    return [await request_service.request_to_out(r, current_user) for r in reqs]


@router.get("/my", response_model=list[RequestOut])
async def list_my_requests(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[RequestOut]:
    reqs = await request_service.list_my_requests(db, current_user)
    return [await request_service.request_to_out(r, current_user) for r in reqs]


@router.get("/{request_id}", response_model=RequestOut)
async def get_request(
    request_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RequestOut:
    req = await request_service.get_request(db, request_id, current_user)
    return await request_service.request_to_out(req, current_user)


@router.patch("/{request_id}/approve", response_model=RequestOut)
async def approve_request(
    request_id: int,
    current_user: Annotated[User, Depends(require_role(UserRole.donor))],
    db: Annotated[AsyncSession, Depends(get_db)],
    approve_in: RequestApprove | None = Body(default=None),
) -> RequestOut:
    pickup_loc = approve_in.pickup_location if approve_in else None
    req = await request_service.approve_request(db, request_id, current_user, pickup_location=pickup_loc)
    return await request_service.request_to_out(req, current_user)


@router.patch("/{request_id}/reject", response_model=RequestOut)
async def reject_request(
    request_id: int,
    current_user: Annotated[User, Depends(require_role(UserRole.donor))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RequestOut:
    req = await request_service.reject_request(db, request_id, current_user)
    return await request_service.request_to_out(req, current_user)


@router.patch("/{request_id}/pickup", response_model=RequestOut)
async def pickup_request(
    request_id: int,
    current_user: Annotated[User, Depends(require_role(UserRole.donor))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RequestOut:
    req = await request_service.pickup_request(db, request_id, current_user)
    return await request_service.request_to_out(req, current_user)


@router.patch("/{request_id}/cancel", response_model=RequestOut)
async def cancel_request(
    request_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RequestOut:
    req = await request_service.cancel_request(db, request_id, current_user)
    return await request_service.request_to_out(req, current_user)
