"""Matching router — location-aware item suggestions for recipients and NGOs.

Single endpoint: GET /api/matching/suggestions
Auth: recipient or ngo role required (donors and admins are not permitted).
Params: lat, lng — must be provided together or not at all (422 if partial).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, require_role
from app.models.user import User, UserRole
from app.schemas.matching import SuggestionItem
from app.services import matching_service

router = APIRouter(prefix="/api/matching", tags=["matching"])


@router.get("/suggestions", response_model=list[SuggestionItem])
async def get_suggestions(
    current_user: Annotated[User, Depends(require_role(UserRole.recipient, UserRole.ngo))],
    db: Annotated[AsyncSession, Depends(get_db)],
    lat: Annotated[float | None, Query(ge=-90, le=90)] = None,
    lng: Annotated[float | None, Query(ge=-180, le=180)] = None,
) -> list[SuggestionItem]:
    """Return top-20 scored available items for the authenticated recipient or NGO.

    lat and lng are optional but must be provided together. Providing only one
    returns 422 Unprocessable Entity.
    """
    _validate_coordinates(lat, lng)
    return list(await matching_service.get_suggestions(db, current_user, lat, lng))


def _validate_coordinates(lat: float | None, lng: float | None) -> None:
    """Enforce that lat and lng are always provided together or not at all."""
    if (lat is None) != (lng is None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="lat and lng must be provided together",
        )
