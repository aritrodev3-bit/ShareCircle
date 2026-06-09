"""Analytics router — admin-only platform aggregate endpoints.

All five endpoints require the admin role, enforced at the dependency layer.
All endpoints are read-only; no state mutations occur.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, require_role
from app.models.user import User, UserRole
from app.schemas.analytics import (
    AnalyticsSummary,
    CategoryBreakdownItem,
    DonationTrendItem,
    PlatformActivityItem,
    TopCityItem,
)
from app.services import analytics_service

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

AdminUser = Annotated[User, Depends(require_role(UserRole.admin))]
DB = Annotated[AsyncSession, Depends(get_db)]


@router.get("/summary", response_model=AnalyticsSummary)
async def get_summary(
    _admin: AdminUser,
    db: DB,
) -> AnalyticsSummary:
    """Return platform-wide aggregate counts (donors, recipients, NGOs, items, requests)."""
    return await analytics_service.get_summary(db)


@router.get("/category-breakdown", response_model=list[CategoryBreakdownItem])
async def get_category_breakdown(
    _admin: AdminUser,
    db: DB,
) -> list[CategoryBreakdownItem]:
    """Return count of donated items grouped by category, sorted by count descending."""
    return await analytics_service.get_category_breakdown(db)


@router.get("/donation-trend", response_model=list[DonationTrendItem])
async def get_donation_trend(
    _admin: AdminUser,
    db: DB,
) -> list[DonationTrendItem]:
    """Return daily donation counts for the last 30 days using items.donated_at."""
    return await analytics_service.get_donation_trend(db)


@router.get("/top-cities", response_model=list[TopCityItem])
async def get_top_cities(
    _admin: AdminUser,
    db: DB,
) -> list[TopCityItem]:
    """Return top 10 cities by total item listing count (all statuses)."""
    return await analytics_service.get_top_cities(db)


@router.get("/platform-activity", response_model=list[PlatformActivityItem])
async def get_platform_activity(
    _admin: AdminUser,
    db: DB,
) -> list[PlatformActivityItem]:
    """Return daily new users, items, and requests for the last 30 days."""
    return await analytics_service.get_platform_activity(db)
