import enum
from datetime import datetime
from typing import TYPE_CHECKING, Any

from geoalchemy2 import Geography
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.request import DonationRequest
    from app.models.user import User


class ItemStatus(str, enum.Enum):
    available = "available"
    reserved = "reserved"
    donated = "donated"
    removed = "removed"


class ItemCondition(str, enum.Enum):
    new = "new"
    like_new = "like_new"
    good = "good"
    fair = "fair"


class ItemCategory(str, enum.Enum):
    clothing = "clothing"
    furniture = "furniture"
    electronics = "electronics"
    books = "books"
    kitchen = "kitchen"
    toys = "toys"
    medical = "medical"
    other = "other"


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    donor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[ItemCategory] = mapped_column(
        Enum(ItemCategory, name="item_category"),
        nullable=False,
        index=True,
    )
    condition: Mapped[ItemCondition] = mapped_column(
        Enum(ItemCondition, name="item_condition"),
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    status: Mapped[ItemStatus] = mapped_column(
        Enum(ItemStatus, name="item_status"),
        nullable=False,
        server_default=ItemStatus.available.value,
        index=True,
    )
    location: Mapped[Any | None] = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False)
    )
    city: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    pincode: Mapped[str] = mapped_column(String(10), nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(500))
    donated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    donor: Mapped["User"] = relationship(back_populates="items")
    requests: Mapped[list["DonationRequest"]] = relationship(back_populates="item")
