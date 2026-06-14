# Phase 13E: Expert and Admin Operational Clarity

## 1. Scope
This phase improves expert/admin operational clarity only. It adjusts visible labels, helper copy, action wording, and dashboard explanation without changing backend workflow, database, API payloads, reports, or public pages.

## 2. Customer Feedback Addressed
- Expert request viewing clarity.
- Expert status-change clarity.
- RequestDetail navigation and operations clarity.
- Admin dashboard metric clarity.
- Expert workload visibility assessment.
- Status wording consistency.

## 3. Changes Made
- `src/pages/ExpertConsole.tsx`: changed in-progress wording to `در حال پیگیری` and changed the primary request action from `مشاهده / خلاصه` to `مشاهده جزئیات`.
- `src/pages/RequestDetail.tsx`: changed in-progress wording to `در حال پیگیری` and added short helper copy to the operations/status-change card.
- `src/pages/AdminPanel.tsx`: improved manager-facing dashboard copy and metric labels, including `کل درخواست‌ها`, `درخواست‌های جدید`, `حجم هفته اخیر`, and `بدون کارشناس`.

## 4. Expert UI Findings
- ExpertConsole already showed tracking code, customer, route, transport method, status badge, and request actions.
- The primary action is now clearer as `مشاهده جزئیات`.
- RequestDetail back navigation already returns to the expert console through the existing PageNav behavior.
- Status-change values and behavior were preserved; only helper text and visible labels were clarified.
- Timeline rendering continues to use the existing data source and Persian action/status labels.

## 5. Admin UI Findings
- Dashboard cards are now more manager-friendly and explain request volume and missing-expert counts more clearly.
- Status distribution uses Persian business labels and avoids raw internal codes where mappings exist.
- Existing admin dashboard data does not expose per-expert workload analytics in this frontend view.
- Automatic distribution wording remains `توزیع خودکار درخواست‌ها`.

## 6. Behavior Preservation
- Backend unchanged.
- Database unchanged.
- API payloads unchanged.
- Workflow unchanged.
- Automatic assignment unchanged.
- Reports unchanged.
- Public pages unchanged.

## 7. Label Rules
- `assigned` is displayed as `در انتظار بررسی`.
- Missing expert is displayed as `بدون کارشناس`.
- No visible `ارجاع شده` / `ارجاع‌شده` wording was added.
- Automatic assignment is displayed as `توزیع خودکار درخواست‌ها`.

## 8. Deferred Items
- Backend-supported expert workload analytics.
- Richer admin operational dashboard.
- Dashboard charts.
- Manager-level daily summary.
- SLA/priority only if product decision changes later.

## 9. Verification
- `npm.cmd run lint`: passed with existing unrelated warnings in shared UI/context files and `UserManagement`.
- `npm.cmd run build`: passed.
- `npm.cmd run check:structure`: passed.
- `python -m pytest -q`: blocked because `python` is not available in PATH in this session.
- `git -c safe.directory=D:/Projects/webapp/15-forwarder/forwarder diff --check`: passed. Git reported only line-ending normalization warnings.
- Smoke checks: local dev server served `/expert` and `/admin` with HTTP 200. Full authenticated manual smoke checks were limited in this sandbox.
