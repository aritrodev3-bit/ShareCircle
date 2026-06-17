# Phase 9 Critical Implementation Findings & Custom Rules

The following findings and rules take precedence for Phase 9 implementation. They resolve discrepancies between the backend-only PRD and the frontend Next.js requirements.

## 1. Feature Layer
- **Layer:** Next.js Frontend ONLY.
- **FastAPI Backend:** There is NO backend development or backend changes for Phase 9. Do not add any routers, services, schemas, or config fields to the FastAPI backend.
- **Route Handler Path:** `frontend/src/app/api/ai/describe-item/route.ts`
- **Frontend Page Path:** `frontend/src/app/listings/page.tsx`

## 2. API Contract
- **Request Body:** `{ title: string, notes?: string }` (notes is optional; category is not an input).
- **Response Body:** `{ description: string, category: ItemCategory, condition: ItemCondition }` (no tags).
- **Enums mapping:**
  - `ItemCategory`: `clothing`, `furniture`, `electronics`, `books`, `kitchen`, `toys`, `medical`, `other`
  - `ItemCondition`: `new`, `like_new`, `good`, `fair`

## 3. Redis Rate Limiting (Next.js Route Handler)
- **Daily Limit:** Counter key `ai_rate:{user_id}:{YYYY-MM-DD}` in UTC.
- **Limit Value:** Enforced by `AI_DAILY_RATE_LIMIT` environment variable (default: `10`).
- **TTL:** 24-hour (86400 seconds) TTL on first write of the day.
- **Atomic Operations:** Increment counter only after a successful 200 response from OpenRouter.
- **Singleton Pattern:** Ensure a singleton Redis client is used in `frontend/src/lib/redis.ts` to prevent connection leaks.

## 4. Error Status Codes
The route handler must not swallow errors as 200 OK. It must return:
- `401 Unauthorized` if Supabase session is absent or invalid.
- `400 Bad Request` if `title` is missing or empty.
- `429 Too Many Requests` if the daily Redis limit is exceeded.
- `422 Unprocessable Entity` if the OpenRouter response does not conform to the expected schema (description is non-empty string, category is valid, condition is valid).
- `503 Service Unavailable` if the OpenRouter API is unreachable or fails.

## 5. OpenRouter Prompt Constraints (PRD Section 9.5)
- **Primary Model:** `google/gemma-2-9b-it:free`
- **System Prompt:** Verbatim system instructions instructing Gemma to return raw JSON matching `{description, category, condition}`.
- **User Prompt:** Compiled using user input `{ title, notes }`.
- **Fallbacks:** Defer any multi-model fallback chain. If Gemma fails or is busy, return `503`.

## 6. Frontend UI Integration
- Add "✨ AI Describe" button in the Add New Listing form on `frontend/src/app/listings/page.tsx`.
- Disable button and display spinner while request is in flight.
- Pre-fill fields `description`, `category`, and `condition` on success.
- Show appropriate messages:
  - On 429: "Daily AI limit reached. You can still fill in the details manually."
  - On 422 or 503: "AI generation failed. Please fill in the details manually."

## 7. Testing Requirements
- Jest tests in `frontend/tests/api/describe-item.test.ts` covering:
  - Valid request returns `{ description, category, condition }`
  - Missing `title` returns `400`
  - Unauthenticated request returns `401`
  - Rate limit exceeded returns `429`
  - OpenRouter non-conforming response returns `422`
  - 503 when OpenRouter is unreachable
- Verify `OPENROUTER_API_KEY` is not present in any client-side bundles.
