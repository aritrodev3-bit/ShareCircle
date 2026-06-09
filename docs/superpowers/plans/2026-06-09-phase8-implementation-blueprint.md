# Phase 8 Implementation Blueprint

## 1. Phase Identity and Branch Confirmation

- **Phase Number:** 8
- **Phase Title:** Streamlit Frontend
- **Branch Confirmation:**
  - The current branch is `plan-implementation-blueprint-phase` (which is a dedicated planning branch, not `main`).
  - The implementation changes will be applied to the development branch `phase8-development`.
  - All prior phases (Phases 1-7, covering database design, models, migrations, auth, items, requests/workflow, background email jobs, location matching, and analytics APIs) are complete, tested, and reviewed.

---

## 2. Third-Party Prerequisites

The following prerequisites must be verified or configured in the `.env` file at the project root before running the services or running tests:

⚠️ **User action required before implementation can begin:**

The following must be completed manually. Antigravity cannot do these steps.

**1. Supabase Project & Credentials**
- Go to `https://supabase.com/dashboard` and ensure your project is active.
- Under **Project Settings -> Database**, copy the Connection Strings.
- Under **Project Settings -> API**, copy the Project URL, Anon/Public Key, and the JWT Secret.
- Add these variables to your `.env` file:
  ```env
  SUPABASE_PROJECT_REF=your-project-ref
  SUPABASE_DB_PASSWORD=your-db-password
  DATABASE_URL=postgresql+asyncpg://postgres.your-project-ref:your-password@aws-0-region.pooler.supabase.com:5432/postgres
  ALEMBIC_DATABASE_URL=postgresql+asyncpg://postgres:your-password@db.your-project-ref.supabase.co:5432/postgres
  SUPABASE_URL=https://your-project-ref.supabase.co
  SUPABASE_ANON_KEY=your-supabase-anon-key
  SUPABASE_JWT_SECRET=your-supabase-jwt-secret
  ```

**2. Resend API Key**
- Go to `https://resend.com`, log in, and create an API Key under the **API Keys** section.
- Add the key to your `.env` file (for local development, use `onboarding@resend.dev` as sender):
  ```env
  RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxx
  RESEND_FROM_EMAIL=onboarding@resend.dev
  ```

**3. Supplemental JWT Secret Key**
- Generate a long random string for supplemental JWT signing:
  ```powershell
  [Convert]::ToBase64String((1..48 | ForEach-Object { Get-Random -Maximum 256 }))
  ```
- Add it to your `.env` file:
  ```env
  JWT_SECRET_KEY=your-generated-key-here
  ```

**4. Local Redis (via Docker)**
- Ensure Docker Desktop is running. The Redis service is automatically configured in `docker-compose.yml` to use port `6379`.
- Verify the following broker URLs are in your `.env` file:
  ```env
  CELERY_BROKER_URL=redis://redis:6379/0
  CELERY_RESULT_BACKEND=redis://redis:6379/0
  ```

Reply with ✅ when done so planning can continue.

---

## 3. Sub-Task List

We decompose Phase 8 into a flat, ordered list of tasks following the modular workflow:

| Task ID | Action Verb | File / Module | Description | Dependency |
|---|---|---|---|---|
| **T1** | Verify | `frontend/requirements.txt`, `frontend/.streamlit/config.toml` | Ensure that Streamlit dependencies and native dark theme settings are defined correctly. | none |
| **T2** | Create | `frontend/styles.css` | Implement global brand styles with GiveCircle colors, typography, input padding, metrics cards, and transitions. | T1 |
| **T3** | Create | `frontend/chart_theme.py` | Centralize Plotly chart visual theme settings (`PLOTLY_LAYOUT`) to enforce brand compliance. | T1 |
| **T4** | Create | `frontend/api_client.py` | Create the centralized HTTP helper using `httpx` to handle GET, POST, PATCH, and DELETE calls with token injection. | T1 |
| **T5** | Create | `frontend/components/status_badge.py` | Implement reusable category and status badge chips styled with HSL transparent colors. | T2 |
| **T6** | Create | `frontend/components/item_card.py` | Implement the reusable item preview card component showing title, condition, category, city, and request CTA. | T5 |
| **T7** | Create | `frontend/components/request_card.py` | Implement the reusable request card detailing status, messages, NGO notes, and lifecycle controls. | T5 |
| **T8** | Create | `frontend/app.py` | Implement the Streamlit app root, load CSS, and define the session-based navigation guard. | T2, T4 |
| **T9** | Create | `frontend/pages/1_Login.py` | Implement the Login page form, persist JWT payload in session state, and redirect on success. | T8 |
| **T10** | Create | `frontend/pages/2_Register.py` | Implement the user registration page with role-specific inputs, auto-login, and redirection. | T8 |
| **T11** | Create | `frontend/pages/3_Browse_Items.py` | Implement the public browse catalog with sidebar filters (category multiselect, location radius, condition) and request dialog. | T8, T6 |
| **T12** | Create | `frontend/pages/4_My_Listings.py` | Implement the donor portal for adding new listings, reviewing incoming requests, approving/rejecting, and soft-delete. | T8, T7 |
| **T13** | Create | `frontend/pages/5_My_Requests.py` | Implement the recipient request tracker with cancellation support. | T8, T7 |
| **T14** | Create | `frontend/pages/6_NGO_Dashboard.py` | Implement the NGO dashboard showing bulk metrics and requests history. | T8, T6, T7 |
| **T15** | Create | `frontend/pages/7_Analytics.py` | Implement the admin metrics dashboard rendering 4 Plotly charts using the unified chart theme. | T8, T3 |
| **T16** | Create | `frontend/tests/test_api_client.py` | Write unit tests for `api_client.py` verifying headers and error propagation. | T4 |
| **T17** | Verify | Entire Frontend Application | Perform a manual smoke test end-to-end to verify styling, state preservation, and flows. | T9, T10, T11, T12, T13, T14, T15, T16 |

---

## 4. Acceptance Criteria per Sub-Task

| Task ID | Verbatim Acceptance Criteria satisfied from the Roadmap |
|---|---|
| **T2, T3, T5** | "Global CSS and chart theme follow GiveCircle brand constraints." |
| **T4, T16** | "UI handles `401`, `403`, `404`, `409`, and `422` responses clearly." |
| **T6, T7** | "Shared components render UI and accept callbacks; page files own API mutations." |
| **T7, T12** | "Donor phone is not shown before approval." |
| **T8** | "Unauthenticated users can only access login/register." <br> "Donor-only, recipient-only, NGO-only, and admin-only pages enforce role redirects." |
| **T9** | "Login stores `token`, `user_id`, `role`, `full_name`, and `email` in session state." |
| **T10** | "Register auto-logins and redirects." |
| **T11** | "Browse page supports API filters and request dialog." |
| **T12** | "My Listings supports create, view incoming requests, approve, reject, pickup, and remove." |
| **T13** | "My Requests supports viewing and cancelling pending requests." |
| **T14** | "NGO dashboard supports NGO note and NGO request summary." |
| **T15** | "Analytics page renders summary metrics and four charts." |
| **T17** | Verification of all roadmap requirements working end-to-end. |

---

## 5. State Machines (UI Context)

The frontend UI controls the availability of actions based on item and request statuses:

### Item State Machine in UI

```
Item Statuses: available ➔ reserved ➔ donated
               available ➔ removed
```

- **`available`**:
  - Recipients and NGOs see the "Request This Item" button.
  - Donors see the "Remove Listing" button.
- **`reserved`**:
  - The "Request This Item" button is hidden.
  - The Donor sees the "Mark Picked Up" button on the approved request.
- **`donated`**:
  - No action buttons are displayed. Status badge shows "Donated".
- **`removed`**:
  - Listing is excluded from public browse results. Donor sees status badge "Removed".

### Request State Machine in UI

```
Request Statuses: pending ➔ approved
                  pending ➔ rejected
                  pending ➔ cancelled
                  approved ➔ picked_up
```

- **`pending`**:
  - Requesters (Recipients/NGOs) see the "Cancel Request" button on their My Requests page.
  - Donors see "Approve" and "Reject" buttons on their My Listings page.
- **`approved`**:
  - Donors see the "Mark Picked Up" button.
  - Requester sees the Donor's phone number.
  - "Approve", "Reject", and "Cancel" buttons are hidden.
- **`rejected`**, **`cancelled`**, **`picked_up`**:
  - No action buttons are displayed. The UI renders the final state badge.

All invalid state transitions must be caught. If the backend returns a `409 Conflict`, the UI must display a clear toast or banner alert explaining the state conflict (e.g. "This request has already been processed by the donor" or "This item has already been reserved").

---

## 6. Security and Privacy Requirements

| Security Question | Answer |
|---|---|
| **Which endpoints require authentication?** | All backend endpoints except register (`/api/auth/register`) and login (`/api/auth/login`). |
| **Which endpoints require a specific role?** | - Item creation/modification/deletion: `donor` role only.<br>- Request approval/rejection/pickup: `donor` role only (verified owner).<br>- Request creation: `recipient` or `ngo` role only.<br>- Analytics endpoints: `admin` role only. |
| **Which response fields must be hidden before approval?** | The donor's phone number (`donor.phone`) must never be exposed on the public browse page or item detail cards. It is only shown to the requester after request approval. |
| **Where must row-level ownership be enforced?** | Checked on the backend, but the frontend must only show action controls (Approve/Reject, Cancel, Delete, Edit) if the logged-in user matches the resource's owner ID (`donor_id` or `requester_id`). |
| **Where are JWTs validated?** | Validated by backend middleware on every request. The frontend must store the JWT in `st.session_state["token"]` and include it in the `Authorization: Bearer <token>` header of every API call. |
| **Which secrets must never reach Streamlit/browser code?** | Database URLs, Supabase service keys, the Supabase JWT secret, and the Resend API key must remain on the backend server. The frontend only communicates using the client JWT. |
| **What are the CORS requirements for this phase?** | Backend CORS must be configured to allow origins from the Streamlit server (`http://localhost:8501`). |

---

## 7. Transaction and Concurrency Requirements

- **Concurrent Approvals:**
  - When two donors try to approve competing requests, or a donor attempts to double-approve requests, the backend will reject the second approval with a `409 Conflict`.
  - The frontend must capture this error and show an `st.error` message: *"This item has already been approved for another request. Please refresh the page."*
- **Action Button Key Constraints:**
  - Streamlit reruns scripts on interaction. To prevent double submissions and action conflicts, all dynamically rendered buttons (e.g., in grids of cards) must have unique, deterministic keys:
    - Item Card Request button key: `req_{item_id}`
    - Request Card Approve button key: `approve_{request_id}`
    - Request Card Reject button key: `reject_{request_id}`
    - Request Card Pickup button key: `pickup_{request_id}`
    - Request Card Cancel button key: `cancel_{request_id}`

---

## 8. Test Case Inventory

### Happy-Path Tests
1. **User Authentication:** Login with valid credentials successfully populates `st.session_state["token"]` and other fields, then redirects to Browse Items.
2. **Registration:** Registering a new user completes, performs auto-login, and redirects.
3. **Item Creation:** Donor can submit the Add New Listing form, creating an item with status `available`.
4. **Request Submission:** Recipient can open the request dialog on an item, submit a message, and create a request with status `pending`.
5. **NGO Note persistence:** NGO user requesting an item can add an `ngo_note`, which is correctly visible to the donor.
6. **Request Approval:** Donor approving a request transitions that request to `approved` and the item to `reserved`.
7. **Competing Requests Auto-Rejection:** Approving a request automatically transitions all other pending requests for the same item to `rejected`.
8. **Pickup Confirmation:** Donor confirming pickup transitions the request to `picked_up` and the item to `donated`.

### Rejection and Transition Tests
9. **Cancelled Request:** Recipient cancels their pending request successfully (status transitions to `cancelled`).
10. **Double-Request Prevention:** Clicking the request button is prevented if there is already an active request by the user.
11. **Self-Request Prevention:** Requesters cannot see the "Request This Item" button on items they own.

### Authorization Tests
12. **Navigation Guards:** Trying to access page files (e.g. `My_Listings.py`) without logging in redirects the user back to the Login page.
13. **Role Redirects:** Trying to access `NGO_Dashboard.py` as a donor redirects to Browse Items.
14. **Admin Analytics guard:** Trying to access `Analytics.py` as a non-admin redirects to Browse Items.

### Privacy Tests
15. **Donor Phone Privacy:** Verify that the donor phone number is hidden in browse and pending request views, and only displayed when a request is approved.
16. **NGO Note Privacy:** Verify that the NGO note is only visible to the donor and the NGO requester, not to general browse views.

---

## 9. Risk Register

| Risk | Likelihood | Impact | Proposed Mitigation |
|---|---|---|---|
| **Streamlit Rerun Loop / Double API Calls** | High | Medium | Implement unique widget keys for all buttons. Use Streamlit forms where appropriate to batch input parameters, and use callbacks (`on_click`) to trigger state transitions followed immediately by `st.rerun()`. |
| **Expired JWT Session crash** | Medium | High | Catch `401 Unauthorized` in the centralized HTTP helpers in `api_client.py`. If a 401 is encountered, clear all auth keys from `st.session_state` and redirect the user to the Login page with a clear error warning. |
| **Stale State UI Out of Sync** | Medium | Medium | Implement toast notifications for errors (409 conflict, 404 not found) and force page reruns to reload fresh data from the API whenever actions complete. |
| **GiveCircle Branding Violations** | High | Low | Establish a global stylesheet (`frontend/styles.css`) that overwrites browser defaults. Enforce visual audits on page elements to ensure max font weight is 500, no pure blacks are used, and no purple/amber styling overlaps. |
