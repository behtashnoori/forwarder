# Phase 11F: Admin SLA Management UI

## 1. Scope

This phase adds AdminPanel SLA policy management UI only.

No backend behavior, database schema, migration, SLA calculation logic, ExpertConsole UI, RequestDetail UI, public/customer page, or API response shape was changed.

## 2. UI Added

- Added a new AdminPanel tab: `SLA / مهلت پاسخ‌گویی`.
- Added a policy list powered by the admin SLA policy API.
- Added create/edit form for SLA policies.
- Added enable/disable actions.
- Added empty state: `هنوز قانونی برای SLA تعریف نشده است.`
- Added loading and error states.
- Kept layout RTL and responsive with stacked mobile layout.

The form includes:

- `نام قانون`
- `اولویت`
- `وضعیت‌های مشمول`
- `نوع حمل`
- `روش حمل`
- `مهلت پاسخ‌گویی`
- `آستانه نزدیک به مهلت`
- `ترتیب اعمال`
- `فعال`

## 3. API Usage

The UI uses the existing Phase 11C backend endpoints:

- `GET /api/admin/sla-policies`
- `POST /api/admin/sla-policies`
- `PUT /api/admin/sla-policies/<id>`
- `PATCH /api/admin/sla-policies/<id>/disable`
- `PATCH /api/admin/sla-policies/<id>/enable`

Minimal typed helpers were added to `src/lib/api.ts`:

- `fetchAdminSlaPolicies`
- `createAdminSlaPolicy`
- `updateAdminSlaPolicy`
- `disableAdminSlaPolicy`
- `enableAdminSlaPolicy`

## 4. Behavior Preservation

- Backend unchanged.
- Database unchanged.
- SLA calculation unchanged.
- ExpertConsole unchanged.
- RequestDetail unchanged.
- Other AdminPanel tabs preserved.
- Auth/logout behavior unchanged.
- Existing dashboard data fetching unchanged.

## 5. Validation

Frontend validation covers:

- required `نام قانون`
- positive `مهلت پاسخ‌گویی`
- positive `آستانه نزدیک به مهلت`
- `آستانه نزدیک به مهلت` must not exceed `مهلت پاسخ‌گویی`
- at least one included status
- integer `ترتیب اعمال`

Backend errors are surfaced through the existing toast/error message pattern.

## 6. Responsive/RTL Notes

- The SLA tab is RTL.
- The create/edit form and list stack on mobile.
- Policy fields wrap inside cards to avoid horizontal overflow.
- The AdminPanel tab bar now uses five columns on large screens and two columns on smaller screens.

## 7. Verification

- `npm.cmd run lint`: passed with 10 existing warnings and 0 errors.
- `npm.cmd run build`: passed. Vite reported the existing browserslist age notice and chunk-size warning.
- `npm.cmd run check:structure`: passed.
- `python -m pytest -q`: blocked because `python` is not available in PATH.
- `git diff --check`: passed. Git emitted line-ending notices, but no whitespace errors.
- Smoke checks: blocked. The frontend build passes, but a persistent local dev server could not be kept running from this sandboxed shell session, and no live backend/admin token was available for create/edit/enable/disable API smoke.

## 8. Deferred Items

- ExpertConsole SLA remaining-time display.
- SLA status filter.
- Priority manual override.
- Priority-rule management UI.
- SLA reports.
- Request-to-policy audit link.
