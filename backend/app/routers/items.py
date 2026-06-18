from typing import Annotated
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.dependencies import get_db, get_optional_current_user, require_role
from app.models.item import ItemCategory, ItemCondition, ItemStatus
from app.models.user import User, UserRole
from app.schemas.item import ItemCreate, ItemOut, ItemUpdate
from app.schemas.pagination import PaginatedResponse
from app.services import item_service

router = APIRouter(prefix="/api/items", tags=["items"])


def validate_radius_filter(lat: float | None, lng: float | None, radius_km: float | None) -> None:
    provided_values = [lat is not None, lng is not None, radius_km is not None]
    if any(provided_values) and not all(provided_values):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="lat, lng, and radius_km are required together",
        )


@router.post("", response_model=ItemOut, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=ItemOut, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def create_item(
    item_create: ItemCreate,
    donor: Annotated[User, Depends(require_role(UserRole.donor))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ItemOut:
    item = await item_service.create_item(db, donor, item_create)
    return item_service.item_to_out(item)


@router.get("", response_model=PaginatedResponse[ItemOut])
@router.get("/", response_model=PaginatedResponse[ItemOut], include_in_schema=False)
async def list_items(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
    category: Annotated[list[ItemCategory] | None, Query()] = None,
    status_filter: Annotated[ItemStatus, Query(alias="status")] = ItemStatus.available,
    city: str | None = None,
    condition: ItemCondition | None = None,
    mine: bool = False,
    lat: Annotated[float | None, Query(ge=-90, le=90)] = None,
    lng: Annotated[float | None, Query(ge=-180, le=180)] = None,
    radius_km: Annotated[float | None, Query(gt=0, le=100)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=item_service.MAX_PAGE_SIZE)] = 20,
) -> PaginatedResponse[ItemOut]:
    validate_radius_filter(lat, lng, radius_km)
    return await item_service.list_items(
        db,
        categories=category,
        status_filter=status_filter,
        city=city,
        condition=condition,
        mine=mine,
        current_user=current_user,
        lat=lat,
        lng=lng,
        radius_km=radius_km,
        page=page,
        page_size=page_size,
    )


@router.get("/{item_id}", response_model=ItemOut)
async def get_item(item_id: int, db: Annotated[AsyncSession, Depends(get_db)]) -> ItemOut:
    item = await item_service.get_item(db, item_id)
    return item_service.item_to_out(item)


@router.patch("/{item_id}", response_model=ItemOut)
async def update_item(
    item_id: int,
    item_update: ItemUpdate,
    donor: Annotated[User, Depends(require_role(UserRole.donor))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ItemOut:
    item = await item_service.update_item(db, item_id, donor, item_update)
    return item_service.item_to_out(item)


@router.delete("/{item_id}", response_model=ItemOut)
async def delete_item(
    item_id: int,
    donor: Annotated[User, Depends(require_role(UserRole.donor))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ItemOut:
    item = await item_service.remove_item(db, item_id, donor)
    return item_service.item_to_out(item)


@router.post("/upload")
async def upload_image(
    file: UploadFile = File(...),
    donor: Annotated[User, Depends(require_role(UserRole.donor))] = None,
) -> dict[str, str]:
    # Ensure static uploads directory exists
    os.makedirs("app/static/uploads", exist_ok=True)
    
    # Generate unique filename
    file_extension = os.path.splitext(file.filename or "")[1]
    # Fallback to .jpg if no extension
    if not file_extension:
        file_extension = ".jpg"
        
    new_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join("app/static/uploads", new_filename)
    
    # Save file
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
        
    # Generate URL
    settings = get_settings()
    public_url = f"{str(settings.api_public_url).rstrip('/')}/static/uploads/{new_filename}"
    return {"image_url": public_url}
