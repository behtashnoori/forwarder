# Phase 6N: Expert Dashboard KPIs OpenAPI/Client Alignment

## 1. Scope

This phase aligned Expert Dashboard KPI client usage with OpenAPI documentation for:

- `GET /api/expert/dashboard/kpis`

No runtime code was changed. No backend code, API behavior, auth behavior, routing, styling, schema/model, migrations, dependencies, ExpertLogin auth flow, or unrelated expert API calls were changed.

## 2. Current Frontend Client Usage

`fetchKPIs` is already centralized in `src/lib/api.ts`.

Current helper:

- Location: `src/lib/api.ts`
- Function: `fetchKPIs(expertId?: number): Promise<KPIs>`
- Path: `/api/expert/dashboard/kpis`
- Query behavior: sends `expert_id` when an `expertId` argument is provided
- Auth/token behavior: uses the shared `request()` helper, which attaches `Authorization: Bearer <expert_token>` from `localStorage`

Current frontend caller:

- `src/pages/ExpertConsole.tsx`
- Calls `fetchKPIs(expertId)` from `loadKPIs()`
- Stores the response in `kpis`
- Logs KPI load errors with `console.error`
- Does not show a toast for KPI load failures

Usage is already centralized. No `fetchKPIs` runtime refactor was needed.

## 3. OpenAPI Gap

`GET /api/expert/dashboard/kpis` was missing from `docs/openapi/openapi.yaml`.

Phase 6C and Phase 6M both identified it as an active frontend endpoint that was not documented in OpenAPI.

## 4. Changes Made

| File | Change summary | Reason | Runtime impact |
| --- | --- | --- | --- |
| `docs/openapi/openapi.yaml` | Added `GET /api/expert/dashboard/kpis` under `Expert Console` | Document an active centralized frontend endpoint | None |
| `docs/phase-6n-expert-dashboard-kpis-openapi-client-alignment.md` | Added Phase 6N documentation | Record client usage, contract, and verification | None |

## 5. Endpoint Contract

| Item | Contract |
| --- | --- |
| Method | `GET` |
| Path | `/api/expert/dashboard/kpis` |
| Auth requirement | Bearer token required |
| Request body | None |
| Query params | `expert_id` optional integer, because current `fetchKPIs(expertId)` sends it when provided |
| Success response | Object with `counts` and `sla` groups |
| Error responses | `401` and `500` documented using common OpenAPI error responses |

Known response fields from the current frontend type:

```ts
{
  counts: {
    new: number;
    in_progress: number;
    waiting_for_customer: number;
    closed_today: number;
  };
  sla: {
    overdue: number;
    due_soon: number;
  };
}
```

Known uncertainty:

- The schema keeps `additionalProperties: true` at object levels to reflect the current documentation style and avoid over-constraining fields not locked by this phase.
- No generated client was introduced.

## 6. Behavior Preservation

- UI behavior unchanged.
- Backend/API behavior unchanged.
- Auth/token behavior unchanged.
- Error/loading behavior unchanged.
- `fetchKPIs` remains unchanged and centralized.
- `ExpertLogin` was not refactored.
- Expert mutations, notifications, request list/detail, quote, message, assignment, and status behavior were not touched.

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
- Expert experts-list OpenAPI documentation
- Generated OpenAPI client
- Full expert API client review
- Frontend warning cleanup
