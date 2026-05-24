# Phase 6M: Expert Console API Client Inventory & First Refactor Plan

## 1. Scope

This phase is inventory and planning only.

No runtime code was changed. No frontend code was refactored. No backend code, API behavior, routing, styling, schema/model, auth/security, dependencies, or OpenAPI files were changed.

## 2. Expert API Usage Inventory

| Frontend file | Endpoint/path used | Method | Centralized or direct? | Auth/token behavior | Read/write | OpenAPI documented? | Risk level |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `src/components/ExpertLogin.tsx` | `/api/expert/auth/login` | POST | Direct `fetch` | No bearer token; stores returned expert/token in `localStorage` | Write/auth | Yes | High |
| `src/pages/ExpertConsole.tsx` | `/api/expert/requests` | GET | Centralized via `fetchExpertRequests` | Shared `request()` reads `expert_token` | Read | Yes | Medium |
| `src/pages/ExpertConsole.tsx` | `/api/expert/dashboard/kpis` | GET | Centralized via `fetchKPIs` | Shared `request()` reads `expert_token`; passes `expert_id` query | Read | Missing | Low |
| `src/pages/ExpertConsole.tsx` | `/api/expert/experts` | GET | Centralized via `fetchExperts` | Shared `request()` reads `expert_token` | Read | Missing | Low |
| `src/pages/ExpertConsole.tsx` | `/api/expert/requests/{id}/assign` | POST | Centralized via `assignRequest` | Shared `request()` reads `expert_token` | Write/mutation | Yes | High |
| `src/pages/ExpertConsole.tsx` | `/api/expert/requests/{id}/status` | POST | Centralized via `changeRequestStatus` | Shared `request()` reads `expert_token` | Write/mutation | Missing | High |
| `src/pages/RequestDetail.tsx` | `/api/expert/requests/{id}` | GET | Centralized via `fetchExpertRequestDetail` | Shared `request()` reads `expert_token` | Read | Yes | Medium |
| `src/pages/RequestDetail.tsx` | `/api/expert/requests/{id}/status` | POST | Centralized via `changeRequestStatus` | Shared `request()` reads `expert_token` | Write/mutation | Missing | High |
| `src/pages/RequestDetail.tsx` | `/api/expert/requests/{id}/messages` | POST | Centralized via `addMessage` | Shared `request()` reads `expert_token` | Write/mutation | Yes | High |
| `src/components/QuoteModal.tsx` | `/api/expert/requests/{id}/quote` | POST | Centralized via `submitQuote` | Shared `request()` reads `expert_token` | Write/mutation | Yes | High |
| `src/lib/api.ts` | `/api/expert/notifications` | GET | Centralized helper exists | Shared `request()` reads `expert_token`; accepts `expert_id` and `unread_only` | Read | Partially documented; frontend helper sends `expert_id`, OpenAPI lists `unread_only`/`limit` | Medium |
| `src/lib/api.ts` | `/api/expert/requests/{id}/mark-read` | POST | Centralized helper exists | Shared `request()` reads `expert_token`; passes `expert_id` query | Write/mutation | Missing | Medium |
| `src/lib/api.ts` | `/api/expert/requests/{id}/quote/latest` | GET | No active frontend helper/caller found | N/A | Read | Yes | Low |
| No active frontend file found | `/api/expert/auth/refresh` | POST | No active caller found | Token lifecycle endpoint | Write/auth | Yes | High |
| No active frontend file found | `/api/expert/auth/logout` | POST | No active caller found | Local logout currently clears storage only | Write/auth | Yes | High |

## 3. Current API Client Coverage

`src/lib/api.ts` already centralizes most active Expert Console API usage:

- `fetchExpertRequests(params)` for request list reads.
- `fetchExpertRequestDetail(requestId)` for request detail reads, including messages and latest quote fields in the detail payload.
- `submitQuote(requestId, payload)` for quote creation.
- `assignRequest(requestId, expertId)` for assignment mutation.
- `changeRequestStatus(requestId, status, note)` for status mutation.
- `addMessage(requestId, messageType, content, subject, expertId)` for message creation.
- `fetchNotifications(expertId, unreadOnly)` for notifications read, though no active page/component caller was found in this inventory.
- `fetchKPIs(expertId)` for Expert Console KPI reads.
- `markRequestAsRead(requestId, expertId)` for request read-marker mutation, though no active page/component caller was found in this inventory.
- `fetchExperts()` for expert list reads.

The shared `request()` helper attaches `Authorization: Bearer <expert_token>` from `localStorage` and parses common `message`/`error` error payloads.

## 4. Scattered Calls

Only one active expert-related direct API call was found:

| File | Direct call | Notes |
| --- | --- | --- |
| `src/components/ExpertLogin.tsx` | `fetch(`${env.API_URL}/api/expert/auth/login`, { method: "POST", ... })` | Auth-sensitive login flow stores `expert_user` and `expert_token`, shows local validation/error state, and redirects by role. |

No direct frontend calls were found for request list/detail, quote creation, messages, assignment, status update, notifications, KPIs, expert list, or mark-read. Those active Expert Console calls already use `src/lib/api.ts`.

## 5. OpenAPI Gaps

Used by frontend but missing or weakly documented in `docs/openapi/openapi.yaml`:

| Endpoint | Frontend status | OpenAPI gap |
| --- | --- | --- |
| `/api/expert/dashboard/kpis` | Used via `fetchKPIs` in `ExpertConsole.tsx` | Missing from OpenAPI |
| `/api/expert/experts` | Used via `fetchExperts` in `ExpertConsole.tsx` and `RequestDetail.tsx` | Missing from OpenAPI |
| `/api/expert/requests/{id}/status` | Used via `changeRequestStatus` | Missing from OpenAPI |
| `/api/expert/requests/{id}/mark-read` | Helper exists, no active caller found | Missing from OpenAPI |
| `/api/expert/notifications` | Helper exists, no active caller found | OpenAPI documents `unread_only`/`limit`, while the frontend helper also sends `expert_id` |

OpenAPI documents `/api/expert/auth/login`, `/api/expert/auth/refresh`, `/api/expert/auth/logout`, request list/detail, assignment, quote create, quote latest, messages, and notification mark-read.

## 6. Recommended First Refactor Slice

Recommended Phase 6N slice: `Expert Dashboard KPIs OpenAPI/Client Alignment`.

Why this is the safest next slice:

- It is read-only.
- It has an active frontend caller in `src/pages/ExpertConsole.tsx`.
- It is limited to one endpoint: `GET /api/expert/dashboard/kpis`.
- It already has a centralized helper, so Phase 6N can focus on documenting/typing alignment rather than changing UI behavior.
- It avoids auth flow changes, status mutation, quote creation, message creation, assignment, and read-marker mutation.

Phase 6N should not refactor login first. Login is the only scattered direct expert call, but it is auth-sensitive and owns token storage, role redirect behavior, loading state, and local form errors.

## 7. Risks

- Auth/token drift between direct login handling and shared `request()` behavior.
- Response shape drift because several expert helper return types are broad or locally duplicated.
- Mutation side effects in assignment, status updates, quote creation, message creation, and mark-read flows.
- Inconsistent error handling between direct login fetch and shared client errors.
- Missing OpenAPI documentation for active KPI, expert list, and status endpoints.
- Duplicated or loosely typed response shapes between `src/lib/api.ts`, `ExpertConsole.tsx`, and `RequestDetail.tsx`.

## 8. Recommended Phase 6N Prompt Summary

Phase 6N should focus only on `GET /api/expert/dashboard/kpis`.

Recommended goal:

- Keep runtime behavior unchanged.
- Do not change UI rendering.
- Review the existing `fetchKPIs(expertId)` helper and active usage in `ExpertConsole.tsx`.
- Add or update documentation/OpenAPI coverage for `/api/expert/dashboard/kpis` if the phase allows OpenAPI documentation changes.
- If code changes are allowed, keep them limited to type alignment or a tiny helper rename only if needed.
- Run lint, build, structure check, pytest, and `git diff --check`.

## 9. Deferred Items

- Generated OpenAPI client
- Full expert API refactor
- Auth flow redesign
- OpenAPI gap completion beyond the first KPI slice
- CRM API client refactor
- User management API client refactor
- Frontend warning cleanup
