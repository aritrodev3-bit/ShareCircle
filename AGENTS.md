# AGENTS.md

## Scope and Source Order

This file is repository-wide Codex guidance. Place narrower `AGENTS.md` files only when a subtree needs stricter rules.

Use these documents in this order:

1. `docs/superpowers/plans/phase_9_findings.md` is the absolute source of truth for Phase 9 AI Feature architecture, schemas, and flow.
2. `docs/superpowers/plans/community_donation_platform_prd_v2.md` is the product source of truth.
3. `docs/superpowers/plans/2026-06-03-community-donation-platform-roadmap (1).md` is the required implementation order.
4. `docs/superpowers/plans/2026-06-03-community-donation-platform-implementation-plan.md` is the architecture and execution reference.
5. `docs/superpowers/plans/2026-06-03-third-party-setup-runbook-supabase.md` is the environment and third-party setup reference.

Do not duplicate or reinterpret product requirements in code comments, docs, or prompts. When requirements conflict, follow the PRD for product behavior, the roadmap for sequencing, and the implementation plan for architecture details that do not contradict the PRD.

## Implementation Workflow

- Work phase-by-phase in roadmap order. Do not start a later phase until the current phase has implementation, tests, and review completed.
- Before editing a phase, read the relevant PRD sections, the matching roadmap phase, and the implementation-plan architecture notes.
- Keep changes scoped to the current phase unless a dependency must be corrected to make the phase pass.
- Prefer small, reviewable changes with stable API contracts before frontend work.
- Do not add placeholder stubs, fake integrations, or dead code. If an integration cannot be completed because credentials or services are unavailable, implement explicit configuration validation and document the blocker.
- Treat the runbook as required setup context. Never assume missing third-party credentials, database extensions, or service URLs.

## Architecture Discipline

- FastAPI owns API routing, authentication dependencies, authorization, and business workflow entry points.
- Service modules own business logic and state transitions. Routers must delegate to services and avoid inline business rules.
- Supabase PostgreSQL/PostGIS is the source of truth. Do not introduce a local PostgreSQL service unless the PRD or roadmap changes.
- SQLAlchemy 2.0 async ORM is the data access layer. Do not use raw SQL for application logic unless a migration or PostGIS/index operation cannot be expressed safely through SQLAlchemy.
- Alembic owns schema changes. Never create tables from application startup code.
- Celery/Redis handles post-commit background work only. Email failures must not roll back committed business state.
- Streamlit page files own API mutations and session-state workflow. Shared frontend components render data and accept callbacks; they must not hide API calls.
- Keep API response schemas stable and shared through `backend/app/schemas/`. Do not duplicate Pydantic schemas across routers or services.

## Coding Standards

- Use Python 3.11-compatible code with explicit type hints for public functions, service functions, schemas, and model fields.
- Use SQLAlchemy 2.0 declarative patterns with typed mapped columns and relationships.
- Keep enum values, lifecycle states, and role names centralized. Do not compare against ad hoc string literals when an enum exists.
- Centralize request lifecycle transitions and return the documented HTTP error class for invalid transitions.
- Validate configuration with `pydantic-settings`; required env vars must fail clearly at startup with the variable name.
- Do not commit secrets, real credentials, `.env`, generated caches, or local runtime artifacts.
- Keep CSS in `frontend/styles.css` and chart defaults in `frontend/chart_theme.py`. Avoid inline Streamlit CSS except through approved shared components.
- Follow existing file and module naming. Avoid new abstractions unless they remove meaningful duplication or enforce a cross-cutting rule.

## Testing Standards

- Add or update tests in the same phase as implementation.
- Backend tests use `pytest` and `pytest-asyncio`; async database tests must isolate state and not depend on ordering.
- External services such as Resend must be mocked in automated tests.
- Database and migration tests must verify Supabase/PostGIS assumptions where practical, including extension availability and required indexes.
- Workflow tests must cover valid transitions, invalid transitions, authorization failures, duplicate/conflict behavior, and privacy boundaries.
- Frontend tests should cover API client behavior and error propagation where practical; role-based Streamlit flows require manual smoke testing until automated coverage exists.
- E2E tests must use Playwright explicit waits and assertions. Do not use `time.sleep()`.
- Maintain at least 80% backend line coverage once backend phases are complete.

## Security Standards

- Enforce authentication and role authorization in backend dependencies/services, not only in frontend navigation.
- Never expose service-role keys, Resend API keys, JWT secrets, database passwords, or private connection strings to Streamlit/browser-facing code.
- Validate Supabase-issued JWTs for authenticated endpoints and reject inactive users.
- Enforce owner checks for donor listing mutation and request workflow actions.
- Preserve privacy boundaries in response schemas; do not return contact data outside approved workflow states.
- Use environment-configurable CORS for deployed environments.
- Treat missing rate limiting, token revocation hardening, uploads, admin moderation, and production deployment hardening as documented production gaps until explicitly implemented.

## Documentation Standards

- Keep setup and run instructions aligned with the runbook, `.env.example`, Docker Compose, and actual commands.
- Document production gaps separately instead of weakening implementation standards.
- Document API contracts when response shapes or error codes are introduced or changed.
- Do not restate the PRD feature list in README or implementation docs. Link back to the PRD and document only operational, architectural, or workflow details.
- Update this `AGENTS.md` only for recurring engineering guidance, review feedback, or workflow rules.

## Review Standards

- Review for requirement alignment against the PRD, phase alignment against the roadmap, and architectural alignment against the implementation plan.
- Prioritize correctness of lifecycle transitions, authorization, privacy, transaction boundaries, migration safety, and test isolation.
- Confirm no router contains business logic that belongs in a service.
- Confirm migrations are intentional, reviewed, and compatible with async SQLAlchemy and Supabase/PostGIS.
- Confirm error responses use the documented status-code contract.
- Confirm frontend changes do not bypass backend authorization or leak protected data.
- Confirm tests cover the changed behavior and any important regression risk.

## Definition of Done

A task is done only when:

- The implemented behavior matches the PRD and the current roadmap phase.
- Architecture follows the implementation plan or the deviation is documented and justified.
- Relevant unit, integration, migration, frontend, or E2E tests are added or updated.
- Required verification commands for the phase have been run successfully, or any inability to run them is clearly reported with the reason.
- Secrets and local artifacts are not committed.
- Documentation affected by the change is updated.
- The change is reviewable, with no unrelated refactors or metadata churn.
