# Phase 11E: Connect SLA Policies to Assignment and SLA Calculation

## 1. Scope

This phase connects backend SLA policies to assignment/status-transition SLA calculation and centralizes expert SLA status calculation.

No AdminPanel UI, ExpertConsole UI, RequestDetail UI, frontend files, customer-facing behavior, manual priority override, priority-rule UI, migration, response-shape change, or new tab was added.

## 2. Previous Behavior

- Expert status update to `assigned` used a hardcoded two-hour SLA deadline.
- Direct assignment through `assignment_service` set `status = assigned` but did not set `sla_due_at`.
- Expert request list/detail duplicated hardcoded `sla_status` calculation.
- Expert KPI SLA counts used hardcoded two-hour due-soon query logic.
- SLA policy service existed but was not wired into live assignment/status/KPI flows.

## 3. New Behavior

- Status update to `assigned` now uses `sla_policy_service.assign_sla_due_at_if_needed`.
- Direct assignment now intentionally sets `sla_due_at` when it is empty.
- Existing `sla_due_at` values are preserved and not overwritten.
- Request list/detail `sla_status` now uses centralized SLA service calculation.
- Expert KPI `sla.overdue` and `sla.due_soon` keep the same response shape while using centralized service status calculation.
- If no matching active policy exists, the legacy fallback still calculates `now + 120 minutes`.

## 4. SLA Policy Resolution

Policy resolution uses:

- request priority, such as `normal`, `high`, or `urgent`
- target/current request status, usually `assigned` or `in_progress`
- optional transport method scope
- optional shipping type scope

Only active policies are considered.

When multiple policies match, the first policy by `sort_order`, then `name`, then `id` wins.

Disabled policies are ignored.

If no policy matches, legacy fallback is used:

- response deadline: 120 minutes
- due-soon threshold: 120 minutes

## 5. Behavior Preservation

- Frontend unchanged.
- API response shape unchanged.
- AdminPanel UI unchanged.
- ExpertConsole UI unchanged.
- RequestDetail UI unchanged.
- Public shipment creation unchanged beyond existing Phase 11D priority logic.
- Status labels unchanged.
- Request actions unchanged.
- Existing `sla_due_at` preservation unchanged.
- Terminal statuses remain excluded from Expert KPI active SLA counts.

## 6. Intentional Behavior Changes

- Hardcoded assigned SLA deadline was replaced by policy-backed calculation.
- Direct assignment now sets `sla_due_at` if it was empty.
- Expert list/detail/KPI SLA status calculation now flows through `sla_policy_service`.
- Legacy fallback preserves the previous 120-minute behavior when no matching active policy exists.

## 7. Tests Added or Updated

| Test file | Test name | Behavior covered |
| --- | --- | --- |
| `backend/tests/test_expert_assignment_referral_contract.py` | `test_expert_status_update_assigned_uses_fallback_two_hour_sla_contract` | Status update uses service fallback when no policy exists. |
| `backend/tests/test_expert_assignment_referral_contract.py` | `test_expert_status_update_assigned_uses_matching_sla_policy_contract` | Status update uses matching active SLA policy deadline. |
| `backend/tests/test_expert_assignment_referral_contract.py` | `test_expert_status_update_ignores_disabled_sla_policy_contract` | Disabled policy is ignored and fallback is used. |
| `backend/tests/test_expert_assignment_referral_contract.py` | `test_direct_assignment_sets_sla_due_at_through_policy_service_contract` | Direct assignment now creates SLA due date through service. |
| `backend/tests/test_expert_assignment_referral_contract.py` | `test_expert_request_sla_status_uses_policy_threshold_contract` | List/detail `sla_status` uses policy near-deadline threshold. |
| `backend/tests/test_expert_assignment_referral_contract.py` | `test_expert_dashboard_sla_kpi_uses_policy_threshold_contract` | Expert KPI SLA counts use policy threshold with unchanged response shape. |

## 8. Deferred Items

- AdminPanel SLA management UI.
- ExpertConsole remaining-time display.
- SLA status filter.
- Priority manual override.
- Request-to-policy audit link.
- Advanced SLA reports.
- OpenAPI extension for additional fields, since no response shape changed in this phase.

## 9. Verification

- Backend Python compile check for updated files: passed using bundled Codex Python.
- `npm.cmd run lint`: passed with 10 existing warnings and 0 errors. Warnings are the existing React fast-refresh/shared-export warnings plus the existing `UserManagement.tsx` hook dependency warning.
- `npm.cmd run build`: passed. Vite reported the existing browserslist age notice and chunk-size warning.
- `npm.cmd run check:structure`: passed.
- `python -m pytest -q`: blocked because `python` is not available in PATH.
- `git diff --check`: passed. Git emitted line-ending notices, but no whitespace errors.
