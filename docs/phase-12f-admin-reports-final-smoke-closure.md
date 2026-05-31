# Phase 12F: Admin Reports Final Smoke and Closure

## 1. Scope

This phase is verification and closure only. No report features, PDF export, backend behavior, frontend behavior, API response shapes, migrations, request workflow, automatic assignment behavior, or AdminPanel redesign were added in this phase.

## 2. Reports Track Summary

- Phase 12A audited the current admin/reporting data sources and created the reports/export roadmap.
- Phase 12B added the admin-only JSON overview endpoint:
  - `GET /api/admin/reports/overview?period=weekly|monthly|yearly`
- Phase 12C added the admin-only XLSX export endpoint:
  - `GET /api/admin/reports/export.xlsx?period=weekly|monthly|yearly`
- Phase 12D added the AdminPanel `گزارش‌ها` tab with weekly, monthly, and yearly Excel download buttons.

PDF is intentionally skipped. The first reporting version is Excel-only.

## 3. Final Architecture

- AdminPanel renders a `گزارش‌ها` tab after `داشبورد`.
- The frontend download helper calls the XLSX export endpoint with the admin auth token.
- The XLSX export endpoint returns an attachment with the Excel MIME type and period-based filename.
- The XLSX service reuses the Phase 12B report overview service.
- Report metrics have one source of truth in `backend/services/admin_report_overview_service.py`.
- The XLSX layer only transforms the shared JSON report payload into workbook sheets.

## 4. Dependency Review

- `openpyxl>=3.1,<4.0` is recorded in:
  - `requirements.txt`
  - `backend/requirements.txt`
- The bundled Python runtime can import `openpyxl`; observed version: `3.1.5`.
- The project `python` command is not available in this shell.
- The bundled Python runtime does not include Flask or pytest, so this environment cannot confirm full pytest import behavior. `ModuleNotFoundError: No module named 'openpyxl'` was not reproduced with the bundled Python; the blocker here is missing Flask/pytest or missing `python` launcher.

## 5. Verification Results

- `npm.cmd run lint`: passed with 10 existing warnings.
- `npm.cmd run build`: passed with existing Browserslist/chunk-size warnings.
- `npm.cmd run check:structure`: passed.
- `python -m pytest -q`: blocked because `python` is not on PATH in this shell.
- Bundled Python pytest attempt: blocked because bundled Python has no `pytest`.
- Bundled Python backend import check: blocked because bundled Python has no `flask`.
- `git diff --check`: passed; Git reported CRLF normalization warnings only.

## 6. Backend/API Smoke

Live backend/API smoke was not completed in this shell because there is no runnable backend test/runtime environment:

- `python` is not on PATH.
- Bundled Python has `openpyxl` but lacks Flask and pytest.

Static/code-path confirmation:

- JSON route exists in `backend/routes/admin_panel.py`.
- XLSX route exists in `backend/routes/admin_panel.py`.
- Both routes are protected with `@require_role('admin')`.
- Invalid periods are handled through the shared Phase 12B period validation error path.
- Contract tests exist in `backend/tests/test_admin_panel_read_contract.py` for auth, invalid period, overview response sections, XLSX headers, workbook opening, sheet names, labels, exclusions, and empty reports.

## 7. XLSX File Smoke

Live generated-file smoke was not completed because backend execution is blocked in this shell.

Static/code-path confirmation:

- `backend/services/admin_report_xlsx_service.py` creates these sheets:
  - `خلاصه مدیریتی`
  - `وضعیت درخواست‌ها`
  - `توزیع نوع حمل`
  - `توزیع مبدا و مقصد`
  - `عملکرد کارشناسان`
  - `مشتریان و درخواست‌ها`
  - `روند زمانی`
  - `جزئیات درخواست‌ها`
- Empty arrays still create sheets with headers.
- Headers are bolded, header rows are frozen, columns are best-effort auto-sized, and right-to-left sheet view is enabled.
- Contract tests assert workbooks open with `openpyxl.load_workbook`.

## 8. AdminPanel Smoke

Browser smoke was not completed because no live backend/browser session was started for this verification-only phase.

Static/code-path confirmation:

- `src/pages/AdminPanel.tsx` includes the `گزارش‌ها` tab after `داشبورد`.
- `src/components/AdminReportsTab.tsx` renders weekly/monthly/yearly Excel download cards and buttons.
- The UI uses the existing toast pattern for friendly download errors.
- Per-button loading state is implemented with `در حال آماده‌سازی فایل...`.
- Existing tabs remain present:
  - `داشبورد`
  - `مدیریت کاربران`
  - `توزیع خودکار درخواست‌ها`
  - `تنظیمات سایت`

## 9. Label/Exclusion Checks

Confirmed by code inspection and test coverage:

- No SLA report columns are added to the JSON/XLSX report feature.
- No priority report columns are added to the JSON/XLSX report feature.
- No PDF was implemented.
- No fake data is rendered in the reports UI.
- Visible `ارجاع شده` / `ارجاع‌شده` labels are excluded from the report feature.
- `assigned` is labeled as `در انتظار بررسی`.
- Missing/unassigned expert is labeled as `بدون کارشناس`.
- Missing fields are labeled as `ثبت نشده`.
- Customer phone/company appear only in the admin-only export path.
- Secrets, tokens, and password hashes are not exported.

## 10. Behavior Preservation

Confirmed by code scope:

- Existing dashboard tab is preserved.
- Existing users tab is preserved.
- Existing automatic distribution tab is preserved.
- Existing site settings tab is preserved.
- Auth/logout flow is unchanged.
- Request workflow is unchanged.
- Automatic assignment behavior is unchanged.
- ExpertConsole was not changed during the reports UI/export phases.
- RequestDetail was not changed during the reports UI/export phases.
- Public/customer pages were not changed.

## 11. Deferred Items

- Optional PDF executive summary.
- Custom date range.
- Scheduled email reports.
- Larger data export optimization.
- Charts inside AdminPanel if needed later.
- Full live backend/API/browser smoke in an environment with project Python, Flask, pytest, and a running backend.

## 12. Closure Decision

`REPORTS_TRACK_CODE_COMPLETE_PENDING_ENV_SMOKE`

Reason: lint/build/structure/diff checks pass, `openpyxl` is recorded and importable in the bundled runtime, and the reports architecture is implemented with tests. However, full pytest and live API/browser/download smoke are blocked in this shell by the unavailable project Python runtime and missing Flask/pytest in the bundled Python.
