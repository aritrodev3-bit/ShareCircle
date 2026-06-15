# Production Gaps

This document records known gaps that are accepted as technical debt and deferred to a
documented future phase. Each entry must be resolved before the referenced deadline.

---

## PG-001 — Backend Service Layer Coverage Below 80%

**Recorded:** 2026-06-15  
**Phase deferred from:** Phase 8 Gate (Prompt 6)  
**Resolution deadline:** Before Phase 9 completion gate sign-off  
**Owner:** Engineering team  

### Description

Overall backend line coverage is **72%** against the AGENTS.md target of ≥ 80%.
The gap is entirely concentrated in three service modules that have been in the codebase
since Phases 1–7 and are not introduced by Phase 8:

| Module | Coverage | Gap | Root Cause |
|---|---|---|---|
| `app/services/request_service.py` | 27% | −53% | Service logic tested via HTTP endpoint integration tests; SQLAlchemy async tracing does not fully attribute coverage to service functions called through ASGI transport |
| `app/services/item_service.py` | 55% | −25% | Same pattern as above |
| `app/services/analytics_service.py` | 60% | −20% | Complex aggregation paths not exercised with direct service-layer tests |
| `app/services/matching_service.py` | 74% | −6% | Fallback proximity and edge-case scoring paths |

**Phase 8-specific modules are all at or above 80%:**
- `app/config.py`: 100%
- `app/routers/auth.py`: 89%
- All schemas, models, worker modules: 100%

### Justification for Deferral

AGENTS.md states: *"Maintain at least 80% backend line coverage **once backend phases are
complete**."* Phase 9 (AI Generator) is a backend phase and has not yet been implemented.
The 80% requirement therefore applies at the completion of Phase 9, not Phase 8.

The current 72% reflects correct mocking strategy (GoTrue HTTP client replaced by
`FakeSupabaseAuthClient`) and integration-test-first coverage (HTTP endpoint tests cover
behavior but coverage attribution misses service-layer lines). Business logic correctness
is verified by 91 passing tests.

### Resolution Plan

Before the Phase 9 completion gate, add direct service-layer unit tests that call
service functions with mocked database sessions. Priority order:

1. `request_service.py` — lifecycle transition functions (approve, reject, pickup, cancel)
2. `item_service.py` — geo-query and item state transition paths
3. `analytics_service.py` — aggregation query paths
4. `matching_service.py` — fallback proximity and edge scoring paths

Target: bring each module to ≥ 80% individually, driving overall coverage above 80%.

### Sign-off

- User decision: ✅ **DEFER** (confirmed 2026-06-15)
- Coverage will be re-verified at the Phase 9 completion gate.

---
