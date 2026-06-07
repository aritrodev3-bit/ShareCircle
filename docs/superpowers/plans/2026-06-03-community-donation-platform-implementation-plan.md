# Community Donation Platform Updated Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a production-conscious MVP for a community donation platform with donor listings, recipient/NGO requests, transactional approval workflows, email notifications, location-aware matching, admin analytics, and a Streamlit frontend.

**Architecture:** FastAPI owns the API and business rules, Supabase-managed PostgreSQL/PostGIS is the source of truth, Redis/Celery handles post-commit email work, and Streamlit provides the MVP frontend. The implementation enforces explicit lifecycle transitions, privacy boundaries, transactional request approval/pickup, and stable API contracts before frontend build-out.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, Alembic, Supabase PostgreSQL + PostGIS, Redis, Celery, Resend, Streamlit, Plotly, httpx, pytest, pytest-asyncio, Playwright.

---

## Architecture Overview

Build a production-conscious MVP using FastAPI, Supabase PostgreSQL/PostGIS, Redis/Celery, and Streamlit. The platform connects donors, recipients, NGOs, and admins through item listing, request approval, pickup confirmation, location-aware matching, email notifications, and analytics.

This revised plan treats the system as an MVP with explicit production safeguards:
- Item quantity is display-only for v1.
- State transitions are explicit and enforced.
- Request approval and pickup are transactional.
- Analytics use durable lifecycle timestamps, not mutable `updated_at`.
- In-app notifications and admin moderation are deferred unless explicitly added later.

## System Components

Backend API:
- `auth`: registration, login, Supabase Auth JWT session handling, `/me`, preferences.
- `items`: donor listing CRUD, filtering, pagination, soft delete.
- `requests`: item request lifecycle with strict transition validation.
- `matching`: ranked item suggestions for recipients/NGOs.
- `analytics`: admin-only reporting.
- `health`: API, DB, and Redis health checks.
- `dependencies`: DB sessions, current user, role guards.

Data layer:
- SQLAlchemy async models: `User`, `Item`, `DonationRequest`.
- Defer `Notification` unless in-app notifications are implemented.
- Supabase-managed PostgreSQL is used as the application database; Supabase Auth is used for authentication; Supabase Storage, Realtime, Edge Functions, and Data API are not used in v1.
- PostgreSQL-specific types: `ARRAY(String)` for preferences, PostGIS `Geography(POINT, 4326)` for item location.
- PostGIS must be enabled in the Supabase project before migrations run.
- Manual Alembic migration review required for PostGIS extension assumptions, spatial indexes, relational indexes, and enum creation.

Background jobs:
- Celery worker with Redis broker/result backend.
- Email tasks only after committed DB state.
- Resend failures must not roll back business state.
- Task logging and retry limits required.

Frontend:
- Streamlit app with session-state auth.
- Shared API client.
- Shared components render UI and accept callbacks; page files own API actions and refresh behavior.
- Pages: login, register, browse items, my listings, my requests, NGO dashboard, analytics.

Testing:
- Backend unit/integration tests per phase.
- Supabase-backed PostgreSQL/PostGIS test database or isolated Supabase staging project.
- E2E Playwright tests against live services.
- Minimum 80% backend line coverage.

## Dependency Graph

Infrastructure first:
- Docker Compose for API/worker/frontend/Redis, Supabase database credentials, env validation, database engine, Alembic, health checks.

Data model foundation:
- Models and migrations must exist before all services.
- Indexes, timestamps, and constraints must be included from the initial migration.

Auth before business flows:
- Items, requests, matching, analytics, and frontend routing depend on JWT and role guards.

Items before requests:
- Requests require existing available items.
- Matching and analytics depend on item lifecycle states.

Requests before jobs:
- Email jobs are triggered by request state changes.
- Tasks must dispatch only after commit.

Matching and analytics after workflows:
- Matching depends on available items, preferences, and optional location.
- Analytics depends on durable lifecycle timestamps.

Frontend after API contracts:
- Build frontend only after response shapes and error contracts are stable.

## Database Design Review

Use these core tables for v1:
- `users`
- `items`
- `donation_requests`
- Optional/deferred: `audit_events`

Remove or defer `notifications` unless in-app notification endpoints and UI are added.

Supabase database and auth decisions:
- Use Supabase as managed PostgreSQL/PostGIS.
- Use Supabase Auth for user registration, login, and JWT session management; FastAPI middleware validates Supabase-issued JWTs.
- Do not expose Supabase service-role or secret API keys to the frontend.
- The Supabase anon/public key may be used for client-side Supabase Auth session handling only.
- Prefer Supabase's direct database connection for Alembic migrations.
- Prefer Supabase's session pooler or direct connection for the FastAPI async SQLAlchemy app. Avoid transaction pooling for code paths that rely on connection/session behavior unless tested with SQLAlchemy and Alembic.
- Use a separate Supabase project for tests/staging, or a separate test database/schema if the chosen Supabase plan supports the workflow safely.

Required model changes:
- `items.quantity` is display-only in v1. It does not support partial fulfillment.
- Add `items.donated_at`.
- Add `items.removed_at`.
- Add `donation_requests.approved_at`.
- Add `donation_requests.picked_up_at`.
- Add `donation_requests.cancelled_at`.
- Keep `created_at` and `updated_at` timezone-aware.

Required indexes:
- Unique index on `users.email`.
- Indexes on `items.status`, `items.category`, `items.city`, `items.donor_id`.
- Spatial index on `items.location`.
- Indexes on `donation_requests.item_id`, `donation_requests.requester_id`, `donation_requests.status`.

State rules:
- Item states:
  - `available -> reserved`
  - `reserved -> donated`
  - `available -> removed`
  - `reserved -> removed` only if approved request is also rejected/cancelled by service logic
- Request states:
  - `pending -> approved`
  - `pending -> rejected`
  - `pending -> cancelled`
  - `approved -> picked_up`
- All invalid transitions return `409 Conflict`.

Transactional rules:
- Approval must lock the target request and item.
- Approval must approve one request, reject competing pending requests, and set item status to `reserved` in one transaction.
- Pickup must lock the approved request and item, then set request `picked_up`, item `donated`, and item `donated_at`.

## API Design Review

Required endpoints:
- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `PATCH /api/auth/me/preferences`
- `POST /api/items/`
- `GET /api/items/`
- `GET /api/items/{id}`
- `PATCH /api/items/{id}`
- `DELETE /api/items/{id}`
- `POST /api/requests/`
- `GET /api/requests/my`
- `GET /api/requests/incoming`
- `PATCH /api/requests/{id}/approve`
- `PATCH /api/requests/{id}/reject`
- `PATCH /api/requests/{id}/pickup`
- `PATCH /api/requests/{id}/cancel`
- `GET /api/matching/suggestions`
- `GET /api/analytics/summary`
- `GET /api/analytics/category-breakdown`
- `GET /api/analytics/donation-trend`
- `GET /api/analytics/top-cities`
- `GET /api/analytics/platform-activity`
- `GET /health`
- `GET /health/db`
- `GET /health/redis`

Response contract requirements:
- `ItemOut` includes donor id and donor name.
- `ItemOut` must not expose donor phone before approval.
- Request responses include request id, item id, item title, requester name, donor name, status, message, `ngo_note`, timestamps, and lifecycle timestamps.
- Approved request detail may expose donor phone only to the approved requester and donor.
- Analytics summary includes `people_helped`, based on picked-up requests.

Query rules:
- `GET /api/items/` accepts repeated `category` query params.
- `status` defaults to `available`.
- `mine=true` returns authenticated donor-owned listings.
- `page` default is `1`.
- `page_size` default is `20`, max is `100`.
- Invalid pagination returns `422`.
- Radius filtering requires all of `lat`, `lng`, and `radius_km`; partial radius input returns `422`.
- Coordinate validation:
  - `lat` between `-90` and `90`
  - `lng` between `-180` and `180`
  - `radius_km` greater than `0`, capped at `100`

API error contract:
- `400`: business input error.
- `401`: unauthenticated.
- `403`: authenticated but unauthorized.
- `404`: missing resource.
- `409`: invalid state transition or conflict.
- `422`: malformed body/query.

## Security Review

Authentication:
- Passwords managed through Supabase Auth; never stored in plaintext in the application database.
- JWT payload includes `sub`, `role`, `user_id`, `exp`; issued and signed by Supabase Auth.
- Middleware validates the Supabase-issued JWT on every authenticated request, checking token expiry and user active status.
- Deactivated users are rejected even with otherwise valid JWTs.

Authorization:
- Donor-only item creation.
- Donor owner-only item update/delete.
- Recipient/NGO-only item request creation.
- Donor item owner-only approve/reject/pickup.
- Request owner-only cancel.
- Admin-only analytics.
- NGO note visible only to donor and NGO.

Privacy:
- Donor phone is never returned in browse/list endpoints.
- Donor phone is visible only after approval to the approved requester.
- Recipient contact data is not exposed unless required by the donor workflow.

Operational security:
- CORS local origin is acceptable for MVP, but production CORS must be env-configurable.
- No image uploads in v1; `image_url` is URL-only.
- Login rate limiting and refresh-token revocation are deferred but documented as production gaps.

## Potential Risks

- Concurrent approval can corrupt state unless row locks are used.
- Supabase PostGIS setup must be verified before migrations run; autogenerate alone is insufficient for extension and spatial-index correctness.
- Streamlit is not ideal for high-scale public production usage.
- Celery retries can duplicate emails unless task retry behavior is bounded.
- Analytics over growing tables may become slow without indexes or later materialized summaries.
- Supabase Auth session lifecycle with refresh token support must be configured for production; token revocation gaps should be documented.
- Null item locations must be handled deliberately in matching and radius filters.

## Missing Requirements Resolved

Use these v1 decisions:
- Quantity is display-only.
- Notifications table and in-app notification UI are deferred.
- Admin moderation is deferred; admin scope is analytics only.
- Image upload is deferred; `image_url` accepts optional URL strings only.
- Recipient/NGO location is not stored in profile; matching accepts optional query coordinates.
- Pickup scheduling is deferred; `pickup_scheduled_at` may remain nullable and unused.
- Email templates are simple Python constants.
- Supabase production database hardening, backups, connection pooling, and secret rotation must be documented before launch.
- Audit events are recommended but optional for MVP. If implemented, they should track approval, rejection, pickup, cancellation, and item removal.

## Recommended Build Order

1. Infrastructure:
   - Create Docker Compose for API, worker, frontend, and Redis; use Supabase for PostgreSQL/PostGIS instead of a local DB container.
   - Create backend Dockerfile, `.env.example`, settings validation, async DB engine, Redis config, Alembic async setup, Streamlit theme config.
   - Add Supabase connection variables and document direct vs pooler database URLs.
   - Add `/health`, `/health/db`, `/health/redis`.
   - Test Supabase DB connectivity.

2. Models and migrations:
   - Implement users, items, donation requests.
   - Add lifecycle timestamps and required indexes.
   - Verify PostGIS is enabled in Supabase, and add spatial index manually in migration.
   - Defer notifications unless in-app notification scope is added.
   - Test persistence, relationships, indexes where practical.

3. Auth:
   - Implement schemas, Supabase Auth integration, JWT session validation middleware, auth service, dependencies, role guards.
   - Enforce inactive-user rejection.
   - Test register, login, `/me`, invalid/expired token, inactive user, preferences.

4. Items:
   - Implement item schemas, filters, pagination, `mine=true`, radius validation, soft delete.
   - Enforce owner-only mutation and status-aware updates.
   - Treat quantity as display-only.
   - Test filtering, pagination bounds, null location, invalid radius inputs, owner authorization, soft delete.

5. Requests/workflow:
   - Implement explicit state transition service.
   - Prevent self-request.
   - Prevent duplicate active requests.
   - Implement transactional approval with row locks.
   - Implement reject, cancel, pickup with `409` invalid-transition handling.
   - Handle item removal with active requests.
   - Test every valid and invalid transition.

6. Background jobs:
   - Implement Celery app, email service, email templates, and tasks.
   - Dispatch tasks only after DB commit.
   - Add retry limits and structured task logging.
   - Mock Resend in tests.
   - Test no business rollback on email failure.

7. Matching and analytics:
   - Implement scoring for available items only.
   - Exclude removed, reserved, donated, and null-location items from radius-specific results.
   - Use fallback proximity score when coordinates are absent.
   - Implement analytics using `donated_at`, `created_at`, and picked-up requests.
   - Test empty datasets, known aggregates, and score ordering.

8. Frontend:
   - Implement API client and session-state auth.
   - Build pages with role guards.
   - Keep API mutations in pages; components render and accept callbacks.
   - Ensure donor phone is shown only after approval.
   - Add frontend handling for `401`, `403`, `404`, `409`, and `422`.

9. E2E and final verification:
   - Add donor, recipient, NGO, and admin flows.
   - Include edge cases: duplicate request, self-request blocked, stale approval conflict, item removed flow.
   - Run backend coverage.
   - Run E2E tests against live services.
   - Perform manual smoke test from listing through request, approval, pickup, and analytics update.
