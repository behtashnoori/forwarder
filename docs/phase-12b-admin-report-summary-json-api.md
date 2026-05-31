# Phase 12B: Admin Report Summary JSON API

## 1. Scope

This phase adds the backend JSON reporting API only. It does not add Excel export, PDF export, AdminPanel UI, frontend code, dependencies, migrations, request workflow changes, or automatic assignment changes.

## 2. Endpoint

Added endpoint:

- `GET /api/admin/reports/overview?period=weekly|monthly|yearly`

Auth:

- Admin-only via the existing `@require_role('admin')` route protection.
- Missing token follows the existing admin auth behavior.
- Non-admin users receive the existing forbidden response shape.

Query params:

- `period`: optional; defaults to `weekly`.
- Valid values: `weekly`, `monthly`, `yearly`.
- Invalid period returns `400` with `{"error": "دوره گزارش نامعتبر است"}`.

Implementation:

- Route: `backend/routes/admin_panel.py`
- Service: `backend/services/admin_report_overview_service.py`

## 3. Period Logic

The report uses UTC because the current project stores and compares request timestamps with `datetime.utcnow()`.

Boundaries use inclusive start and exclusive end:

- `weekly`: from UTC start of today minus 6 days through UTC start of tomorrow.
- `monthly`: from UTC first day of the current calendar month through UTC first day of next month.
- `yearly`: from UTC January 1 of the current calendar year through UTC January 1 of next year.

The response metadata includes `timezone_basis: "UTC"`.

## 4. Response Sections

The endpoint returns:

- `metadata`
  - `period`, `period_label_fa`, `start_date`, `end_date`, `generated_at`, `timezone_basis`
- `summary`
  - `total_requests`, `new_requests`, `pending_review_requests`, `in_progress_requests`, `completed_requests`, `lost_or_rejected_requests`, `unassigned_requests`, `requests_last_24h`, `requests_last_7d`
- `requests_by_status`
  - `status`, `label_fa`, `count`, `percent_of_total`, `latest_created_at`
- `transport_distribution`
  - `transport_method`, `label_fa`, `count`, `percent_of_total`, `completed_count`, `in_progress_count`
- `location_distribution`
  - `location_type`, `location_type_label_fa`, `province`, `county`, `city`, `count`, `percent_of_total`, `top_transport_method`
- `expert_performance`
  - `expert_id`, `expert_name`, `username`, `role`, `assigned_count`, `active_count`, `completed_count`, `lost_or_rejected_count`, `completion_rate`
- `customer_concentration`
  - `customer_name`, `phone`, `company`, `request_count`, `latest_request_date`, `latest_request_status`, `latest_request_status_label_fa`, `dominant_transport_method`, `dominant_origin`, `dominant_destination`
- `trends`
  - `bucket`, `label`, `request_count`
- `request_details`
  - `id`, `tracking_number`, `created_at`, `status`, `status_label_fa`, `customer_name`, `phone`, `transport_method`, origin/destination fields, `expert_name`, cargo fields, pickup/delivery dates, `has_unread_for_assignee`

`ShipmentRequest.status` is the canonical status source for reporting. `status_request_status` is intentionally not merged into report metrics.

## 5. Persian Labels

Status labels:

- `new`: `جدید`
- `assigned`: `در انتظار بررسی`
- `in_progress`: `در حال بررسی`
- `quoted`: `پیشنهاد ارسال‌شده`
- `waiting_for_customer`: `منتظر مشتری`
- `won`: `پذیرفته‌شده`
- `lost`: `ردشده / از دست‌رفته`
- `closed`: `مختومه`

Missing values:

- Unassigned/missing expert: `بدون کارشناس`
- Missing location/customer/company/transport fields: `ثبت نشده`

The response does not use visible `ارجاع شده` / `ارجاع‌شده` labels.

## 6. Exclusions

Confirmed exclusions:

- No SLA fields.
- No response deadline fields.
- No overdue/due-soon fields.
- No priority fields.
- No Excel export.
- No PDF export.
- No AdminPanel UI changes.

## 7. Tests

Updated:

- `backend/tests/test_admin_panel_read_contract.py`

Coverage added:

- Missing token cannot access the overview endpoint.
- Non-admin cannot access.
- Admin can access.
- `weekly`, `monthly`, and `yearly` periods work.
- Invalid period returns 400.
- Required response sections are present.
- Summary counters cover total/new/assigned/in-progress/completed/lost/unassigned.
- Persian labels use `در انتظار بررسی`, `بدون کارشناس`, and `ثبت نشده`.
- `ارجاع شده` / `ارجاع‌شده` are absent.
- SLA and priority keys are absent.
- Empty report returns zero counts and empty arrays safely.

## 8. Verification

- `py_compile` for the new service, route, and updated admin tests: passed.
- `npm.cmd run lint`: passed with 10 existing warnings.
- `npm.cmd run build`: passed with existing Browserslist/chunk-size warnings.
- `npm.cmd run check:structure`: passed.
- `python -m pytest -q`: blocked because `python` is not on PATH in this shell.
- `git diff --check`: passed; Git reported CRLF normalization warnings only.
