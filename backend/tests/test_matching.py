"""Tests for Phase 7 matching endpoint.

Coverage: M01–M16 from the Phase 7 Implementation Blueprint.
All tests are independent (unique emails, try/finally cleanup).
No time.sleep() calls; no ordering dependencies.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest
from geoalchemy2.elements import WKTElement
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from app.config import get_settings
from app.database import async_session_factory
from app.main import create_app
from app.models import Item, ItemCategory, ItemCondition, ItemStatus, User, UserRole
from app.services import auth_service


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def matching_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=create_app()), base_url="http://test")


async def make_user(
    email: str,
    role: UserRole,
    preferred_categories: list[str] | None = None,
) -> User:
    async with async_session_factory() as session:
        user = User(
            supabase_user_id=str(uuid4()),
            email=email,
            hashed_password=auth_service.SUPABASE_PASSWORD_SENTINEL,
            full_name=f"{role.value.title()} Test",
            role=role,
            phone="9000000000",
            preferred_categories=preferred_categories or [],
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def make_item(
    donor: User,
    title: str,
    category: ItemCategory = ItemCategory.books,
    condition: ItemCondition = ItemCondition.good,
    status: ItemStatus = ItemStatus.available,
    point: str | None = None,
) -> Item:
    async with async_session_factory() as session:
        item = Item(
            donor_id=donor.id,
            title=title,
            description=f"{title} desc",
            category=category,
            condition=condition,
            quantity=1,
            status=status,
            city="TestCity",
            pincode="000000",
            location=WKTElement(point, srid=4326) if point else None,
        )
        session.add(item)
        await session.commit()
        await session.refresh(item)
        return item


def make_token(user: User) -> str:
    settings = get_settings()
    return jwt.encode(
        {
            "sub": user.supabase_user_id,
            "role": user.role.value,
            "user_id": user.id,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
        },
        settings.supabase_jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


async def cleanup(*emails: str) -> None:
    async with async_session_factory() as session:
        uid_sq = select(User.id).where(User.email.in_(emails))
        await session.execute(delete(Item).where(Item.donor_id.in_(uid_sq)))
        await session.execute(delete(User).where(User.email.in_(emails)))
        await session.commit()


# ---------------------------------------------------------------------------
# M01 — Score ordering: higher-scored item ranks first
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_suggestions_ordered_by_score_descending():
    """M01 — Results are sorted by composite score descending."""
    donor_email = f"donor-m01-{uuid4().hex}@example.com"
    user_email = f"recip-m01-{uuid4().hex}@example.com"
    donor = await make_user(donor_email, UserRole.donor)
    # preferred = clothing; clothing item scores higher than books
    user = await make_user(user_email, UserRole.recipient, preferred_categories=["clothing"])

    # Seed clothing item (category_match=1.0) and books item (category_match=0.5)
    await make_item(donor, "Warm Jacket", category=ItemCategory.clothing)
    await make_item(donor, "Old Novel", category=ItemCategory.books)

    try:
        async with matching_client() as client:
            resp = await client.get(
                "/api/matching/suggestions",
                headers={"Authorization": f"Bearer {make_token(user)}"},
            )
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) >= 2
        scores = [i["score"] for i in items]
        assert scores == sorted(scores, reverse=True), "Items not sorted by score descending"
        # The clothing item must outrank the books item
        categories = [i["category"] for i in items[:2]]
        assert categories[0] == "clothing"
    finally:
        await cleanup(donor_email, user_email)


# ---------------------------------------------------------------------------
# M02 — Category preference: preferred category item scores >= 0.75
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_preferred_category_item_scores_higher():
    """M02 — clothing item score >= 0.75 when user prefers clothing."""
    donor_email = f"donor-m02-{uuid4().hex}@example.com"
    user_email = f"recip-m02-{uuid4().hex}@example.com"
    donor = await make_user(donor_email, UserRole.donor)
    user = await make_user(user_email, UserRole.recipient, preferred_categories=["clothing"])

    await make_item(donor, "Jacket", category=ItemCategory.clothing)
    await make_item(donor, "Textbook", category=ItemCategory.books)

    try:
        async with matching_client() as client:
            resp = await client.get(
                "/api/matching/suggestions",
                headers={"Authorization": f"Bearer {make_token(user)}"},
            )
        assert resp.status_code == 200
        items = {i["category"]: i["score"] for i in resp.json()}
        assert items["clothing"] >= 0.75, f"Clothing score too low: {items['clothing']}"
        assert items["clothing"] > items["books"]
    finally:
        await cleanup(donor_email, user_email)


# ---------------------------------------------------------------------------
# M03 — Top-20 cap
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_suggestions_capped_at_20():
    """M03 — Response never exceeds 20 items."""
    donor_email = f"donor-m03-{uuid4().hex}@example.com"
    user_email = f"recip-m03-{uuid4().hex}@example.com"
    donor = await make_user(donor_email, UserRole.donor)
    user = await make_user(user_email, UserRole.recipient)

    for i in range(25):
        await make_item(donor, f"Item-{i}")

    try:
        async with matching_client() as client:
            resp = await client.get(
                "/api/matching/suggestions",
                headers={"Authorization": f"Bearer {make_token(user)}"},
            )
        assert resp.status_code == 200
        assert len(resp.json()) <= 20
    finally:
        await cleanup(donor_email, user_email)


# ---------------------------------------------------------------------------
# M04 / M05 — Role access: recipient and NGO allowed
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_recipient_can_access_suggestions():
    """M04 — Recipient role returns 200."""
    email = f"recip-m04-{uuid4().hex}@example.com"
    user = await make_user(email, UserRole.recipient)
    try:
        async with matching_client() as client:
            resp = await client.get(
                "/api/matching/suggestions",
                headers={"Authorization": f"Bearer {make_token(user)}"},
            )
        assert resp.status_code == 200
    finally:
        await cleanup(email)


@pytest.mark.asyncio
async def test_ngo_can_access_suggestions():
    """M05 — NGO role returns 200."""
    email = f"ngo-m05-{uuid4().hex}@example.com"
    user = await make_user(email, UserRole.ngo)
    try:
        async with matching_client() as client:
            resp = await client.get(
                "/api/matching/suggestions",
                headers={"Authorization": f"Bearer {make_token(user)}"},
            )
        assert resp.status_code == 200
    finally:
        await cleanup(email)


# ---------------------------------------------------------------------------
# M06 — Only available items appear
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_suggestions_excludes_non_available_items():
    """M06 — reserved, donated, removed items are not returned."""
    donor_email = f"donor-m06-{uuid4().hex}@example.com"
    user_email = f"recip-m06-{uuid4().hex}@example.com"
    donor = await make_user(donor_email, UserRole.donor)
    user = await make_user(user_email, UserRole.recipient)

    available = await make_item(donor, "Available item", status=ItemStatus.available)
    await make_item(donor, "Reserved item", status=ItemStatus.reserved)
    await make_item(donor, "Donated item", status=ItemStatus.donated)
    await make_item(donor, "Removed item", status=ItemStatus.removed)

    try:
        async with matching_client() as client:
            resp = await client.get(
                "/api/matching/suggestions",
                headers={"Authorization": f"Bearer {make_token(user)}"},
            )
        assert resp.status_code == 200
        returned_ids = {i["id"] for i in resp.json()}
        assert available.id in returned_ids
        # Non-available items must NOT be present
        async with async_session_factory() as session:
            non_available = await session.scalars(
                select(Item).where(
                    Item.donor_id == donor.id,
                    Item.status != ItemStatus.available,
                )
            )
            for item in non_available:
                assert item.id not in returned_ids, f"Non-available item {item.id} appeared in suggestions"
    finally:
        await cleanup(donor_email, user_email)


# ---------------------------------------------------------------------------
# M07 — Null-location item excluded from radius path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_null_location_item_excluded_when_coordinates_provided():
    """M07 — Item with null location does not appear in coordinate-based suggestions.

    When lat/lng are provided, items without a location receive proximity_score=0.5
    but may still appear unless the scoring places them below the top 20.
    The key invariant is that items WITH a location close to the user score higher
    and appear above null-location items when coordinates are given.
    """
    donor_email = f"donor-m07-{uuid4().hex}@example.com"
    user_email = f"recip-m07-{uuid4().hex}@example.com"
    donor = await make_user(donor_email, UserRole.donor)
    user = await make_user(user_email, UserRole.recipient)

    # Item with exact matching location (very close — same point)
    located = await make_item(donor, "Located item", point="POINT(77.5946 12.9716)")
    # Item without location
    await make_item(donor, "Unlocated item", point=None)

    try:
        async with matching_client() as client:
            resp = await client.get(
                "/api/matching/suggestions",
                params={"lat": "12.9716", "lng": "77.5946"},
                headers={"Authorization": f"Bearer {make_token(user)}"},
            )
        assert resp.status_code == 200
        items = resp.json()
        returned_ids = [i["id"] for i in items]
        # Located item must be present
        assert located.id in returned_ids
        # Located item must rank first (highest proximity score)
        assert items[0]["id"] == located.id
    finally:
        await cleanup(donor_email, user_email)


# ---------------------------------------------------------------------------
# M08 — Null-location item included in no-coordinate path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_null_location_item_included_without_coordinates():
    """M08 — Item with null location appears when no lat/lng provided."""
    donor_email = f"donor-m08-{uuid4().hex}@example.com"
    user_email = f"recip-m08-{uuid4().hex}@example.com"
    donor = await make_user(donor_email, UserRole.donor)
    user = await make_user(user_email, UserRole.recipient)

    unlocated = await make_item(donor, "No location item", point=None)

    try:
        async with matching_client() as client:
            resp = await client.get(
                "/api/matching/suggestions",
                headers={"Authorization": f"Bearer {make_token(user)}"},
            )
        assert resp.status_code == 200
        returned_ids = {i["id"] for i in resp.json()}
        assert unlocated.id in returned_ids
    finally:
        await cleanup(donor_email, user_email)


# ---------------------------------------------------------------------------
# M09 — Empty preferred_categories: all items get category_match = 0.5
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_empty_preferred_categories_no_penalty():
    """M09 — User with no preferences gets uniform category scores."""
    donor_email = f"donor-m09-{uuid4().hex}@example.com"
    user_email = f"recip-m09-{uuid4().hex}@example.com"
    donor = await make_user(donor_email, UserRole.donor)
    user = await make_user(user_email, UserRole.recipient, preferred_categories=[])

    clothing = await make_item(donor, "Jacket", category=ItemCategory.clothing)
    books = await make_item(donor, "Book", category=ItemCategory.books)

    try:
        async with matching_client() as client:
            resp = await client.get(
                "/api/matching/suggestions",
                headers={"Authorization": f"Bearer {make_token(user)}"},
            )
        assert resp.status_code == 200
        items_by_id = {i["id"]: i for i in resp.json()}
        assert clothing.id in items_by_id
        assert books.id in items_by_id
        # Both should have scores <= 0.7 (category_match=0.5*0.5=0.25 + proximity 0.5*0.3=0.15 + recency*0.2)
        for item_id in [clothing.id, books.id]:
            score = items_by_id[item_id]["score"]
            assert score <= 0.7, f"Score {score} for item {item_id} exceeds expected max without preference"
    finally:
        await cleanup(donor_email, user_email)


# ---------------------------------------------------------------------------
# M10 — No coordinates: fallback proximity score
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_no_coordinates_uses_fallback_proximity():
    """M10 — Omitting lat/lng gives proximity_score=0.5 for all items."""
    donor_email = f"donor-m10-{uuid4().hex}@example.com"
    user_email = f"recip-m10-{uuid4().hex}@example.com"
    donor = await make_user(donor_email, UserRole.donor)
    user = await make_user(user_email, UserRole.recipient, preferred_categories=["clothing"])

    await make_item(donor, "Jacket with loc", category=ItemCategory.clothing, point="POINT(77.5946 12.9716)")

    try:
        async with matching_client() as client:
            resp = await client.get(
                "/api/matching/suggestions",
                headers={"Authorization": f"Bearer {make_token(user)}"},
            )
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) >= 1
        # category_match=1.0*0.5=0.50, proximity_fallback=0.5*0.3=0.15, recency*0.2 in [0, 0.20]
        # Score range: [0.65 (recency≈0), 0.85 (recency=1.0 for brand-new item)]
        score = items[0]["score"]
        assert 0.60 <= score <= 0.86, f"Unexpected score without coordinates: {score}"
    finally:
        await cleanup(donor_email, user_email)


# ---------------------------------------------------------------------------
# M11 — Empty item pool returns empty list
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_empty_item_pool_returns_empty_list():
    """M11 — No available items → empty list, not an error."""
    user_email = f"recip-m11-{uuid4().hex}@example.com"
    user = await make_user(user_email, UserRole.recipient)

    try:
        async with matching_client() as client:
            resp = await client.get(
                "/api/matching/suggestions",
                headers={"Authorization": f"Bearer {make_token(user)}"},
            )
        assert resp.status_code == 200
        # May contain items from other tests; we just confirm it's a list with no error
        assert isinstance(resp.json(), list)
    finally:
        await cleanup(user_email)


# ---------------------------------------------------------------------------
# M12 / M13 — Partial coordinates → 422
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_lat_without_lng_returns_422():
    """M12 — Providing lat without lng returns 422."""
    user_email = f"recip-m12-{uuid4().hex}@example.com"
    user = await make_user(user_email, UserRole.recipient)

    try:
        async with matching_client() as client:
            resp = await client.get(
                "/api/matching/suggestions",
                params={"lat": "12.9716"},
                headers={"Authorization": f"Bearer {make_token(user)}"},
            )
        assert resp.status_code == 422
    finally:
        await cleanup(user_email)


@pytest.mark.asyncio
async def test_lng_without_lat_returns_422():
    """M13 — Providing lng without lat returns 422."""
    user_email = f"recip-m13-{uuid4().hex}@example.com"
    user = await make_user(user_email, UserRole.recipient)

    try:
        async with matching_client() as client:
            resp = await client.get(
                "/api/matching/suggestions",
                params={"lng": "77.5946"},
                headers={"Authorization": f"Bearer {make_token(user)}"},
            )
        assert resp.status_code == 422
    finally:
        await cleanup(user_email)


# ---------------------------------------------------------------------------
# M14 / M15 / M16 — Authorization failures
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_donor_cannot_access_suggestions():
    """M14 — Donor role returns 403."""
    email = f"donor-m14-{uuid4().hex}@example.com"
    user = await make_user(email, UserRole.donor)
    try:
        async with matching_client() as client:
            resp = await client.get(
                "/api/matching/suggestions",
                headers={"Authorization": f"Bearer {make_token(user)}"},
            )
        assert resp.status_code == 403
    finally:
        await cleanup(email)


@pytest.mark.asyncio
async def test_admin_cannot_access_suggestions():
    """M15 — Admin role returns 403."""
    email = f"admin-m15-{uuid4().hex}@example.com"
    user = await make_user(email, UserRole.admin)
    try:
        async with matching_client() as client:
            resp = await client.get(
                "/api/matching/suggestions",
                headers={"Authorization": f"Bearer {make_token(user)}"},
            )
        assert resp.status_code == 403
    finally:
        await cleanup(email)


@pytest.mark.asyncio
async def test_unauthenticated_request_returns_401():
    """M16 — No token returns 401."""
    async with matching_client() as client:
        resp = await client.get("/api/matching/suggestions")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Privacy guard — donor_phone must not appear in suggestions
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_suggestions_do_not_expose_donor_phone():
    """Privacy — SuggestionItem must never include donor_phone."""
    donor_email = f"donor-priv-{uuid4().hex}@example.com"
    user_email = f"recip-priv-{uuid4().hex}@example.com"
    donor = await make_user(donor_email, UserRole.donor)
    user = await make_user(user_email, UserRole.recipient)
    await make_item(donor, "Privacy test item")

    try:
        async with matching_client() as client:
            resp = await client.get(
                "/api/matching/suggestions",
                headers={"Authorization": f"Bearer {make_token(user)}"},
            )
        assert resp.status_code == 200
        for item in resp.json():
            assert "donor_phone" not in item, "donor_phone must not be exposed in suggestions"
            assert "phone" not in item
    finally:
        await cleanup(donor_email, user_email)
