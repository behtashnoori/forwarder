# Phase 6C: Frontend API Client Refactor Inventory

## 1. Scope

Phase 6C is review and planning only. No runtime code, backend code, frontend behavior, schemas, migrations, auth/security behavior, dependencies, or API contracts were changed.

The goal was to inventory frontend API usage, compare it with `docs/openapi/openapi.yaml`, and choose a low-risk first refactor slice for a future phase.

## 2. Frontend API Usage Inventory

| Frontend file | Endpoint/path used | Method | Domain | Centralized or scattered? | OpenAPI documented? | Risk level |
| --- | --- | --- | --- | --- | --- | --- |
| `src/lib/api.ts` | `/api/shipment-request` | POST | Public shipment request | Centralized | Yes | Medium |
| `src/lib/api.ts` | `/api/transport-methods` | GET | Public shipment request | Centralized | Yes | Low |
| `src/lib/api.ts` | `/api/provinces`, `/api/counties`, `/api/cities` | GET | Location lookup | Centralized | No | Medium |
| `src/lib/api.ts` | `/api/countries`, `/api/international-cities` | GET | Location lookup | Centralized | No | Medium |
| `src/lib/api.ts` | `/api/iran-ports`, `/api/port-province-mappings`, `/api/recommended-ports` | GET | Port lookup | Centralized | No | Medium |
| `src/lib/api.ts` | `/api/expert/requests` | GET | Expert console | Centralized | Yes | Medium |
| `src/lib/api.ts` | `/api/expert/requests/{id}` | GET | Expert console | Centralized | Yes | Medium |
| `src/lib/api.ts` | `/api/expert/requests/{id}/quote` | POST | Expert console | Centralized | Yes | High |
| `src/lib/api.ts` | `/api/expert/requests/{id}/assign` | POST | Expert console | Centralized | Yes | High |
| `src/lib/api.ts` | `/api/expert/requests/{id}/messages` | POST | Expert console | Centralized | Yes | High |
| `src/lib/api.ts` | `/api/expert/notifications` | GET | Expert console | Centralized | Yes | Medium |
| `src/lib/api.ts` | `/api/expert/requests/{id}/status` | POST | Expert console | Centralized | No | High |
| `src/lib/api.ts` | `/api/expert/dashboard/kpis` | GET | Expert console | Centralized | No | Medium |
| `src/lib/api.ts` | `/api/expert/requests/{id}/mark-read` | POST | Expert console | Centralized | No | Medium |
| `src/lib/api.ts` | `/api/expert/experts` | GET | Expert console | Centralized | No | Medium |
| `src/lib/api.ts` | `/api/site-settings`, `/api/admin/site-settings`, `/api/admin/upload` | GET/PUT/POST | Site settings | Centralized | Yes | Medium |
| `src/lib/api.ts` | `/api/crm/customers`, `/api/crm/opportunities`, `/api/crm/activities`, `/api/crm/dashboard/kpis` | GET/POST | CRM | Centralized | Yes | Medium |
| `src/lib/api.ts` | `/crm/customers/{id}` | GET/PUT | CRM | Centralized | No, and likely path mismatch | High |
| `src/lib/api.ts` | `/api/user-management/*` | GET/POST/PUT | User management | Centralized | Yes | High |
| `src/lib/api.ts` | `/api/admin/referral-rules*` | GET/POST/PUT/DELETE | Admin referral rules | Centralized | Yes | High |
| `src/App.tsx` | `/api/health` | GET | App health | Scattered | No | Low |
| `src/components/ExpertLogin.tsx` | `/api/expert/auth/login` | POST | Expert auth | Scattered | Yes | Medium |
| `src/pages/AdminPanel.tsx` | `/api/admin/dashboard` | GET | Admin panel | Scattered | Yes | Medium |
| `src/pages/UserManagement.tsx` | `/api/user-management/users` | GET/POST | User management | Scattered | Yes | High |
| `src/pages/UserManagement.tsx` | `/api/user-management/users/{id}` | PUT/DELETE | User management | Scattered | Yes | High |
| `src/pages/UserManagement.tsx` | `/api/user-management/transport-methods` | GET | User management | Scattered | Yes | Medium |
| `src/pages/UserManagement.tsx` | `/api/user-management/assignment-rules` | GET | User management | Scattered | Yes | Medium |
| `src/pages/UserManagement.tsx` | `/api/user-management/assignment-statistics` | GET | User management | Scattered | Yes | Medium |
| `src/pages/CustomerDashboard.tsx` | `/api/customer/profile/{customer_id}` | GET | Customer gamification | Scattered | Yes | Low |
| `src/pages/CustomerRequestDetail.tsx` | `/api/customer/workflow/{customer_id}?request_id=` | GET | Customer gamification | Scattered | Yes | Medium |
| `src/pages/VerifyEmail.tsx` | `/api/customer/verify-email?token=` | GET | Customer gamification | Scattered | Yes | Medium |
| `src/pages/PublicTracking.tsx` | `/api/public/track/{identifier}` | GET | Public tracking | Scattered | Yes | Low |

No direct API calls were found under `src/hooks/*`. The hooks currently inspected are UI/state helpers rather than backend access points.

## 3. API Client Structure

The main frontend API client is `src/lib/api.ts`. It provides:

- `API_BASE_URL` normalization from `env.API_URL`.
- `request<T>()` for JSON requests.
- automatic `Authorization: Bearer <expert_token>` header when `localStorage.expert_token` exists.
- JSON error parsing using `message` first, then `error`, then a status fallback.
- typed helper functions for shipment request, expert console, CRM, user management, referral rules, site settings, and location lookups.

The main gaps are:

- Direct `fetch()` remains in several pages and one auth component.
- Auth token reads and `Authorization` header construction are duplicated in `AdminPanel.tsx` and `UserManagement.tsx`.
- `ExpertLogin.tsx` owns login response parsing and token storage directly.
- Customer public pages compose URLs directly instead of using shared helpers.
- Multipart upload is implemented as a special direct `fetch()` inside `src/lib/api.ts`, which is acceptable because it needs browser-managed `FormData` headers.

## 4. OpenAPI Alignment

| Endpoint | Frontend usage | OpenAPI status | Mismatch if any | Action needed |
| --- | --- | --- | --- | --- |
| `/api/public/track/{identifier}` | Direct `fetch` in `PublicTracking.tsx` | Documented | Usage is scattered but contract exists | Good first client extraction candidate |
| `/api/customer/profile/{customer_id}` | Direct `fetch` in `CustomerDashboard.tsx` | Documented | Usage is scattered | Add client helper in a later customer slice |
| `/api/customer/workflow/{customer_id}` | Direct `fetch` in `CustomerRequestDetail.tsx` | Documented | Query param is hand-built | Add client helper after public tracking |
| `/api/customer/verify-email` | Direct `fetch` in `VerifyEmail.tsx` | Documented | Direct response handling | Add client helper only after preserving redirect/error UX assumptions |
| `/api/admin/dashboard` | Direct `fetch` in `AdminPanel.tsx` | Documented | Auth and 401 cleanup are page-local | Add admin client helper after auth handling decision |
| `/api/user-management/users*` | Direct `fetch` in `UserManagement.tsx`, helpers also exist in `api.ts` | Documented | Duplicate implementations | Consolidate carefully after tests/manual QA |
| `/api/user-management/transport-methods` | Direct `fetch` in `UserManagement.tsx`, helper exists | Documented | Duplicate implementations | Fold into existing helper in user-management slice |
| `/api/user-management/assignment-rules` | Direct `fetch` in `UserManagement.tsx`, helper exists | Documented | Duplicate implementations | Fold into existing helper in user-management slice |
| `/api/user-management/assignment-statistics` | Direct `fetch` in `UserManagement.tsx`, helper exists | Documented | Duplicate implementations | Fold into existing helper in user-management slice |
| `/api/expert/auth/login` | Direct `fetch` in `ExpertLogin.tsx` | Documented | Auth side effects are component-owned | Consider auth client only after token lifecycle plan |
| `/api/expert/requests/{id}/status` | Centralized helper in `api.ts` | Missing | Frontend uses endpoint not in OpenAPI | Add OpenAPI coverage before generated clients |
| `/api/expert/dashboard/kpis` | Centralized helper in `api.ts` | Missing | Frontend uses endpoint not in OpenAPI | Add OpenAPI coverage |
| `/api/expert/requests/{id}/mark-read` | Centralized helper in `api.ts` | Missing | Frontend uses endpoint not in OpenAPI | Add OpenAPI coverage |
| `/api/expert/experts` | Centralized helper in `api.ts` | Missing | Frontend uses endpoint not in OpenAPI | Add OpenAPI coverage |
| `/api/provinces`, `/api/counties`, `/api/cities` | Centralized helpers in `api.ts` | Missing | Core shipment form dependencies are undocumented | Add OpenAPI coverage |
| `/api/countries`, `/api/international-cities` | Centralized helpers in `api.ts` | Missing | Core international shipment dependencies are undocumented | Add OpenAPI coverage |
| `/api/iran-ports`, `/api/port-province-mappings`, `/api/recommended-ports` | Centralized helpers in `api.ts` | Missing | Port recommendation dependencies are undocumented | Add OpenAPI coverage |
| `/api/health` | Direct `fetch` in `App.tsx` | Missing | App status check is undocumented | Decide whether to document as internal health endpoint |
| `/api/crm/customers/{customer_id}` | Helper appears as `/crm/customers/{id}` | Documented as `/api/crm/customers/{customer_id}` | Frontend helper likely omits `/api` prefix | Verify usage and fix in a future CRM slice if used |
| `/api/customer/register` | Not found in frontend API usage scan | Documented | Documented but currently not obviously consumed | Keep documented; verify frontend flow later |
| `/api/customer/complete-step` | Not found in frontend API usage scan | Documented | Documented but currently not obviously consumed | Keep documented; verify workflow UI later |
| `/api/admin/reports/assignment-summary` | Not found in frontend API usage scan | Documented | Backend contract exists but no current UI usage found | No frontend refactor needed yet |
| `/api/admin/shipment-requests*` | Not found in frontend API usage scan | Documented | Backend contract exists but no current UI usage found | No frontend refactor needed yet |

## 5. Refactor Candidates

| Candidate | Why it is attractive | Risk | Notes |
| --- | --- | --- | --- |
| Public tracking API client | Public, read-only, one endpoint, OpenAPI-documented, no auth | Low | Best first slice |
| Customer profile/workflow read client | Public, read-only, OpenAPI-documented | Low to medium | Good after public tracking; workflow query handling needs care |
| Site settings API client cleanup | Already mostly centralized | Low to medium | Upload should stay special-case unless wrapped carefully |
| User management page consolidation | Helpers already exist but page uses direct fetch | High | Admin-only write/delete flows and broad UI state make it risky |
| Admin dashboard client | Single read endpoint but auth behavior is page-local | Medium | Needs consistent 401 handling decision |
| Expert auth client | Important duplication removal | Medium | Token storage and role navigation must stay exact |
| Expert console client completion | Mostly centralized | Medium | First document missing OpenAPI endpoints |
| CRM client audit | Mostly centralized | Medium to high | Potential `/crm/customers/{id}` vs `/api/crm/customers/{id}` mismatch needs focused verification |

## 6. Recommended Phase 6D

Recommended next phase: **Phase 6D: Public Tracking API Client Refactor**.

This is the smallest safe slice because it touches one public read-only endpoint, has no auth header behavior, has no mutation side effects, is already documented in OpenAPI, and is isolated in `src/pages/PublicTracking.tsx`.

Suggested scope for Phase 6D:

- Add a typed `fetchPublicTracking(identifier)` helper to `src/lib/api.ts`.
- Replace only the direct `fetch()` in `src/pages/PublicTracking.tsx`.
- Preserve current loading, 404, toast, and response shape behavior.
- Do not change UI layout or backend behavior.
- Run lint, build, check:structure, pytest, and `git diff --check`.

## 7. Risks

- Response shape drift between OpenAPI examples and frontend assumptions, especially for nested workflow, quote, route, and expert fields.
- Duplicate raw API path strings make later backend path changes hard to audit.
- Auth handling is inconsistent between `request<T>()`, `AdminPanel.tsx`, `UserManagement.tsx`, and `ExpertLogin.tsx`.
- Error handling differs between shared client throws and page-local status checks.
- Some frontend-used endpoints are not yet documented in OpenAPI, especially location and expert console helper endpoints.
- A generated client should not be introduced until the OpenAPI gaps are closed and response contracts are stronger.
- The CRM detail/update helpers may have a missing `/api` prefix and need focused verification before any CRM refactor.

## 8. Deferred Items

- Generated API client.
- Full frontend feature refactor.
- UI redesign.
- Backend contract changes.
- OpenAPI completion for location, expert status/KPI/read marker, health, and expert list endpoints.
- Central auth/session module.
- Warning cleanup.

## Verification

Commands run for this phase:

| Command | Result |
| --- | --- |
| `npm.cmd run lint` | Passed; existing warnings remain for Fast Refresh and React hook dependencies |
| `npm.cmd run build` | Passed; existing Browserslist and chunk-size warnings remain |
| `npm.cmd run check:structure` | Passed |
| `python -m pytest -q` | Passed: 86 passed, 724 warnings |
| `git diff --check` | Passed; existing CRLF warnings were reported for previously modified backend/test files |
