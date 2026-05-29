# Phase 11G: Expert Console SLA Display Integration

## 1. Scope

This phase only improves SLA visibility in the Expert Console. It does not change backend behavior, database schema, SLA policy calculation, routing, AdminPanel, RequestDetail, public/customer pages, or API response shapes.

## 2. UI Changes Made

| Area | Change |
| --- | --- |
| SLA summary card | Renamed the operational card to `مهلت پاسخ‌گویی` and kept the existing `گذشته از مهلت` and `نزدیک به مهلت` KPI counts. |
| Positive SLA state | Shows `همه درخواست‌ها در محدوده مجاز پاسخ‌گویی هستند.` when both SLA KPI counts are zero. |
| Request-level SLA badges | Each request card now shows `گذشته از مهلت`, `نزدیک به مهلت`, `در محدوده مجاز`, or `مهلت ثبت نشده`. |
| Remaining-time display | When `sla_due_at` exists, the request card shows a simple frontend-calculated remaining time or `از مهلت گذشته`. |
| SLA filter | Added a local-only SLA filter for `همه مهلت‌ها`, `نزدیک به مهلت`, and `گذشته از مهلت`; it does not send new backend query params. |

## 3. Data Used

The UI uses only existing Expert Console data:

- `kpis.sla.overdue`
- `kpis.sla.due_soon`
- `request.sla_due_at`
- `request.sla_status`
- `request.priority`

Remaining time is computed on the frontend from `request.sla_due_at`. It updates when the page data refreshes.

## 4. Behavior Preservation

- Backend unchanged.
- API response shape unchanged.
- AdminPanel unchanged.
- RequestDetail unchanged.
- Request fetching unchanged.
- Search behavior unchanged.
- Existing status filter behavior unchanged.
- Existing priority filter behavior unchanged.
- Request actions such as `مشاهده / خلاصه`, `ارجاع به من`, and `شروع پیگیری` unchanged.
- Auth/logout behavior unchanged.

## 5. Null Safety

If `sla_due_at` is missing or null, the request card renders `مهلت ثبت نشده` and does not attempt date math. If `sla_status` is missing while `sla_due_at` exists, the badge falls back to the safe on-time presentation. Invalid dates render `مهلت نامعتبر` instead of crashing.

## 6. Deferred Items

- Backend SLA status filter.
- Real-time countdown/polling.
- Priority manual override.
- SLA reports.
- Request-to-policy audit display.

## 7. Verification

| Check | Result |
| --- | --- |
| `npm.cmd run lint` | Passed with the existing 10 warnings. |
| `npm.cmd run build` | Passed with existing browserslist age and bundle-size warnings. |
| `npm.cmd run check:structure` | Passed. |
| `python -m pytest -q` | Blocked because `python` is not available in PATH in this environment. |
| `git diff --check` | Passed with line-ending warnings only. |
| Manual smoke checks | Not completed; the local dev server could not remain reachable from this environment, and expert login/backend data was not available. |
