# Phase 4M: Referral Service Extraction

## 1. Scope

Phase 4M was a narrow, low-risk extraction of admin referral rule logic into `backend/services/referral_service.py`.

In scope:

- `GET /api/admin/referral-rules`
- `POST /api/admin/referral-rules`
- `PUT /api/admin/referral-rules/<int:rule_id>`
- `DELETE /api/admin/referral-rules/<int:rule_id>`
- `POST /api/admin/referral-rules/preview`
- Referral rule payload construction.
- Referral rule create/update/delete validation and persistence.
- Current preview behavior through the existing `referral_engine.preview_assignment` flow.
- Current transaction behavior for referral rule write endpoints.

Reviewed but not refactored in this phase:

- Referral auto-assignment internals in `backend/referral_engine.py`; route extraction only delegates preview to the existing engine.
- Public shipment request referral auto-assignment invocation in `backend/services/shipment_service.py`; that behavior was not changed.
- Direct expert assignment and manual assignment behavior; those remain covered by Phase 4L and were not changed.

Out of scope: database migrations, model/schema changes, frontend changes, auth/security changes, direct expert assignment, quote logic, message logic, notification logic, request list/detail refactors, referral rule redesign, behavior fixes, new endpoints, dependency changes, and broad route-module refactors.

## 2. Before

Before this extraction, referral admin route logic lived directly in `backend/routes/admin_panel.py` inside:

- `get_referral_rules()` for `GET /api/admin/referral-rules`
- `create_referral_rule()` for `POST /api/admin/referral-rules`
- `update_referral_rule()` for `PUT /api/admin/referral-rules/<int:rule_id>`
- `delete_referral_rule()` for `DELETE /api/admin/referral-rules/<int:rule_id>`
- `preview_referral_rule()` for `POST /api/admin/referral-rules/preview`

The route module directly handled:

- Referral rule query ordering by `priority ASC, name`.
- Safe JSON decoding of `conditions` and `action` for list payloads.
- Derived fields such as `action_type`, `pool_expert_count`, and `strategy`.
- Create validation for name, action type, direct expert, pool experts, and pool strategy.
- Create persistence and commit.
- Update rule lookup, field patching, action validation, `updated_at`, persistence, and commit.
- Delete rule lookup, linked state deletion, rule deletion, and commit.
- Preview request payload validation and dry-run call to `referral_engine.preview_assignment`.
- Rollback/error handling for write endpoints.

Pre-change checks were run before editing:

| Check | Result |
| --- | --- |
| `python -m pytest -q` | Passed: `67 passed` |
| `python -m pytest backend/tests/test_expert_assignment_referral_contract.py backend/tests/test_referral_engine.py -q` | Passed: `8 passed` |
| `npm run lint` | Passed with existing warnings: `0 errors`, `17 warnings` |
| `npm run build` | Passed with existing Vite/Browserslist/chunk-size warnings |
| `npm run check:structure` | Passed |
| `git diff --check` | Passed |

## 3. Characterization Tests

`backend/tests/test_expert_assignment_referral_contract.py` was extended with `test_referral_rule_crud_contracts`.

Locked behaviors:

- Creating a referral rule without a name returns the existing `400` payload.
- Creating a referral rule with an invalid action type returns the existing `400` payload.
- Creating a valid direct referral rule returns the existing `201` response shape: `message` and `rule_id`.
- Updating a referral rule with an invalid action type returns the existing `400` payload.
- Updating a referral rule returns the existing success payload.
- Deleting a missing referral rule returns the existing `404` payload.
- Deleting an existing referral rule returns the existing success payload and removes the rule.

Existing tests continue to lock referral rule list shape, referral preview missing-id behavior, referral preview response shape, and referral engine auto-assignment/log behavior.

## 4. Service Design

| Service file | Function | Previous location | Responsibility | Behavior impact |
| --- | --- | --- | --- | --- |
| `backend/services/referral_service.py` | `list_referral_rules(filters=None)` | `get_referral_rules()` in `backend/routes/admin_panel.py` | Query referral rules in current order and build list response. | None; same top-level key and ordering. |
| `backend/services/referral_service.py` | `build_referral_rule_payload(rule)` | Inline formatter in `get_referral_rules()` | Decode JSON safely and build current referral rule payload including derived fields. | None; same keys and fallback behavior. |
| `backend/services/referral_service.py` | `create_referral_rule(payload, actor)` | `create_referral_rule()` in `backend/routes/admin_panel.py` | Validate create payload, persist rule, commit, and return current `201` payload. | None; same validation/error/success behavior. |
| `backend/services/referral_service.py` | `update_referral_rule(rule_id, payload)` | `update_referral_rule()` in `backend/routes/admin_panel.py` | Lookup rule, apply allowed updates, validate action, set `updated_at`, commit, and return current payload. | None; same validation/not-found/success behavior. |
| `backend/services/referral_service.py` | `delete_referral_rule(rule_id)` | `delete_referral_rule()` in `backend/routes/admin_panel.py` | Delete linked rule state and the referral rule, commit, and return current payload. | None; same not-found/success behavior. |
| `backend/services/referral_service.py` | `preview_referral_assignment(payload)` | `preview_referral_rule()` in `backend/routes/admin_panel.py` | Validate `request_id` and delegate dry-run preview to the existing referral engine. | None; same preview behavior. |
| `backend/services/referral_service.py` | `build_referral_preview_payload(result)` | Inline return in `preview_referral_rule()` | Return the referral engine preview payload unchanged. | None; same response shape. |
| `backend/services/referral_service.py` | `run_referral_auto_assignment(payload=None, actor=None)` | Existing referral engine usage patterns | Thin wrapper around current auto-assignment behavior for future route extraction. | None; no current route behavior changed. |
| `backend/services/referral_service.py` | `build_referral_assignment_payload(result)` | N/A | Minimal helper for future route extraction. | None; helper only. |
| `backend/services/referral_service.py` | `create_referral_log_if_needed(...)` | Referral engine internals | Documents that current referral logs are created by the engine. | None; helper only. |
| `backend/services/referral_service.py` | `normalize_referral_payload(payload, require_name=False)` | Inline create validation in `create_referral_rule()` | Preserve current create validation/defaults. | None; same error messages. |
| `backend/services/referral_service.py` | `ReferralServiceError` and subclasses | Inline route branches | Carry current error payload text and HTTP status back to thin routes. | None; same status codes and error payloads. |

## 5. Changes Made

| File | Change summary | Reason | API behavior impact | Risk |
| --- | --- | --- | --- | --- |
| `backend/routes/admin_panel.py` | Imported `referral_service` and replaced inline referral rule list/create/update/delete/preview logic with service calls. | Keep referral admin routes as thin controllers. | None intended; URL, methods, decorators, status codes, payloads, and rollback behavior preserved. | Low; only referral endpoints changed. |
| `backend/services/referral_service.py` | Added referral rule list/payload/create/update/delete/preview helpers plus validation and error classes. | Move referral business logic to the service layer without adding a repository layer. | None intended; logic mirrors previous inline behavior and delegates preview to existing engine. | Low; no model/schema/dependency changes. |
| `backend/tests/test_expert_assignment_referral_contract.py` | Added referral CRUD characterization for validation, create/update/delete responses, and persistence. | Lock behavior around extracted referral endpoints. | None; test only. | Low. |
| `docs/phase-4m-referral-service-extraction.md` | Added this phase report. | Document scope, before/after checks, service design, contract preservation, and deferred work. | None. | Low. |

## 6. Endpoint Contract Preservation

| Endpoint | Method | Auth/role preserved? | Response shape preserved? | Status code preserved? | Error behavior preserved? | Side effects preserved? | Commit/rollback behavior preserved? | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `/api/admin/referral-rules` | `GET` | Yes; existing `@require_role('admin')` retained. | Yes; response remains `{referral_rules}` with current rule keys. | Yes; `200`, auth/role failure, and `500` behavior preserved. | Yes; generic list error payload preserved. | Yes; read-only behavior preserved. | Yes; no write transaction added. | Ordering remains `priority ASC, name`. |
| `/api/admin/referral-rules` | `POST` | Yes; existing `@require_role('admin')` retained. | Yes; success remains `{message, rule_id}`. | Yes; `201`, `400`, `401`, auth/role failure, and `500` behavior preserved. | Yes; validation and generic create error payloads preserved. | Yes; referral rule creation is preserved. | Yes; service commits on success; route rolls back on validation/value/generic errors. | No action validation behavior was changed. |
| `/api/admin/referral-rules/<int:rule_id>` | `PUT` | Yes; existing `@require_role('admin')` retained. | Yes; success remains `{message}`. | Yes; `200`, `400`, `404`, auth/role failure, and `500` behavior preserved. | Yes; missing rule, invalid action, value, and generic update payloads preserved. | Yes; update fields and `updated_at` behavior preserved. | Yes; service commits on success; route rolls back on errors. | Existing partial-update semantics preserved. |
| `/api/admin/referral-rules/<int:rule_id>` | `DELETE` | Yes; existing `@require_role('admin')` retained. | Yes; success remains `{message}`. | Yes; `200`, `404`, auth/role failure, and `500` behavior preserved. | Yes; missing rule and generic delete payloads preserved. | Yes; linked `ReferralRuleState` deletion and rule deletion preserved; logs remain untouched. | Yes; service commits on success; route rolls back on errors. | Audit logs remain preserved. |
| `/api/admin/referral-rules/preview` | `POST` | Yes; existing `@require_role('admin')` retained. | Yes; referral engine preview payload returned unchanged. | Yes; `200`, `400`, auth/role failure, and `500` behavior preserved. | Yes; missing `request_id` and generic preview payloads preserved. | Yes; dry-run/no-write behavior preserved. | Yes; no commit/rollback behavior added. | Delegates to existing `referral_engine.preview_assignment`. |

## 7. After

Post-change checks:

| Check | Result |
| --- | --- |
| `python -m pytest -q` | Passed: `68 passed` |
| `python -m pytest backend/tests/test_expert_assignment_referral_contract.py backend/tests/test_referral_engine.py -q` | Passed: `9 passed` |
| Targeted referral tests | Covered by `test_referral_rule_crud_contracts`, existing referral API tests, and `test_referral_engine_and_api`; passed. |
| `npm run lint` | Passed with existing warnings: `0 errors`, `17 warnings` |
| `npm run build` | Passed with existing Vite/Browserslist/chunk-size warnings |
| `npm run check:structure` | Passed |
| `git diff --check` | Passed |

## 8. Deferred Items

Explicitly deferred and not changed in Phase 4M:

- Manual assignment behavior fix.
- Expert request list/detail extraction.
- Referral rule redesign.
- Repository layer.
- Model split.
- Frontend refactor.
- CI/CD.
- OpenAPI documentation.
