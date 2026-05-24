# Phase 5G: User Delete & Reassignment Cleanup Service Extraction

## 1. Scope

Phase 5G was limited to extracting the user delete cleanup flow from `backend/routes/user_management.py` into a focused service module.

Only this endpoint was in scope:

- `DELETE /api/user-management/users/<user_id>`

No user list/create/update behavior, assignment rules, transport methods, assignment statistics, manual assignment, migration, schema/model, frontend, or auth/security behavior was changed.

## 2. Before

Before this refactor, the delete route directly handled:

- reading the current authenticated user;
- self-delete guard;
- target user lookup;
- missing target behavior;
- admin target delete block;
- subordinate `manager_id` cleanup;
- notification, message, log, assignment log, specialization, activity, task, and report cleanup;
- assignment rule creator reassignment to the current admin;
- shipment request and opportunity unassignment;
- target user delete;
- three intermediate `flush()` calls and final `commit()`;
- route-level rollback and 500 error mapping.

Checks before Phase 5G changes:

- `python -m pytest -q`: `74 passed`
- `python -m pytest backend/tests/test_user_management_contract.py -q`: `5 passed`
- `npm.cmd run lint`: passed with 17 existing warnings and 0 errors
- `npm.cmd run build`: passed with existing Browserslist and chunk-size warnings
- `npm.cmd run check:structure`: passed
- `git diff --check`: passed; Git printed the existing Windows line-ending notice for `backend/routes/user_management.py` and `backend/tests/test_user_management_contract.py`

## 3. Characterization Tests

The existing user-management contract test already covered:

- self-delete guard;
- missing user behavior;
- successful delete response shape;
- subordinate manager cleanup;
- shipment request unassignment;
- assignment rule creator reassignment;
- specialization cleanup;
- assignment log cleanup;
- expert console log, message, and notification cleanup;
- activity, task, and report cleanup.

Phase 5G strengthened the same test with current behavior for:

- blocking deletion of another admin user;
- opportunity unassignment for opportunities assigned to the deleted user.

No new API behavior was introduced by the test changes.

## 4. Service Design

| service file | function | previous location | responsibility | behavior impact |
| --- | --- | --- | --- | --- |
| `backend/services/user_delete_service.py` | `delete_user_with_cleanup(user_id, current_user)` | `delete_user` route | Orchestrate guard checks, cleanup order, flushes, delete, commit, and success payload. | None. |
| `backend/services/user_delete_service.py` | `get_delete_target_user_or_none(user_id)` | `delete_user` route | Look up target user using the current legacy query behavior. | None. |
| `backend/services/user_delete_service.py` | `validate_user_delete_allowed(target_user, current_user, user_id)` | `delete_user` route | Preserve current auth, self-delete, missing user, and admin target guards. | None. |
| `backend/services/user_delete_service.py` | `cleanup_user_subordinates(target_user)` | `delete_user` route | Unset `manager_id` for direct subordinates. | None. |
| `backend/services/user_delete_service.py` | `cleanup_user_related_records(target_user)` | `delete_user` route | Delete directly related notifications, messages, logs, assignment logs, specializations, activities, tasks, and reports. | None. |
| `backend/services/user_delete_service.py` | `reassign_assignment_rules_created_by(target_user, current_user)` | `delete_user` route | Reassign `AssignmentRule.created_by` to the current admin. | None. |
| `backend/services/user_delete_service.py` | `unassign_user_shipments_and_opportunities(target_user)` | `delete_user` route | Clear `assigned_to` on shipment requests and opportunities. | None. |
| `backend/services/user_delete_service.py` | `build_delete_user_response_payload(target_user)` | `delete_user` route | Build the current success response payload. | None. |

## 5. Changes Made

| file | change summary | reason | API behavior impact | risk |
| --- | --- | --- | --- | --- |
| `backend/services/user_delete_service.py` | Added delete guard, cleanup, reassignment, unassignment, and commit orchestration helpers. | Move delete cleanup logic out of the route without changing behavior. | None intended; contract tests pass. | Medium |
| `backend/routes/user_management.py` | Replaced inline delete cleanup logic with a service call and mapped service exceptions to existing responses. | Keep route focused on current user lookup, service call, response, and existing rollback handling. | None intended. | Medium |
| `backend/tests/test_user_management_contract.py` | Added admin delete block and opportunity unassignment characterization. | Lock explicitly required delete cleanup behavior. | None. | Low |
| `docs/phase-5g-user-delete-cleanup-service-extraction.md` | Added Phase 5G extraction report. | Document scope, cleanup preservation, checks, and deferred work. | None. | Low |

## 6. Endpoint Contract Preservation

| endpoint | method | auth/role preserved? | response shape preserved? | status codes preserved? | error payloads preserved? | commit/rollback behavior preserved? |
| --- | --- | --- | --- | --- | --- | --- |
| `/api/user-management/users/<user_id>` | DELETE | Yes, `@require_role("admin")` unchanged. | Yes, success remains `{ "message": ... }`. | Yes. | Yes, auth, self-delete, missing user, admin delete block, SQLAlchemy, and generic errors keep current payloads. | Yes, service keeps the same flush and commit order; route keeps rollback on SQLAlchemy and generic exceptions. |

## 7. Cleanup Behavior Preservation

The service preserves the existing cleanup order:

1. Unset `manager_id` for subordinates of the deleted user.
2. Delete expert-specific notifications, messages, logs, assignment logs, specializations, activities, tasks, and reports.
3. `flush()`.
4. Reassign `AssignmentRule.created_by` from deleted user to current admin.
5. `flush()`.
6. Clear `ShipmentRequest.assigned_to` and `Opportunity.assigned_to`.
7. `flush()`.
8. Delete the target user.
9. `commit()`.

## 8. After

Post-change checks:

- `python -m pytest -q`: `74 passed`
- `python -m pytest backend/tests/test_user_management_contract.py -q`: `5 passed`
- `npm.cmd run lint`: passed with 17 existing warnings and 0 errors
- `npm.cmd run build`: passed with existing Browserslist and chunk-size warnings
- `npm.cmd run check:structure`: passed
- `git diff --check`: passed; Git printed the existing Windows line-ending notice for `backend/routes/user_management.py` and `backend/tests/test_user_management_contract.py`

## 9. Deferred Items

- Manual assignment fix.
- Repository layer.
- OpenAPI documentation.
- Frontend refactor.
- Deployment pipeline.
