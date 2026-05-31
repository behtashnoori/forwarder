# Phase 12A: Admin Reports Export Audit and Roadmap

## 1. Scope

This phase is audit and planning only. It does not implement report APIs, Excel export, PDF export, AdminPanel UI, backend runtime code, dependencies, migrations, API response shape changes, request workflow changes, or automatic assignment changes.

Reporting scope for this branch excludes SLA, response deadlines, overdue/due-soon, and priority metrics.

## 2. Current AdminPanel Structure

AdminPanel is implemented in `src/pages/AdminPanel.tsx`.

Current tabs:

- `dashboard`: admin dashboard summary cards and distributions.
- `users`: renders `src/pages/UserManagement.tsx`.
- `referral-rules`: renders `src/components/ReferralRulesTab.tsx`, currently presented as automatic request distribution.
- `site-settings`: renders `src/components/SiteSettingsTab.tsx`.

A future `گزارش‌ها` tab should fit after `dashboard` and before `users`. Reports are a core admin management activity, and placing them near dashboard keeps analytics/distribution/export functions together.

Existing admin dashboard/report sections:

- Admin dashboard UI exists in `AdminPanel.tsx`.
- Admin dashboard endpoint exists at `GET /api/admin/dashboard`.
- Admin assignment-summary endpoint exists at `GET /api/admin/reports/assignment-summary`.
- No AdminPanel reports/export tab exists yet.
- No XLSX/PDF download UI exists yet.

Existing admin report services:

- `backend/services/admin_dashboard_service.py` calculates dashboard summary metrics.
- `backend/services/admin_report_service.py` calculates an assignment summary payload, but it includes response-time/SLA concepts and should not be reused as-is for this branch's first management reports.

## 3. Available Data Sources

Primary models:

- `ShipmentRequest`
  - Available: `id`, `tracking_code`, `created_at`, `status`, `status_request_status`, `transport_method`, `domestic_transport_method`, `international_transport_method`, `shipping_type`, origin/destination domestic location IDs, international origin/destination country/city/address fields, customer first/last name, `contact_phone`, `customer_id`, `assigned_to`, cargo description/weight/volume/value, `pickup_date`, `delivery_date`, `has_unread_for_assignee`.
  - Present but excluded from this branch's report scope: `sla_due_at`, `last_customer_touch_at`, `priority`.
- `ExpertUser`
  - Available: expert ID, username, full name, email, phone, role, active flag, manager/department/specialization metadata.
- `Province`, `County`, `City`
  - Available for domestic origin/destination labels.
- `Customer`
  - Available when `ShipmentRequest.customer_id` is linked: company name, first/last name, email, phone/mobile, CRM metadata.
  - Gap: public shipment requests currently store customer name/phone directly on `ShipmentRequest` and may not have linked `Customer` records or company names.
- `ExpertConsoleLog`, `ReferralAssignmentLog`, `ExpertConsoleNotification`
  - Available for assignment/audit side effects and unread/request activity context.
- `TransportMethod`
  - Available for Persian transport method labels where values match configured method names.
- `Report`
  - Existing CRM saved-report metadata model. It is not an export engine and should not drive Phase 12B unless a later product decision wants saved report definitions.

Relevant services/endpoints:

- `backend/routes/admin_panel.py`
  - `GET /api/admin/dashboard`
  - `GET /api/admin/shipment-requests`
  - `GET /api/admin/shipment-requests/<id>`
  - `GET /api/admin/reports/assignment-summary`
- `backend/services/admin_dashboard_service.py`
- `backend/services/admin_report_service.py`
- `backend/services/admin_shipment_request_service.py`
- `backend/services/shipment_service.py`
- `backend/services/assignment_service.py`
- `backend/referral_engine.py`
- `backend/services/expert_request_list_service.py`

## 4. Existing Report Logic

Already calculated:

- Total requests: `admin_dashboard_service.build_admin_dashboard_metrics`.
- Requests by status: `build_status_summary`.
- Requests by transport method: `build_transport_method_summary`.
- Requests by province: `build_top_provinces_payload`, origin province only.
- Assigned/unassigned requests: dashboard has `unassigned_count`; assignment summary joins assigned requests to experts.
- Expert workload: `admin_report_service.build_assignments_per_expert` calculates assignments, won/lost/active, and conversion rate for active experts.
- Recent requests: admin shipment request list supports date filters and created-at sorting.
- Last 24 hours and last 7 days: dashboard calculates both.

Partially available or missing:

- Customer concentration: can be computed from request customer name/phone and optional linked `Customer`, but no current admin report calculates it.
- Trend by date: no current admin dashboard/report groups requests by day/month/year.
- Destination province distribution: not currently calculated; top province uses origin only.
- International origin/destination reporting: raw country/city fields are available, but current dashboard location helpers focus on domestic Province/County/City.
- Assignment summary endpoint currently includes response-time and SLA fields, which are excluded from this branch's reporting scope.

## 5. Recommended Report Periods

Recommended definitions:

- `weekly`: last 7 days including today, using `created_at >= start_of_today - 6 days` through end of current day.
- `monthly`: current calendar month, from day 1 through the end of the current day/month.
- `yearly`: current calendar year, from January 1 through the end of the current day/year.

Implementation note for Phase 12B: define boundaries in backend service code once, use inclusive start and exclusive end for safer SQL filtering, and document timezone behavior. The project currently uses `datetime.utcnow()` in many places, so UTC boundaries are safest initially unless the product explicitly chooses Tehran-local reporting periods.

## 6. Recommended Excel Workbook

Recommended file format: XLSX.

General sorting:

- Summary sheet: fixed metric order.
- Status/transport/location/expert/customer sheets: descending request count, then label/name ascending.
- Details sheet: newest requests first by `created_at DESC`.

Recommended sheets:

### A. خلاصه مدیریتی

Purpose: high-level overview for the selected period.

Metrics:

- کل درخواست‌ها
- درخواست‌های جدید
- در انتظار بررسی
- در حال بررسی
- تکمیل‌شده
- ردشده / از دست‌رفته
- بدون کارشناس
- درخواست‌های ۲۴ ساعت اخیر
- درخواست‌های ۷ روز اخیر

Availability: all metrics are available from `ShipmentRequest.status`, `assigned_to`, and `created_at`.

### B. وضعیت درخواست‌ها

Columns:

- وضعیت
- برچسب فارسی وضعیت
- تعداد درخواست
- درصد از کل
- آخرین تاریخ ثبت در این وضعیت

Availability: available from `ShipmentRequest.status` and `created_at`.

### C. توزیع نوع حمل

Columns:

- نوع حمل
- برچسب فارسی نوع حمل
- تعداد درخواست
- درصد از کل
- تعداد تکمیل‌شده
- تعداد در حال بررسی

Availability: available by coalescing `domestic_transport_method`, `international_transport_method`, and `transport_method`. Persian labels can come from `TransportMethod.name_fa` when a match exists; otherwise use a small fallback map and then raw value.

### D. توزیع مبدا و مقصد

Columns:

- نوع موقعیت: مبدا / مقصد
- استان
- شهرستان
- شهر
- تعداد درخواست
- درصد از کل
- رایج‌ترین نوع حمل

Availability: available for domestic requests through `Province`, `County`, and `City`. For international requests, Phase 12B should either add separate international columns or use the country/city fields with `ثبت نشده` for domestic-only location parts.

### E. عملکرد کارشناسان

Columns:

- شناسه کارشناس
- نام کارشناس
- نام کاربری
- نقش
- کل درخواست‌های تخصیص‌یافته
- فعال
- تکمیل‌شده
- ردشده / از دست‌رفته
- نرخ تکمیل

Availability: available from `ExpertUser` and `ShipmentRequest.assigned_to/status`. Do not include response-time, SLA, or priority-based workload in this branch.

### F. مشتریان و درخواست‌ها

Columns:

- نام مشتری
- شماره تماس
- شرکت
- تعداد درخواست
- آخرین تاریخ درخواست
- وضعیت آخرین درخواست
- نوع حمل غالب
- مبدا غالب
- مقصد غالب

Availability: name/phone are available on `ShipmentRequest`; company is available only when `customer_id` links to `Customer.company_name`, otherwise use `ثبت نشده`.

### G. جزئیات درخواست‌ها

Columns:

- شناسه
- کد رهگیری
- تاریخ ثبت
- وضعیت
- نام مشتری
- شماره تماس
- نوع حمل
- مبدا استان
- مبدا شهرستان
- مبدا شهر
- مقصد استان
- مقصد شهرستان
- مقصد شهر
- کارشناس
- شرح بار
- وزن
- حجم
- ارزش بار
- تاریخ بارگیری
- تاریخ تحویل
- خوانده‌نشده برای کارشناس

Availability: available from `ShipmentRequest`, `ExpertUser`, and location tables. Use `ثبت نشده` for missing values.

## 7. Persian Labels

Recommended status labels:

- `new`: `جدید`
- `assigned`: `در انتظار بررسی`
- `in_progress`: `در حال بررسی`
- `quoted`: `پیشنهاد ارسال‌شده`
- `waiting_for_customer`: `منتظر مشتری`
- `won`: `پذیرفته‌شده`
- `lost`: `ردشده / از دست‌رفته`
- `closed`: `مختومه`
- Unknown status: raw status value plus a future warning/count in logs, not a Persian guess.

Missing values:

- Missing expert: `بدون کارشناس`
- Missing location/customer/company fields: `ثبت نشده`

Explicit exclusions:

- `assigned` must be displayed as `در انتظار بررسی`.
- `unassigned` must be displayed as `بدون کارشناس`.
- SLA is excluded.
- Priority is excluded.

## 8. XLSX vs PDF Recommendation

XLSX should be implemented first.

Reasons:

- Admins need tabular operational data across multiple sheets; Excel is a natural fit for filtering, sorting, and follow-up analysis.
- No current XLSX dependency is present in `package.json`, `requirements.txt`, or `backend/requirements.txt`; Phase 12C can add one deliberately with tests.
- PDF export has higher Persian/RTL/font risk. Persian shaping, right-to-left layout, font embedding, table overflow, and page breaks are all more fragile in PDF than XLSX.
- PDF is better suited to a short executive summary, not the detailed operational workbook described here.

Recommendation:

- Phase 12C: implement XLSX export first.
- Phase 12E: evaluate optional PDF executive summary only after JSON and XLSX are stable.

## 9. Recommended Backend API Design

Future endpoints, admin-only:

- `GET /api/admin/reports/overview?period=weekly|monthly|yearly`
  - JSON summary for AdminPanel and tests.
  - Returns workbook-equivalent sections except raw binary file content.
- `GET /api/admin/reports/export.xlsx?period=weekly|monthly|yearly`
  - XLSX download for the same period and section definitions.

Rules:

- Require admin auth with `@require_role('admin')`.
- Invalid `period` returns 400.
- No public access.
- Do not reuse `GET /api/admin/reports/assignment-summary` as the main endpoint because it currently includes SLA/response-time concepts.
- Use one report data service in Phase 12B, then have XLSX export consume the same data in Phase 12C to avoid metric drift.

## 10. Recommended AdminPanel UI

Future tab label: `گزارش‌ها`.

Suggested v1 controls:

- `گزارش هفتگی Excel`
- `گزارش ماهانه Excel`
- `گزارش سالانه Excel`
- Loading state during download.
- Error state with the server error message or a generic failure.
- No fake data.
- No PDF button in v1.

Placement:

- Add the tab after `داشبورد` and before `مدیریت کاربران`.
- Keep visual style consistent with the existing compact AdminPanel tab and card patterns.

## 11. Risks and Gaps

- Incomplete or inconsistent request status values.
- Mismatch between `status` and `status_request_status`; reporting should use `status` as canonical unless Phase 12B documents a specific fallback.
- Large exports if request volume grows; Phase 12C should consider streaming or row limits if needed.
- Persian PDF/font/RTL risk.
- Privacy/customer data exposure; reports include customer phone/company only because they are admin-only.
- Dependency availability for XLSX export; no XLSX library is currently declared.
- Date/timezone ambiguity because the app uses UTC timestamps while users may expect Tehran-local periods.
- Missing reliable expert performance fields beyond assigned request status counts.
- Missing customer/company fields for public requests without CRM `Customer` linkage.
- No SLA reporting in this branch.
- No priority reporting in this branch.
- Existing assignment-summary report includes SLA/response-time fields and should be treated as legacy/out-of-scope for the new reports.

## 12. Phased Roadmap

### Phase 12B: Backend Report Summary JSON API Only

- Add a new admin-only report overview endpoint.
- Implement period parsing and data aggregation.
- Return JSON sections matching the future workbook structure.
- Exclude SLA and priority.
- Add backend tests.
- No Excel, PDF, or UI.

### Phase 12C: Backend XLSX Export

- Add a deliberate XLSX dependency.
- Reuse Phase 12B report data service.
- Generate XLSX with the recommended sheets.
- Add content-type/download tests and sheet-name/content checks.
- No PDF or UI changes unless only wiring the endpoint contract in docs/tests.

### Phase 12D: AdminPanel Reports UI

- Add `گزارش‌ها` tab.
- Add weekly/monthly/yearly Excel download buttons.
- Implement loading/error states.
- No fake data.
- No PDF button.

### Phase 12E: Optional PDF Executive Summary

- Evaluate PDF dependency, Persian font embedding, RTL rendering, and page layout.
- Implement only a short executive summary if product approves.
- Do not make PDF a replacement for XLSX.

### Phase 12F: Final Smoke and Closure

- Run full frontend/backend verification.
- Manual smoke admin auth, report overview, XLSX download, empty data, invalid period, non-admin access, and large-ish fixture behavior.
- Document final accepted behavior.

## 13. Recommended Phase 12B Prompt

Copy-paste prompt:

```text
You are working on the Forwarder project.

We are now entering:

Phase 12B: Backend Report Summary JSON API Only

Goal:
Implement the backend JSON report summary for future admin reports. Do not implement Excel, PDF, or frontend UI in this phase.

Use the Phase 12A roadmap:
docs/phase-12a-admin-reports-export-audit-roadmap.md

Scope:
- Add an admin-only JSON endpoint:
  GET /api/admin/reports/overview?period=weekly|monthly|yearly
- Implement backend report summary service code.
- Add or update backend tests.
- Preserve existing API response shapes for all existing endpoints.

Do not:
- Implement XLSX export.
- Implement PDF export.
- Modify AdminPanel UI.
- Add frontend code.
- Add dependencies unless absolutely necessary for JSON only.
- Create migrations.
- Include SLA.
- Include response deadline.
- Include overdue/due-soon.
- Include priority metrics.
- Use visible `ارجاع شده` / `ارجاع‌شده` labels.
- Change request workflow.
- Change automatic assignment behavior.

Reporting period definitions:
- weekly: last 7 days including today
- monthly: current calendar month
- yearly: current calendar year

Use `ShipmentRequest.status` as the canonical status for reporting.
If `status_request_status` differs, document the risk but do not merge it into metrics unless needed for an existing fixture.

Required Persian labels:
- new -> جدید
- assigned -> در انتظار بررسی
- in_progress -> در حال بررسی
- quoted -> پیشنهاد ارسال‌شده
- waiting_for_customer -> منتظر مشتری
- won -> پذیرفته‌شده
- lost -> ردشده / از دست‌رفته
- closed -> مختومه
- missing expert -> بدون کارشناس
- missing fields -> ثبت نشده

Recommended JSON sections:
- summary
- requests_by_status
- transport_distribution
- location_distribution
- expert_performance
- customer_concentration
- request_details
- metadata

Tests:
- admin auth required
- non-admin forbidden
- invalid period returns 400
- weekly/monthly/yearly filtering works
- counts match fixtures
- JSON sections are present
- assigned label is `در انتظار بررسی`
- unassigned label is `بدون کارشناس`
- SLA/priority fields are absent
- empty report works

Documentation:
Create:
docs/phase-12b-admin-report-summary-json-api.md

Verification:
Run:
- npm.cmd run lint
- npm.cmd run build
- npm.cmd run check:structure
- python -m pytest -q
- git diff --check

Final report:
1. Changed files
2. Endpoint added
3. Runtime behavior changed? Yes/No and exact scope
4. Period definitions implemented
5. JSON sections implemented
6. SLA excluded? Yes/No
7. Priority excluded? Yes/No
8. API response shapes preserved? Yes/No
9. Tests added/updated
10. Test/build results
11. Whether Phase 12B is acceptable

Do not enter Phase 12C.
Do not implement Excel.
Do not implement PDF.
Do not modify AdminPanel UI.
```

## 14. Verification

- `npm.cmd run lint`: to be run after this documentation-only change.
- `npm.cmd run build`: to be run after this documentation-only change.
- `npm.cmd run check:structure`: to be run after this documentation-only change.
- `python -m pytest -q`: to be run after this documentation-only change; previous local session had Python/Pytest availability issues, so record any environment blocker if it repeats.
- `git diff --check`: to be run after this documentation-only change.
