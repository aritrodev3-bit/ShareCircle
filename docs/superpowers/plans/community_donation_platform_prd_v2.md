# Community Donation Platform — Product Requirements Document (v2)

> **Audience:** This document is a complete build specification for OpenAI Codex (or any agentic coding assistant). Every section is written so Codex can build the project end-to-end with zero ambiguity, no duplicate code, and no placeholder stubs.
>
> **Changelog from v1:** 20 bugs and logic gaps fixed. Brand design system and Streamlit theming section added. See inline `[FIX]` markers.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Tech Stack](#2-tech-stack)
3. [Third-Party Services Setup](#3-third-party-services-setup)
4. [Repository Structure](#4-repository-structure)
5. [Data Models](#5-data-models)
6. [Backend — FastAPI](#6-backend--fastapi)
7. [Background Jobs — Celery + Redis](#7-background-jobs--celery--redis)
8. [Frontend — Streamlit](#8-frontend--streamlit)
9. [Brand Design System — GiveCircle](#9-brand-design-system--givecircle)
10. [Build Phases](#10-build-phases)
11. [Testing Strategy](#11-testing-strategy)
12. [Environment Variables Reference](#12-environment-variables-reference)
13. [Running the Project](#13-running-the-project)

---

## 1. Project Overview

A web-based platform that streamlines donation and distribution of reusable items by connecting **Donors**, **Recipients**, and **NGOs**. It handles item listing, request management, location-aware matching, delivery coordination, and impact analytics.

### Roles

| Role | Capability |
|------|-----------|
| **Donor** | Register, list items, approve/reject requests, mark items as picked up |
| **Recipient** | Browse items, submit requests, track request status |
| **NGO** | Manage bulk requests on behalf of communities, view allocation reports |
| **Admin** | View platform-wide analytics, moderate listings |

### Core Flows

1. Donor lists an item → item status = `available`
2. Recipient/NGO requests the item → status = `pending_approval`
3. Donor approves → status = `reserved`; background job sends email notification
4. Pickup confirmed → status = `donated`; impact counters increment

---

## 2. Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Backend API | FastAPI | 0.111.x |
| ORM | SQLAlchemy 2.0 (async) | 2.0.x |
| Migrations | Alembic | 1.13.x |
| Database | Supabase PostgreSQL + PostGIS | 16 |
| Background Jobs | Celery | 5.4.x |
| Message Broker | Redis | 7.x |
| Auth | Supabase Auth (JWT sessions) | — |
| Email | Resend API | — |
| Frontend | Streamlit | 1.35.x |
| Charts | Plotly | 5.x |
| HTTP Client (Streamlit→API) | httpx | 0.27.x |
| Testing (unit + integration) | pytest + pytest-asyncio | — |
| E2E Testing | Playwright (Python) | 1.44.x |
| Containerisation | Docker + Docker Compose | — |

---

## 3. Third-Party Services Setup

> Codex must not skip this section. Every user-facing integration requires the human operator to complete these steps before running the project. Codex must validate all required env vars at startup using `pydantic-settings` and raise a clear `ValueError` with the variable name if any are missing.

---

### 3.1 Supabase PostgreSQL + PostGIS

PostGIS is the spatial extension running within Supabase PostgreSQL. It enables distance-based item matching (find items within N km of recipient). The database is hosted and managed by Supabase; no local PostgreSQL container is required.

**Supabase project setup:**

1. Go to [supabase.com/dashboard](https://supabase.com/dashboard) and create a new project.
2. Save the project reference ID and database password.
3. Open **Project Settings → Database** and copy the connection strings from the Connect panel.
4. Enable PostGIS: open **Database → Extensions**, search for `postgis`, and enable it.
5. Verify PostGIS with: `select postgis_version();`

**Connection string format:**

```
# Application (FastAPI / SQLAlchemy) — use session pooler or direct URL:
postgresql+asyncpg://postgres.YOUR_PROJECT_REF:PASSWORD@aws-0-REGION.pooler.supabase.com:5432/postgres

# Migrations (Alembic) — use direct URL:
postgresql+asyncpg://postgres:PASSWORD@db.YOUR_PROJECT_REF.supabase.co:5432/postgres
```

Set `DATABASE_URL` (application) and `ALEMBIC_DATABASE_URL` (migrations) in `.env`. Avoid transaction-pooler mode until tested with SQLAlchemy row-locking workflows. If the database password contains special characters, URL-encode it in the connection string.

---

### 3.2 Redis

Redis is the message broker for Celery. It queues background tasks like sending emails and updating match scores.

**Local setup via Docker (recommended):**

```bash
# Already in docker-compose.yml.
docker compose up -d redis
```

**Manual setup:**

```bash
# Ubuntu / Debian
sudo apt install redis-server
sudo systemctl start redis

# macOS
brew install redis
brew services start redis
```

**Connection string format:**

```
redis://localhost:6379/0
```

Set this as `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` in `.env`.

---

### 3.3 Resend (Email)

Resend sends transactional emails (approval notifications, pickup reminders).

**Setup steps:**

1. Go to [resend.com](https://resend.com) and create a free account.
2. Navigate to **API Keys** → **Create API Key** → copy the key.
3. (Optional for custom domain) Go to **Domains** → **Add Domain** → follow DNS verification. For development, use the default `onboarding@resend.dev` sender which works without domain setup.
4. Set the key in `.env`:

```
RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxx
RESEND_FROM_EMAIL=onboarding@resend.dev
```

> **Note:** Free tier allows 100 emails/day and 3,000/month. Sufficient for a portfolio project.

---

### 3.4 Environment File

Create a `.env` file in the project root. A `.env.example` is committed to the repo. **Never commit `.env` itself.**

```env
# .env.example
# Supabase database
DATABASE_URL=postgresql+asyncpg://postgres.YOUR_PROJECT_REF:PASSWORD@aws-0-REGION.pooler.supabase.com:5432/postgres
ALEMBIC_DATABASE_URL=postgresql+asyncpg://postgres:PASSWORD@db.YOUR_PROJECT_REF.supabase.co:5432/postgres
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
# Supabase Auth
SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key
JWT_SECRET_KEY=change-this-to-a-long-random-string
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxx
RESEND_FROM_EMAIL=onboarding@resend.dev
API_BASE_URL=http://localhost:8000
```

---

## 4. Repository Structure

```
donation-platform/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI app factory
│   │   ├── config.py                # Settings via pydantic-settings
│   │   ├── database.py              # Async engine + session factory
│   │   ├── dependencies.py          # get_db, get_current_user
│   │   ├── models/
│   │   │   ├── __init__.py          # [FIX] Import all models here so Alembic autogenerate picks them up
│   │   │   ├── user.py
│   │   │   ├── item.py
│   │   │   ├── request.py
│   │   │   └── notification.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── item.py
│   │   │   ├── request.py
│   │   │   ├── analytics.py
│   │   │   └── pagination.py        # [FIX] PaginatedResponse generic schema
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── items.py
│   │   │   ├── requests.py
│   │   │   ├── matching.py
│   │   │   └── analytics.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── auth_service.py
│   │   │   ├── item_service.py
│   │   │   ├── request_service.py
│   │   │   ├── matching_service.py
│   │   │   └── email_service.py
│   │   └── worker/
│   │       ├── __init__.py
│   │       ├── celery_app.py
│   │       ├── tasks.py
│   │       └── email_templates.py
│   ├── alembic/
│   │   ├── env.py                   # [FIX] Must use async migration pattern — see Section 5
│   │   ├── script.py.mako
│   │   └── versions/
│   ├── alembic.ini
│   ├── Dockerfile                   # [FIX] Added — used by api and worker services
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_database_connection.py  # [FIX] Added to tree
│   │   ├── test_auth.py
│   │   ├── test_items.py
│   │   ├── test_requests.py
│   │   ├── test_matching.py
│   │   ├── test_tasks.py
│   │   └── test_analytics.py
│   └── requirements.txt
├── frontend/
│   ├── app.py                       # Streamlit entry point + nav guard
│   ├── styles.css                   # [FIX] Added to tree — single source of all custom CSS
│   ├── pages/
│   │   ├── 1_Login.py
│   │   ├── 2_Register.py
│   │   ├── 3_Browse_Items.py
│   │   ├── 4_My_Listings.py
│   │   ├── 5_My_Requests.py
│   │   ├── 6_NGO_Dashboard.py
│   │   └── 7_Analytics.py
│   ├── components/
│   │   ├── item_card.py
│   │   ├── request_card.py          # [FIX] Now fully specced in Section 8.4
│   │   └── status_badge.py
│   ├── api_client.py
│   └── requirements.txt
├── e2e_tests/
│   ├── conftest.py
│   ├── test_donor_flow.py
│   ├── test_recipient_flow.py
│   └── test_ngo_flow.py
├── docker-compose.yml
├── .env.example
└── README.md
```

**Rules for Codex:**
- No logic in routers — routers call service functions only.
- No raw SQL — use SQLAlchemy ORM exclusively.
- No duplicate Pydantic schemas — define once in `schemas/`, import everywhere.
- No inline CSS strings in Streamlit — use `st.markdown` with a single shared CSS block loaded from `frontend/styles.css`.

---

## 5. Data Models

All models live in `backend/app/models/`. Use SQLAlchemy 2.0 declarative style with `mapped_column` and Python type hints.

### [FIX] Alembic Async Configuration

Alembic's default `env.py` uses a synchronous engine. With `asyncpg` this will crash. The `env.py` must use the async migration pattern:

```python
# alembic/env.py — complete async pattern
import asyncio
from logging.config import fileConfig
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy import pool
from alembic import context

# [CRITICAL] Import all models so autogenerate sees them
from app.models import Base  # models/__init__.py re-exports Base and all models

config = context.config
fileConfig(config.config_file_name)
target_metadata = Base.metadata

def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online():
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()

asyncio.run(run_migrations_online())
```

`models/__init__.py` must import every model class and re-export `Base`:

```python
# models/__init__.py
from app.database import Base  # noqa: F401
from app.models.user import User, UserRole  # noqa: F401
from app.models.item import Item, ItemStatus, ItemCondition, ItemCategory  # noqa: F401
from app.models.request import DonationRequest, RequestStatus  # noqa: F401
from app.models.notification import Notification  # noqa: F401
```

---

### 5.1 User

```python
class UserRole(str, enum.Enum):
    donor = "donor"
    recipient = "recipient"
    ngo = "ngo"
    admin = "admin"

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    # [FIX] Added: required by matching_service.py category scoring
    preferred_categories: Mapped[Optional[list]] = mapped_column(
        ARRAY(String), server_default="{}"
    )
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    items: Mapped[List["Item"]] = relationship(back_populates="donor")
    requests: Mapped[List["DonationRequest"]] = relationship(back_populates="requester")
    # [FIX] Added: ORM relationship for Notification
    notifications: Mapped[List["Notification"]] = relationship(back_populates="user")
```

> **Codex note:** `ARRAY(String)` requires `from sqlalchemy.dialects.postgresql import ARRAY`. This is a PostgreSQL-specific type — do not use generic SQLAlchemy `JSON` as a substitute; arrays are more efficient for this use case and integrate with SQLAlchemy's ORM filtering.

---

### 5.2 Item

```python
class ItemStatus(str, enum.Enum):
    available = "available"
    reserved = "reserved"
    donated = "donated"
    removed = "removed"   # [FIX] Added: soft-delete status; distinct from donated

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
    donor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[ItemCategory] = mapped_column(Enum(ItemCategory), nullable=False)
    condition: Mapped[ItemCondition] = mapped_column(Enum(ItemCondition), nullable=False)
    quantity: Mapped[int] = mapped_column(default=1)
    status: Mapped[ItemStatus] = mapped_column(Enum(ItemStatus), default=ItemStatus.available)
    location: Mapped[Optional[Any]] = mapped_column(Geography(geometry_type="POINT", srid=4326))
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    pincode: Mapped[str] = mapped_column(String(10), nullable=False)
    image_url: Mapped[Optional[str]] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

    donor: Mapped["User"] = relationship(back_populates="items")
    requests: Mapped[List["DonationRequest"]] = relationship(back_populates="item")
```

> **PostGIS note for Codex:** Import `Geography` from `geoalchemy2`. The `location` column stores a lat/lng point. Use `ST_DWithin` for radius queries and `ST_Distance` for sorting by proximity. PostGIS runs as an extension within Supabase PostgreSQL and must be enabled in the Supabase dashboard before migrations run.

---

### 5.3 DonationRequest

```python
class RequestStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    picked_up = "picked_up"
    cancelled = "cancelled"

class DonationRequest(Base):
    __tablename__ = "donation_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), nullable=False)
    requester_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text)
    ngo_note: Mapped[Optional[str]] = mapped_column(Text)  # [FIX] Added: NGO bulk context note
    status: Mapped[RequestStatus] = mapped_column(Enum(RequestStatus), default=RequestStatus.pending)
    pickup_scheduled_at: Mapped[Optional[datetime]]
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

    item: Mapped["Item"] = relationship(back_populates="requests")
    requester: Mapped["User"] = relationship(back_populates="requests")
```

---

### 5.4 Notification

```python
class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    # [FIX] Added: back-reference to User
    user: Mapped["User"] = relationship(back_populates="notifications")
```

---

### [FIX] 5.5 Pagination Schema

Define once in `schemas/pagination.py`, import wherever list endpoints return paginated data:

```python
from typing import Generic, List, TypeVar
from pydantic import BaseModel

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int
```

The `GET /api/items/` endpoint returns `PaginatedResponse[ItemOut]`.

---

## 6. Backend — FastAPI

### 6.1 App Factory (`main.py`)

```python
# [FIX] Removed: import of non-existent create_tables from database.py
# Tables are managed exclusively by Alembic migrations.
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, items, requests, matching, analytics

def create_app() -> FastAPI:
    app = FastAPI(title="Community Donation Platform", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:8501"],  # [FIX] Scoped to Streamlit origin only
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
    app.include_router(items.router, prefix="/api/items", tags=["items"])
    app.include_router(requests.router, prefix="/api/requests", tags=["requests"])
    app.include_router(matching.router, prefix="/api/matching", tags=["matching"])
    app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])

    return app

app = create_app()
```

> **Codex note:** `database.py` provides `AsyncSession` and the `Base` declarative base only. It does not expose a `create_tables` function. Table creation is Alembic's responsibility.

---

### 6.2 Auth Router (`routers/auth.py`)

| Method | Path | Body | Response | Notes |
|--------|------|------|----------|-------|
| POST | `/api/auth/register` | `UserCreate` | `UserOut` | Hash password with bcrypt |
| POST | `/api/auth/login` | `OAuth2PasswordRequestForm` | `Token` | Return JWT |
| GET | `/api/auth/me` | — | `UserOut` | Requires bearer token |
| PATCH | `/api/auth/me/preferences` | `PreferencesUpdate` | `UserOut` | Update preferred_categories |

JWT payload must include: `sub` (user email), `role`, `user_id`, `exp`. Authentication is handled through Supabase Auth; the JWT issued by Supabase is validated by FastAPI middleware on every authenticated request.

**[FIX] `PreferencesUpdate` schema:**

```python
class PreferencesUpdate(BaseModel):
    preferred_categories: List[ItemCategory]
```

This endpoint allows recipients and NGOs to set their category preferences, which are then used by the matching engine.

---

### 6.3 Items Router (`routers/items.py`)

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| POST | `/api/items/` | Donor only | Create listing |
| GET | `/api/items/` | Any | Returns `PaginatedResponse[ItemOut]`; filters: `category`, `condition`, `city`, `radius_km`, `lat`, `lng`, `status`, `page`, `page_size` |
| GET | `/api/items/{id}` | Any | Single item with donor info |
| PATCH | `/api/items/{id}` | Donor (owner) | Update title/description/condition/quantity |
| DELETE | `/api/items/{id}` | Donor (owner) | [FIX] Soft-delete: set status=`removed`, not `donated` |

**Radius filter implementation in `item_service.py`:**

```python
from geoalchemy2.functions import ST_DWithin, ST_GeogFromText

# Add to query when lat/lng/radius_km are provided:
point = ST_GeogFromText(f"SRID=4326;POINT({lng} {lat})")
query = query.where(ST_DWithin(Item.location, point, radius_km * 1000))
```

**[FIX] Pagination implementation in `item_service.py`:**

```python
async def list_items(db: AsyncSession, filters: ItemFilter, page: int, page_size: int):
    base_query = build_filter_query(filters)  # returns Select object
    total = await db.scalar(select(func.count()).select_from(base_query.subquery()))
    items = (await db.execute(base_query.offset((page - 1) * page_size).limit(page_size))).scalars().all()
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size),
    )
```

---

### 6.4 Requests Router (`routers/requests.py`)

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| POST | `/api/requests/` | Recipient or NGO | Submit request for an item |
| GET | `/api/requests/my` | Any auth | Requests made by current user |
| GET | `/api/requests/incoming` | Donor | Requests on donor's items |
| PATCH | `/api/requests/{id}/approve` | Donor (item owner) | Approve → trigger Celery task |
| PATCH | `/api/requests/{id}/reject` | Donor (item owner) | Reject → trigger Celery task |
| PATCH | `/api/requests/{id}/pickup` | Donor (item owner) | Confirm pickup → item status=`donated`, request status=`picked_up` |
| PATCH | `/api/requests/{id}/cancel` | Request owner | Cancel own pending request |

**Business rules (enforce in `request_service.py`):**
- A user cannot request the same item twice (check by `item_id` + `requester_id` with status not in `[rejected, cancelled]`).
- An item can only have one approved request at a time. Approving one auto-rejects all other `pending` requests for the same item.
- Only items with status `available` can receive new requests.
- `ngo_note` is accepted in the POST body but only stored if the requester role is `ngo`.

---

### 6.5 Matching Router (`routers/matching.py`)

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| GET | `/api/matching/suggestions` | Recipient or NGO | Returns scored list of available items |

**Matching score formula (in `matching_service.py`):**

```python
# category_match: 1.0 if item.category in user.preferred_categories, else 0.5
# If user.preferred_categories is empty, category_match = 0.5 for all items (no penalty)
# proximity_score: 1 / (1 + distance_km) — requires lat/lng query params (optional; 0.5 if not provided)
# recency_score: 1 / (1 + days_since_listed)

score = (category_match * 0.5) + (proximity_score * 0.3) + (recency_score * 0.2)
```

Return the top 20 results sorted by score descending. Only items with status=`available` are considered.

---

### 6.6 Analytics Router (`routers/analytics.py`)

All analytics endpoints require `role == admin`. Queries must use SQLAlchemy aggregations, not raw SQL.

| Method | Path | Response |
|--------|------|----------|
| GET | `/api/analytics/summary` | `{total_donors, total_recipients, total_ngos, total_items_listed, total_items_donated, total_requests}` |
| GET | `/api/analytics/category-breakdown` | `[{category, count}]` — items with status=`donated` per category |
| GET | `/api/analytics/donation-trend` | `[{date, count}]` — donations per day for last 30 days |
| GET | `/api/analytics/top-cities` | `[{city, count}]` — top 10 cities by item listings (all statuses) |
| GET | `/api/analytics/platform-activity` | `[{date, new_users, new_items, new_requests}]` — last 30 days |

---

## 7. Background Jobs — Celery + Redis

### 7.1 Why Celery

Email sending is I/O-bound and must not block the API response. When a donor approves a request, the API returns `200 OK` immediately and Celery handles the email asynchronously.

### 7.2 Celery App (`worker/celery_app.py`)

```python
from celery import Celery
from app.config import settings

celery_app = Celery(
    "donation_platform",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)
```

### 7.3 Tasks (`worker/tasks.py`)

Define exactly these tasks. All parameters are plain JSON-serialisable types (str, int) — no ORM objects.

```python
@celery_app.task(name="send_request_notification")
def send_request_notification(
    donor_email: str,          # [FIX] Notifies the DONOR, so to= is donor_email
    donor_name: str,
    requester_name: str,
    item_title: str,
) -> None:
    """Notify donor that a new request was received for their item."""
    ...

@celery_app.task(name="send_approval_notification")
def send_approval_notification(
    requester_email: str,
    requester_name: str,
    item_title: str,
    donor_phone: str,
    pickup_instructions: str,
) -> None:
    """Notify recipient their request was approved."""
    ...

@celery_app.task(name="send_rejection_notification")
def send_rejection_notification(
    requester_email: str,
    requester_name: str,
    item_title: str,
) -> None:
    """Notify recipient their request was rejected."""
    ...

@celery_app.task(name="send_pickup_confirmation")
def send_pickup_confirmation(
    donor_email: str,
    donor_name: str,
    requester_email: str,      # [FIX] Added: task must notify both parties
    requester_name: str,
    item_title: str,
) -> None:
    """Send pickup confirmation email to both donor and recipient."""
    # Call send_email twice: once to donor, once to requester
    ...
```

### 7.4 Email Service (`services/email_service.py`)

```python
import resend
from app.config import settings

resend.api_key = settings.RESEND_API_KEY

def send_email(to: str, subject: str, html_body: str) -> None:
    resend.Emails.send({
        "from": settings.RESEND_FROM_EMAIL,
        "to": to,
        "subject": subject,
        "html": html_body,
    })
```

All email HTML templates are defined as Python string constants in `worker/email_templates.py`. No Jinja2.

### 7.5 Wiring Tasks into Services

In `request_service.py`, call `.delay()` **after** the DB commit, never before. Pattern:

```python
async def approve_request(db: AsyncSession, request_id: int, current_user: User):
    # ... update DB ...
    await db.commit()
    await db.refresh(request)
    # Fire task AFTER commit — data is now visible to the worker
    send_approval_notification.delay(
        requester_email=request.requester.email,
        requester_name=request.requester.full_name,
        item_title=request.item.title,
        donor_phone=current_user.phone or "not provided",
        pickup_instructions="Contact the donor to arrange pickup.",
    )
    return request
```

### 7.6 Starting the Worker

```bash
# From project root, after activating venv:
celery -A backend.app.worker.celery_app worker --loglevel=info
```

This is included in `docker-compose.yml` as a separate service.

---

## 8. Frontend — Streamlit

### 8.1 Session State Schema

All Streamlit pages share state via `st.session_state`. Define these keys and only these keys:

```python
# Set on login:
st.session_state["token"]      # str — JWT bearer token
st.session_state["user_id"]    # int
st.session_state["role"]       # str: "donor" | "recipient" | "ngo" | "admin"
st.session_state["full_name"]  # str
st.session_state["email"]      # str — needed for display and preference updates
```

---

### 8.2 API Client (`api_client.py`)

All HTTP calls go through this module. No `requests` or `httpx` calls anywhere else in the frontend.

```python
import os           # [FIX] os was missing from original snippet
import httpx
import streamlit as st
from typing import Any, Optional

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

def _headers() -> dict:
    token = st.session_state.get("token")
    return {"Authorization": f"Bearer {token}"} if token else {}

def get(path: str, params: Optional[dict] = None) -> Any:
    resp = httpx.get(f"{BASE_URL}{path}", headers=_headers(), params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()

def post(path: str, json: dict) -> Any:
    resp = httpx.post(f"{BASE_URL}{path}", headers=_headers(), json=json, timeout=10)
    resp.raise_for_status()
    return resp.json()

def patch(path: str, json: Optional[dict] = None) -> Any:
    resp = httpx.patch(f"{BASE_URL}{path}", headers=_headers(), json=json or {}, timeout=10)
    resp.raise_for_status()
    return resp.json()

def delete(path: str) -> Any:
    # [FIX] Added: required by My Listings page for item soft-delete
    resp = httpx.delete(f"{BASE_URL}{path}", headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()
```

---

### 8.3 Pages

#### `pages/1_Login.py`
- Email + password form.
- On success: store `token`, `user_id`, `role`, `full_name`, `email` in session_state, redirect to Browse Items via `st.switch_page`.
- Show role-appropriate welcome message.

#### `pages/2_Register.py`
- Full name, email, password, role selector (Donor / Recipient / NGO), phone (optional).
- After registration, auto-login (call `/api/auth/login`) and redirect.

#### `pages/3_Browse_Items.py`
- Sidebar filters: category (multiselect), condition, city (text), radius (slider 5–100 km), status=available.
- Item grid using `components/item_card.py`.
- Each card has a "Request This Item" button (visible only to Recipients and NGOs).
- Clicking the button opens an `st.dialog` with a message textarea, optional NGO Note field (visible if role=ngo), and submit button.

#### `pages/4_My_Listings.py`
- Donor-only page (redirect others to Browse Items).
- "Add New Listing" expander with form: title, category, condition, quantity, description, city, pincode, lat, lng (optional).
- Table of donor's items with status badges.
- Incoming requests per item shown in expandable sections using `components/request_card.py`.
- Approve/Reject buttons on each pending request row.
- "Mark Picked Up" button on approved requests.
- "Remove Listing" button calls DELETE endpoint → sets status=`removed`.

#### `pages/5_My_Requests.py`
- Recipient-only page.
- Table of submitted requests with status badge, item title, donor name, and timestamps using `components/request_card.py`.
- "Cancel" button on pending requests.

#### `pages/6_NGO_Dashboard.py`
- NGO-only page.
- Browse items (same filter sidebar as page 3) with additional "NGO Note" field on request submission.
- Table of all NGO's requests with status badges.
- Summary metrics: total requested, approved, distributed.

#### `pages/7_Analytics.py`
- Admin-only page (redirect others).
- Four Plotly charts in a 2×2 grid:
  1. Bar chart — Category breakdown of donated items.
  2. Line chart — Donation trend over last 30 days.
  3. Bar chart — Top 10 cities by item listings.
  4. Grouped bar chart — Platform activity (new users, items, requests per day).
- Summary metric cards at the top: total donors, recipients, items donated, people helped (= total `picked_up` requests).

---

### 8.4 Shared Components

#### `components/item_card.py`
Single function `render_item_card(item: dict, show_request_button: bool, on_request_click: callable = None)`. Renders a styled card with title, category badge, condition, city, and status badge. The `on_request_click` callback is called with `item["id"]` when the request button is clicked. No duplicated card HTML anywhere else.

#### `components/request_card.py`
**[FIX] Now fully specced.** Single function `render_request_card(request: dict, viewer_role: str)`. Renders: item title, requester name (shown to donor) or donor name (shown to recipient/NGO), status badge, message, ngo_note (if present and viewer is donor or ngo), timestamps, and action buttons appropriate to `viewer_role`. No action button logic lives in page files.

#### `components/status_badge.py`
Single function `status_badge(status: str) -> str`. Returns an HTML `<span>` with the GiveCircle colour-coded chip (see Section 9). Import and use in all pages and components via `st.markdown(..., unsafe_allow_html=True)`.

---

## 9. Brand Design System — GiveCircle

> This section translates the GiveCircle brand guidelines into a Streamlit-compatible implementation. Codex must implement all styles via `frontend/styles.css` injected once in `app.py`. No inline style strings in any page or component file.

---

### 9.1 Colour Tokens

These are the canonical values. Use these variable names as comments in `styles.css` for maintainability.

```css
/* === GiveCircle Colour Tokens === */

/* Backgrounds */
/* --bg-primary:    #0A0B07  — page root */
/* --bg-secondary:  #111309  — sidebar, panels */
/* --bg-tertiary:   #181A0E  — nested panels */
/* --surface-1:     #1F2211  — cards, modals */
/* --surface-2:     #272B14  — nested cards */
/* --surface-hover: #2F3419  — hover state */

/* Lime accent */
/* --lime-400: #BADE52  — all lime text */
/* --lime-500: #A7D129  — primary CTA buttons only */
/* --lime-600: #85A820  — focus rings, input borders */
/* --lime-700: #6B8A1A  — hover on lime elements */

/* Olive structure */
/* --olive-500: #616F39  — secondary buttons, progress */
/* --olive-600: #4E5530  — dividers, inactive borders */
/* --olive-700: #3E4326  — border-left accent bars only */

/* Text */
/* --text-primary:   #E8EDE0  — headings, key data */
/* --text-secondary: #9AA582  — body copy, labels */
/* --text-muted:     #616B4E  — captions only */

/* Semantic */
/* --success: #A7D129  */
/* --warning: #D4A017  */
/* --error:   #E05C5C  */
/* --info:    #7BAFD4  */
```

---

### 9.2 Streamlit Theme Configuration (`frontend/.streamlit/config.toml`)

Create this file. It controls Streamlit's native theme before any CSS injection:

```toml
[theme]
base = "dark"
backgroundColor = "#0A0B07"
secondaryBackgroundColor = "#111309"
textColor = "#E8EDE0"
primaryColor = "#A7D129"
font = "sans serif"
```

> `primaryColor` affects Streamlit's native interactive elements (sliders, checkboxes, radio buttons, progress bars) without needing custom CSS.

---

### 9.3 Global CSS Injection (`frontend/styles.css`)

Load this file once in `app.py`:

```python
# app.py — top of file
def load_css():
    with open("styles.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()
```

The complete `styles.css` content Codex must write:

```css
/* =============================================
   GiveCircle — Streamlit Global Styles
   ============================================= */

/* --- Page root --- */
.stApp {
    background-color: #0A0B07;
    color: #E8EDE0;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-size: 14px;
    line-height: 1.6;
}

/* --- Sidebar --- */
[data-testid="stSidebar"] {
    background-color: #111309;
    border-right: 0.5px solid rgba(167, 209, 41, 0.08);
}
[data-testid="stSidebar"] .stMarkdown p {
    color: #9AA582;
    font-size: 12px;
}

/* --- Main content padding --- */
.main .block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
    max-width: 1100px;
}

/* --- Headings --- */
h1 { font-size: 22px; font-weight: 500; color: #E8EDE0; line-height: 1.3; }
h2 { font-size: 18px; font-weight: 500; color: #E8EDE0; line-height: 1.4; }
h3 { font-size: 15px; font-weight: 500; color: #E8EDE0; line-height: 1.5; }

/* --- Body text --- */
p, li { color: #9AA582; font-size: 14px; font-weight: 400; }

/* --- Metric cards (st.metric) --- */
[data-testid="stMetric"] {
    background-color: #1F2211;
    border: 0.5px solid rgba(167, 209, 41, 0.08);
    border-radius: 14px;
    padding: 14px 16px;
}
[data-testid="stMetricLabel"] { color: #9AA582; font-size: 12px; font-weight: 400; }
[data-testid="stMetricValue"] { color: #BADE52; font-size: 28px; font-weight: 500; }

/* --- Buttons --- */
/* Primary button */
.stButton > button[kind="primary"],
.stButton > button {
    background-color: #A7D129;
    color: #0A0B07;
    border: none;
    border-radius: 10px;
    font-weight: 500;
    font-size: 14px;
    padding: 10px 20px;
    transition: background-color 150ms ease;
}
.stButton > button:hover {
    background-color: #6B8A1A;
    color: #0A0B07;
}
.stButton > button:active {
    transform: scale(0.98);
}

/* Secondary button — use st.button with key prefix "secondary_" and override via class if needed */
.stButton > button[kind="secondary"] {
    background-color: transparent;
    color: #BADE52;
    border: 1px solid #616F39;
    border-radius: 10px;
}
.stButton > button[kind="secondary"]:hover {
    background-color: #2F3419;
}

/* --- Form inputs --- */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div,
.stMultiSelect > div > div {
    background-color: #111309;
    border: 0.5px solid rgba(167, 209, 41, 0.16);
    border-radius: 10px;
    color: #E8EDE0;
    font-size: 14px;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border: 1px solid #85A820;
    box-shadow: 0 0 0 3px rgba(167, 209, 41, 0.15);
    outline: none;
}
/* Placeholder colour */
.stTextInput input::placeholder,
.stTextArea textarea::placeholder {
    color: #616B4E;
}

/* --- Expander --- */
.streamlit-expanderHeader {
    background-color: #1F2211;
    border: 0.5px solid rgba(167, 209, 41, 0.08);
    border-radius: 10px;
    color: #E8EDE0;
    font-weight: 500;
}
.streamlit-expanderContent {
    background-color: #181A0E;
    border: 0.5px solid rgba(167, 209, 41, 0.08);
    border-top: none;
    border-radius: 0 0 10px 10px;
}

/* --- Dataframe / tables --- */
[data-testid="stDataFrame"] {
    border: 0.5px solid rgba(167, 209, 41, 0.08);
    border-radius: 14px;
    overflow: hidden;
}

/* --- Divider --- */
hr {
    border: none;
    border-top: 0.5px solid rgba(167, 209, 41, 0.08);
    margin: 1.5rem 0;
}

/* --- Alerts / info boxes --- */
.stAlert {
    background-color: rgba(123, 175, 212, 0.08);
    border-left: 3px solid #7BAFD4;
    border-radius: 6px;
    color: #9AA582;
}

/* --- Slider --- */
.stSlider > div > div > div {
    color: #9AA582;
}

/* --- Tabs --- */
.stTabs [data-baseweb="tab-list"] {
    background-color: #111309;
    border-bottom: 0.5px solid rgba(167, 209, 41, 0.08);
}
.stTabs [data-baseweb="tab"] {
    color: #9AA582;
    font-weight: 400;
}
.stTabs [aria-selected="true"] {
    color: #BADE52;
    border-bottom: 2px solid #A7D129;
    background-color: transparent;
}

/* --- Plotly chart containers --- */
.js-plotly-plot {
    background-color: #1F2211 !important;
    border-radius: 14px;
    border: 0.5px solid rgba(167, 209, 41, 0.08);
}
```

---

### 9.4 Item Card HTML Template

Used inside `components/item_card.py`. The function builds this HTML string and calls `st.markdown(html, unsafe_allow_html=True)`:

```python
def render_item_card(item: dict, show_request_button: bool, on_request_click=None):
    from components.status_badge import status_badge, category_badge

    html = f"""
    <div style="
        background-color: #1F2211;
        border: 0.5px solid rgba(167,209,41,0.08);
        border-radius: 14px;
        padding: 14px 16px;
        margin-bottom: 12px;
        transition: background-color 150ms ease;
    ">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:8px;">
            <span style="font-size:15px; font-weight:500; color:#E8EDE0;">{item['title']}</span>
            {status_badge(item['status'])}
        </div>
        <div style="margin-bottom:6px;">
            {category_badge(item['category'])}
        </div>
        <p style="font-size:14px; color:#9AA582; margin:6px 0;">{item['description'][:120]}{'...' if len(item['description']) > 120 else ''}</p>
        <div style="display:flex; gap:12px; font-size:12px; color:#616B4E; margin-top:8px;">
            <span>📍 {item['city']}</span>
            <span>Condition: {item['condition'].replace('_', ' ').title()}</span>
            <span>Qty: {item['quantity']}</span>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

    if show_request_button and on_request_click:
        if st.button("Request This Item", key=f"req_{item['id']}"):
            on_request_click(item["id"])
```

---

### 9.5 Status Badge and Category Badge

Both live in `components/status_badge.py`:

```python
def status_badge(status: str) -> str:
    """Returns an HTML span chip for item or request status."""
    config = {
        "available":  ("rgba(167,209,41,0.12)",  "#BADE52"),
        "reserved":   ("rgba(123,175,212,0.12)", "#7BAFD4"),
        "donated":    ("rgba(97,107,78,0.25)",   "#9AA582"),
        "removed":    ("rgba(224,92,92,0.10)",   "#E05C5C"),
        "pending":    ("rgba(212,160,23,0.12)",  "#D4BA50"),
        "approved":   ("rgba(167,209,41,0.12)",  "#BADE52"),
        "rejected":   ("rgba(224,92,92,0.10)",   "#E05C5C"),
        "picked_up":  ("rgba(97,107,78,0.25)",   "#9AA582"),
        "cancelled":  ("rgba(97,107,78,0.25)",   "#9AA582"),
    }
    bg, color = config.get(status, ("rgba(97,107,78,0.25)", "#9AA582"))
    label = status.replace("_", " ").title()
    return (
        f'<span style="background:{bg}; color:{color}; border:0.5px solid {color}33; '
        f'border-radius:6px; padding:2px 8px; font-size:11px; font-weight:500;">'
        f'{label}</span>'
    )

def category_badge(category: str) -> str:
    """Returns an olive-tinted chip for item category."""
    return (
        f'<span style="background:rgba(97,111,57,0.35); color:#CEEA7A; '
        f'border-radius:6px; padding:2px 8px; font-size:11px; font-weight:500;">'
        f'{category.title()}</span>'
    )
```

---

### 9.6 Plotly Chart Theme

All Plotly figures must use this base layout. Define it once in `frontend/chart_theme.py` and import in `pages/7_Analytics.py`:

```python
# frontend/chart_theme.py
PLOTLY_LAYOUT = dict(
    paper_bgcolor="#1F2211",
    plot_bgcolor="#1F2211",
    font=dict(family="Inter, sans-serif", color="#9AA582", size=12),
    title_font=dict(color="#E8EDE0", size=15, family="Inter, sans-serif"),
    colorway=["#A7D129", "#616F39", "#7BAFD4", "#D4A017", "#E05C5C"],
    xaxis=dict(
        gridcolor="rgba(167,209,41,0.06)",
        linecolor="rgba(167,209,41,0.08)",
        tickfont=dict(color="#9AA582"),
    ),
    yaxis=dict(
        gridcolor="rgba(167,209,41,0.06)",
        linecolor="rgba(167,209,41,0.08)",
        tickfont=dict(color="#9AA582"),
    ),
    margin=dict(l=40, r=20, t=50, b=40),
    hoverlabel=dict(
        bgcolor="#272B14",
        bordercolor="rgba(167,209,41,0.16)",
        font_color="#E8EDE0",
    ),
)

def apply_theme(fig):
    """Call fig.update_layout(**PLOTLY_LAYOUT) and return fig."""
    fig.update_layout(**PLOTLY_LAYOUT)
    return fig
```

Usage in analytics page:

```python
from chart_theme import apply_theme
import plotly.express as px

fig = px.bar(df, x="category", y="count", title="Donations by category")
fig = apply_theme(fig)
st.plotly_chart(fig, use_container_width=True)
```

---

### 9.7 Brand Rules Codex Must Not Violate

These are hard constraints derived from the GiveCircle brand guidelines:

1. **Lime (`#A7D129`) must only fill buttons.** Never use it as a card background, section header fill, or modal background. As text, always use `#BADE52` (lime-400), not `#A7D129`.
2. **No pure `#000000` backgrounds.** The page root is `#0A0B07`. Pure black is only permitted as text colour on lime-filled buttons.
3. **Font weight max 500.** Never use `font-weight: 600` or `700` in any stylesheet or inline style.
4. **No drop shadows.** Elevation is achieved by surface lightness steps. The only permitted `box-shadow` is the focus ring: `0 0 0 3px rgba(167,209,41,0.15)`.
5. **No gradients on surfaces.** Gradient fills are only permitted on progress bar elements.
6. **Sentence case everywhere.** No Title Case in headings written to the UI. Page titles use sentence case.
7. **Lime appears at most 2–3 times per screen.** Primary CTA, 1–2 status indicators or key data points, and an active nav label. All else uses olive or text-secondary.
8. **No amber (`#D4A017`) and lime on the same component.** One warm accent per element.
9. **Semantic fills at 12% opacity maximum.** Never solid semantic colour on any container larger than a button.
10. **All borders use lime-based transparency.** `rgba(167,209,41,0.08)` for default, `rgba(167,209,41,0.16)` for emphasis. Solid `#3E4326` hex is only used as a `border-left` accent bar.

---

## 10. Build Phases

Codex must build in this exact sequence. Do not proceed to the next phase until the current phase passes its tests.

---

### Phase 1 — Infrastructure

**Tasks:**
1. Create `docker-compose.yml` with four services: `db` (postgis/postgis:16-3.4), `redis` (redis:7-alpine), `api` (FastAPI, port 8000), `worker` (Celery — same image as api, different command).
2. **[FIX] Create `backend/Dockerfile`** — both `api` and `worker` services use this image:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
```

3. Create `backend/app/config.py` using `pydantic-settings`. Every field marked `Required` in Section 12 must raise a `ValidationError` at startup if missing.
4. Create `backend/app/database.py` with async SQLAlchemy engine, `AsyncSession` factory, and `Base` declarative base. No `create_tables` function.
5. Create `backend/alembic.ini` and `backend/alembic/env.py` using the async pattern in Section 5.
6. Create `.env.example`.
7. Create `frontend/.streamlit/config.toml` with theme values from Section 9.2.

**Tests:** `pytest backend/tests/test_database_connection.py` — assert the engine can connect and execute `SELECT 1`.

---

### Phase 2 — Models and Migrations

**Tasks:**
1. Implement all four models in `backend/app/models/`.
2. **[FIX] Populate `models/__init__.py`** with all model imports as shown in Section 5.
3. Run `alembic revision --autogenerate -m "initial"` — verify the migration creates all tables, all enum types, and the PostGIS `geography` column on `items`.
4. Run `alembic upgrade head`.

**Tests:** `pytest backend/tests/test_models.py` — create one instance of each model, persist to test DB, assert round-trip integrity and that all relationships load without error.

---

### Phase 3 — Auth

**Tasks:**
1. Implement `UserCreate`, `UserOut`, `Token`, `PreferencesUpdate` schemas.
2. Implement `auth_service.py`: `create_user`, `authenticate_user`, `create_access_token`, `get_user_from_token`, `update_preferences`.
3. Implement `routers/auth.py` with all four endpoints.
4. Implement `dependencies.py`: `get_db`, `get_current_user`, `require_role`.

**Tests:** `pytest backend/tests/test_auth.py`
- Register → assert 201, user in DB, password hashed (not stored in plaintext).
- Login with correct credentials → assert JWT returned with correct `role` in payload.
- Login with wrong password → assert 401.
- GET `/me` with valid token → assert correct user data.
- GET `/me` with invalid/expired token → assert 401.
- PATCH `/me/preferences` → assert preferred_categories updated.

---

### Phase 4 — Items

**Tasks:**
1. Implement all item schemas including `PaginatedResponse[ItemOut]`.
2. Implement `item_service.py` with PostGIS radius filtering and pagination.
3. Implement `routers/items.py`.

**Tests:** `pytest backend/tests/test_items.py`
- Create item as Donor → assert 201, status=`available`.
- Create item as Recipient → assert 403.
- List items with category filter → assert only matching items returned.
- List items with radius filter → assert only the near item returned.
- List items with pagination → assert `total_pages` correct, second page returns correct slice.
- Update item as owner → assert 200.
- Update item as non-owner → assert 403.
- DELETE item → assert status=`removed` (not `donated`), item still in DB.

---

### Phase 5 — Requests and Workflow

**Tasks:**
1. Implement request schemas (include `ngo_note` field).
2. Implement `request_service.py` with all business rules.
3. Implement `routers/requests.py`.

**Tests:** `pytest backend/tests/test_requests.py`
- Submit request (recipient) → assert status=`pending`.
- Submit request (ngo) with ngo_note → assert ngo_note stored.
- Duplicate request → assert 400.
- Request on non-available item → assert 400.
- Approve request → assert approved, all other pending requests for same item auto-rejected.
- Reject request → assert rejected.
- Non-owner approving → assert 403.
- Mark pickup → assert item status=`donated`, request status=`picked_up`.
- Cancel own pending request → assert status=`cancelled`.

---

### Phase 6 — Celery Tasks

**Tasks:**
1. Implement `celery_app.py`, `tasks.py`, `email_service.py`, `email_templates.py`.
2. Wire task `.delay()` calls into `request_service.py` after DB commits.

**Tests:** `pytest backend/tests/test_tasks.py` — mock `resend.Emails.send`, call each task directly, assert the mock was called with correct `to` address and that the `html` string contains expected substrings (item title, recipient name).

---

### Phase 7 — Matching and Analytics

**Tasks:**
1. Implement `matching_service.py` with scoring formula.
2. Implement `routers/matching.py`.
3. Implement analytics queries in `routers/analytics.py`.
4. **[FIX] Seed an admin user in `tests/conftest.py`** to enable analytics endpoint tests.

**Tests:**
- `pytest backend/tests/test_matching.py` — seed 5 items and a recipient with preferences; assert top result has highest composite score; assert items with status != `available` are excluded.
- `pytest backend/tests/test_analytics.py` — seed known data with an admin user; assert summary counts exact; category breakdown sums to total donated items.

---

### Phase 8 — Streamlit Frontend

**Tasks:**
1. Create `frontend/.streamlit/config.toml`.
2. Create `frontend/styles.css` with all CSS from Section 9.3.
3. Create `frontend/chart_theme.py`.
4. Implement `api_client.py` (with `delete` method).
5. Implement all shared components (`item_card.py`, `request_card.py`, `status_badge.py`).
6. Implement all 7 pages.
7. Implement `app.py`: load CSS, implement navigation guard (unauthenticated users see only Login and Register in sidebar; all other pages redirect to Login if token is absent from session_state).

**Manual smoke test:** Start API + Streamlit, register as Donor, list an item, register as Recipient, request the item, approve as Donor, confirm pickup. Verify status trail through all states. Verify visual appearance matches brand rules in Section 9.7.

---

### Phase 9 — E2E Tests (Playwright)

**Tasks:**
1. Install: `pip install pytest-playwright && playwright install chromium`
2. Create `e2e_tests/conftest.py`:
   - `base_url` fixture: `http://localhost:8501`
   - `api_url` fixture: `http://localhost:8000`
   - `donor_credentials`, `recipient_credentials`, `ngo_credentials`, `admin_credentials` fixtures: create test users via POST `/api/auth/register` in `session` scope setup.
   - **[FIX] Teardown:** Call `PATCH /api/requests/{id}/cancel` and `DELETE /api/items/{id}` for test data cleanup. Do NOT call a non-existent DELETE `/users` endpoint. Test user cleanup is handled by a direct DB `DELETE` statement run via `psycopg2` against the Supabase PostgreSQL test database in the session teardown fixture (not through the API).

**Test: `test_donor_flow.py`**
```
1. Navigate to Register page, fill form as Donor, submit.
2. Assert redirect to Browse Items page.
3. Navigate to My Listings, open Add New Listing expander, fill form, submit.
4. Assert new item appears in listings table with status chip "Available".
```

**Test: `test_recipient_flow.py`**
```
1. Log in as Recipient.
2. Navigate to Browse Items, apply category filter matching seeded item.
3. Assert item card is visible with correct title.
4. Click "Request This Item", fill message, submit.
5. Navigate to My Requests, assert request appears with status "Pending".
```

**Test: `test_ngo_flow.py`**
```
1. Log in as NGO.
2. Navigate to NGO Dashboard, submit request with NGO Note text.
3. Assert request appears in NGO requests table.
4. Assert NGO Note text is visible in the request row.
```

**All E2E tests must use `page.wait_for_selector` and `expect(locator).to_be_visible()`. No `time.sleep()` calls.**

---

## 11. Testing Strategy

### Unit Tests
- Use `pytest` with `pytest-asyncio`.
- Each test function is independent — use a per-function `AsyncSession` with `begin_nested` that rolls back after the test.
- Mock all external calls (Resend) using `unittest.mock.patch`.

### Integration Tests
- Run against a dedicated Supabase test database (separate Supabase project or isolated schema).
- `conftest.py` session fixture runs `alembic upgrade head` against the test DB before the suite and `alembic downgrade base` after.
- The test `DATABASE_URL` must be set in the test environment, not inferred from `.env`.

### E2E Tests
- Playwright tests run against live servers (FastAPI + Streamlit + Celery).
- Start all services before running E2E suite.
- E2E tests live in a separate directory and run with a separate `pytest` command.

### Coverage
- Backend unit + integration tests must achieve ≥ 80% line coverage.
- Run: `pytest --cov=app --cov-report=term-missing`

---

## 12. Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | **Yes** | — | Async Supabase PostgreSQL connection string (application / session pooler) |
| `ALEMBIC_DATABASE_URL` | **Yes** | — | Async Supabase PostgreSQL direct connection string (Alembic migrations) |
| `SUPABASE_URL` | **Yes** | — | Supabase project URL (`https://YOUR_PROJECT_REF.supabase.co`) |
| `SUPABASE_ANON_KEY` | **Yes** | — | Supabase Auth anon/public key for client-side session handling |
| `CELERY_BROKER_URL` | **Yes** | — | Redis URL for Celery broker |
| `CELERY_RESULT_BACKEND` | **Yes** | — | Redis URL for task results |
| `JWT_SECRET_KEY` | **Yes** | — | Random 32+ char string for signing JWTs (used alongside Supabase Auth JWT validation) |
| `JWT_ALGORITHM` | No | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `60` | JWT expiry in minutes |
| `RESEND_API_KEY` | **Yes** | — | Resend API key (`re_...`) |
| `RESEND_FROM_EMAIL` | No | `onboarding@resend.dev` | Sender email address |
| `API_BASE_URL` | No | `http://localhost:8000` | Used by Streamlit to reach FastAPI |

---

## 13. Running the Project

### Option A — Docker Compose (recommended)

```bash
# 1. Clone the repo and create your .env from the example:
cp .env.example .env
# Edit .env with your Resend API key and a strong JWT_SECRET_KEY

# 2. Build and start all services:
docker compose up --build

# 3. Run migrations (first time only):
docker compose exec api alembic upgrade head

# 4. Open the app:
# Streamlit:  http://localhost:8501
# API docs:   http://localhost:8000/docs
```

### Option B — Local (no Docker)

```bash
# Prerequisites: Python 3.11+, Supabase project with PostgreSQL + PostGIS, Redis 7

# 1. Create virtual environments:
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cd ../frontend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Ensure Supabase project is reachable and Redis is running (see Section 3 for setup)

# 3. Copy and fill .env
cp .env.example .env

# 4. Run migrations:
cd backend && alembic upgrade head

# 5. Start FastAPI:
uvicorn app.main:app --reload --port 8000

# 6. Start Celery worker (new terminal):
celery -A app.worker.celery_app worker --loglevel=info

# 7. Start Streamlit (new terminal):
cd frontend && streamlit run app.py

# App: http://localhost:8501 | API docs: http://localhost:8000/docs
```

### Running Tests

```bash
# Backend unit + integration tests:
cd backend
pytest tests/ -v --cov=app --cov-report=term-missing

# E2E tests (requires all services running):
cd e2e_tests
pytest -v
```

---

*End of PRD v2. All 20 issues from the v1 critique have been addressed. The GiveCircle design system has been fully integrated into Section 9.*
