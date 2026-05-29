# Phase 11B: SLA Current Behavior Characterization

## 1. Scope

This phase only adds characterization tests and documentation for the current SLA and priority behavior.

No runtime behavior was changed. No SLA management feature, SLA policy model, SLA policy table, migration, API endpoint, frontend UI, AdminPanel SLA menu, ExpertConsole change, RequestDetail change, or priority-rule feature was added.

## 2. Current Behavior Locked

Request creation SLA defaults:

- Public shipment requests start with `priority = normal`.
- Public shipment requests start with `sla_due_at = None`.
- Public shipment requests keep the current `status = new` and `status_request_status = new` defaults.
- `sla_status` is not persisted as a `ShipmentRequest` database column.

Assigned status SLA behavior:

- Expert status update to `assigned` creates an SLA due date only when `sla_due_at` is empty.
- The created due date is approximately `now + 2 hours`.
- If `sla_due_at` already exists, status update to `assigned` preserves the existing value.

Direct assignment behavior:

- Direct assignment through `assignment_service.assign_request_to_expert` sets `status = assigned`.
- Direct assignment currently does not create or modify `sla_due_at`.
- This is locked as current behavior even though it remains a future SLA gap.

Computed SLA status behavior:

- `on_time` is returned when there is no due-soon or overdue condition.
- `due_soon` is returned when the request is not past due and the due date is within the current hardcoded two-hour window.
- `overdue` is returned when `now > sla_due_at`.
- Null `sla_due_at` serializes safely and does not crash list/detail responses.

Expert KPI SLA counts:

- `kpis.sla.overdue` counts requests with `sla_due_at < now` and the current active statuses used by the endpoint.
- `kpis.sla.due_soon` counts requests due within the current two-hour window and current active statuses.
- Terminal statuses such as `closed` are not counted by the current Expert KPI SLA logic.

Priority behavior:

- Observed values `low`, `normal`, `high`, and `urgent` can be stored and returned by current request-list behavior.
- Public shipment creation still defaults to `normal`.
- Expert request-list priority filtering is exact-match filtering on `ShipmentRequest.priority`.
- Priority does not currently drive SLA calculation; SLA values in tests are manually prepared data.

Admin report SLA behavior:

- Admin assignment summary SLA violation logic counts past-due requests in its current report-active statuses.
- Not-past-due requests and terminal closed requests are not counted.

## 3. Tests Added or Updated

| Test file | Test name | Behavior locked | Endpoint/service covered |
| --- | --- | --- | --- |
| `backend/tests/test_shipment_request_contract.py` | `test_create_domestic_shipment_request_preserves_response_defaults_and_commit` | Existing public request defaults now also assert `sla_due_at is None`. | `POST /api/shipment-request` |
| `backend/tests/test_shipment_request_contract.py` | `test_public_shipment_request_sla_defaults_contract` | Public SLA defaults, status defaults, and absence of persisted `sla_status`. | `POST /api/shipment-request`, `ShipmentRequest` model table |
| `backend/tests/test_expert_assignment_referral_contract.py` | `test_expert_request_priority_filter_exact_match_contract` | Exact-match priority filtering for `low`, `normal`, `high`, `urgent`. | `GET /api/expert/requests` |
| `backend/tests/test_expert_assignment_referral_contract.py` | `test_expert_request_sla_status_serialization_contract` | Current computed `on_time`, `due_soon`, `overdue`, and null-SLA serialization behavior. | `GET /api/expert/requests`, `GET /api/expert/requests/<id>` |
| `backend/tests/test_expert_assignment_referral_contract.py` | `test_expert_dashboard_sla_kpi_counts_contract` | Current Expert KPI overdue/due-soon counts and terminal-status exclusion. | `GET /api/expert/dashboard/kpis` |
| `backend/tests/test_expert_assignment_referral_contract.py` | `test_expert_status_update_assigned_sets_current_two_hour_sla_contract` | Status update to `assigned` sets `sla_due_at` to approximately `now + 2 hours` when empty. | `POST /api/expert/requests/<id>/status` |
| `backend/tests/test_expert_assignment_referral_contract.py` | `test_expert_status_update_preserves_existing_sla_due_at_contract` | Existing `sla_due_at` is preserved when status updates to `assigned`. | `POST /api/expert/requests/<id>/status` |
| `backend/tests/test_expert_assignment_referral_contract.py` | `test_direct_assignment_preserves_current_no_sla_due_at_behavior` | Direct assignment sets status/assignee but keeps `sla_due_at = None`. | `assignment_service.assign_request_to_expert` |
| `backend/tests/test_admin_panel_read_contract.py` | `test_admin_assignment_summary_sla_violation_contract` | Current admin report SLA violation counting for active, future, and terminal statuses. | `admin_report_service.calculate_sla_violations` |

## 4. Known Current Gaps Preserved

- SLA deadline creation is hardcoded to two hours in the expert status update path.
- The due-soon threshold is hardcoded to two hours.
- `assignment_service` direct assignment does not set `sla_due_at`.
- Priority is not product-managed yet.
- Priority is not connected to SLA policy calculation.
- No admin SLA policy exists.
- No SLA policy table exists.
- No AdminPanel SLA menu exists.
- `sla_status` remains computed on read rather than persisted.

## 5. Why No Feature Was Added

Phase 11B exists to lock current behavior before changing it. SLA policy tables, priority rules, AdminPanel SLA management, real policy-backed ExpertConsole SLA display, remaining-time calculations, and migration work are intentionally deferred to later phases.

The next implementation phase should build on these tests so future changes can show exactly which current behaviors are intentionally replaced and which remain compatible.

## 6. Verification

- `python -m pytest -q backend/tests/test_shipment_request_contract.py backend/tests/test_expert_assignment_referral_contract.py backend/tests/test_admin_panel_read_contract.py`: blocked because `python` is not available in PATH.
- `.venv\Scripts\python.exe -m pytest -q ...`: blocked because the virtualenv points to a missing `C:\Users\HOME\AppData\Local\Programs\Python\Python312\python.exe`.
- Bundled Codex Python pytest attempt: blocked because pytest is not installed in that bundled runtime.
- Bundled Codex Python compile check: passed for the updated backend test files.
- `npm.cmd run lint`: passed with 10 existing warnings and 0 errors. Warnings are the existing React fast-refresh/shared-export warnings plus the existing `UserManagement.tsx` hook dependency warning.
- `npm.cmd run build`: passed. Vite reported the existing browserslist age notice and chunk-size warning.
- `npm.cmd run check:structure`: passed.
- `python -m pytest -q`: blocked because `python` is not available in PATH.
- `git diff --check`: passed. Git emitted line-ending notices, but no whitespace errors.
