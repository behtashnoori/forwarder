# Phase 12C: Admin Report XLSX Export

## 1. Scope

This phase adds backend XLSX export only. It does not add PDF export, AdminPanel UI, frontend code, migrations, request workflow changes, or automatic assignment changes.

## 2. Endpoint

Added endpoint:

- `GET /api/admin/reports/export.xlsx?period=weekly|monthly|yearly`

Auth:

- Admin-only through the existing `@require_role('admin')` route protection.
- Missing token and non-admin responses follow existing admin auth conventions.

Query params:

- `period`: optional; defaults to `weekly`.
- Valid values: `weekly`, `monthly`, `yearly`.
- Invalid period returns `400` with `{"error": "دوره گزارش نامعتبر است"}`.

Response:

- Content-Type: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- Content-Disposition: attachment
- Filename pattern: `forwarder-report-{period}.xlsx`

## 3. Data Source

The XLSX export reuses the Phase 12B report overview service:

- `backend/services/admin_report_overview_service.py`

The XLSX service calls the JSON report data builder and only translates that shared payload into workbook sheets. Report numbers therefore have one source of truth.

## 4. Workbook Sheets

Implemented sheets:

- `خلاصه مدیریتی`
  - Metadata and summary metrics.
  - Columns: `شاخص`, `مقدار`
- `وضعیت درخواست‌ها`
  - Source: `requests_by_status`
  - Columns: `وضعیت`, `برچسب فارسی وضعیت`, `تعداد درخواست`, `درصد از کل`, `آخرین تاریخ ثبت در این وضعیت`
- `توزیع نوع حمل`
  - Source: `transport_distribution`
  - Columns: `نوع حمل`, `برچسب فارسی نوع حمل`, `تعداد درخواست`, `درصد از کل`, `تعداد تکمیل‌شده`, `تعداد در حال بررسی`
- `توزیع مبدا و مقصد`
  - Source: `location_distribution`
  - Columns: `نوع موقعیت`, `استان`, `شهرستان`, `شهر`, `تعداد درخواست`, `درصد از کل`, `رایج‌ترین نوع حمل`
- `عملکرد کارشناسان`
  - Source: `expert_performance`
  - Columns: `شناسه کارشناس`, `نام کارشناس`, `نام کاربری`, `نقش`, `کل درخواست‌های تخصیص‌یافته`, `فعال`, `تکمیل‌شده`, `ردشده / از دست‌رفته`, `نرخ تکمیل`
- `مشتریان و درخواست‌ها`
  - Source: `customer_concentration`
  - Columns: `نام مشتری`, `شماره تماس`, `شرکت`, `تعداد درخواست`, `آخرین تاریخ درخواست`, `وضعیت آخرین درخواست`, `نوع حمل غالب`, `مبدا غالب`, `مقصد غالب`
- `روند زمانی`
  - Source: `trends`
  - Columns: `بازه`, `عنوان بازه`, `تعداد درخواست`
- `جزئیات درخواست‌ها`
  - Source: `request_details`
  - Columns: `شناسه`, `کد رهگیری`, `تاریخ ثبت`, `وضعیت`, `نام مشتری`, `شماره تماس`, `نوع حمل`, origin/destination columns, `کارشناس`, cargo fields, pickup/delivery dates, `خوانده‌نشده برای کارشناس`

Empty arrays still create sheets with headers.

## 5. Formatting

Implemented formatting:

- Bold table headers.
- Light header fill on table sheets.
- Freeze header row on table sheets.
- Freeze summary metrics area on the summary sheet.
- Best-effort column auto-sizing.
- Persian sheet names.
- Right-to-left sheet view enabled through `openpyxl` sheet view support.
- Minimal styling only.

## 6. Exclusions

Confirmed exclusions:

- No SLA columns or fields.
- No response deadline fields.
- No overdue/due-soon fields.
- No priority columns or fields.
- No PDF.
- No AdminPanel UI.
- No visible `ارجاع شده` / `ارجاع‌شده` wording.

## 7. Security

- Endpoint is admin-only.
- Export does not include secrets, tokens, password hashes, or internal auth fields.
- Customer phone/company fields are included only because this is an admin-only management report.

## 8. Tests

Updated:

- `backend/tests/test_admin_panel_read_contract.py`

Coverage added:

- Missing token cannot download XLSX.
- Non-admin cannot download XLSX.
- Admin can download XLSX.
- Weekly/monthly/yearly downloads work.
- Invalid period returns 400.
- XLSX content type and attachment filename are set.
- Response body opens as a valid workbook.
- Expected sheet names exist.
- Expected sheet headers exist.
- Summary metrics are present.
- Assigned label is `در انتظار بررسی`.
- No visible `ارجاع شده` / `ارجاع‌شده`.
- No SLA or priority columns.
- Empty report creates all sheets with headers.

## 9. Verification

- `py_compile` for touched backend Python files: passed.
- `npm.cmd run lint`: passed with 10 existing warnings.
- `npm.cmd run build`: passed with existing Browserslist/chunk-size warnings.
- `npm.cmd run check:structure`: passed.
- `python -m pytest -q`: blocked because `python` is not on PATH in this shell.
- `git diff --check`: passed; Git reported CRLF normalization warnings only.
