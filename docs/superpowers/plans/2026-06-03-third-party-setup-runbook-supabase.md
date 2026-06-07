# Third-Party Setup Runbook with Supabase

Use this runbook before Phase 1 so `.env` has every required credential and connection string before development starts.

Google OAuth is not present in the PRD and is not configured. Supabase is now used only for managed PostgreSQL/PostGIS in v1; Supabase Auth, Storage, Realtime, Edge Functions, and Data API are out of scope unless explicitly added later.

## 1. Local prerequisites

Install:
- Docker Desktop or Docker Engine with Docker Compose.
- Git.
- Python 3.11+.
- Optional: `psql` for direct database checks.
- Optional: Supabase CLI for local database inspection and migration workflows.

Verify locally:

```powershell
docker --version
docker compose version
python --version
```

## 2. Supabase project

Why:
- Supabase provides the managed PostgreSQL database.
- PostGIS provides radius filtering and proximity matching.
- Supabase Auth handles user registration, login, and JWT session issuance; the app validates Supabase-issued JWTs in FastAPI middleware.

Setup:
1. Go to `https://supabase.com/dashboard`.
2. Create a new project.
3. Save the project reference ID.
4. Save the database password you set during project creation.
5. Open Project Settings, then Database.
6. Copy the database connection strings from the Connect panel.
7. Open Project Settings, then API.
8. Copy the Project URL and the anon/public key (used for Supabase Auth client-side session handling).
9. Enable PostGIS:
   - Open Database, then Extensions.
   - Search for `postgis`.
   - Enable the extension.
10. Verify PostGIS later with:

```sql
select postgis_version();
```

Connection-string guidance:
- Use the direct database URL for Alembic migrations.
- Use the direct URL or session pooler URL for the FastAPI async SQLAlchemy app.
- Avoid transaction-pooler mode until tested with SQLAlchemy, Alembic, and row-locking workflows.
- If the database password contains special characters, URL-encode it in the connection string.

Credentials required:

```env
SUPABASE_PROJECT_REF=your-project-ref
SUPABASE_DB_PASSWORD=url-encoded-password-if-needed
DATABASE_URL=postgresql+asyncpg://postgres.your-project-ref:your-password@aws-0-region.pooler.supabase.com:5432/postgres
ALEMBIC_DATABASE_URL=postgresql+asyncpg://postgres:your-password@db.your-project-ref.supabase.co:5432/postgres
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key
```

Test database strategy:
- Preferred: create a separate Supabase project for test/staging.
- Acceptable for early MVP: use a separate schema or database only if the Supabase plan and migration workflow support it safely.

```env
TEST_DATABASE_URL=postgresql+asyncpg://postgres.test-project-ref:test-password@test-host:5432/postgres
```

## 3. Redis

Why:
- Celery uses Redis as broker and result backend.
- FastAPI enqueues background email jobs through Redis.
- Celery workers consume queued jobs from Redis.

Local setup:
- Use Docker with `redis:7-alpine`.

Local env:

```env
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
CELERY_TASK_MAX_RETRIES=3
```

Production:
- Use a managed Redis provider.
- Require authentication and TLS.

Example production shape:

```env
CELERY_BROKER_URL=rediss://:password@redis-host:6379/0
CELERY_RESULT_BACKEND=rediss://:password@redis-host:6379/0
```

## 4. Resend

Why:
- Sends transactional emails for request received, approval, rejection, and pickup confirmation.

Setup:
1. Go to `https://resend.com`.
2. Create an account.
3. Open API Keys.
4. Create an API key.
5. Prefer sending-only access for this app.
6. Copy the key into `.env`.
7. For local development, use `onboarding@resend.dev`.
8. For production, add and verify a sending domain, then use a domain sender.

Env:

```env
RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxx
RESEND_FROM_EMAIL=onboarding@resend.dev
```

Production sender example:

```env
RESEND_FROM_EMAIL=GiveCircle <noreply@yourdomain.com>
```

Security:
- Never expose `RESEND_API_KEY` in Streamlit/browser-facing code.
- Never commit `.env`.
- Mock Resend in automated tests.

## 5. JWT/auth secret

Why:
- Supabase Auth issues and signs JWTs for user sessions.
- FastAPI middleware validates Supabase-issued JWTs using the Supabase JWT secret.
- A local `JWT_SECRET_KEY` may also be configured for any supplemental application-level signing needs.

Locate the Supabase JWT secret:
- Open Supabase Dashboard → Project Settings → API → JWT Settings.
- Copy the `JWT Secret` value.

Generate a supplemental app secret locally in PowerShell (if needed):

```powershell
[Convert]::ToBase64String((1..48 | ForEach-Object { Get-Random -Maximum 256 }))
```

Env:

```env
SUPABASE_JWT_SECRET=paste-supabase-jwt-secret-here
JWT_SECRET_KEY=paste-generated-secret-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

Production:
- Supabase Auth session lifecycle with refresh token support handles token renewal.
- Store all secrets in a secrets manager.
- Rotate the Supabase JWT secret with a planned token invalidation window.

## 6. App URLs and CORS

Why:
- Streamlit calls FastAPI.
- FastAPI must allow the Streamlit origin.

Local:

```env
API_BASE_URL=http://localhost:8000
PUBLIC_APP_URL=http://localhost:8501
API_PUBLIC_URL=http://localhost:8000
CORS_ALLOWED_ORIGINS=http://localhost:8501
```

Production:

```env
API_BASE_URL=https://api.yourdomain.com
PUBLIC_APP_URL=https://yourdomain.com
API_PUBLIC_URL=https://api.yourdomain.com
CORS_ALLOWED_ORIGINS=https://yourdomain.com
```

## 7. Runtime and logging

Local:

```env
ENVIRONMENT=local
LOG_LEVEL=INFO
```

Production:

```env
ENVIRONMENT=production
LOG_LEVEL=INFO
SENTRY_DSN=
```

## Complete `.env` template

Create `.env` in the project root:

```env
# Supabase database
SUPABASE_PROJECT_REF=your-project-ref
SUPABASE_DB_PASSWORD=url-encoded-password-if-needed
DATABASE_URL=postgresql+asyncpg://postgres.your-project-ref:your-password@aws-0-region.pooler.supabase.com:5432/postgres
ALEMBIC_DATABASE_URL=postgresql+asyncpg://postgres:your-password@db.your-project-ref.supabase.co:5432/postgres
TEST_DATABASE_URL=postgresql+asyncpg://postgres.test-project-ref:test-password@test-host:5432/postgres

# Supabase Auth
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_JWT_SECRET=your-supabase-jwt-secret

# Redis / Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
CELERY_TASK_MAX_RETRIES=3

# Auth (supplemental)
JWT_SECRET_KEY=paste-generated-32-plus-character-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Email / Resend
RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxx
RESEND_FROM_EMAIL=onboarding@resend.dev

# App URLs
API_BASE_URL=http://localhost:8000
PUBLIC_APP_URL=http://localhost:8501
API_PUBLIC_URL=http://localhost:8000
CORS_ALLOWED_ORIGINS=http://localhost:8501

# Runtime
ENVIRONMENT=local
LOG_LEVEL=INFO
SENTRY_DSN=
```

## Readiness checklist

- Supabase project created.
- Supabase database password saved.
- Supabase direct database URL copied for Alembic.
- Supabase application database URL copied for FastAPI.
- PostGIS enabled in Supabase.
- Separate test/staging Supabase database strategy chosen.
- Supabase Auth enabled in the Supabase project.
- Supabase project URL copied.
- Supabase anon/public key copied.
- Supabase JWT secret copied for FastAPI middleware validation.
- Redis local Docker service planned.
- Resend API key created.
- Resend sender selected.
- JWT secret generated.
- CORS origins set.
- `.env` created locally and excluded from git.
- `.env.example` will contain placeholders only.

