# Phase 13G: Pre-Deploy Manual Smoke and Residual Cleanup

## 1. Scope
Pre-deploy smoke and minimal residual cleanup only. No features were added, no redesign was performed, and backend/database/API/workflow/report behavior was not changed.

## 2. Baseline Verification
- `npm.cmd run lint`: passed with existing unrelated warnings in shared UI/context files and `UserManagement`.
- `npm.cmd run build`: passed.
- `npm.cmd run check:structure`: passed.
- `python -m pytest -q`: blocked because `python` is not available in PATH in this session.
- `git -c safe.directory=D:/Projects/webapp/15-forwarder/forwarder diff --check`: passed. Git reported only line-ending normalization warnings.

## 3. Public Landing Smoke
- HTTP smoke: `/` served with status 200.
- Static inspection confirmed service-oriented landing copy, acceptable top-level structure, visible tracking area, about/contact anchors, domestic/international request buttons, and footer without fake social links.
- Full manual browser/mobile interaction was not available in this sandbox.

## 4. Domestic Request Smoke
- Static inspection confirmed the domestic request flow opens through `LocationForm`.
- Province-only origin/destination remains supported.
- Optional county/city details remain expandable.
- Transport dropdown styling and RTL readability improvements are present.
- Cargo details remain optional, and numeric values are stored as input strings so `0` is not dropped by UI state.
- Native date fields remain unchanged.
- Live test submission was not attempted because a staging/live backend smoke environment was not available.

## 5. International Request Smoke
- Static inspection confirmed the international request flow opens through `LocationForm`.
- International location fields, transport dropdown, optional cargo details, and native date fields remain present.
- Live test submission was not attempted because a staging/live backend smoke environment was not available.

## 6. Success and Tracking Smoke
- HTTP smoke: `/customer/track/INVALID-CODE` served with status 200.
- Static inspection confirmed success state tracking-code visibility, copy button, tracking action, new request action, and home action.
- Invalid tracking copy is clear.
- No unsupported SMS/email/Bale notification promise was found in the public success/tracking target files.

## 7. Expert Smoke
- HTTP smoke: `/expert` served with status 200.
- Static inspection confirmed clear request labels, `مشاهده جزئیات`, `assigned` mapped to `در انتظار بررسی`, understandable RequestDetail status-change helper text, and readable timeline rendering.
- RequestDetail residual visible SLA display was found and removed as presentational cleanup.
- Authenticated expert login, status change, note creation, and live detail navigation were not manually exercised in this sandbox.

## 8. Admin Smoke
- HTTP smoke: `/admin` served with status 200.
- Static inspection confirmed manager-friendly dashboard labels, `بدون کارشناس`, status distribution mappings, reports/users/automatic-distribution/site-settings tabs, and automatic distribution wording.
- Authenticated admin login, tab interaction, and logout were not manually exercised in this sandbox.

## 9. Reports Smoke
- Static inspection confirmed the XLSX service defines the expected sheets:
  - `خلاصه مدیریتی`
  - `وضعیت درخواست‌ها`
  - `توزیع نوع حمل`
  - `توزیع مبدا و مقصد`
  - `عملکرد کارشناسان`
  - `مشتریان و درخواست‌ها`
  - `روند زمانی`
  - `جزئیات درخواست‌ها`
- Existing backend tests include assertions that report payloads/workbooks exclude visible `ارجاع شده` / `ارجاع‌شده`, SLA, and priority columns/fields.
- Live weekly/monthly/yearly Excel downloads were not manually exercised because authenticated staging smoke was not available.

## 10. Residual Wording Sweep
- `ارجاع شده`: not found in inspected visible target files.
- `ارجاع‌شده`: not found in inspected visible target files.
- `assigned`: appears only as internal code/type/API naming or mapped to `در انتظار بررسی` in visible UI.
- `SLA`: visible RequestDetail SLA badge/rows were found and removed. Remaining SLA references are internal/backend/docs or pre-existing non-target documentation.
- `اولویت` / `priority`: no visible target UI was found after the sweep; remaining references are internal types/backend/docs/tests.
- Unsupported notification wording: no public promise for SMS/email/Bale notification was found in the target public flow.

## 11. Residual Cleanup
- Removed visible RequestDetail SLA badge and request-info SLA rows.
- Kept backend fields, API response shape, database fields, and workflow untouched.

## 12. Behavior Preservation
- Backend unchanged.
- Database unchanged.
- API payloads unchanged.
- Workflow unchanged.
- Automatic assignment unchanged.
- Reports behavior unchanged.

## 13. Deferred Items
- Jalali date picker.
- Backend-supported expert workload analytics.
- Richer manager dashboard.
- Notification channels only after formal approval.
- Custom date range reports.

## 14. Closure Decision
READY_FOR_COMMIT_PENDING_STAGING_SMOKE

Code/build/static route smoke is clean and the residual visible SLA issue was fixed. Full staging smoke with authenticated users, real submission, status changes, notes, and Excel downloads remains pending.
