from datetime import datetime
from pydantic import BaseModel, Field

from app.models.request import RequestStatus


class RequestCreate(BaseModel):
    item_id: int
    message: str | None = Field(default=None, max_length=1000)
    ngo_note: str | None = Field(default=None, max_length=1000)


class RequestApprove(BaseModel):
    pickup_location: str | None = Field(default=None, max_length=1000)


class RequestOut(BaseModel):
    id: int
    item_id: int
    requester_id: int
    item_title: str
    donor_name: str
    donor_phone: str | None
    requester_name: str
    message: str | None
    ngo_note: str | None
    status: RequestStatus
    pickup_scheduled_at: datetime | None
    approved_at: datetime | None
    picked_up_at: datetime | None
    cancelled_at: datetime | None
    created_at: datetime
    updated_at: datetime
    pickup_location: str | None = None
    item_city: str | None = None
    item_pincode: str | None = None
    item_lat: float | None = None
    item_lng: float | None = None

    model_config = {"from_attributes": True}
