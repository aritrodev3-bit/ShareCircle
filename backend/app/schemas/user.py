from pydantic import BaseModel, EmailStr, Field

from app.models.item import ItemCategory
from app.models.user import UserRole


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    role: UserRole
    phone: str | None = Field(default=None, max_length=20)


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    phone: str | None
    preferred_categories: list[str]
    is_active: bool

    model_config = {"from_attributes": True}


class PreferencesUpdate(BaseModel):
    preferred_categories: list[ItemCategory]
