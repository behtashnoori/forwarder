# Phase 5D: Transport Methods Service Extraction

## 1. Scope

Phase 5D was limited to a small service-layer extraction for transport method logic in `backend/routes/user_management.py`.

Only these endpoints were in scope:

- `GET /api/user-management/transport-methods`
- `POST /api/user-management/transport-methods`

No runtime behavior change, API contract change, auth/security change, migration, schema/model change, frontend change, dependency change, assignment rule change, user CRUD change, assignment statistics change, manual assignment change, or delete cleanup refactor was made.

## 2. Before

Before this refactor, transport method logic lived directly in `backend/routes/user_management.py`.

The route handlers directly performed:

- active transport method query filtering;
- ordering by `TransportMethod.name_fa`;
- response item payload construction;
- transport method creation with current defaults;
- `db.session.commit()` on successful create;
- `db.session.rollback()` in the route error handler.

Endpoints reviewed:

- `GET /api/user-management/transport-methods`
- `POST /api/user-management/transport-methods`

Checks before change:

- `python -m pytest -q`: `74 passed`
- `python -m pytest backend/tests/test_user_management_contract.py -q`: `5 passed`
- `npm run lint`: passed with 17 existing warnings and 0 errors
- `npm run build`: passed with existing Browserslist/chunk warnings
- `npm run check:structure`: passed
- `git diff --check`: passed

## 3. Characterization Tests

Phase 5B already covered transport method list response shape and active-only ordering in `backend/tests/test_user_management_contract.py`.

Phase 5D extended that test to cover:

- current invalid empty create payload behavior returning 500;
- current create success status code and response shape;
- persistence of `name`, `name_fa`, `description`, and `is_active`;
- current commit behavior for successful creation.

These checks were added because `POST /transport-methods` had not yet been specifically characterized before moving creation logic into a service.

## 4. Service Design

| service file | function | previous location | responsibility | behavior impact |
| --- | --- | --- | --- | --- |
| `backend/services/transport_method_service.py` | `normalize_transport_method_payload(payload)` | Route local `data` variable | Centralize payload handoff without changing current `None`/invalid payload semantics. | None; preserves current failure behavior. |
| `backend/services/transport_method_service.py` | `build_transport_method_payload(method)` | `get_transport_methods` | Build the current transport method response item shape. | None. |
| `backend/services/transport_method_service.py` | `list_transport_methods()` | `get_transport_methods` | Query active methods ordered by `name_fa` and return payload list. | None. |
| `backend/services/transport_method_service.py` | `create_transport_method(payload)` | `create_transport_method` | Create method with current defaults and commit on success. | None. |

## 5. Changes Made

| file | change summary | reason | API behavior impact | risk |
| --- | --- | --- | --- | --- |
| `backend/services/transport_method_service.py` | Added small transport method service functions for list/build/create/payload handoff. | Move transport method data and payload logic out of route handlers. | None intended; characterization tests pass. | Low |
| `backend/routes/user_management.py` | Replaced inline transport method query/build/create logic with service calls while preserving decorators and route error handlers. | Keep route focused on request/response flow. | None intended; URLs, methods, status codes, payloads, and rollback handlers remain unchanged. | Low |
| `backend/tests/test_user_management_contract.py` | Extended transport method characterization to include create success and invalid empty payload behavior. | Lock create contract before and after extraction. | None | Low |
| `docs/phase-5d-transport-method-service-extraction.md` | Added Phase 5D extraction report. | Document scope, contract preservation, checks, and deferred work. | None | Low |

## 6. Endpoint Contract Preservation

| endpoint | method | auth/role preserved? | response shape preserved? | status code preserved? | error behavior preserved? | ordering preserved? | commit/rollback behavior preserved? | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `/api/user-management/transport-methods` | GET | Yes, `@require_role("admin")` unchanged. | Yes, `{ "transport_methods": [...] }` unchanged. | Yes. | Yes, route still catches exceptions and returns current 500 payload. | Yes, active methods ordered by `name_fa`. | Read-only; no commit/rollback. | Payload construction moved to service. |
| `/api/user-management/transport-methods` | POST | Yes, `@require_role("admin")` unchanged. | Yes, `{ "message", "transport_method_id" }` unchanged. | Yes, success remains 201. | Yes, route still rolls back and returns current 500 payload on exception. | N/A | Yes, service commits on success; route rollback on exception remains. | Current lack of explicit validation is preserved. |

## 7. After

Post-change checks:

- `python -m pytest -q`: `74 passed`
- `python -m pytest backend/tests/test_user_management_contract.py -q`: `5 passed`
- `npm run lint`: passed with 17 existing warnings and 0 errors
- `npm run build`: passed with existing Browserslist/chunk warnings
- `npm run check:structure`: passed
- `git diff --check`: passed

## 8. Deferred Items

- User CRUD service extraction.
- Delete/reassignment cleanup extraction.
- Manual assignment fix.
- Assignment statistics extraction.
- Repository layer.
- Frontend refactor.
- OpenAPI documentation.
- Deployment pipeline.
