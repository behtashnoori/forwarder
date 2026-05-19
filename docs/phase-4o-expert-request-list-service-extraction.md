# Phase 4O: Expert Request List Service Extraction

## 1. Scope

Phase 4O performed a limited extraction of the Expert Console request list
logic from the route layer into a service module.

Only `GET /api/expert/requests` was changed. No database model, schema,
migration, frontend code, auth/role logic, request detail logic, quote logic,
message logic, notification logic, assignment logic, or referral logic was
changed.

## 2. Before

Before this phase, request list logic lived directly in
`backend/routes/expert_console.py` inside `get_shipment_requests`.

Endpoint reviewed:

- `GET /api/expert/requests`

Pre-change checks:

- `python -m pytest -q`: 68 passed
- `python -m pytest backend/tests/test_expert_assignment_referral_contract.py -q`: 8 passed
- `python -m pytest backend/tests/test_cors.py -q`: 2 passed
- `npm.cmd run lint`: passed with existing warnings, 0 errors
- `npm.cmd run build`: passed
- `npm.cmd run check:structure`: passed
- `git diff --check`: passed

## 3. Characterization Tests

Added `test_expert_request_list_filters_visibility_and_order_contract` in
`backend/tests/test_expert_assignment_referral_contract.py`.

The test locks current request list behavior for:

- auth-protected access through existing bearer-token setup
- expert visibility limited to requests assigned to that expert
- admin visibility across assigned and unassigned requests
- admin `assigned_to` filtering
- comma-separated `status` filtering across both status fields
- `priority` plus `search` filtering
- default `created_at desc` ordering
- explicit `created_at asc` ordering
- pagination shape and values
- core item payload fields such as `assigned_to`, `customer`, and `has_unread`

The test records existing behavior and does not require any new endpoint
behavior.

## 4. Service Design

| service file | function | previous location | responsibility | behavior impact |
| --- | --- | --- | --- | --- |
| `backend/services/expert_request_list_service.py` | `normalize_request_list_filters` | `get_shipment_requests` route | Preserve query parameter defaults and `per_page` cap | None |
| `backend/services/expert_request_list_service.py` | `apply_request_list_visibility` | `get_shipment_requests` route | Preserve admin vs expert request visibility and admin `assigned_to` filter | None |
| `backend/services/expert_request_list_service.py` | `apply_request_list_filters` | `get_shipment_requests` route | Preserve status, priority, search, and sort behavior | None |
| `backend/services/expert_request_list_service.py` | `build_request_list_item_payload` | `get_shipment_requests` route | Preserve per-request list item payload shape | None |
| `backend/services/expert_request_list_service.py` | `build_request_list_response_payload` | `get_shipment_requests` route | Preserve top-level `requests` and `pagination` payload | None |
| `backend/services/expert_request_list_service.py` | `list_expert_requests` | `get_shipment_requests` route | Coordinate query, pagination, and payload construction | None |

## 5. Changes Made

| file | change summary | reason | API behavior impact | risk |
| --- | --- | --- | --- | --- |
| `backend/routes/expert_console.py` | Replaced inline request list query/filter/payload logic with service calls | Keep route thin while preserving decorators and error handling | None | Low |
| `backend/services/expert_request_list_service.py` | Added extracted request list service helpers | Move list business/query logic out of route | None | Low |
| `backend/tests/test_expert_assignment_referral_contract.py` | Added request list characterization coverage | Lock list contract before and after extraction | None | Low |
| `docs/phase-4o-expert-request-list-service-extraction.md` | Added phase documentation | Record scope, design, contract, and verification | None | Low |

## 6. Endpoint Contract Preservation

| endpoint | method | auth/role preserved? | response shape preserved? | status code preserved? | error behavior preserved? | filters/pagination preserved? | side effects preserved? | commit/rollback behavior preserved? | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `/api/expert/requests` | `GET` | Yes, existing `@require_auth` and `get_current_user` handling remain in the route | Yes | Yes | Yes, route-level generic 500 handling remains unchanged | Yes | Yes, endpoint remains read-only | Yes, no commit or rollback behavior was added | Logic moved to service without API contract changes |

## 7. After

Post-change verification:

- `python -m pytest backend/tests/test_expert_assignment_referral_contract.py::test_expert_request_list_filters_visibility_and_order_contract -q`: 1 passed
- `python -m pytest backend/tests/test_expert_assignment_referral_contract.py -q`: 9 passed
- `python -m pytest backend/tests/test_cors.py -q`: 2 passed
- `python -m pytest -q`: 69 passed
- `npm.cmd run lint`: passed with existing warnings, 0 errors
- `npm.cmd run build`: passed
- `npm.cmd run check:structure`: passed
- `git diff --check`: passed

## 8. Deferred Items

- assignment rule redesign
- manual assignment behavior fix
- repository layer
- model split
- frontend refactor
- CI/CD
- OpenAPI documentation
