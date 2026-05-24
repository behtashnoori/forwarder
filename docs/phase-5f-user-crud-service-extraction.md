# Phase 5F: User CRUD Service Extraction

## 1. Scope

Phase 5F was limited to extracting non-delete user CRUD logic from `backend/routes/user_management.py` into a service module.

Only these endpoints were in scope:

- `GET /api/user-management/users`
- `POST /api/user-management/users`
- `PUT /api/user-management/users/<user_id>`

No delete user behavior, delete/reassignment cleanup, migration, schema/model, frontend, auth/security, assignment rule, transport method, assignment statistics, or manual assignment behavior was changed.

## 2. Before

Before this refactor, the user-management route directly handled:

- querying and ordering users by `ExpertUser.full_name`;
- building the user list payload, including manager, subordinate count, specializations, and workload;
- validating required create fields;
- duplicate username checks for create and update;
- bcrypt password hashing;
- create-time optional email, phone, and department normalization;
- user creation and specialization creation;
- user update, optional password update, and specialization replacement;
- create/update commits and route-level rollback behavior.

Checks before Phase 5F changes:

- `python -m pytest -q`: `74 passed`
- `python -m pytest backend/tests/test_user_management_contract.py -q`: `5 passed`
- `npm.cmd run lint`: passed with 17 existing warnings and 0 errors
- `npm.cmd run build`: passed with existing Browserslist and chunk-size warnings
- `npm.cmd run check:structure`: passed
- `git diff --check`: passed; Git printed the existing Windows line-ending notice for `backend/routes/user_management.py`

## 3. Characterization Tests

The existing user-management contract tests already covered:

- admin-only access behavior for user reads;
- `GET /users` response shape;
- list ordering by `full_name`;
- specialization payload shape;
- workload payload values;
- create validation failures;
- duplicate username create behavior;
- create response shape and status code;
- create-time email, phone, and department normalization;
- specialization creation;
- missing user update behavior;
- update response shape and status code;
- specialization replacement behavior.

Phase 5F strengthened the same contract test with current behavior for:

- bcrypt password hash storage instead of plaintext;
- duplicate email/unique constraint behavior returning the current 409 payload.

No new API behavior was introduced by the test changes.

## 4. Service Design

| service file | function | previous location | responsibility | behavior impact |
| --- | --- | --- | --- | --- |
| `backend/services/user_service.py` | `list_users_payload()` | `get_users` route | Query users ordered by `full_name` and return current response items. | None. |
| `backend/services/user_service.py` | `build_user_payload(user)` | `get_users` route | Build the current user payload including manager, subordinate count, specializations, and workload. | None. |
| `backend/services/user_service.py` | `build_user_specialization_payload(specialization)` | `get_users` route | Build the current nested specialization payload. | None. |
| `backend/services/user_service.py` | `create_user(payload)` | `create_user` route | Validate, hash password, normalize create fields, create user and specializations, and commit. | None. |
| `backend/services/user_service.py` | `update_user(user_id, payload)` | `update_user` route | Find user, enforce duplicate username behavior, update fields/password/specializations, and commit. | None. |
| `backend/services/user_service.py` | `replace_user_specializations(user_id, specializations)` | `update_user` route | Preserve delete-then-add specialization replacement behavior. | None. |
| `backend/services/user_service.py` | `hash_password(password)` | create/update routes | Preserve bcrypt password hashing behavior. | None. |
| `backend/services/user_service.py` | `normalize_optional_create_string(value, lowercase=False)` | `create_user` route | Preserve create-time optional string normalization. | None. |

## 5. Changes Made

| file | change summary | reason | API behavior impact | risk |
| --- | --- | --- | --- | --- |
| `backend/services/user_service.py` | Added service helpers and small service exceptions for user list/create/update. | Move non-delete user CRUD logic out of route handlers. | None intended; contract tests pass. | Medium-low |
| `backend/routes/user_management.py` | Replaced inline GET/POST/PUT user logic with service calls while preserving decorators and route error handling. | Keep route focused on request, service call, response, and current error mapping. | None intended. | Medium-low |
| `backend/tests/test_user_management_contract.py` | Added password hash and duplicate email characterization checks. | Lock explicitly requested behavior before/after extraction. | None. | Low |
| `docs/phase-5f-user-crud-service-extraction.md` | Added Phase 5F extraction report. | Document scope, service design, checks, and deferred work. | None. | Low |

## 6. Endpoint Contract Preservation

| endpoint | method | auth/role preserved? | response shape preserved? | status code preserved? | error behavior preserved? | specialization/workload preserved? | commit/rollback behavior preserved? |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `/api/user-management/users` | GET | Yes, `@require_role("admin")` unchanged. | Yes, `{ "users": [...] }` unchanged. | Yes. | Yes, route still returns the current 500 payload on exception. | Yes. | Read-only; no commit/rollback. |
| `/api/user-management/users` | POST | Yes, `@require_role("admin")` unchanged. | Yes, `{ "message", "user_id" }` unchanged. | Yes, success remains 201. | Yes, validation errors remain 400, duplicate email/integrity remains 409, generic error remains 500. | Yes, specialization creation behavior is unchanged. | Yes, service commits on success and route rolls back on integrity/generic exceptions. |
| `/api/user-management/users/<user_id>` | PUT | Yes, `@require_role("admin")` unchanged. | Yes, `{ "message": ... }` unchanged. | Yes. | Yes, missing user remains 404, duplicate username remains 400, generic error remains 500. | Yes, specialization replacement behavior is unchanged. | Yes, service commits on success and route rolls back on generic exceptions. |

## 7. After

Post-change checks:

- `python -m pytest -q`: `74 passed`
- `python -m pytest backend/tests/test_user_management_contract.py -q`: `5 passed`
- `npm.cmd run lint`: passed with 17 existing warnings and 0 errors
- `npm.cmd run build`: passed with existing Browserslist and chunk-size warnings
- `npm.cmd run check:structure`: passed
- `git diff --check`: passed; Git printed the existing Windows line-ending notice for `backend/routes/user_management.py` and `backend/tests/test_user_management_contract.py`

## 8. Deferred Items

- Delete/reassignment cleanup extraction.
- Manual assignment fix.
- Repository layer.
- OpenAPI documentation.
- Frontend refactor.
- Deployment pipeline.
