# Community Donation Platform Implementation Roadmap

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this roadmap phase-by-phase. Each phase must be completed, tested, and reviewed before starting the next phase.

**Goal:** Build a production-conscious MVP for a role-based community donation platform with item listings, request workflows, email notifications, location-aware matching, analytics, and a Streamlit frontend.

**Architecture:** FastAPI owns API and business rules, Supabase-managed PostgreSQL/PostGIS is the source of truth, Redis/Celery handles post-commit email jobs, and Streamlit provides the MVP frontend. The implementation enforces explicit lifecycle transitions, transactional approval/pickup paths, privacy boundaries, and stable API contracts before frontend work begins.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, Alembic, Supabase PostgreSQL + PostGIS, Redis, Celery, Resend, Streamlit, Plotly, httpx, pytest, pytest-asyncio, Playwright.

---

## Phase 1

### Goal
Establish the project skeleton, runtime configuration, Docker services, Supabase database connectivity, Redis connectivity, health checks, and migration foundation.

### Files to create
- `docker-compose.yml`
- `.env.example`
- `backend/Dockerfile`
- `backend/requirements.txt`
- `backend/alembic.ini`
- `backend/alembic/env.py`
- `backend/alembic/script.py.mako`
- `backend/alembic/versions/.gitkeep`
- `backend/app/__init__.py`
- `backend/app/main.py`
- `backend/app/config.py`
- `backend/app/database.py`
- `backend/app/dependencies.py`
- `backend/app/routers/__init__.py`
- `backend/app/routers/health.py`
- `backend/tests/conftest.py`
- `backend/tests/test_database_connection.py`
- `backend/tests/test_health.py`
- `frontend/requirements.txt`
- `frontend/.streamlit/config.toml`

### Files to modify
- None expected if starting from an empty repository.

### Dependencies
- Docker and Docker Compose.
- Supabase project with PostgreSQL connection string.
- PostGIS enabled in Supabase.
- Redis container.
- Python 3.11 runtime.

### Acceptance criteria
- Docker Compose defines `redis`, `api`, `worker`, and later `frontend` services; no local PostgreSQL service is required because Supabase provides the database.
- `.env.example` documents Supabase direct and application database URLs.
- Settings validation fails clearly when required env vars are missing.
- FastAPI app starts without creating tables directly.
- Alembic uses the async migration pattern.
- `/health` reports API process health.
- `/health/db` verifies database connectivity.
- `/health/redis` verifies Redis connectivity.
- Streamlit theme config exists but frontend pages are not yet implemented.

### Tests required
- `pytest backend/tests/test_database_connection.py`
- `pytest backend/tests/test_health.py`
- Tests must verify `SELECT 1` against the Supabase async engine.
- Tests must verify health endpoints return expected success payloads when dependencies are reachable.

### Risks
- Async Alembic setup can fail if it uses a synchronous engine.
- Supabase connection strings may require URL-encoding special characters in the database password.
- Direct vs pooler connection modes may behave differently with Alembic and SQLAlchemy.
- Settings validation can block tests unless test env vars are isolated from local `.env`.

---

## Phase 2

### Goal
Implement the Supabase database schema, lifecycle timestamps, indexes, PostGIS verification, and first migration.

### Files to create
- `backend/app/models/__init__.py`
- `backend/app/models/user.py`
- `backend/app/models/item.py`
- `backend/app/models/request.py`
- `backend/app/schemas/__init__.py`
- `backend/app/schemas/pagination.py`
- `backend/tests/test_models.py`
- `backend/tests/test_migrations.py`
- `backend/alembic/versions/0001_initial_schema.py`

### Files to modify
- `backend/alembic/env.py`
- `backend/app/database.py`

### Dependencies
- Phase 1 complete.
- Supabase project or isolated Supabase test environment available.
- PostGIS enabled in Supabase before migrations run.

### Acceptance criteria
- `users`, `items`, and `donation_requests` tables exist.
- `notifications` is not implemented in v1 unless in-app notification scope is reintroduced.
- `items.quantity` exists as display-only metadata.
- `items.donated_at` and `items.removed_at` exist.
- `donation_requests.approved_at`, `picked_up_at`, and `cancelled_at` exist.
- `created_at` and `updated_at` are timezone-aware.
- PostGIS extension is enabled in Supabase and verified by migration/test.
- Spatial index exists on `items.location`.
- Required relational indexes exist.
- All models are imported through `models/__init__.py` for Alembic metadata discovery.

### Tests required
- Model persistence and round-trip tests for each table.
- Relationship loading tests for donor items and user requests.
- Migration test verifies PostGIS extension exists in Supabase.
- Migration test verifies required indexes exist.
- Test verifies `quantity` does not affect request fulfillment logic because fulfillment is indivisible in v1.

### Risks
- Alembic autogenerate may miss spatial indexes and should not be trusted blindly for Supabase/PostGIS details.
- PostgreSQL enum migrations may need manual correction.
- Timezone handling can become inconsistent if defaults use naive datetimes.
- Supabase pooled connections may not be appropriate for migrations; use the direct database URL for Alembic.

---

## Phase 3

### Goal
Implement authentication through Supabase Auth, JWT session validation, role guards, current-user loading, and preference updates.

### Files to create
- `backend/app/schemas/user.py`
- `backend/app/schemas/auth.py`
- `backend/app/services/__init__.py`
- `backend/app/services/auth_service.py`
- `backend/app/routers/auth.py`
- `backend/tests/test_auth.py`

### Files to modify
- `backend/app/main.py`
- `backend/app/dependencies.py`
- `backend/app/models/user.py`

### Dependencies
- Phase 2 schema and migrations complete.
- Supabase Auth enabled in the Supabase project.

### Acceptance criteria
- Users can register as donor, recipient, NGO, or admin.
- Passwords are managed through Supabase Auth and never stored in plaintext in the application database.
- Login returns a Supabase Auth JWT containing `sub`, `role`, `user_id`, and `exp`.
- Middleware validates the Supabase-issued JWT on every authenticated request.
- `/api/auth/me` returns the authenticated active user.
- Inactive users are rejected even with otherwise valid JWTs.
- `/api/auth/me/preferences` updates category preferences for matching.
- Role guard helper supports donor, recipient, NGO, and admin restrictions.

### Tests required
- Register success.
- Duplicate email rejection.
- Password handling via Supabase Auth assertion.
- Login success.
- Login wrong password returns `401`.
- Invalid token returns `401`.
- Expired token returns `401`.
- Inactive user token returns `401`.
- Preferences update persists valid categories.

### Risks
- JWT payload drift can break frontend session state.
- Missing inactive-user checks create authorization holes.
- Supabase Auth session lifecycle with refresh token support must be considered for production token revocation.
- Password policy is minimal for MVP and should be documented as a production gap.

---

## Phase 4

### Goal
Implement item listing APIs with donor ownership rules, pagination, filters, radius queries, soft delete, and privacy-safe response shapes.

### Files to create
- `backend/app/schemas/item.py`
- `backend/app/services/item_service.py`
- `backend/app/routers/items.py`
- `backend/tests/test_items.py`

### Files to modify
- `backend/app/main.py`
- `backend/app/schemas/pagination.py`
- `backend/app/models/item.py`

### Dependencies
- Phase 3 auth and role guards complete.

### Acceptance criteria
- Donors can create items.
- Non-donors cannot create items.
- `GET /api/items/` returns paginated `ItemOut` results.
- `ItemOut` includes donor id and donor name.
- `ItemOut` does not expose donor phone before approval.
- `status` defaults to `available`.
- `mine=true` returns authenticated donor-owned listings.
- Repeated `category` query params are supported.
- `page` defaults to `1`; `page_size` defaults to `20` and is capped at `100`.
- Radius filtering requires all of `lat`, `lng`, and `radius_km`.
- Invalid coordinates and invalid pagination return `422`.
- Item update and delete are donor-owner only.
- Delete soft-removes item by setting status `removed` and `removed_at`.
- Removed, donated, and reserved items are excluded from default browse results.

### Tests required
- Donor create item success.
- Recipient create item returns `403`.
- Owner update success.
- Non-owner update returns `403`.
- Soft delete sets `removed` and `removed_at`.
- Default list only returns available items.
- Category multiselect filtering.
- City and condition filtering.
- Radius filtering with correct `POINT(lng lat)` behavior.
- Partial radius query returns `422`.
- Invalid lat/lng/radius returns `422`.
- Null-location items do not appear in radius-specific results.
- Pagination bounds and max page size.

### Risks
- Coordinate order mistakes will silently return wrong distance results.
- Spatial query performance depends on the spatial index being correct.
- `mine=true` must not leak other donors' data.

---

## Phase 5

### Goal
Implement the donation request workflow with explicit state transitions, duplicate prevention, self-request prevention, row-locking, and privacy-aware response contracts.

### Files to create
- `backend/app/schemas/request.py`
- `backend/app/services/request_service.py`
- `backend/app/routers/requests.py`
- `backend/tests/test_requests.py`
- `backend/tests/test_request_state_transitions.py`

### Files to modify
- `backend/app/main.py`
- `backend/app/models/request.py`
- `backend/app/models/item.py`

### Dependencies
- Phase 4 item APIs complete.

### Acceptance criteria
- Recipients and NGOs can request available items.
- Donors cannot request items.
- Users cannot request their own items.
- Duplicate active requests are rejected.
- Requests against non-available items are rejected.
- Recipient-submitted `ngo_note` is ignored or rejected according to schema validation; v1 should reject it for clarity.
- Donor owner can approve, reject, and confirm pickup.
- Approval locks the request and item, approves one request, rejects competing pending requests, sets item `reserved`, and sets `approved_at`.
- Pickup locks the approved request and item, sets request `picked_up`, item `donated`, `picked_up_at`, and `donated_at`.
- Request owner can cancel only pending requests.
- Invalid lifecycle transitions return `409 Conflict`.
- Donor phone is exposed only to the approved requester and the donor.
- Request responses include item title, donor name, requester name, statuses, message, `ngo_note`, timestamps, and lifecycle timestamps.

### Tests required
- Recipient request success.
- NGO request with `ngo_note` success.
- Recipient `ngo_note` rejected.
- Donor request returns `403`.
- Self-request blocked.
- Duplicate active request blocked.
- Request removed/reserved/donated item blocked.
- Approve request success.
- Approval auto-rejects competing pending requests.
- Non-owner approval returns `403`.
- Re-approving returns `409`.
- Reject pending request success.
- Reject approved/picked-up/cancelled request returns `409`.
- Pickup approved request success.
- Pickup before approval returns `409`.
- Cancel own pending request success.
- Cancel approved request returns `409`.
- Remove item with active requests follows defined service behavior.
- Donor phone privacy assertions before and after approval.

### Risks
- Row locking must be done carefully with async SQLAlchemy.
- Service code can become hard to maintain unless transitions are centralized.
- Concurrent duplicate requests may still need a database-level strategy if service checks are insufficient.

---

## Phase 6

### Goal
Implement asynchronous email jobs through Celery/Redis and wire them into committed request workflow events.

### Files to create
- `backend/app/worker/__init__.py`
- `backend/app/worker/celery_app.py`
- `backend/app/worker/tasks.py`
- `backend/app/worker/email_templates.py`
- `backend/app/services/email_service.py`
- `backend/tests/test_tasks.py`

### Files to modify
- `backend/app/services/request_service.py`
- `backend/app/config.py`
- `backend/requirements.txt`
- `docker-compose.yml`

### Dependencies
- Phase 5 request workflow complete.
- Redis service available.
- Resend env vars configured.

### Acceptance criteria
- Celery app uses JSON serialization.
- Tasks accept only JSON-serializable primitive values.
- Request-created task notifies donor.
- Approval task notifies approved requester.
- Rejection task notifies rejected requester.
- Pickup confirmation notifies donor and requester.
- Tasks are dispatched only after DB commit.
- Email failures do not roll back business state.
- Retry behavior is bounded and logged.

### Tests required
- Mock Resend send call.
- Direct task tests verify recipient address, subject, and key HTML content.
- Request service tests verify task dispatch happens after successful commit path.
- Request service tests verify no task dispatch on failed transition.
- Email failure test verifies task failure does not mutate already committed DB state.

### Risks
- Duplicate emails can occur if retries are not bounded or idempotent enough.
- Worker import paths can differ between Docker and local runs.
- Resend free-tier limits can affect manual testing.

---

## Phase 7

### Goal
Implement location-aware matching and admin analytics using durable timestamps and SQLAlchemy aggregations.

### Files to create
- `backend/app/schemas/analytics.py`
- `backend/app/schemas/matching.py`
- `backend/app/services/matching_service.py`
- `backend/app/services/analytics_service.py`
- `backend/app/routers/matching.py`
- `backend/app/routers/analytics.py`
- `backend/tests/test_matching.py`
- `backend/tests/test_analytics.py`

### Files to modify
- `backend/app/main.py`
- `backend/app/models/item.py`
- `backend/app/models/request.py`

### Dependencies
- Phase 5 lifecycle timestamps complete.

### Acceptance criteria
- Matching returns top 20 available items by composite score.
- Matching excludes removed, reserved, and donated items.
- Matching supports optional `lat` and `lng`.
- Matching uses fallback proximity score when coordinates are absent.
- Radius-specific matching excludes null-location items.
- Analytics endpoints require admin role.
- Summary includes total donors, recipients, NGOs, items listed, items donated, total requests, and people helped.
- Donation trend uses `donated_at`, not mutable `updated_at`.
- Category breakdown counts donated items.
- Platform activity uses stable creation timestamps.
- Empty analytics datasets return valid zero/empty responses.

### Tests required
- Matching score ordering with seeded data.
- Matching excludes non-available items.
- Matching handles empty preferences.
- Matching handles absent coordinates.
- Matching handles null item location.
- Non-admin analytics returns `403`.
- Summary counts exact seeded data.
- People helped equals picked-up requests.
- Donation trend uses `donated_at`.
- Category breakdown sums to donated total.
- Empty dataset tests.

### Risks
- Matching formula may become expensive as item volume grows.
- Analytics queries over large tables may require future materialization.
- Timezone inconsistencies can shift daily trend buckets.

---

## Phase 8: Google Authentication

### Goal
Implement Google OAuth authentication on the FastAPI backend using Supabase Auth/GoTrue integration. Maintain a clean, secure, role-based JWT verification flow.

### Files to modify
- `backend/app/config.py` (Add Supabase Google OAuth environment variables)
- `backend/app/routers/auth.py` (Add endpoints for OAuth callback and login urls)
- `backend/app/dependencies.py` (Update current user JWT verification to validate Google-auth users if needed)
- `backend/tests/test_auth.py` (Unit/integration tests for authentication flow)

### Dependencies
- Phase 7 backend APIs complete and tested (verified baseline at `v0.7-stable`).

### Acceptance criteria
- Secure Google OAuth registration and login flow.
- Correctly map Google-authenticated users to roles (Donor/Recipient/NGO) in the database.
- Issue and validate standard JWT access tokens.
- Securely store OAuth credentials using environment variables.

### Tests required
- Unit and integration tests for Google OAuth routes and token parsing.
- Mocking external GoTrue/Supabase calls in test suites.

### Risks
- OAuth redirects and callback configuration mismatches in local development.
- Ensuring role assignment is prompt and secure during first-time OAuth login.

---

## Phase 9: AI Generator Feature

### Goal
Add an AI-powered listing description/tags generator using the Google Gemini API (or a mock service fallback if API keys are unavailable).

### Files to create
- `backend/app/services/ai_generator.py` (Service module for Gemini API communication)
- `backend/app/routers/ai_generator.py` (Router for generating description and tags)

### Files to modify
- `backend/app/main.py` (Register the new router)

### Dependencies
- Stable database schemas and items endpoints.

### Acceptance criteria
- Endpoint `POST /api/items/generate` returns structured descriptions and tags based on item title and category.
- Graceful error handling and fallback when API limits are hit or credentials are not configured.
- Prompt templates tuned to generate friendly, concise listing copy and appropriate tags.

### Tests required
- Backend unit tests for AI generation endpoints using mock Gemini API clients.

### Risks
- API rate limits, costs, and token consumption.
- Handling unverified/inappropriate input titles gracefully.

---

## Phase 10: Next.js Frontend

### Goal
Build a premium, next-generation Next.js web application utilizing TailwindCSS and TypeScript, replacing the deprecated Streamlit UI. Follow GiveCircle brand identity guidelines strictly.

### Files to create
- `frontend/` (Initialize new Next.js project skeleton)
- Pages: Dashboard, Login, Register, Browse Listings, My Listings, My Requests, NGO Dashboard, Admin Analytics.

### Dependencies
- Phase 8 (Google Auth) and Phase 9 (AI Generator) backend components complete.

### Acceptance criteria
- Modern responsive layout utilizing Emerald and Slate color palettes.
- Absolutely NO purple/indigo or pure white backgrounds.
- Client-side routing and protected routes based on user role.
- Support Google OAuth login flow and integration with AI generator endpoint.
- Clear error feedback for API errors (400, 401, 403, 404, 409, 422).

### Tests required
- Next.js component unit tests.
- Manual verification of branding and role-based redirects.

---

## Phase 11: Smoke Testing

### Goal
Merge and integrate Phase 8, 9, and 10 to validate full end-to-end functionality.

### Acceptance criteria
- Docker Compose cleanly spins up the API, Next.js frontend, Redis, and Celery worker.
- Users can log in via email/password or Google OAuth, list items with AI description generator, request items, and complete matching flows.

---

## Phase 12: Full E2E Playwright Testing

### Goal
Develop a comprehensive Playwright end-to-end testing suite validating the Next.js frontend against the FastAPI backend.

### Files to create
- `e2e_tests/conftest.py` (E2E configurations, seed data cleanup with retries)
- `e2e_tests/test_donor_flow.py`
- `e2e_tests/test_recipient_flow.py`
- `e2e_tests/test_ngo_flow.py`
- `e2e_tests/test_admin_analytics.py`
- `e2e_tests/test_edge_cases.py`

### Dependencies
- Staging-like environment running Next.js frontend and FastAPI backend.

### Acceptance criteria
- E2E donor flow covers listing, request approval, and pickup.
- E2E recipient flow covers browse, request, and cancellation.
- NGO flow covers dashboard and NGO notes.
- Admin flow covers analytics dashboard access guards.
- Edge cases test self-request block, duplicate requests, and soft deletes.
