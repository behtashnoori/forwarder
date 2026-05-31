# Phase 12D: AdminPanel Reports UI

## 1. Scope

This phase adds AdminPanel UI for downloading XLSX reports only. It does not change backend behavior, Excel generation, PDF export, request workflow, automatic assignment, migrations, or unrelated pages.

## 2. UI Added

Added a new AdminPanel tab:

- `گزارش‌ها`

Placement:

- After `داشبورد`
- Before `مدیریت کاربران`

Added report cards:

- `گزارش هفتگی`
  - Button: `دانلود Excel هفتگی`
- `گزارش ماهانه`
  - Button: `دانلود Excel ماهانه`
- `گزارش سالانه`
  - Button: `دانلود Excel سالانه`

Each card has a short description and a dedicated download button. While a report is downloading, only that button is disabled and shows `در حال آماده‌سازی فایل...`. Download failures use the existing toast pattern.

## 3. API Usage

The UI calls:

- `GET /api/admin/reports/export.xlsx?period=weekly`
- `GET /api/admin/reports/export.xlsx?period=monthly`
- `GET /api/admin/reports/export.xlsx?period=yearly`

Implementation:

- `src/lib/api.ts`
  - Added `downloadAdminReportXlsx(token, period)`.
  - Sends the admin auth token as `Authorization: Bearer ...`.
  - Fetches the XLSX response as a blob.
  - Reads filename from `Content-Disposition` when available.
  - Falls back to `forwarder-report-{period}.xlsx`.
- `src/components/AdminReportsTab.tsx`
  - Creates an object URL, triggers browser download, and revokes the object URL.

## 4. Behavior Preservation

- Backend unchanged in this phase.
- Excel service unchanged in this phase.
- PDF not implemented.
- Dashboard tab unchanged.
- Users tab unchanged.
- Automatic distribution tab unchanged.
- Site settings tab unchanged.
- Auth/logout behavior unchanged.

## 5. Exclusions

Confirmed exclusions:

- No SLA.
- No priority.
- No PDF.
- No fake report rows or sample metrics.
- No visible `ارجاع شده` / `ارجاع‌شده`.

## 6. Responsive/RTL Notes

- AdminPanel remains `dir="rtl"`.
- Report cards use a responsive grid: stacked on mobile and three columns on wider screens.
- The tab list now adapts across mobile, tablet, and desktop to avoid horizontal overflow.
- Styling follows the existing AdminPanel card/button pattern.

## 7. Verification

- `npm.cmd run lint`: passed with 10 existing warnings.
- `npm.cmd run build`: passed with existing Browserslist/chunk-size warnings.
- `npm.cmd run check:structure`: passed.
- `python -m pytest -q`: blocked because `python` is not on PATH in this shell.
- `git diff --check`: passed; Git reported CRLF normalization warnings only.
- Manual smoke checks: not run in this session because no running backend/browser session was started.
