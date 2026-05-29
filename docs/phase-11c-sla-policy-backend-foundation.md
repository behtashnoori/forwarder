# Phase 11C: SLA Policy Backend Foundation

## 1. Scope

This phase adds the backend foundation for admin-managed SLA policies only.

No AdminPanel UI, ExpertConsole UI, RequestDetail UI, priority auto-rule behavior, customer-facing SLA behavior, public shipment creation behavior, expert request list/detail response shape, Expert KPI response shape, or direct assignment behavior was changed.

## 2. What Was Added

- `SlaPolicy` backend model/table.
- Alembic migration for the `sla_policy` table.
- `backend/services/sla_policy_service.py`.
- Admin-only SLA policy API endpoints.
- Backend contract tests for auth, CRUD, enable/disable, validation, service resolution, fallback, due-date calculation, and SLA status calculation.
- Minimal OpenAPI documentation for the new admin SLA policy endpoints.
- This phase documentation.

## 3. SLA Policy Model

Table: `sla_policy`

| Field | Behavior |
| --- | --- |
| `id` | Primary key, SQLite-compatible integer variant. |
| `name` | Required admin-visible policy name. |
| `priority_scope` | Required string. Allowed values: `low`, `normal`, `high`, `urgent`, `all`. Default: `all`. |
| `request_status_scope` | Required text field containing a JSON list. Default service value: `["assigned", "in_progress"]`. |
| `transport_method_scope` | Optional string. When present, the policy only matches that transport method. |
| `shipping_type_scope` | Optional string. Allowed values: `domestic`, `international`, `all`. |
| `response_time_minutes` | Required positive integer. |
| `near_deadline_threshold_minutes` | Required positive integer. Must not exceed `response_time_minutes`. |
| `is_active` | Boolean, default `true`. Disable is preferred over delete. |
| `sort_order` | Integer, default `100`. Lower values win when multiple active policies match. |
| `created_at` | Required datetime. |
| `updated_at` | Required datetime. |

`shipment_request.sla_policy_id` was intentionally not added in this phase. Request-to-policy traceability is useful for auditability, but deferring it keeps this foundation smaller and avoids changing current request behavior or data shape before product rules are finalized.

## 4. SLA Service Behavior

Service file: `backend/services/sla_policy_service.py`

The service supports:

- list SLA policies in deterministic order: `sort_order`, `name`, `id`
- create SLA policy
- update SLA policy
- enable/disable SLA policy
- validate payloads
- serialize policy response payloads
- resolve the first matching active policy for a request or priority/status context
- calculate due date from a policy and start time
- calculate `on_time`, `due_soon`, and `overdue`
- provide legacy fallback behavior when no active policy matches

Legacy fallback:

- `response_time_minutes = 120`
- `near_deadline_threshold_minutes = 120`
- null `sla_due_at` returns `on_time`

This fallback mirrors the current hardcoded two-hour behavior without replacing existing expert request/KPI code in this phase.

Conflict handling:

- Advanced duplicate/conflict validation is deferred.
- Current v1 resolution uses `sort_order`, then `name`, then `id`.
- Admins can disable a policy without deleting it.

## 5. Admin API

All endpoints are admin-only and use the existing `require_role("admin")` protection.

### `GET /api/admin/sla-policies`

Returns:

```json
{
  "sla_policies": []
}
```

### `POST /api/admin/sla-policies`

Creates a policy.

Request fields:

- `name`
- `priority_scope`
- `request_status_scope`
- `transport_method_scope`
- `shipping_type_scope`
- `response_time_minutes`
- `near_deadline_threshold_minutes`
- `is_active`
- `sort_order`

Returns `201`:

```json
{
  "message": "SLA policy created",
  "sla_policy": {}
}
```

### `PUT /api/admin/sla-policies/<policy_id>`

Updates editable fields and returns:

```json
{
  "message": "SLA policy updated",
  "sla_policy": {}
}
```

### `PATCH /api/admin/sla-policies/<policy_id>/disable`

Sets `is_active` to `false`. Repeated disable is safe.

### `PATCH /api/admin/sla-policies/<policy_id>/enable`

Sets `is_active` to `true`.

Errors:

- invalid payload: `400` with `{ "error": "..." }`
- missing policy: `404` with `{ "error": "SLA policy not found" }`
- missing token / forbidden role: existing auth error formats

## 6. Behavior Preservation

- Public shipment creation unchanged.
- Existing expert request list/detail shape unchanged.
- Existing Expert KPI shape unchanged.
- Existing direct assignment behavior unchanged.
- Existing hardcoded expert status-update SLA behavior unchanged.
- Existing frontend unchanged.
- AdminPanel UI unchanged.
- ExpertConsole UI unchanged.
- RequestDetail UI unchanged.
- Priority auto-rules not implemented.
- Priority is not connected to SLA policy resolution in existing request flows yet.

## 7. Tests Added

| Test file | Test name | Behavior covered |
| --- | --- | --- |
| `backend/tests/test_sla_policy_contract.py` | `test_sla_policy_admin_auth_contract` | Missing token, non-admin forbidden, admin list access. |
| `backend/tests/test_sla_policy_contract.py` | `test_sla_policy_create_list_and_order_contract` | Create response shape, default active behavior, deterministic list ordering. |
| `backend/tests/test_sla_policy_contract.py` | `test_sla_policy_create_validation_contract` | Validation errors for missing/invalid name, scopes, minutes, booleans, and sort order. |
| `backend/tests/test_sla_policy_contract.py` | `test_sla_policy_update_disable_enable_contract` | Update fields, validation, not found, idempotent disable, enable. |
| `backend/tests/test_sla_policy_contract.py` | `test_sla_policy_service_resolution_and_calculation_contract` | Legacy fallback, policy resolution, due-date calculation, SLA status calculation, disabled policy fallback. |

Phase 11B tests remain relevant and should continue to pass once the Python test environment is repaired.

## 8. Deferred Items

- Priority auto-rules.
- Priority manual override UI/API.
- AdminPanel SLA management UI.
- ExpertConsole real SLA integration.
- Remaining-time display.
- Request-to-policy audit link.
- Advanced conflict validation.
- SLA report dashboards.
- Replacing existing hardcoded expert/KPI SLA calculations with the centralized service.

## 9. Verification

- Backend Python compile check for updated files: passed using bundled Codex Python.
- `npm.cmd run lint`: passed with 10 existing warnings and 0 errors. Warnings are the existing React fast-refresh/shared-export warnings plus the existing `UserManagement.tsx` hook dependency warning.
- `npm.cmd run build`: passed. Vite reported the existing browserslist age notice and chunk-size warning.
- `npm.cmd run check:structure`: passed.
- `python -m pytest -q`: blocked because `python` is not available in PATH.
- `git diff --check`: passed. Git emitted line-ending notices, but no whitespace errors.
