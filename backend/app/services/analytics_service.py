"""Analytics service — admin-only aggregate queries over platform data.

All functions:
  - Use SQLAlchemy ORM aggregate expressions (no raw SQL).
  - Return empty lists / zero counts on empty datasets (never raise on empty).
  - Use durable lifecycle timestamps for trend queries:
      * donated_at  for donation trends   (set exactly once at pickup; never mutated)
      * created_at  for platform activity (immutable insertion timestamp)
  - Never use updated_at for any grouping — it is mutable and corrupts historical buckets.
  - Use UTC-consistent date truncation to avoid timezone bucket shifts.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import cast, func, select, union
from sqlalchemy.dialects.postgresql import ARRAY as PgArray  # noqa: F401 (imported for future use)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.types import Date

from app.models.item import Item, ItemStatus
from app.models.request import DonationRequest, RequestStatus
from app.models.user import User, UserRole
from app.schemas.analytics import (
    AnalyticsSummary,
    CategoryBreakdownItem,
    DonationTrendItem,
    PlatformActivityItem,
    TopCityItem,
)

_TREND_DAYS = 30
_TOP_CITIES_LIMIT = 10


async def get_summary(db: AsyncSession) -> AnalyticsSummary:
    """Return platform-wide aggregate counts."""

    # Role counts
    role_counts_result = await db.execute(
        select(User.role, func.count(User.id).label("cnt"))
        .where(User.is_active == True)  # noqa: E712
        .group_by(User.role)
    )
    role_counts: dict[str, int] = {row.role.value: row.cnt for row in role_counts_result}

    # Item counts
    item_counts_result = await db.execute(
        select(Item.status, func.count(Item.id).label("cnt")).group_by(Item.status)
    )
    item_counts: dict[str, int] = {row.status.value: row.cnt for row in item_counts_result}

    total_items_listed = sum(item_counts.values())
    total_items_donated = item_counts.get(ItemStatus.donated.value, 0)

    # Request counts
    total_requests_result = await db.execute(select(func.count(DonationRequest.id)))
    total_requests: int = total_requests_result.scalar_one() or 0

    # People helped = count of picked_up requests (physically received, not just approved)
    people_helped_result = await db.execute(
        select(func.count(DonationRequest.id)).where(
            DonationRequest.status == RequestStatus.picked_up
        )
    )
    people_helped: int = people_helped_result.scalar_one() or 0

    return AnalyticsSummary(
        total_donors=role_counts.get(UserRole.donor.value, 0),
        total_recipients=role_counts.get(UserRole.recipient.value, 0),
        total_ngos=role_counts.get(UserRole.ngo.value, 0),
        total_items_listed=total_items_listed,
        total_items_donated=total_items_donated,
        total_requests=total_requests,
        people_helped=people_helped,
    )


async def get_category_breakdown(db: AsyncSession) -> list[CategoryBreakdownItem]:
    """Return count of donated items per category, sorted by count descending."""
    result = await db.execute(
        select(Item.category, func.count(Item.id).label("cnt"))
        .where(Item.status == ItemStatus.donated)
        .group_by(Item.category)
        .order_by(func.count(Item.id).desc())
    )
    rows = result.all()
    return [CategoryBreakdownItem(category=row.category.value, count=row.cnt) for row in rows]


async def get_donation_trend(db: AsyncSession, days: int = _TREND_DAYS) -> list[DonationTrendItem]:
    """Return daily donation counts for the last N days.

    Uses items.donated_at — set exactly once when status transitions to picked_up.
    Never uses updated_at (mutable; would corrupt historical day buckets).
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(
            cast(Item.donated_at, Date).label("donation_date"),
            func.count(Item.id).label("cnt"),
        )
        .where(
            Item.donated_at.is_not(None),
            Item.donated_at >= cutoff,
        )
        .group_by(cast(Item.donated_at, Date))
        .order_by(cast(Item.donated_at, Date))
    )
    rows = result.all()
    return [DonationTrendItem(date=str(row.donation_date), count=row.cnt) for row in rows]


async def get_top_cities(db: AsyncSession, limit: int = _TOP_CITIES_LIMIT) -> list[TopCityItem]:
    """Return cities ranked by total item listing count (all statuses).

    All item statuses are included — this represents overall platform reach by geography,
    not just active listings.
    """
    result = await db.execute(
        select(Item.city, func.count(Item.id).label("cnt"))
        .group_by(Item.city)
        .order_by(func.count(Item.id).desc())
        .limit(limit)
    )
    rows = result.all()
    return [TopCityItem(city=row.city, count=row.cnt) for row in rows]


async def get_platform_activity(
    db: AsyncSession, days: int = _TREND_DAYS
) -> list[PlatformActivityItem]:
    """Return daily new users, items, and requests for the last N days.

    All three subqueries use stable created_at timestamps (never updated_at).
    Results are outer-joined on date so a day with only new users (but no items
    or requests) still appears in the result.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Subquery: daily new users
    user_sq = (
        select(
            cast(User.created_at, Date).label("d"),
            func.count(User.id).label("new_users"),
        )
        .where(User.created_at >= cutoff)
        .group_by(cast(User.created_at, Date))
        .subquery("user_daily")
    )

    # Subquery: daily new items
    item_sq = (
        select(
            cast(Item.created_at, Date).label("d"),
            func.count(Item.id).label("new_items"),
        )
        .where(Item.created_at >= cutoff)
        .group_by(cast(Item.created_at, Date))
        .subquery("item_daily")
    )

    # Subquery: daily new requests
    req_sq = (
        select(
            cast(DonationRequest.created_at, Date).label("d"),
            func.count(DonationRequest.id).label("new_requests"),
        )
        .where(DonationRequest.created_at >= cutoff)
        .group_by(cast(DonationRequest.created_at, Date))
        .subquery("req_daily")
    )

    # Union all dates from the three subqueries to avoid missing days.
    # Use standalone union() — chaining .union() on a CompoundSelect is not supported in SA 2.x.
    all_dates_sq = union(
        select(user_sq.c.d.label("d")),
        select(item_sq.c.d.label("d")),
        select(req_sq.c.d.label("d")),
    ).subquery("all_dates")

    result = await db.execute(
        select(
            all_dates_sq.c.d.label("date"),
            func.coalesce(user_sq.c.new_users, 0).label("new_users"),
            func.coalesce(item_sq.c.new_items, 0).label("new_items"),
            func.coalesce(req_sq.c.new_requests, 0).label("new_requests"),
        )
        .outerjoin(user_sq, user_sq.c.d == all_dates_sq.c.d)
        .outerjoin(item_sq, item_sq.c.d == all_dates_sq.c.d)
        .outerjoin(req_sq, req_sq.c.d == all_dates_sq.c.d)
        .order_by(all_dates_sq.c.d)
    )
    rows = result.all()
    return [
        PlatformActivityItem(
            date=str(row.date),
            new_users=row.new_users,
            new_items=row.new_items,
            new_requests=row.new_requests,
        )
        for row in rows
    ]
