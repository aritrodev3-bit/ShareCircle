from math import ceil
from typing import Sequence

from fastapi import HTTPException, status
from geoalchemy2.elements import WKTElement
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.item import Item, ItemCategory, ItemCondition, ItemStatus
from app.models.user import User
from app.schemas.item import ItemCreate, ItemOut, ItemUpdate
from app.schemas.pagination import PaginatedResponse

MAX_PAGE_SIZE = 100


def point_from_coordinates(lat: float | None, lng: float | None) -> WKTElement | None:
    if lat is None or lng is None:
        return None
    return WKTElement(f"POINT({lng} {lat})", srid=4326)


def item_to_out(item: Item) -> ItemOut:
    return ItemOut(
        id=item.id,
        donor_id=item.donor_id,
        donor_name=item.donor.full_name,
        title=item.title,
        description=item.description,
        category=item.category,
        condition=item.condition,
        quantity=item.quantity,
        status=item.status,
        city=item.city,
        pincode=item.pincode,
        image_url=item.image_url,
        donated_at=item.donated_at,
        removed_at=item.removed_at,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


async def create_item(db: AsyncSession, donor: User, item_create: ItemCreate) -> Item:
    item = Item(
        donor_id=donor.id,
        title=item_create.title,
        description=item_create.description,
        category=item_create.category,
        condition=item_create.condition,
        quantity=item_create.quantity,
        status=ItemStatus.available,
        location=point_from_coordinates(item_create.lat, item_create.lng),
        city=item_create.city,
        pincode=item_create.pincode,
        image_url=str(item_create.image_url) if item_create.image_url is not None else None,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    await db.refresh(item, attribute_names=["donor"])
    return item


async def get_item(db: AsyncSession, item_id: int) -> Item:
    result = await db.execute(
        select(Item).where(Item.id == item_id).options(selectinload(Item.donor))
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item


def apply_item_filters(
    query: Select[tuple[Item]],
    *,
    categories: Sequence[ItemCategory] | None,
    status_filter: ItemStatus | None,
    city: str | None,
    condition: ItemCondition | None,
    mine: bool,
    current_user: User | None,
    lat: float | None,
    lng: float | None,
    radius_km: float | None,
) -> Select[tuple[Item]]:
    if mine:
        if current_user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
        query = query.where(Item.donor_id == current_user.id)
    elif status_filter is not None:
        query = query.where(Item.status == status_filter)

    if categories:
        query = query.where(Item.category.in_(categories))
    if city is not None:
        query = query.where(Item.city == city)
    if condition is not None:
        query = query.where(Item.condition == condition)
    if lat is not None and lng is not None and radius_km is not None:
        query = query.where(Item.location.is_not(None))
        query = query.where(
            func.ST_DWithin(
                Item.location,
                func.ST_SetSRID(func.ST_MakePoint(lng, lat), 4326),
                radius_km * 1000,
            )
        )
    return query


async def list_items(
    db: AsyncSession,
    *,
    categories: Sequence[ItemCategory] | None,
    status_filter: ItemStatus | None,
    city: str | None,
    condition: ItemCondition | None,
    mine: bool,
    current_user: User | None,
    lat: float | None,
    lng: float | None,
    radius_km: float | None,
    page: int,
    page_size: int,
) -> PaginatedResponse[ItemOut]:
    base_query = select(Item).options(selectinload(Item.donor))
    filtered_query = apply_item_filters(
        base_query,
        categories=categories,
        status_filter=status_filter,
        city=city,
        condition=condition,
        mine=mine,
        current_user=current_user,
        lat=lat,
        lng=lng,
        radius_km=radius_km,
    )

    total_result = await db.execute(select(func.count()).select_from(filtered_query.order_by(None).subquery()))
    total = total_result.scalar_one()

    result = await db.execute(
        filtered_query.order_by(Item.id.asc()).offset((page - 1) * page_size).limit(page_size)
    )
    items = result.scalars().all()
    return PaginatedResponse[ItemOut](
        items=[item_to_out(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total else 0,
    )


def ensure_item_owner(item: Item, user: User) -> None:
    if item.donor_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the item owner can modify it")


async def update_item(db: AsyncSession, item_id: int, owner: User, item_update: ItemUpdate) -> Item:
    item = await get_item(db, item_id)
    ensure_item_owner(item, owner)

    update_data = item_update.model_dump(exclude_unset=True)
    lat = update_data.pop("lat", None)
    lng = update_data.pop("lng", None)
    if lat is not None or lng is not None:
        if lat is None or lng is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Both lat and lng are required to update location",
            )
        item.location = point_from_coordinates(lat, lng)

    for field_name, value in update_data.items():
        if field_name == "image_url" and value is not None:
            value = str(value)
        setattr(item, field_name, value)

    await db.commit()
    await db.refresh(item)
    await db.refresh(item, attribute_names=["donor"])
    return item


async def remove_item(db: AsyncSession, item_id: int, owner: User) -> Item:
    item = await get_item(db, item_id)
    ensure_item_owner(item, owner)
    item.status = ItemStatus.removed
    item.removed_at = func.now()
    await db.commit()
    await db.refresh(item)
    await db.refresh(item, attribute_names=["donor"])
    return item
