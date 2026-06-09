"""Matching service — location-aware composite-score ranking of available items.

Scoring formula (from PRD §6.5):
    category_match  = 1.0 if item.category in user.preferred_categories else 0.5
                      (0.5 for all items when preferred_categories is empty — no penalty)
    proximity_score = 1 / (1 + distance_km)  when lat/lng provided AND item.location is not null
                      0.5                     when lat/lng absent OR item.location is null
    recency_score   = 1 / (1 + days_since_listed)

    score = (category_match × 0.5) + (proximity_score × 0.3) + (recency_score × 0.2)

Returns the top 20 results sorted by score descending.
Only ItemStatus.available items are considered.
"""

from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.item import Item, ItemStatus
from app.models.user import User
from app.schemas.matching import SuggestionItem

MAX_SUGGESTIONS = 20


def _category_match(item: Item, preferred: list[str]) -> float:
    """Return 1.0 if item matches any preferred category, else 0.5.

    When preferred_categories is empty the user has expressed no preference,
    so all items receive the neutral score 0.5 (no item is penalised).
    """
    if not preferred:
        return 0.5
    return 1.0 if item.category.value in preferred else 0.5


def _proximity_score(item: Item, lat: float | None, lng: float | None) -> float:
    """Return proximity score based on straight-line distance.

    Uses ST_Distance result (metres) fetched alongside the item.
    Falls back to 0.5 when:
      - No coordinates were provided by the caller, OR
      - The item has no location stored (null geography column).
    """
    if lat is None or lng is None or item.location is None:
        return 0.5
    # distance_km is injected as a transient attribute by the service
    distance_km: float = getattr(item, "_distance_km", None) or 0.0
    return 1.0 / (1.0 + distance_km)


def _recency_score(item: Item) -> float:
    """Return recency score based on days since item was listed."""
    now = datetime.now(timezone.utc)
    created = item.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    days = max(0.0, (now - created).total_seconds() / 86400)
    return 1.0 / (1.0 + days)


def _composite_score(item: Item, preferred: list[str], lat: float | None, lng: float | None) -> float:
    cm = _category_match(item, preferred)
    ps = _proximity_score(item, lat, lng)
    rs = _recency_score(item)
    return (cm * 0.5) + (ps * 0.3) + (rs * 0.2)


async def get_suggestions(
    db: AsyncSession,
    current_user: User,
    lat: float | None,
    lng: float | None,
) -> Sequence[SuggestionItem]:
    """Return up to MAX_SUGGESTIONS scored available items for the requester.

    When lat/lng are provided, items with null location receive proximity_score=0.5
    (they are not excluded from this path — only from radius-specific ST_DWithin
    queries which are not used here). The scoring naturally ranks location-bearing
    items higher when the user provides coordinates.
    """
    # Fetch all available items with donor relationship
    result = await db.execute(
        select(Item)
        .options(selectinload(Item.donor))
        .where(Item.status == ItemStatus.available)
    )
    items: list[Item] = list(result.scalars().all())

    # Compute distance_km for items that have a location when coordinates supplied
    if lat is not None and lng is not None:
        await _attach_distances(db, items, lat, lng)

    preferred: list[str] = list(current_user.preferred_categories or [])

    # Score every item in Python (acceptable at MVP scale; flag for future SQL scoring)
    scored: list[tuple[float, Item]] = [
        (_composite_score(item, preferred, lat, lng), item)
        for item in items
    ]
    scored.sort(key=lambda t: t[0], reverse=True)
    top = scored[:MAX_SUGGESTIONS]

    return [_to_suggestion(score, item) for score, item in top]


async def _attach_distances(db: AsyncSession, items: list[Item], lat: float, lng: float) -> None:
    """Attach _distance_km transient attribute to each item that has a location.

    Items without a location keep no _distance_km attribute and will receive
    proximity_score=0.5 via the fallback in _proximity_score().
    """
    from sqlalchemy import text

    location_item_ids = [item.id for item in items if item.location is not None]
    if not location_item_ids:
        return

    # Use raw text for ST_Distance — geoalchemy2 function expression on raw WKB
    # column value is the safest cross-platform approach here.
    rows = await db.execute(
        text(
            "SELECT id, ST_Distance(location::geography, "
            "ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography) / 1000.0 AS dist_km "
            "FROM items WHERE id = ANY(:ids)"
        ),
        {"lat": lat, "lng": lng, "ids": location_item_ids},
    )
    distance_map: dict[int, float] = {row.id: row.dist_km for row in rows}

    id_to_item = {item.id: item for item in items}
    for item_id, dist_km in distance_map.items():
        if item_id in id_to_item:
            id_to_item[item_id]._distance_km = dist_km  # transient; not persisted


def _to_suggestion(score: float, item: Item) -> SuggestionItem:
    return SuggestionItem(
        id=item.id,
        title=item.title,
        category=item.category,
        condition=item.condition,
        city=item.city,
        donor_name=item.donor.full_name,
        image_url=item.image_url,
        score=round(score, 6),
        created_at=item.created_at,
    )
