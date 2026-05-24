# Phase 5E: Assignment Statistics Service Extraction

## 1. Scope

Phase 5E was limited to extracting assignment statistics response logic from `backend/routes/user_management.py` into a small service module.

Only this endpoint was in scope:

- `GET /api/user-management/assignment-statistics`

No API behavior change, auth/security change, migration, schema/model change, frontend change, assignment rule change, transport method change, user CRUD change, manual assignment change, or delete cleanup refactor was made.

## 2. Before

Before this refactor, the route handler directly imported `assignment_engine`, called `assignment_engine.get_assignment_statistics()`, and returned that payload with `jsonify`.

The route handler owned:

- fetching raw statistics from the current assignment engine;
- returning the current response payload unchanged;
- preserving the existing route-level error handling.

Checks before change:

- `python -m pytest -q`: `74 passed`
- `python -m pytest backend/tests/test_user_management_contract.py -q`: `5 passed`
- `npm.cmd run lint`: passed with 17 existing warnings and 0 errors
- `npm.cmd run build`: passed with existing Browserslist and chunk-size warnings
- `npm.cmd run check:structure`: passed
- `git diff --check`: passed

Note: direct `npm run ...` in this PowerShell environment is blocked by the local execution policy for `npm.ps1`, so the npm package scripts were executed through `npm.cmd run ...`.

## 3. Characterization Tests

The existing user-management contract test already covers the assignment statistics endpoint:

- status code remains `200`;
- response keys remain `total_assignments`, `automatic_assignments`, `manual_assignments`, and `expert_workloads`;
- assignment counts remain the current values for the seeded data;
- `expert_workloads` keeps the current item shape with `expert_id`, `expert_name`, and `workload`;
- manual assignment failure behavior remains covered separately in the same test.

No new behavior was introduced by the test suite.

## 4. Service Design

| service file | function | previous location | responsibility | behavior impact |
| --- | --- | --- | --- | --- |
| `backend/services/assignment_statistics_service.py` | `get_assignment_statistics_payload()` | `get_assignment_statistics` route | Fetch raw statistics from the existing `assignment_engine`. | None. |
| `backend/services/assignment_statistics_service.py` | `build_assignment_statistics_response_payload(raw_stats)` | Route returned raw stats directly | Centralize response payload handoff while preserving the current shape. | None. |
| `backend/services/assignment_statistics_service.py` | `normalize_assignment_statistics(raw_stats)` | N/A | Explicitly preserve the current assignment engine payload without mutation. | None. |

## 5. Changes Made

| file | change summary | reason | API behavior impact | risk |
| --- | --- | --- | --- | --- |
| `backend/services/assignment_statistics_service.py` | Added small service functions for fetching and returning assignment statistics payloads. | Move statistics logic out of the route handler. | None intended; payload remains the assignment engine payload. | Low |
| `backend/routes/user_management.py` | Replaced the inline `assignment_engine` import/call with a service call. | Keep the route focused on decorators, service call, `jsonify`, and error handling. | None intended; decorators, status codes, and error payload remain unchanged. | Low |
| `docs/phase-5e-assignment-statistics-service-extraction.md` | Added Phase 5E extraction report. | Document scope, contract preservation, checks, and deferred work. | None | Low |

## 6. Endpoint Contract Preservation

| endpoint | method | auth/role preserved? | response shape preserved? | status code preserved? | error behavior preserved? | expert_workloads preserved? | commit/rollback behavior preserved? | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `/api/user-management/assignment-statistics` | GET | Yes, `@require_role("admin")` unchanged. | Yes, the existing assignment engine payload is returned unchanged. | Yes. | Yes, route still catches exceptions and returns the current 500 payload. | Yes, shape and source remain the current assignment engine behavior. | Yes; endpoint is read-only and had no commit/rollback. | Route now delegates statistics payload retrieval to service. |

## 7. After

Post-change checks:

- `python -m pytest -q`: `74 passed`
- `python -m pytest backend/tests/test_user_management_contract.py -q`: `5 passed`
- `npm.cmd run lint`: passed with 17 existing warnings and 0 errors
- `npm.cmd run build`: passed with existing Browserslist and chunk-size warnings
- `npm.cmd run check:structure`: passed
- `git diff --check`: passed; Git printed the existing Windows line-ending notice for `backend/routes/user_management.py`

## 8. Deferred Items

- User CRUD service extraction.
- Delete/reassignment cleanup extraction.
- Manual assignment fix.
- Repository layer.
- Frontend refactor.
- OpenAPI documentation.
- Deployment pipeline.
