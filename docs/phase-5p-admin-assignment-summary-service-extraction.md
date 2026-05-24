# Phase 5P: Admin Assignment Summary Service Extraction

## 1. Scope

Phase 5P only extracts the `GET /api/admin/reports/assignment-summary` report logic from `backend/routes/admin_panel.py` into a service layer.

No frontend, schema, migration, auth, admin dashboard, referral rule, user management, customer gamification, repository, or dependency changes are included.

## 2. Before

Before this phase, the assignment summary route owned all query, aggregation, response-time, SLA, and payload-building logic directly in the Flask route handler.

The route already used SQLAlchemy 2.x-compatible `case(...)` syntax and a SQLite-compatible Python response-time calculation after Phase 5N.

## 3. Characterization Tests

`backend/tests/test_admin_panel_read_contract.py` covered the seeded test database response for:

- successful `200` status
- top-level keys: `assignments_per_expert`, `overall_stats`, `generated_at`
- per-expert report fields and counts
- overall assignment counts, conversion rate, response-time hours, and SLA violations

Phase 5P also strengthens auth/role characterization for the assignment-summary endpoint:

- missing token returns `401`
- non-admin expert token returns `403`

## 4. Service Design

The new service file is `backend/services/admin_report_service.py`.

The service exposes:

- `get_assignment_summary_payload()`
- `build_assignment_summary_response_payload()`
- `build_assignments_per_expert()`
- `build_overall_assignment_stats()`
- `calculate_avg_response_time_hours()`
- `calculate_conversion_rate()`
- `calculate_sla_violations()`

The service intentionally stays close to the previous route logic and does not introduce a repository layer.

## 5. Changes Made

- Added `admin_report_service.py`.
- Moved assignment-summary query and payload-building logic into the service.
- Updated `admin_panel.py` so the route calls `admin_report_service.get_assignment_summary_payload()` and preserves the existing `jsonify` and error handling.
- Extended admin read contract tests for assignment-summary auth/role behavior.

## 6. Endpoint Contract Preservation

Preserved:

- URL: `GET /api/admin/reports/assignment-summary`
- auth/role behavior: admin only
- success status code
- error payload on unexpected failures
- response shape
- `assignments_per_expert`
- `overall_stats`
- `generated_at`
- `total_assignments`
- `total_won`
- `overall_conversion_rate`
- `avg_response_time_hours`
- `sla_violations`
- SQLite-compatible response-time calculation
- SQLAlchemy 2.x-compatible `case(...)` syntax

## 7. After

After Phase 5P, the assignment-summary route is a thin controller. The report logic lives in `admin_report_service.py`, and existing admin dashboard behavior remains unchanged.

## 8. Deferred Items

- Extract admin shipment request list/detail logic.
- Consider consolidating admin read/report services only after more characterization coverage.
- Defer repository-layer introduction until repeated query boundaries are clearer.
