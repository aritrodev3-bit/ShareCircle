from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl

from app.models.item import ItemCategory, ItemCondition, ItemStatus


class ItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    category: ItemCategory
    condition: ItemCondition
    quantity: int = Field(default=1, ge=1)
    city: str = Field(min_length=1, max_length=100)
    pincode: str = Field(min_length=1, max_length=10)
    image_url: HttpUrl | None = None
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)


class ItemUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, min_length=1)
    category: ItemCategory | None = None
    condition: ItemCondition | None = None
    quantity: int | None = Field(default=None, ge=1)
    city: str | None = Field(default=None, min_length=1, max_length=100)
    pincode: str | None = Field(default=None, min_length=1, max_length=10)
    image_url: HttpUrl | None = None
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)


class ItemOut(BaseModel):
    id: int
    donor_id: int
    donor_name: str
    title: str
    description: str
    category: ItemCategory
    condition: ItemCondition
    quantity: int
    status: ItemStatus
    city: str
    pincode: str
    image_url: str | None
    donated_at: datetime | None
    removed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
