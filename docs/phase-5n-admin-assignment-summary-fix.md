# Phase 5N: Admin Assignment Summary Fix

## 1. Scope

This phase fixes only:

- `GET /api/admin/reports/assignment-summary`

No frontend, schema/model, migration, auth/role decorator, unrelated admin endpoint, customer gamification, user management, assignment/referral service, or repository layer change was made.

## 2. Previous 500 Behavior

Phase 5M characterized the endpoint as returning:

```json
{"error": "خطا در تولید گزارش"}
```

with status `500`.

## 3. Root Cause

The report query used legacy SQLAlchemy `case([...])` syntax. SQLAlchemy 2.x requires positional `case((condition, value), else_=...)` whens.

After fixing that syntax, the old SQL-level average response-time expression was also kept out of the critical path by calculating the average from fetched datetime rows. This keeps the endpoint compatible with the SQLite test database while preserving the route's intended response fields.

## 4. Fix Applied

In `backend/routes/admin_panel.py`:

- replaced `case([(condition, 1)], else_=0)` with `case((condition, 1), else_=0)`
- preserved expert assignment counts, won/lost/active counts, conversion rate, SLA violation count, and generated timestamp
- calculated overall response-time hours from assignment/action datetime rows in Python

## 5. New Response Contract

Successful response status is `200`.

Top-level keys:

- `assignments_per_expert`
- `overall_stats`
- `generated_at`

Each expert summary includes:

- `expert_id`
- `expert_name`
- `username`
- `role`
- `total_assignments`
- `won_count`
- `lost_count`
- `active_count`
- `conversion_rate`
- `avg_response_time_hours`

`overall_stats` includes:

- `total_assignments`
- `total_won`
- `overall_conversion_rate`
- `avg_response_time_hours`
- `sla_violations`

## 6. Tests Updated

`backend/tests/test_admin_panel_read_contract.py` now locks successful assignment-summary behavior instead of the previous 500 behavior.

The test verifies:

- status `200`
- top-level response keys
- per-expert assignment totals and conversion fields
- overall totals, average response time, and SLA violations
- isolated seeded SQLite DB behavior

## 7. Verification

Required verification commands were run before and after the change:

- `python -m pytest -q`
- `python -m pytest backend/tests/test_admin_panel_read_contract.py -q`
- `npm.cmd run lint`
- `npm.cmd run build`
- `npm.cmd run check:structure`
- `git diff --check`

## 8. Deferred Items

- Extract assignment-summary logic into `admin_report_service.py`
- Extract dashboard metrics into `admin_dashboard_service.py`
- Decide whether per-expert `avg_response_time_hours` should be implemented instead of remaining `None`
- Broader SQLAlchemy legacy query cleanup
