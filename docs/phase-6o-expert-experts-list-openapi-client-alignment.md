# Phase 6O: Expert Experts-List OpenAPI/Client Alignment

## 1. Scope

This phase aligned Expert Experts-List client usage with OpenAPI documentation for:

- `GET /api/expert/experts`

No runtime code was changed. No backend code, API behavior, auth behavior, routing, styling, schema/model, migrations, dependencies, ExpertLogin auth flow, or unrelated expert API calls were changed.

## 2. Current Frontend Client Usage

`fetchExperts` is already centralized in `src/lib/api.ts`.

Current helper:

- Location: `src/lib/api.ts`
- Function: `fetchExperts(): Promise<{ experts: ExpertUser[] }>`
- Path: `/api/expert/experts`
- Query behavior: no query params
- Auth/token behavior: uses the shared `request()` helper, which attaches `Authorization: Bearer <expert_token>` from `localStorage`

Current frontend callers:

- `src/pages/ExpertConsole.tsx`
  - Uses `fetchExperts()` as a fallback when `expert_user` is not available in `localStorage`.
  - Selects the mock expert id or the first returned expert.
- `src/pages/RequestDetail.tsx`
  - Imports `fetchExperts`, but no active call was found in the current inspected file.

Usage is already centralized. No `fetchExperts` runtime refactor was needed.

## 3. OpenAPI Gap

`GET /api/expert/experts` was missing from `docs/openapi/openapi.yaml`.

Phase 6C and Phase 6M identified it as an active centralized frontend endpoint that lacked OpenAPI coverage.

## 4. Changes Made

| File | Change summary | Reason | Runtime impact |
| --- | --- | --- | --- |
| `docs/openapi/openapi.yaml` | Added `GET /api/expert/experts` under `Expert Console` | Document an active centralized frontend endpoint | None |
| `docs/phase-6o-expert-experts-list-openapi-client-alignment.md` | Added Phase 6O documentation | Record client usage, contract, and verification | None |

## 5. Endpoint Contract

| Item | Contract |
| --- | --- |
| Method | `GET` |
| Path | `/api/expert/experts` |
| Auth requirement | Bearer token required |
| Request body | None |
| Query params | None used by the current client |
| Success response | Object with `experts` array |
| Error responses | `401` and `500` documented using common OpenAPI error responses |

Known response fields from the current frontend type:

```ts
{
  experts: Array<{
    id: number;
    username: string;
    full_name: string;
    role: string;
  }>;
}
```

Known uncertainty:

- The schema keeps `additionalProperties: true` to match the current OpenAPI style and avoid over-constraining fields not locked by this phase.
- No generated client was introduced.

## 6. Behavior Preservation

- UI behavior unchanged.
- Backend/API behavior unchanged.
- Auth/token behavior unchanged.
- Error/loading behavior unchanged.
- `fetchExperts` remains unchanged and centralized.
- `ExpertLogin` was not refactored.
- Expert request list/detail, quote, message, notification, assignment, and status behavior were not touched.

## 7. Verification

| Check | Result |
| --- | --- |
| `npm.cmd run lint` | Pass, with existing warnings |
| `npm.cmd run build` | Pass, with existing Browserslist/chunk-size warnings |
| `npm.cmd run check:structure` | Pass |
| `python -m pytest -q` | Pass |
| `git diff --check` | Pass, with existing CRLF warnings |
| OpenAPI parse with PyYAML | Pass |

## 8. Deferred Items

- ExpertLogin API client refactor
- Expert status update OpenAPI documentation
- Expert mark-read OpenAPI documentation
- Generated OpenAPI client
- Full expert API client review
- Frontend warning cleanup
