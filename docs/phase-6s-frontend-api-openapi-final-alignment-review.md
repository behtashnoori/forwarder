# Phase 6S: Frontend API/OpenAPI Final Alignment Review

## 1. Scope

This phase is review and documentation only.

No runtime code, frontend code, backend code, API behavior, OpenAPI contract, schema/model, migration, auth/security behavior, styling, routing, or dependencies were changed.

Reviewed:

- `src/lib/api.ts`
- `src/pages/*`
- `src/components/*`
- `src/hooks/*`
- `docs/openapi/openapi.yaml`
- Phase 6C through 6R documentation

## 2. Completed Frontend API Client Refactors

| Phase | Endpoint/domain | Files changed | Status | Notes |
| --- | --- | --- | --- | --- |
| 6C | Frontend API inventory | `docs/phase-6c-frontend-api-client-refactor-inventory.md` | Completed | Identified Public Tracking as first safe slice and noted direct user-management/auth calls. |
| 6D | `GET /api/public/track/<identifier>` | `src/lib/api.ts`, public tracking page, docs | Completed | Public tracking call centralized. |
| 6E | `GET /api/customer/profile/<customer_id>` | `src/lib/api.ts`, customer profile caller, docs | Completed | Customer profile read centralized. |
| 6F | `GET /api/customer/workflow/<customer_id>` | `src/lib/api.ts`, customer workflow caller, docs | Completed | Customer workflow read centralized. |
| 6G | `GET /api/customer/verify-email` | `src/lib/api.ts`, verify email page, docs | Completed | Email verification call centralized with existing UX preserved. |
| 6H | `POST /api/customer/register` | docs only | Verified no-op | No active frontend caller found; no unused helper added. |
| 6I | `POST /api/customer/complete-step` | docs only | Verified no-op | No active frontend caller found; no unused helper added. |
| 6J | `GET /api/admin/dashboard` | `src/lib/api.ts`, admin dashboard caller, docs | Completed | Admin dashboard call centralized. |
| 6K | `GET /api/admin/reports/assignment-summary` | docs only | Verified no-op | No active frontend caller found. |
| 6L | `GET /api/admin/shipment-requests*` | docs only | Verified no-op | No active frontend callers found. |
| 6M | Expert Console inventory | docs only | Completed | Found expert calls mostly centralized; login remained direct and high risk. |
| 6N | `GET /api/expert/dashboard/kpis` | `docs/openapi/openapi.yaml`, docs | Completed | Existing centralized helper documented in OpenAPI. |
| 6O | `GET /api/expert/experts` | `docs/openapi/openapi.yaml`, docs | Completed | Existing centralized helper documented in OpenAPI. |
| 6P | `POST /api/expert/requests/<id>/status` | `docs/openapi/openapi.yaml`, docs | Completed | Existing centralized helper documented in OpenAPI. |
| 6Q | `POST /api/expert/requests/<id>/mark-read` | `docs/openapi/openapi.yaml`, docs | Completed | Existing centralized helper documented in OpenAPI; no active frontend caller found. |
| 6R | `POST /api/expert/auth/login` | docs only | Deferred | Auth refactor deferred because login owns token storage, role routing, and custom error behavior. |

## 3. Remaining Direct API Calls

| File | Endpoint/path | Reason remaining | Risk level | Recommended action |
| --- | --- | --- | --- | --- |
| `src/components/ExpertLogin.tsx` | `POST /api/expert/auth/login` | Auth boundary; current component parses JSON before success checks and owns token storage, toast, and role navigation. | High | Defer until auth-specific frontend tests or manual QA checklist exist. |
| `src/pages/UserManagement.tsx` | `/api/user-management/users`, `/api/user-management/transport-methods`, `/api/user-management/assignment-rules`, `/api/user-management/assignment-statistics` | Page still has direct admin CRUD/fetch logic despite helpers existing in `src/lib/api.ts`; behavior is admin/auth-heavy and broad. | Medium-high | Plan a focused UserManagement frontend client consolidation phase. |
| `src/App.tsx` | `GET /api/health` | Small app health probe; not part of the main API client refactor slices. | Low | Keep deferred or document as internal health endpoint before wrapping. |
| `src/lib/api.ts` | `fetch()` inside specialized helpers | These are centralized helpers with custom status/error behavior or upload requirements. | Low | Accept; do not force them through the generic helper unless behavior is explicitly characterized. |

## 4. OpenAPI Gap Review

| Endpoint | Documented? | Used by frontend? | Risk | Action |
| --- | --- | --- | --- | --- |
| `GET /api/public/track/{identifier}` | Yes | Yes | Low | No action. |
| `GET /api/customer/profile/{customer_id}` | Yes | Yes | Low | No action. |
| `GET /api/customer/workflow/{customer_id}` | Yes | Yes | Low | No action. |
| `GET /api/customer/verify-email` | Yes | Yes | Low | No action. |
| `GET /api/admin/dashboard` | Yes | Yes | Low | No action. |
| `GET /api/expert/dashboard/kpis` | Yes | Yes | Low | No action. |
| `GET /api/expert/experts` | Yes | Yes | Low | No action. |
| `POST /api/expert/requests/{request_id}/status` | Yes | Yes | Medium | No action for now; mutation behavior is documented. |
| `POST /api/expert/requests/{request_id}/mark-read` | Yes | Helper exists, no active caller found | Low | No action. |
| `POST /api/expert/auth/login` | Yes | Yes, direct | High | Keep documented; defer refactor. |
| `GET /api/provinces`, `GET /api/counties`, `GET /api/cities` | Not fully covered in OpenAPI | Yes, centralized helpers | Medium | OpenAPI gap completion later. |
| `GET /api/countries`, `GET /api/international-cities` | Not fully covered in OpenAPI | Yes, centralized helpers | Medium | OpenAPI gap completion later. |
| `GET /api/iran-ports`, `GET /api/port-province-mappings`, `GET /api/recommended-ports` | Not fully covered in OpenAPI | Yes, centralized helpers | Medium | OpenAPI gap completion later. |
| `GET /api/health` | Not documented in OpenAPI | Yes, direct app probe | Low | Document later as internal health endpoint if desired. |
| User management endpoints | Mostly documented | Yes, direct page calls and helpers | Medium-high | Refactor only in a focused UserManagement frontend phase. |

## 5. API Client Health Review

`src/lib/api.ts` is now the main frontend API surface for most domains. It contains public shipment, public tracking, customer reads, admin dashboard, expert console, site settings, CRM, user management, referral rules, and port/location helpers.

Health notes:

- Size: The file is large and functional, but still readable. Splitting by domain may help later, but doing it now would create broad import churn.
- Type quality: Many important response shapes are typed, especially newer centralized helpers. Some older CRM/user-management/location helpers still use broad or partial types.
- Error handling: The generic `request()` helper centralizes bearer-token behavior and error extraction, but several helpers intentionally use direct `fetch()` for custom status handling or upload behavior.
- Auth/token consistency: Most protected helpers use `expert_token` through the shared `request()` helper. ExpertLogin remains intentionally direct because it creates the token and owns login-specific UX.
- Generated client readiness: A generated OpenAPI client should still be deferred. OpenAPI coverage is much better for the reviewed slices, but location/port/health and some admin/user-management/frontend assumptions still need cleanup before generation would be low-churn.

## 6. Closure Decision

Decision: `READY_TO_CLOSE_FRONTEND_API_ALIGNMENT`

Reason:

- The safe active frontend slices from Phase 6C were centralized or explicitly verified as no-ops.
- Expert OpenAPI gaps discovered during inventory were closed for KPI, experts-list, status update, and request mark-read.
- Remaining direct calls are understood and intentionally deferred due to auth sensitivity, broad admin/user-management coupling, or low-risk internal health probing.
- No blocking OpenAPI gap remains for the recently refactored active slices.

## 7. Recommended Next Phase

Recommended: `Phase 6T: Final Stabilization & Closure Report`

This is the most practical next step because multiple backend and frontend alignment phases have accumulated. A stabilization report can consolidate closure state, known warnings, deferred risks, and the next safe work queue before starting another refactor stream.

## 8. Deferred Items

- Generated OpenAPI client
- Full frontend refactor
- UserManagement frontend API consolidation
- ExpertLogin auth helper extraction
- Location/port/health OpenAPI gap completion
- UI redesign
- Warning cleanup
- Repository layer
- Deployment pipeline

## 9. Verification

| Check | Result |
| --- | --- |
| `npm.cmd run lint` | Pass, existing 17 warnings |
| `npm.cmd run build` | Pass, existing Browserslist/chunk-size warnings |
| `npm.cmd run check:structure` | Pass |
| `python -m pytest -q` | Pass, `86 passed, 724 warnings` |
| `git diff --check` | Pass, existing CRLF warnings |
| OpenAPI parse with PyYAML | Pass |
