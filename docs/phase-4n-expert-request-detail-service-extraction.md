# Phase 4N: Expert Request Detail Service Extraction

## 1. Scope

Phase 4N was a narrow, low-risk extraction of expert-console request detail logic from `backend/routes/expert_console.py` into `backend/services/expert_request_detail_service.py`.

In scope:

- `GET /api/expert/requests/<int:request_id>`
- Request lookup and current access checks.
- Request detail payload construction.
- Current nested customer, route, cargo, date, assignee, timeline, message, and latest quote payloads.
- Current request-detail not-found, forbidden, and generic error behavior.

Out of scope: database migrations, model/schema changes, frontend changes, auth/security changes, quote write/read endpoint logic, message creation logic, notification logic, assignment logic, referral logic, expert request list extraction, new endpoints, dependency changes, and broad route-module refactors.

## 2. Before

Before this extraction, request detail logic lived directly in `backend/routes/expert_console.py` inside:

- `get_shipment_request_detail()` for `GET /api/expert/requests/<int:request_id>`

The route directly handled:

- Loading the target `ShipmentRequest`.
- Returning `404` for missing requests.
- Calling `get_current_user()` and enforcing current access behavior: admin can access any request; non-admin can access only assigned requests.
- Loading origin/destination province/county/city rows.
- Loading the assigned expert row.
- Loading timeline logs ordered newest-first.
- Loading messages ordered newest-first.
- Loading the latest quote in a safe `try/except` block.
- Formatting all nested response payloads.
- Calculating SLA status.
- Returning the existing generic request-detail error payload on unexpected errors.

Pre-change checks were run before editing. In this workspace `python` is not on PATH and the virtualenv needs access to its base Python install, so the pytest commands were executed through `.venv\Scripts\python.exe -m pytest`:

| Check | Result |
| --- | --- |
| `python -m pytest -q` | Failed before this phase's edits with two existing CORS OPTIONS failures in `backend/tests/test_cors.py`; `66 passed`, `2 failed`. |
| `python -m pytest backend/tests/test_expert_assignment_referral_contract.py -q` | Passed: `8 passed`. |

## 3. Characterization Tests

`backend/tests/test_expert_assignment_referral_contract.py` was extended before extraction in `test_expert_request_read_contracts_and_access_errors`.

Locked behaviors:

- Unauthenticated request-detail access returns the existing `401` token payload.
- Missing request returns the existing `404` payload.
- Forbidden access for an unassigned expert returns the existing `403` payload.
- Successful response keeps the existing top-level keys.
- Assigned expert payload keeps `id`, `name`, and `username`.
- Customer payload keeps `first_name`, `last_name`, `phone`, and `full_name`.
- Route payload keeps `origin` and `destination`, each with `province`, `county`, and `city`.
- Cargo payload keeps `description`, `weight`, `volume`, `value`, and `special_instructions`.
- Dates payload keeps `pickup_date` and `delivery_date`.
- Initial seeded detail response keeps `latest_quote: null`, empty `messages`, and empty `timeline`.

The existing message characterization test continues to lock message listing shape inside request detail after a message is created.

## 4. Service Design

| Service file | Function | Previous location | Responsibility | Behavior impact |
| --- | --- | --- | --- | --- |
| `backend/services/expert_request_detail_service.py` | `get_expert_request_detail(request_id, user)` | `get_shipment_request_detail()` in `backend/routes/expert_console.py` | Load target request, enforce access, and return current detail payload. | None; same endpoint behavior. |
| `backend/services/expert_request_detail_service.py` | `get_request_detail_target_or_none(request_id)` | Inline request lookup in route | Load target `ShipmentRequest`. | None; same not-found behavior. |
| `backend/services/expert_request_detail_service.py` | `can_access_request_detail(req, user)` | `_can_access_request()` behavior in route | Preserve admin-or-assigned-expert access behavior. | None; same forbidden behavior. |
| `backend/services/expert_request_detail_service.py` | `build_request_detail_payload(req)` | Inline route response construction | Build the top-level request-detail payload. | None; same response shape. |
| `backend/services/expert_request_detail_service.py` | `build_assignment_detail_payload(req)` | Inline assigned expert formatter | Build assigned expert nested payload. | None; same keys and values. |
| `backend/services/expert_request_detail_service.py` | `build_customer_detail_payload(req)` | Inline customer formatter | Build customer nested payload. | None; same keys and fallback. |
| `backend/services/expert_request_detail_service.py` | `build_route_detail_payload(req)` | Inline location lookup/formatter | Build origin/destination nested payloads. | None; same `نامشخص` fallback behavior. |
| `backend/services/expert_request_detail_service.py` | `build_cargo_detail_payload(req)` | Inline cargo formatter | Build cargo nested payload. | None; same keys and values. |
| `backend/services/expert_request_detail_service.py` | `build_dates_detail_payload(req)` | Inline date formatter | Build pickup/delivery date payload. | None; same ISO/null behavior. |
| `backend/services/expert_request_detail_service.py` | `build_timeline_payload(request_id)` | Inline log query/formatter | Query and build timeline payload newest-first. | None; same ordering and fields. |
| `backend/services/expert_request_detail_service.py` | `build_messages_payload(request_id)` | Inline message query/formatter | Query messages newest-first and reuse current message payload helper. | None; same fields. |
| `backend/services/expert_request_detail_service.py` | `build_latest_quote_payload(request_id)` | Inline safe latest quote block | Build latest quote payload and preserve safe failure behavior. | None; same payload and silent failure behavior. |
| `backend/services/expert_request_detail_service.py` | `build_sla_status(req)` | Inline SLA calculation | Calculate current SLA status. | None; same thresholds. |
| `backend/services/expert_request_detail_service.py` | `ExpertRequestDetailServiceError` subclasses | Inline route branches | Carry current `404`/`403` error payload text and status back to thin route. | None; same status codes and errors. |

## 5. Changes Made

| File | Change summary | Reason | API behavior impact | Risk |
| --- | --- | --- | --- | --- |
| `backend/routes/expert_console.py` | Imported `expert_request_detail_service` and replaced inline request-detail logic with a service call. | Keep request detail route as a thin controller. | None intended; URL, method, decorator, status codes, payloads, and generic error behavior preserved. | Low; only one GET detail endpoint changed. |
| `backend/services/expert_request_detail_service.py` | Added request-detail lookup, access, nested payload, latest quote, message, timeline, and SLA helpers. | Move request-detail business/formatting logic to service layer without adding a repository layer. | None intended; logic mirrors previous inline behavior. | Low; no model/schema/dependency changes. |
| `backend/tests/test_expert_assignment_referral_contract.py` | Expanded request-detail characterization for unauthenticated access and important nested payload shapes. | Lock request-detail contract before extraction. | None; test only. | Low. |
| `docs/phase-4n-expert-request-detail-service-extraction.md` | Added this phase report. | Document scope, before/after checks, service design, contract preservation, and deferred work. | None. | Low. |

## 6. Endpoint Contract Preservation

| Endpoint | Method | Auth/role preserved? | Response shape preserved? | Status code preserved? | Error behavior preserved? | Side effects preserved? | Commit/rollback behavior preserved? | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `/api/expert/requests/<int:request_id>` | `GET` | Yes; existing `@require_auth` retained. | Yes; top-level and nested detail payloads preserved. | Yes; `200`, `401`, `403`, `404`, and `500` behavior preserved. | Yes; token, missing request, forbidden, and generic detail payloads preserved. | Yes; endpoint remains read-only with no side effects. | Yes; no commit/rollback behavior added. | Latest quote safe `try/except` behavior preserved; messages and timeline remain newest-first. |

## 7. After

Post-change checks:

| Check | Result |
| --- | --- |
| `python -m pytest -q` | Failed with the same two unrelated CORS OPTIONS failures in `backend/tests/test_cors.py`; `66 passed`, `2 failed`. |
| `python -m pytest backend/tests/test_expert_assignment_referral_contract.py -q` | Passed: `8 passed`. |
| Targeted expert request detail tests | Covered by expanded `test_expert_request_read_contracts_and_access_errors` and `test_expert_message_contracts_access_creation_and_listing`; passed through the expert contract suite. |
| `npm run lint` | Passed via `npm.cmd run lint` after PowerShell blocked `npm.ps1`; existing warnings only: `0 errors`, `17 warnings`. |
| `npm run build` | Passed via `npm.cmd run build`; existing Browserslist/chunk-size warnings only. |
| `npm run check:structure` | Passed. |
| `git diff --check` | Passed; Git warned that the updated Markdown file will use CRLF when touched. |

## 8. Deferred Items

Explicitly deferred and not changed in Phase 4N:

- Expert request list extraction.
- Assignment rule redesign.
- Manual assignment behavior fix.
- Repository layer.
- Model split.
- Frontend refactor.
- CI/CD.
- OpenAPI documentation.
