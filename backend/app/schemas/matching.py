from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.item import ItemCategory, ItemCondition


class SuggestionItem(BaseModel):
    """Response schema for a single matched item suggestion.

    Privacy: donor_phone is intentionally absent — this is a pre-approval
    browse surface equivalent to ItemOut. Contact details are only revealed
    after a request is approved (handled by the requests workflow).
    """

    id: int
    title: str
    category: ItemCategory
    condition: ItemCondition
    city: str
    donor_name: str
    image_url: str | None
    score: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
