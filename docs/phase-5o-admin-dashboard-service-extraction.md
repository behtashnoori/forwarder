# Phase 5O: Admin Dashboard Service Extraction

## 1. Scope

This phase extracts only:

- `GET /api/admin/dashboard`

No frontend, schema/model, migration, auth/role decorator, assignment-summary endpoint, referral rule endpoint, user management endpoint, customer gamification endpoint, repository layer, or dependency file was changed.

## 2. Before

`backend/routes/admin_panel.py` contained the dashboard query and payload-building logic directly in the route handler.

The route calculated:

- total request count
- request counts by transport method
- request counts by status
- last 7 days count
- last 24 hours count
- unassigned new/pending count
- top 10 origin provinces

## 3. Characterization Tests

`backend/tests/test_admin_panel_read_contract.py` already locked the populated dashboard response shape and key metric values.

This phase strengthened coverage for:

- missing token behavior
- non-admin forbidden behavior
- unchanged dashboard success response

The tests use an isolated seeded SQLite database.

## 4. Service Design

Added `backend/services/admin_dashboard_service.py` with focused helpers:

- `get_admin_dashboard_payload()`
- `build_admin_dashboard_metrics()`
- `build_transport_method_summary()`
- `build_status_summary()`
- `build_top_provinces_payload()`

No repository layer was introduced.

## 5. Changes Made

`get_admin_dashboard` in `backend/routes/admin_panel.py` now:

1. keeps `@require_role('admin')`
2. calls `admin_dashboard_service.get_admin_dashboard_payload()`
3. `jsonify`s the same payload
4. preserves the existing error log and `{"error": "خطا در دریافت آمار داشبورد"}` 500 payload

## 6. Endpoint Contract Preservation

Preserved:

- URL: `GET /api/admin/dashboard`
- auth/role requirement: admin
- status code on success: `200`
- error payload on unexpected failure
- response shape
- metric names
- count calculations
- status grouping
- transport method grouping expression
- date windows based on `datetime.utcnow()`
- top-province ordering and limit

## 7. After

The dashboard route is now a thin controller. Dashboard business/query logic lives in the service layer.

## 8. Deferred Items

- Extract `GET /api/admin/reports/assignment-summary` into `admin_report_service.py`
- Extract shipment request list/detail into `admin_request_service.py`
- Broader SQLAlchemy legacy query cleanup
- Repository layer introduction
