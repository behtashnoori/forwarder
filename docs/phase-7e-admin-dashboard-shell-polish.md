# Phase 7E: Admin Dashboard Shell Polish

## 1. Scope

This phase only polished the AdminPanel dashboard shell and dashboard tab presentation in `src/pages/AdminPanel.tsx`.

No backend code, API client code, OpenAPI files, routing, dependencies, auth/security behavior, global styling, shared UI primitives, or unrelated frontend pages were changed.

## 2. Before

- The admin dashboard was functional and already used centralized `fetchAdminDashboard`.
- Metric cards were basic and used a raw gray dashboard shell.
- Loading state was a simple centered spinner.
- Status, transport, and top province sections were readable but visually plain.
- The admin area is tabbed and includes mutation-heavy child areas; those were intentionally left untouched.

## 3. UI Changes Made

- Improved the admin shell header with dashboard framing, badges, subtitle/context, and a clearer refresh action.
- Reworked dashboard metric cards with consistent spacing, icon containers, labels, values, and helper text.
- Improved status summary scanability with bordered rows/cards and compact badges.
- Improved transport method summary with the same card rhythm as status summary.
- Improved top provinces with a ranked list treatment and count badges.
- Improved dashboard loading and no-data/empty states.
- Improved mobile and desktop spacing using single-column mobile layout and responsive desktop grids.
- Kept helper components local to `AdminPanel.tsx`; no shared primitives were created.

## 4. Behavior Preservation

- API helper unchanged: `fetchAdminDashboard(token)` is still used.
- Route behavior unchanged.
- Data fetching behavior unchanged.
- Auth/token behavior unchanged, including missing/invalid token handling.
- Error handling and toast behavior unchanged.
- Tab behavior and tab values unchanged.
- Dashboard calculations unchanged.
- Status label mapping behavior unchanged.
- Transport method label mapping behavior unchanged.
- `top_provinces` conditional rendering unchanged.
- `UserManagement` untouched.
- `ReferralRulesTab` untouched.
- `SiteSettingsTab` untouched.
- Backend/API unchanged.

## 5. Responsive/RTL Notes

- Dashboard metrics stack into a single column on mobile and expand to a four-column desktop grid.
- Status and transport summaries use single-column mobile cards and two-column desktop grids.
- Top province rows stack safely on small screens and align horizontally on larger screens.
- Persian/RTL flow is preserved with wrapping-friendly flex layouts and `break-words` on long labels.

## 6. Verification

- `npm.cmd run lint`: passed with 13 existing warnings in unrelated files.
- `npm.cmd run build`: passed; existing Browserslist and chunk-size warnings remain.
- `npm.cmd run check:structure`: passed.
- `python -m pytest -q`: passed, `86 passed, 724 warnings`.
- `git diff --check`: passed with existing CRLF warnings.

## 7. Deferred Items

- Shared `PageHeader` / `SummaryBand` / `SectionCard` primitives.
- UserManagement UI polish.
- ReferralRulesTab polish.
- SiteSettingsTab polish.
- Expert console polish.
- Full design system extraction.
