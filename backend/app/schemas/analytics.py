from pydantic import BaseModel


class AnalyticsSummary(BaseModel):
    """Platform-wide aggregate summary for admin dashboard.

    people_helped is the count of donation_requests with status=picked_up.
    It is derived from the picked_up lifecycle state, not from approved,
    because approved means reserved but not yet physically received.
    """

    total_donors: int
    total_recipients: int
    total_ngos: int
    total_items_listed: int
    total_items_donated: int
    total_requests: int
    people_helped: int


class CategoryBreakdownItem(BaseModel):
    """Count of donated items per category."""

    category: str
    count: int


class DonationTrendItem(BaseModel):
    """Daily donation count for the last 30 days.

    Uses items.donated_at (set exactly once at pickup confirmation) — never
    items.updated_at which is mutable and would corrupt historical buckets.
    """

    date: str  # ISO date string: YYYY-MM-DD
    count: int


class TopCityItem(BaseModel):
    """Item listing count per city (all statuses included)."""

    city: str
    count: int


class PlatformActivityItem(BaseModel):
    """Daily new users, items, and requests for the last 30 days.

    All three use stable creation timestamps (created_at), never updated_at.
    """

    date: str  # ISO date string: YYYY-MM-DD
    new_users: int
    new_items: int
    new_requests: int
