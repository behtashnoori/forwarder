# Phase 6R: ExpertLogin API Client Refactor Decision

## 1. Scope

This phase reviewed the remaining direct ExpertLogin API call and decided whether to refactor it into the centralized API client now.

In scope:

- `src/components/ExpertLogin.tsx`
- `src/lib/api.ts` auth/API helper patterns
- `POST /api/expert/auth/login`
- Current token storage, error, loading, and navigation behavior

Out of scope:

- Backend code changes
- Auth behavior changes
- Token storage behavior changes
- Login response contract changes
- Routing/navigation changes
- UI/styling changes
- Refresh/logout refactors
- Unrelated expert API calls

## 2. Current Login Flow

`src/components/ExpertLogin.tsx` performs a direct `fetch` call.

| Behavior | Current flow |
| --- | --- |
| URL | `${env.API_URL}/api/expert/auth/login` |
| Method | `POST` |
| Headers | `Content-Type: application/json` |
| Request body | `{ username, password }` |
| Response parsing | Always calls `response.json()` before checking success |
| Success condition | `response.ok && data.success` |
| Token storage | Stores `data.tokens.access_token` as `expert_token` |
| Expert storage | Stores `data.expert` JSON as `expert_user` |
| Success toast | Shows localized welcome message using `data.expert.full_name` |
| Navigation | Admin role goes to `/admin`; all others go to `/expert` |
| Error payload | Uses `data.error` or a localized invalid credentials fallback |
| Network/unexpected error | Logs to console and shows localized retry error |
| Loading behavior | `setLoading(true)` before request and `setLoading(false)` in `finally` |

The backend route currently returns:

- `200` with `{ success: true, expert, tokens }` on success
- `401` with `{ error: "..." }` for invalid credentials
- `500` with `{ error: "..." }` for unexpected errors
- explicit CORS headers for login and preflight behavior

## 3. Decision

Decision: `DEFER_AUTH_REFACTOR`

## 4. If Refactored: API Client Design

No refactor was performed in this phase.

A future safe refactor should avoid the generic `request()` helper unless it can preserve login behavior exactly. A dedicated helper would likely need to:

- call `POST /api/expert/auth/login`
- always parse JSON before interpreting success/failure
- return both `response.ok` and parsed data, or otherwise preserve `response.ok && data.success`
- avoid changing token storage, expert storage, toast, loading, and navigation behavior
- avoid changing refresh/logout behavior in the same slice

## 5. If Deferred: Reason

The refactor was deferred because this is an auth boundary and the current login component owns several product-sensitive behaviors:

- token storage keys: `expert_token`, `expert_user`
- role-based navigation to `/admin` or `/expert`
- localized invalid credentials and retry messages
- direct handling of `response.ok && data.success`
- login-specific CORS behavior on the backend

The existing centralized `request()` helper throws on non-OK responses, while the current login flow parses the response body first and then decides how to show errors. Using the generic helper would risk changing error behavior. A custom helper could preserve behavior, but that should be done in a small auth-specific phase with focused frontend verification.

## 6. Behavior Preservation

- UI behavior unchanged.
- Backend/API behavior unchanged.
- Auth/token behavior unchanged.
- Login response handling unchanged.
- Loading behavior unchanged.
- Navigation behavior unchanged.
- ExpertLogin direct fetch remains in place intentionally.

## 7. Verification

Before documentation changes:

| Check | Result |
| --- | --- |
| `npm.cmd run lint` | Pass, existing 17 warnings |
| `npm.cmd run build` | Pass, existing Browserslist/chunk-size warnings |
| `npm.cmd run check:structure` | Pass |
| `python -m pytest -q` | Pass, `86 passed, 724 warnings` |
| `git diff --check` | Pass, existing CRLF warnings |

After documentation changes:

| Check | Result |
| --- | --- |
| `npm.cmd run lint` | Pass, existing 17 warnings |
| `npm.cmd run build` | Pass, existing Browserslist/chunk-size warnings |
| `npm.cmd run check:structure` | Pass |
| `python -m pytest -q` | Pass, `86 passed, 724 warnings` |
| `git diff --check` | Pass, existing CRLF warnings |

## 8. Deferred Items

- Auth-specific ExpertLogin API helper
- Frontend login behavior tests before auth helper extraction
- Refresh/logout API client review
- Generated OpenAPI client
- Full auth flow review
- Frontend warning cleanup
