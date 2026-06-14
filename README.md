# GiveCircle — Community Donation Platform

GiveCircle is a role-based community donation platform connecting donors, recipients, and NGOs. Donors can list unused items (e.g., furniture, books, clothing), recipients/NGOs can request available listings with spatial matching, and donors can approve requests and confirm pickups. Asynchronous email notifications are sent for all state changes.

## 🚀 Technology Stack (FastAPI Backend)
* **Backend**: FastAPI, SQLAlchemy 2.0 (async), Alembic, Pydantic v2
* **Database**: Supabase PostgreSQL + PostGIS extension
* **Background Jobs**: Redis (broker) + Celery (worker) + Resend (emails)
* **Testing**: pytest, pytest-asyncio

> [!NOTE]
> The original Streamlit frontend has been deprecated. A Next.js frontend will be built in Phase 10.

---

## 🛠️ Local Development Setup

### 1. Environment Configuration
Create a `.env` file in the root directory by copying `.env.example`:
```bash
cp .env.example .env
```
Ensure you fill in your Supabase database credentials, Supabase Auth keys, and Resend API configuration:
* `DATABASE_URL`: Direct database connection pooler URL (async pg driver).
* `SUPABASE_URL` & `SUPABASE_ANON_KEY`: Supabase API endpoints.
* `SUPABASE_JWT_SECRET`: Secret key used to decode and verify asymmetric tokens locally.
* `RESEND_API_KEY`: API key for email delivery (mocked in tests).

### 2. Start Services with Docker Compose
To build and start Redis, the FastAPI API, and the Celery worker:
```bash
docker-compose up --build -d
```
Verify all services are running:
```bash
docker-compose ps
```

* FastAPI Backend is available at: `http://localhost:8000`
* Redis is running on: `127.0.0.1:6379`

### 3. Database Migrations
Migrations are managed using Alembic. To run migrations against your Supabase instance:
```bash
# Enter the api container or run locally
cd backend
alembic upgrade head
```

---

## 🧪 Testing Suite

### Run Backend Unit & Integration Tests
To run the async database, authentication, and service/transition tests with line coverage:
```bash
# Run from root directory
pytest backend/tests/ -v --cov=app --cov-report=term-missing
```

---

## 📂 Git Branch Strategy & Development Guidelines

To align with the restructured project roadmap, the repository follows a strict branching and tag policy:

### 1. Stable Baseline
* **Tag `v0.7-stable`**: This tag is the authoritative stable baseline (commit `39d42e8ff4e367d51a150f5c8258176294918c86`).
* **P0 Rule**: Any commits on `phase7-development` after `v0.7-stable` are unreviewed and **must not** be carried into new work.
* All development branches for Phase 8 and beyond originate directly from `v0.7-stable`.

### 2. Archived Branches
* The original Streamlit implementation and Playwright E2E tests have been archived due to the frontend technology stack change (moving to Next.js).
* **Archived branches**:
  - `old-phase8-streamlit` (Archived Phase 8 Streamlit implementation)
  - `old-phase9-e2e-original` (Archived Phase 9 Playwright E2E testing for Streamlit)
* **P0 Rule**: Do not merge archived branches into active development branches.

### 3. Active Development Branches
Active development proceeds in the following roadmap order:
* `phase8-google-auth` (Google Authentication implementation - **Active Development Start**)
* `phase9-ai-generator` (AI Listing Generator feature - Parallel branch)
* `phase10-nextjs-frontend` (Next.js Frontend replacement - Parallel branch)
* `phase11-smoke-testing` (Integration branch to merge and validate Phases 8, 9, and 10)
* `phase12-e2e-testing` (Deferred Full E2E Playwright Testing on the Next.js frontend, target tag `v0.11-stable` baseline)

---

## 🔒 Frozen Repository Areas
All branches and tags associated with **Phases 1 through 7** are frozen and **must not be modified, renamed, or deleted** under any circumstances. This keeps the completed history stable and auditable.
