# Phase 5B: User Management Characterization

## 1. Scope

Phase 5B was limited to characterization and documentation for `backend/routes/user_management.py`.

No runtime refactor, service extraction, API behavior change, schema/model change, migration, frontend change, dependency change, or business workflow fix was made. The only code added is a dedicated characterization test module that locks current behavior before any later Phase 5C service extraction.

## 2. Route Inventory

| endpoint | method | auth/role | responsibility | read/write/delete | direct DB access | side effects | risk level |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `/api/user-management/transport-methods` | GET | `require_role("admin")` | List active transport methods ordered by `name_fa`. | Read | Yes: `TransportMethod` query | None | Low |
| `/api/user-management/transport-methods` | POST | `require_role("admin")` | Create a transport method. | Write | Yes: `db.session.add/commit` | Inserts `TransportMethod`; rollback on error | Medium |
| `/api/user-management/users` | GET | `require_role("admin")` | List all users with manager, specialization, subordinate count, and workload data. | Read | Yes: `ExpertUser` query plus relationships | None | Medium |
| `/api/user-management/users` | POST | `require_role("admin")` | Create user, hash password, normalize optional email/phone/department, add specializations. | Write | Yes: `ExpertUser`, `ExpertSpecialization`, `flush/commit` | Inserts user and specialization rows; rollback on exception | High |
| `/api/user-management/users/<user_id>` | PUT | `require_role("admin")` | Update username/password/profile/role/manager/specializations. | Write | Yes: `ExpertUser`, `ExpertSpecialization`, `delete/commit` | Replaces specialization rows when provided; rollback on exception | High |
| `/api/user-management/users/<user_id>` | DELETE | `require_role("admin")` | Delete non-admin user and clean or reassign related records. | Delete | Yes: multiple direct `db.session.query(...).delete/update`, `flush/commit` | Unsets subordinates, deletes console/activity/task/report/specialization/assignment log rows, reassigns `AssignmentRule.created_by`, unassigns shipments/opportunities | High |
| `/api/user-management/assignment-rules` | GET | `require_role("admin")` | List assignment rules ordered by priority descending, then name. | Read | Yes: `AssignmentRule` query | None | Medium |
| `/api/user-management/assignment-rules` | POST | `require_role("admin")` | Create assignment rule using current user as creator. | Write | Yes: `AssignmentRule`, `db.session.add/commit` | Inserts rule; rollback on exception | Medium |
| `/api/user-management/assignment-rules/<rule_id>` | PUT | `require_role("admin")` | Update assignment rule fields and JSON conditions. | Write | Yes: `AssignmentRule`, `db.session.commit` | Updates `updated_at`; rollback on exception | Medium |
| `/api/user-management/assignment-rules/<rule_id>` | DELETE | Not registered | No delete route exists for assignment rules in this blueprint. | N/A | N/A | Flask returns current 405 JSON error handler payload | Low |
| `/api/user-management/assignment-statistics` | GET | `require_role("admin")` | Return assignment statistics from `assignment_engine.get_assignment_statistics()`. | Read | Indirect via assignment engine | None | Medium |
| `/api/user-management/manual-assignment` | POST | `require_role("admin")` | Preserve current manual-assignment failure path. | Write intent, currently fails | Calls `assignment_service.preserve_manual_assignment_failure()` then rollback on exception | Currently returns 500 and does not assign or create `AssignmentLog` | High |
| `/api/user-management/ping` | GET | Public | Health check for user management blueprint. | Read | No | None | Low |

## 3. Current Behavior Map

### User CRUD

- List users is admin-only and returns `{ "users": [...] }` ordered by `ExpertUser.full_name`.
- Each user item includes identity fields, role, department, activity flags, manager summary, subordinate count, specialization payloads, and computed workload.
- Create user validates required `username`, `password`, `full_name`, and `role`; duplicate username returns 400; duplicate email integrity errors return 409.
- Create user hashes the password, normalizes optional email/phone/department, flushes the user, inserts provided specializations, then commits.
- Update user supports username uniqueness checks, optional password change, basic fields, role, manager, and full replacement of specializations.
- Delete user blocks self-delete, missing users, and deleting admin users. Non-admin deletion performs broad cleanup before deleting the user.

### Assignment Rules

- List returns `{ "assignment_rules": [...] }` ordered by priority descending, then name.
- Rule `conditions` are stored as JSON text and returned as parsed JSON objects.
- Create uses the authenticated admin id as `created_by`.
- Update modifies direct scalar fields and JSON `conditions`, sets `updated_at`, and commits.
- No assignment-rule delete route is currently registered under `user_management`; `DELETE /api/user-management/assignment-rules/<id>` returns 405 through the global JSON error handler.

### Assignment Stats

- Statistics are returned directly from `assignment_engine.get_assignment_statistics()`.
- Current shape is `{ "total_assignments", "automatic_assignments", "manual_assignments", "expert_workloads" }`.
- `expert_workloads` includes all active users from the engine query, including admins.

### Manual Assignment

- `POST /api/user-management/manual-assignment` currently calls `assignment_service.preserve_manual_assignment_failure()`.
- The route catches the raised exception, rolls back, and returns 500 with `{ "error": "خطا در ارجاع دستی" }`.
- Current characterization confirms this failure has no assignment side effects and creates no `AssignmentLog`.

### Delete/Reassignment Cleanup

- Deleting a non-admin user:
  - unsets subordinate `manager_id`;
  - deletes `ExpertConsoleNotification`, `ExpertConsoleMessage`, `ExpertConsoleLog`, `AssignmentLog`, `ExpertSpecialization`, `Activity`, `Task`, and `Report` records tied to the user;
  - reassigns `AssignmentRule.created_by` to the current admin;
  - unassigns matching `ShipmentRequest.assigned_to` and `Opportunity.assigned_to`;
  - deletes the `ExpertUser` and commits.

## 4. Characterization Tests Added

| test file | test name | behavior locked | endpoint covered |
| --- | --- | --- | --- |
| `backend/tests/test_user_management_contract.py` | `test_admin_auth_role_requirements_and_read_shapes` | 401 missing token, 403 non-admin payload, user list order/shape, specialization/workload shape, active transport method list shape/order, public ping payload | `GET /users`, `GET /transport-methods`, `GET /ping` |
| `backend/tests/test_user_management_contract.py` | `test_user_create_update_not_found_and_persistence_contracts` | Create validation, duplicate username behavior, create status/payload, normalization and specialization commit, update not-found, update payload and persistence | `POST /users`, `PUT /users/<id>` |
| `backend/tests/test_user_management_contract.py` | `test_user_delete_cleanup_and_reassignment_contract` | Delete self guard, delete missing user, non-admin delete payload, subordinate cleanup, shipment unassignment, assignment rule creator reassignment, related-row cleanup | `DELETE /users/<id>` |
| `backend/tests/test_user_management_contract.py` | `test_assignment_rule_crud_and_no_delete_endpoint_contract` | Assignment rule list order/shape, create payload, update not-found, update payload/persistence, current missing DELETE route 405 payload | `GET /assignment-rules`, `POST /assignment-rules`, `PUT /assignment-rules/<id>`, `DELETE /assignment-rules/<id>` |
| `backend/tests/test_user_management_contract.py` | `test_assignment_statistics_and_manual_assignment_failure_contract` | Assignment statistics shape/workload semantics, manual-assignment current 500 payload, rollback/no side effects | `GET /assignment-statistics`, `POST /manual-assignment` |

## 5. Risk Notes

- `user_management.py` still contains broad direct DB writes and multi-model cleanup logic inside route handlers.
- Delete cleanup is high risk because it updates/deletes many tables in one route and relies on operation ordering plus intermediate flushes.
- Manual assignment is intentionally characterized as current failure behavior; fixing it is out of Phase 5B scope.
- Response shapes include nested relationship and computed workload fields that frontend/admin tooling may depend on.
- Role/access behavior is centralized through `require_role("admin")`; any extraction must preserve decorators and error payloads exactly.
- Assignment statistics are read-only at the route level but coupled to `assignment_engine`, which queries active users directly.
- Assignment rule delete is not implemented in this blueprint; callers receive a 405, which is now documented and characterized.

## 6. Phase 5C Recommendation

Start Phase 5C with a small, low-risk extraction of assignment rule read/write logic into a service, before attempting user CRUD or delete cleanup.

Recommended first slice:

- `GET /api/user-management/assignment-rules`
- `POST /api/user-management/assignment-rules`
- `PUT /api/user-management/assignment-rules/<rule_id>`

Reasoning:

- The assignment rule surface is smaller than user CRUD and delete cleanup.
- It already has clear characterization coverage for list order, payload shape, create/update persistence, and current missing delete behavior.
- It avoids the broad multi-table cleanup risks in user deletion.
- It avoids changing the manual assignment failure path.

Keep auth decorators, endpoint URLs, status codes, payload shapes, JSON conditions parsing/serialization, order, commit/rollback behavior, and the current 405 delete behavior unchanged.

## 7. Deferred Items

- Actual service extraction.
- Behavior fixes.
- Manual assignment fix.
- Repository layer.
- Frontend refactor.
- OpenAPI documentation.
- Deployment pipeline.
