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


def item_test_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=create_app()), base_url="http://test")


async def create_user(email: str, role: UserRole) -> User:
    async with async_session_factory() as session:
        user = User(
            supabase_user_id=str(uuid4()),
            email=email,
            hashed_password=auth_service.SUPABASE_PASSWORD_SENTINEL,
            full_name=f"{role.value.title()} User",
            role=role,
            phone="9999999999",
            preferred_categories=[],
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def create_item(
    donor: User,
    title: str,
    category: ItemCategory = ItemCategory.books,
    condition: ItemCondition = ItemCondition.good,
    status: ItemStatus = ItemStatus.available,
    point: str | None = "POINT(77.5946 12.9716)",
) -> Item:
    async with async_session_factory() as session:
        item = Item(
            donor_id=donor.id,
            title=title,
            description=f"{title} description",
            category=category,
            condition=condition,
            quantity=1,
            status=status,
            location=WKTElement(point, srid=4326) if point is not None else None,
            city="Bengaluru",
            pincode="560001",
        )
        session.add(item)
        await session.commit()
        await session.refresh(item)
        return item


def make_token(user: User) -> str:
    settings = get_settings()
    payload = {
        "sub": user.supabase_user_id,
        "role": user.role.value,
        "user_id": user.id,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
    }
    return jwt.encode(payload, settings.supabase_jwt_secret, algorithm=settings.jwt_algorithm)


async def cleanup_users(*emails: str) -> None:
    async with async_session_factory() as session:
        user_ids = select(User.id).where(User.email.in_(emails))
        await session.execute(delete(Item).where(Item.donor_id.in_(user_ids)))
        await session.execute(delete(User).where(User.email.in_(emails)))
        await session.commit()


@pytest.mark.asyncio
async def test_create_item_as_donor_sets_available_status_and_hides_phone():
    email = f"donor-create-{uuid4().hex}@example.com"
    donor = await create_user(email, UserRole.donor)
    token = make_token(donor)

    try:
        async with item_test_client() as client:
            response = await client.post(
                "/api/items/",
                json={
                    "title": "Winter blanket",
                    "description": "Clean blanket for donation.",
                    "category": "clothing",
                    "condition": "good",
                    "quantity": 2,
                    "city": "Bengaluru",
                    "pincode": "560001",
                    "lat": 12.9716,
                    "lng": 77.5946,
                },
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 201
        payload = response.json()
        assert payload["status"] == "available"
        assert payload["donor_id"] == donor.id
        assert payload["donor_name"] == donor.full_name
        assert "donor_phone" not in payload
    finally:
        await cleanup_users(email)


@pytest.mark.asyncio
async def test_create_item_as_recipient_returns_403():
    email = f"recipient-create-{uuid4().hex}@example.com"
    recipient = await create_user(email, UserRole.recipient)
    token = make_token(recipient)

    try:
        async with item_test_client() as client:
            response = await client.post(
                "/api/items/",
                json={
                    "title": "Study books",
                    "description": "Textbooks.",
                    "category": "books",
                    "condition": "good",
                    "quantity": 1,
                    "city": "Bengaluru",
                    "pincode": "560001",
                },
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 403
    finally:
        await cleanup_users(email)


@pytest.mark.asyncio
async def test_list_items_filters_default_available_category_city_condition_and_pagination():
    email = f"donor-list-{uuid4().hex}@example.com"
    donor = await create_user(email, UserRole.donor)
    first = await create_item(donor, "Books one", ItemCategory.books, ItemCondition.good)
    second = await create_item(donor, "Books two", ItemCategory.books, ItemCondition.good)
    await create_item(donor, "Toy one", ItemCategory.toys, ItemCondition.good)
    await create_item(donor, "Reserved books", ItemCategory.books, ItemCondition.good, ItemStatus.reserved)

    try:
        async with item_test_client() as client:
            response = await client.get(
                "/api/items/",
                params=[
                    ("category", "books"),
                    ("city", "Bengaluru"),
                    ("condition", "good"),
                    ("page", "2"),
                    ("page_size", "1"),
                ],
            )

        assert response.status_code == 200
        payload = response.json()
        assert payload["total"] == 2
        assert payload["total_pages"] == 2
        assert payload["page"] == 2
        assert [item["id"] for item in payload["items"]] == [second.id]
        assert first.id != second.id
    finally:
        await cleanup_users(email)


@pytest.mark.asyncio
async def test_list_items_radius_returns_near_items_and_excludes_null_location():
    email = f"donor-radius-{uuid4().hex}@example.com"
    donor = await create_user(email, UserRole.donor)
    near = await create_item(donor, "Near item", point="POINT(77.5946 12.9716)")
    await create_item(donor, "Far item", point="POINT(72.8777 19.0760)")
    await create_item(donor, "Unknown location", point=None)

    try:
        async with item_test_client() as client:
            response = await client.get(
                "/api/items/",
                params={"lat": "12.9716", "lng": "77.5946", "radius_km": "5"},
            )

        assert response.status_code == 200
        item_ids = [item["id"] for item in response.json()["items"]]
        assert item_ids == [near.id]
    finally:
        await cleanup_users(email)


@pytest.mark.asyncio
async def test_radius_and_pagination_validation_returns_422():
    async with item_test_client() as client:
        partial_radius = await client.get("/api/items/", params={"lat": "12.9", "lng": "77.5"})
        invalid_lat = await client.get(
            "/api/items/",
            params={"lat": "91", "lng": "77.5", "radius_km": "5"},
        )
        invalid_page = await client.get("/api/items/", params={"page": "0"})

    assert partial_radius.status_code == 422
    assert invalid_lat.status_code == 422
    assert invalid_page.status_code == 422


@pytest.mark.asyncio
async def test_update_item_owner_only_and_mine_filter():
    owner_email = f"owner-update-{uuid4().hex}@example.com"
    other_email = f"other-update-{uuid4().hex}@example.com"
    owner = await create_user(owner_email, UserRole.donor)
    other = await create_user(other_email, UserRole.donor)
    item = await create_item(owner, "Owner item")
    await create_item(other, "Other item")

    try:
        async with item_test_client() as client:
            other_response = await client.patch(
                f"/api/items/{item.id}",
                json={"title": "Illegal update"},
                headers={"Authorization": f"Bearer {make_token(other)}"},
            )
            owner_response = await client.patch(
                f"/api/items/{item.id}",
                json={"title": "Updated owner item", "quantity": 3},
                headers={"Authorization": f"Bearer {make_token(owner)}"},
            )
            mine_response = await client.get(
                "/api/items/",
                params={"mine": "true"},
                headers={"Authorization": f"Bearer {make_token(owner)}"},
            )

        assert other_response.status_code == 403
        assert owner_response.status_code == 200
        assert owner_response.json()["title"] == "Updated owner item"
        assert owner_response.json()["quantity"] == 3
        assert [listed_item["id"] for listed_item in mine_response.json()["items"]] == [item.id]
    finally:
        await cleanup_users(owner_email, other_email)


@pytest.mark.asyncio
async def test_delete_item_soft_removes_and_keeps_row():
    email = f"donor-delete-{uuid4().hex}@example.com"
    donor = await create_user(email, UserRole.donor)
    item = await create_item(donor, "Delete me")

    try:
        async with item_test_client() as client:
            response = await client.delete(
                f"/api/items/{item.id}",
                headers={"Authorization": f"Bearer {make_token(donor)}"},
            )

        assert response.status_code == 200
        assert response.json()["status"] == "removed"
        assert response.json()["removed_at"] is not None

        async with async_session_factory() as session:
            persisted = await session.get(Item, item.id)
            assert persisted is not None
            assert persisted.status is ItemStatus.removed
            assert persisted.removed_at is not None
    finally:
        await cleanup_users(email)
