# Phase 6Q: Expert Mark-Read OpenAPI/Client Alignment

## 1. Scope

This phase aligned documentation for the existing Expert Console request mark-read API/client path only.

In scope:

- `POST /api/expert/requests/<id>/mark-read`
- `src/lib/api.ts` `markRequestAsRead` inspection
- Frontend usage search for `markRequestAsRead`
- OpenAPI documentation for the endpoint

Out of scope:

- Runtime code changes
- Backend behavior changes
- Frontend UI changes
- ExpertLogin auth flow
- Expert request list/detail, quote, message, notification, assignment, or status behavior changes

## 2. Current Frontend Client Usage

`markRequestAsRead` is already centralized in `src/lib/api.ts`.

- Function: `markRequestAsRead(requestId: number, expertId: number)`
- Method/path: `POST /api/expert/requests/${requestId}/mark-read`
- Query parameters sent by helper: `expert_id`
- Request body: none
- Response type: `{ message: string }`
- Auth/token behavior: uses the shared `request()` helper, so bearer token behavior remains centralized and unchanged.

Frontend usage search:

| Search area | Result |
| --- | --- |
| `src/pages` | No active caller found |
| `src/components` | No active caller found |
| `src/hooks` | No active caller found |

The helper exists and is centralized, but no active frontend call site was found during this phase.

## 3. OpenAPI Gap

`POST /api/expert/requests/{request_id}/mark-read` was missing from `docs/openapi/openapi.yaml`.

`POST /api/expert/notifications/mark-read` was already documented, but that is a separate notification endpoint and not the request mark-read endpoint targeted in this phase.

## 4. Changes Made

| File | Change summary | Reason | Runtime impact |
| --- | --- | --- | --- |
| `docs/openapi/openapi.yaml` | Added `POST /api/expert/requests/{request_id}/mark-read` path | Document existing request mark-read endpoint/helper contract | None |
| `docs/phase-6q-expert-mark-read-openapi-client-alignment.md` | Added Phase 6Q review and verification notes | Record alignment decision and contract | None |

No changes were made to `src/lib/api.ts` or frontend files.

## 5. Endpoint Contract

| Item | Contract |
| --- | --- |
| Method | `POST` |
| Path | `/api/expert/requests/{request_id}/mark-read` |
| Auth | Bearer token required through expert auth context |
| Path params | `request_id` integer |
| Query params | `expert_id` optional; sent by the current centralized helper |
| Request body | None |
| Success status | `200` |
| Success payload | `{ "message": "..." }` |
| Error statuses | `401`, `403`, `404`, `500` |

Known side effects from current backend route:

- Looks up `ShipmentRequest` by `request_id`
- Applies authenticated access checks through the current expert route guard
- Sets `has_unread_for_assignee` to `False`
- Commits on success and rolls back on unexpected error

## 6. Behavior Preservation

- UI behavior unchanged.
- Backend/API behavior unchanged.
- Endpoint method and path unchanged.
- Auth/token behavior unchanged.
- Error/loading behavior unchanged.
- `markRequestAsRead` remains unchanged and centralized.

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
| OpenAPI parse | Pass, request mark-read endpoint documented |

## 8. Deferred Items

- ExpertLogin API client refactor
- Expert notification mark-read client/OpenAPI follow-up if needed
- Generated OpenAPI client
- Full expert API client review
- Frontend warning cleanup
