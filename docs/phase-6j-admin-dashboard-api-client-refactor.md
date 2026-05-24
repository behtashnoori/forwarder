# Phase 6J: Admin Dashboard API Client Refactor

## 1. Scope

This phase refactored only frontend admin dashboard API usage for `GET /api/admin/dashboard` into the centralized API client.

No backend code, OpenAPI documentation, routing, styling, schema, auth/security, dependencies, or unrelated frontend domains were changed.

## 2. Before

The direct admin dashboard API call lived in `src/pages/AdminPanel.tsx`.

The page:

- Read `expert_token` from `localStorage`.
- Guarded missing/null tokens locally and redirected to `/`.
- Called `fetch(`${env.API_URL}/api/admin/dashboard`, { headers: { Authorization: `Bearer ${token}` } })`.
- Parsed the dashboard payload on success.
- Treated `401` as an expired session.
- Showed a dashboard-fetch error for other non-OK responses.
- Showed a server-connection error for thrown fetch errors.

## 3. API Client Design

Added centralized API client exports in `src/lib/api.ts`:

| Export | Responsibility |
| --- | --- |
| `AdminDashboardStats` | Shared TypeScript shape for the current dashboard response |
| `AdminDashboardHttpError` | Preserves HTTP status for route-specific error handling |
| `fetchAdminDashboard(token)` | Calls `GET /api/admin/dashboard` with the same bearer token header behavior |

The helper intentionally keeps explicit token input so `AdminPanel` can preserve its existing missing-token guard and session cleanup behavior.

## 4. Changes Made

| File | Change summary | Reason | Behavior impact |
| --- | --- | --- | --- |
| `src/lib/api.ts` | Added `AdminDashboardStats`, `AdminDashboardHttpError`, and `fetchAdminDashboard(token)` | Centralize the admin dashboard API call while preserving status-aware handling | No behavior change |
| `src/pages/AdminPanel.tsx` | Replaced direct `fetch` call with `fetchAdminDashboard(token)` and reused `AdminDashboardStats` type | Remove scattered raw API call for admin dashboard only | No UI behavior change |
| `docs/phase-6j-admin-dashboard-api-client-refactor.md` | Added phase documentation | Record scope, design, and verification | None |

## 5. Behavior Preservation

- Endpoint path remains `GET /api/admin/dashboard`.
- Bearer token header remains `Authorization: Bearer <token>`.
- Missing or `"null"` token behavior remains in `AdminPanel`.
- `401` still clears `expert_user` and `expert_token`, shows the same destructive toast, and navigates to `/`.
- Other non-OK responses still show the dashboard statistics error toast.
- Network/thrown errors still show the server communication error toast.
- Loading state still starts before the request and clears in `finally`.
- Dashboard metric rendering still reads the same `dashboardStats` fields.
- No dashboard UI, tab behavior, retry behavior, or styling changed.

## 6. Verification

| Check | Result |
| --- | --- |
| `npm.cmd run lint` | Pass, with existing warnings |
| `npm.cmd run build` | Pass, with existing Browserslist/chunk-size warnings |
| `npm.cmd run check:structure` | Pass |
| `python -m pytest -q` | Pass |
| `git diff --check` | Pass, with existing CRLF warnings |

## 7. Deferred Items

- Generated OpenAPI client
- Admin assignment summary API client refactor
- Admin shipment request API client refactor
- Expert API client refactor
- CRM API client refactor
- User management API client refactor
- Frontend warning cleanup
