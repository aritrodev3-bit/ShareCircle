# Git Branch Validation & Repository Governance Report

This report documents the realignment of the GiveCircle repository branching strategy with the restructured implementation roadmap. It serves as an audit trail for the transition from the old Streamlit MVP plan to the Next.js frontend and Google Auth roadmap.

---

## 1. Executive Summary

To accommodate new product direction (deprecated Streamlit UI, Next.js frontend, backend Google Authentication, and AI description generator), the repository branching structure has been realigned.
* **Stable Baseline**: Tag `v0.7-stable` (commit `39d42e8ff4e367d51a150f5c8258176294918c86`) serves as the official stable baseline.
* **Archived Work**: Streamlit UI and related E2E tests have been archived onto dedicated branches and deleted from the active branch list.
* **New Active Tracks**: Clean development branches have been cut from the `v0.7-stable` baseline.

---

## 2. Branch Mapping and Status

| Branch Name | Type | Origin Commit / Tag | Status | Description |
| :--- | :--- | :--- | :--- | :--- |
| `main` | Production | `2df02434` (Tag: `v0.8-stable`) | Active (Pending Phase 8-12 merges) | Main production branch |
| `old-phase8-streamlit` | Archived | `03935722` | **Frozen / Archived** | Original Streamlit frontend MVP |
| `old-phase9-e2e-original` | Archived | `2df02434` | **Frozen / Archived** | Original Playwright E2E tests for Streamlit |
| `phase5-development` | Frozen | `3f309774` (Tag: `v0.5-stable` merge base) | **Frozen / Read-Only** | Phase 5 historical work |
| `phase6-development` | Frozen | `25314a05` (Tag: `v0.6-stable` merge base) | **Frozen / Read-Only** | Phase 6 historical work |
| `phase7-development` | Frozen | `7a2c618e` (Tag: `v0.7-stable` merge base) | **Frozen / Read-Only** | Phase 7 historical work |
| `phase8-google-auth` | Development | `39d42e8f` (Tag: `v0.7-stable`) | **Active (Current Start)** | FastAPI Google OAuth integration |
| `phase9-ai-generator` | Development | `39d42e8f` (Tag: `v0.7-stable`) | Active (Parallel Track) | AI listing generation using Gemini |
| `phase10-nextjs-frontend` | Development | `39d42e8f` (Tag: `v0.7-stable`) | Active (Parallel Track) | Next.js + TailwindCSS frontend |
| `phase11-smoke-testing` | Integration | `39d42e8f` (Tag: `v0.7-stable`) | Active (Integration base) | Merge validation branch for Phases 8-10 |
| `phase12-e2e-testing` | Testing | `39d42e8f` (Tag: `v0.7-stable`) | Active (Post-Integration testing) | Next.js Playwright E2E testing suite |

---

## 3. Ancestry Audit

* **`v0.7-stable` Priority Rule**:
  - The tag `v0.7-stable` points to commit `39d42e8ff4e367d51a150f5c8258176294918c86`.
  - All commits on `phase7-development` after `v0.7-stable` are unreviewed and **must not** be carried forward.
  - Verification: `git merge-base phase8-google-auth phase7-development` returns `39d42e8ff4e367d51a150f5c8258176294918c86`. All active branches are strictly clean forks of the stable tag.

---

## 4. Documentation Update Log

* **`README.md`**: Created/updated to list the new active development tracks, clarify the deprecation of the Streamlit frontend, and document the baseline priority constraints.
* **`docs/superpowers/plans/2026-06-03-community-donation-platform-roadmap (1).md`**: Restructured Phases 8 through 12 to match the updated roadmap (Google Auth, AI Generator, Next.js Frontend, Integration Smoke Testing, Next.js Playwright E2E).

---

## 5. Requires Human Action: GitHub Branch Protection Rules

The following branch protection rules must be configured manually in the GitHub repository settings UI.

### Rule A: Protect the Production Branch (`main`)
* **Target Pattern**: `main`
* **Settings**:
  - [x] **Require a pull request before merging**
    - **Required approvals**: `1`
    - [x] **Dismiss stale pull request approvals when new commits are pushed**
    - [x] **Require review from Code Owners** (if `CODEOWNERS` is added)
  - [x] **Require status checks to pass before merging**
    - [x] **Require branches to be up to date before merging**
  - [x] **Require conversation resolution before merging**
  - [x] **Restrict who can push to matching branches** (restrict to Repository Admins and Release Lead)
  - [x] **Block force pushes**
  - [x] **Block deletions**

### Rule B: Protect Active Development Tracks (`phase*`)
* **Target Pattern**: `phase8-google-auth`, `phase9-ai-generator`, `phase10-nextjs-frontend`, `phase11-smoke-testing`, `phase12-e2e-testing` (Alternatively, use the wildcards `phase8-*`, `phase9-*`, `phase10-*`, `phase11-*`, `phase12-*`)
* **Settings**:
  - [x] **Require a pull request before merging**
    - **Required approvals**: `1`
    - [x] **Dismiss stale pull request approvals when new commits are pushed**
  - [x] **Require conversation resolution before merging**
  - [x] **Block force pushes**
  - [x] **Block deletions**

### Rule C: Freeze Completed Phases 1-7 and Archived Branches
* **Target Patterns**: `phase5-development`, `phase6-development`, `phase7-development`, `old-phase8-streamlit`, `old-phase9-e2e-original`
* **Settings**:
  - [x] **Lock branch** (makes the branches read-only)
  - *If GitHub Rulesets are not available:*
    - [x] **Require a pull request before merging**
      - **Required approvals**: `6` (or set to maximum to block merges)
    - [x] **Restrict who can push to matching branches** (restrict to **no one** / empty list)
    - [x] **Block force pushes**
    - [x] **Block deletions**
