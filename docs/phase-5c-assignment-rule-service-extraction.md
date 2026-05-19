# Phase 5C: Assignment Rules Service Extraction

## 1. Scope

Phase 5C was limited to a small service-layer extraction for assignment rule logic in `backend/routes/user_management.py`.

Only these user-management assignment rule endpoints were in scope:

- `GET /api/user-management/assignment-rules`
- `POST /api/user-management/assignment-rules`
- `PUT /api/user-management/assignment-rules/<rule_id>`

No runtime behavior change, API contract change, auth/security change, migration, schema/model change, frontend change, dependency change, or broad `user_management.py` refactor was made. No `DELETE` assignment rule endpoint was added.

## 2. Before

Before this refactor, assignment rule list/create/update logic lived directly in `backend/routes/user_management.py`.

The route handlers directly performed:

- assignment rule query ordering by `priority` descending, then `name`;
- response item payload construction;
- JSON `conditions` parsing for list responses;
- JSON `conditions` serialization for create/update;
- assignment rule lookup by id;
- assignment rule creation and update;
- `db.session.commit()` on success;
- `db.session.rollback()` in route error handlers.

Endpoints reviewed:

- `GET /api/user-management/assignment-rules`
- `POST /api/user-management/assignment-rules`
- `PUT /api/user-management/assignment-rules/<rule_id>`
- current missing `DELETE /api/user-management/assignment-rules/<rule_id>` behavior, which remains 405.

Checks before change:

- `python -m pytest -q`: `74 passed`
- `python -m pytest backend/tests/test_user_management_contract.py -q`: `5 passed`
- `npm run lint`: passed with 17 existing warnings and 0 errors
- `npm run build`: passed with existing Browserslist/chunk warnings
- `npm run check:structure`: passed
- `git diff --check`: passed

## 3. Characterization Tests

No new tests were required in Phase 5C because Phase 5B already added targeted assignment rule characterization in `backend/tests/test_user_management_contract.py`.

Existing coverage used for this extraction:

- assignment rule list response shape;
- list ordering by priority descending and then name;
- parsed JSON `conditions` in list payload;
- `created_by` nested response payload;
- create status code and response shape;
- create persistence and creator id behavior;
- update not-found behavior;
- update response shape and persistence;
- serialized JSON `conditions` update behavior;
- current missing `DELETE` route behavior returning 405.

These tests are necessary because the service extraction moves the riskiest contract details: ordering, payload construction, JSON parsing/serialization, and commit behavior.

## 4. Service Design

| service file | function | previous location | responsibility | behavior impact |
| --- | --- | --- | --- | --- |
| `backend/services/assignment_rule_service.py` | `parse_conditions(value)` | `get_assignment_rules` | Parse stored JSON conditions with `json.loads`. | None; same parser behavior. |
| `backend/services/assignment_rule_service.py` | `serialize_conditions(value)` | `create_assignment_rule`, `update_assignment_rule` | Serialize request conditions with existing `{}` default when value is `None`. | None; same storage behavior. |
| `backend/services/assignment_rule_service.py` | `normalize_assignment_rule_payload(payload)` | Route local `data` variable | Centralize payload handoff without changing `None` semantics. | None; preserves current failure behavior for invalid/no JSON body. |
| `backend/services/assignment_rule_service.py` | `build_assignment_rule_payload(rule)` | `get_assignment_rules` | Build the current assignment rule item response shape. | None. |
| `backend/services/assignment_rule_service.py` | `list_assignment_rules()` | `get_assignment_rules` | Query rules with current order and return payload list. | None. |
| `backend/services/assignment_rule_service.py` | `get_assignment_rule_or_none(rule_id)` | `update_assignment_rule` | Lookup rule by id. | None; preserves legacy lookup behavior. |
| `backend/services/assignment_rule_service.py` | `create_assignment_rule(payload, created_by_user_id)` | `create_assignment_rule` | Create rule, serialize conditions, apply current defaults, commit. | None. |
| `backend/services/assignment_rule_service.py` | `update_assignment_rule(rule_id, payload)` | `update_assignment_rule` | Update scalar fields, serialize conditions when present, set `updated_at`, commit. | None. |

## 5. Changes Made

| file | change summary | reason | API behavior impact | risk |
| --- | --- | --- | --- | --- |
| `backend/services/assignment_rule_service.py` | Added small assignment rule service functions for list/build/create/update/lookup/conditions handling. | Move assignment rule business/data logic out of route handlers. | None intended; characterization tests pass. | Low-medium |
| `backend/routes/user_management.py` | Replaced inline assignment rule query/build/create/update logic with service calls while preserving decorators and route error handlers. | Keep route focused on request/response flow. | None intended; URLs, methods, status codes, payloads, and rollback handlers remain unchanged. | Low |
| `docs/phase-5c-assignment-rule-service-extraction.md` | Added Phase 5C extraction report. | Document scope, contract preservation, checks, and deferred work. | None | Low |

## 6. Endpoint Contract Preservation

| endpoint | method | auth/role preserved? | response shape preserved? | status code preserved? | error behavior preserved? | conditions behavior preserved? | ordering preserved? | commit/rollback behavior preserved? | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `/api/user-management/assignment-rules` | GET | Yes, `@require_role("admin")` unchanged. | Yes, `{ "assignment_rules": [...] }` unchanged. | Yes. | Yes, route still catches exceptions and returns current 500 payload. | Yes, stored JSON is parsed with `json.loads`. | Yes, priority descending then name. | Read-only; no commit/rollback. | Payload construction moved to service. |
| `/api/user-management/assignment-rules` | POST | Yes, `@require_role("admin")` unchanged. | Yes, `{ "message", "rule_id" }` unchanged. | Yes, success remains 201. | Yes, route still rolls back and returns current 500 payload on exception. | Yes, request `conditions` are serialized to JSON with existing `{}` default. | N/A | Yes, service commits on success; route rollback on exception remains. | `created_by` still comes from current user id. |
| `/api/user-management/assignment-rules/<rule_id>` | PUT | Yes, `@require_role("admin")` unchanged. | Yes, `{ "message" }` unchanged. | Yes, success remains 200 and not-found remains 404. | Yes, route still rolls back and returns current 500 payload on exception. | Yes, conditions are serialized only when present. | N/A | Yes, service commits on success; route rollback on exception remains. | Not-found lookup still occurs before JSON body processing. |
| `/api/user-management/assignment-rules/<rule_id>` | DELETE | N/A; no route added. | Yes, current Flask JSON 405 behavior preserved. | Yes, remains 405. | Yes. | N/A | N/A | N/A | Explicitly out of scope. |

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
- Transport methods extraction.
- Repository layer.
- Frontend refactor.
- OpenAPI documentation.
- Deployment pipeline.
