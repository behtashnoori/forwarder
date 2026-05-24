# Phase 6P: Expert Status Update OpenAPI/Client Alignment

## 1. Scope

This phase aligned documentation for the existing Expert Console status update API/client path only.

In scope:

- `POST /api/expert/requests/<id>/status`
- `src/lib/api.ts` `changeRequestStatus` inspection
- Existing frontend callers of `changeRequestStatus`
- OpenAPI documentation for the endpoint

Out of scope:

- Runtime code changes
- Backend behavior changes
- Frontend UI changes
- ExpertLogin auth flow
- Quote, message, notification, assignment, list, or detail refactors

## 2. Current Frontend Client Usage

`changeRequestStatus` is already centralized in `src/lib/api.ts`.

- Function: `changeRequestStatus(requestId: number, status: string, note?: string)`
- Method/path: `POST /api/expert/requests/${requestId}/status`
- Request body: `{ status, note }`
- Response type: `{ message: string; status: string }`
- Auth/token behavior: uses the shared `request()` helper, so bearer token behavior remains centralized and unchanged.

Current frontend callers:

| Frontend file | Usage | Notes |
| --- | --- | --- |
| `src/pages/ExpertConsole.tsx` | Calls `changeRequestStatus(requestId, newStatus, note)` | Updates status from the console list and reloads KPI/list state through existing behavior. |
| `src/pages/RequestDetail.tsx` | Calls `changeRequestStatus(Number(id), newStatus, note)` | Updates local request status after success through existing behavior. |

No direct frontend `fetch` or raw API call for this endpoint was found.

## 3. OpenAPI Gap

`POST /api/expert/requests/{request_id}/status` was not documented in `docs/openapi/openapi.yaml`.

The endpoint was added using the current frontend client, backend route, and characterization test behavior as sources.

## 4. Changes Made

| File | Change summary | Reason | Runtime impact |
| --- | --- | --- | --- |
| `docs/openapi/openapi.yaml` | Added `ExpertStatusUpdateRequest` schema and `POST /api/expert/requests/{request_id}/status` path | Document active centralized expert status update endpoint | None |
| `docs/phase-6p-expert-status-update-openapi-client-alignment.md` | Added Phase 6P review and verification notes | Record alignment decision and contract | None |

No changes were made to `src/lib/api.ts` or frontend callers.

## 5. Endpoint Contract

| Item | Contract |
| --- | --- |
| Method | `POST` |
| Path | `/api/expert/requests/{request_id}/status` |
| Auth | Bearer token required through expert auth context |
| Path params | `request_id` integer |
| Query params | None |
| Request body | JSON object with `status` and optional `note` |
| Valid statuses | `new`, `assigned`, `in_progress`, `quoted`, `waiting_for_customer`, `won`, `lost`, `closed` |
| Success status | `200` |
| Success payload | `{ "message": "...", "status": "<new_status>" }` |
| Error statuses | `400`, `401`, `403`, `404`, `500` |

Known side effects from current backend route:

- Updates `ShipmentRequest.status`
- Sets `has_unread_for_assignee`
- Sets SLA due date when status becomes `assigned` and no SLA exists
- Creates `ExpertConsoleLog` with `action="status_change"`
- Creates `ExpertConsoleNotification` when the request has an assignee
- Commits on success and rolls back on unexpected error

## 6. Behavior Preservation

- UI behavior unchanged.
- Backend/API behavior unchanged.
- Endpoint method and path unchanged.
- Auth/token behavior unchanged.
- Error/loading behavior unchanged.
- `changeRequestStatus` remains unchanged and centralized.

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
| OpenAPI parse | Pass, status endpoint documented |

## 8. Deferred Items

- ExpertLogin API client refactor
- Expert mark-read OpenAPI documentation
- Expert notifications OpenAPI/client follow-up if needed
- Generated OpenAPI client
- Full expert API client review
- Frontend warning cleanup
