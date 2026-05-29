# Phase 10C: Admin Panel UI Redesign

## 1. Scope
This phase only redesigned the Admin Panel presentation layer in `src/pages/AdminPanel.tsx`. Backend behavior, API contracts, routing, authentication, permissions, and business logic were left unchanged.

## 2. Before
The previous admin panel was functional but visually plain. It used a basic header, compact tabs, simple metric cards, and dense distribution sections with limited hierarchy and polish.

## 3. UI Changes Made
- Redesigned the header with the title `پنل مدیریت`, a soft green `داشبورد مدیریتی` badge, the requested subtitle, and a blue admin/dashboard icon block.
- Added top action controls for notifications, current admin label, refresh, and logout while preserving logout behavior.
- Restyled the tab bar into a wide rounded RTL navigation bar with blue active accent.
- Redesigned KPI cards for total requests, recent requests, weekly trend, and unassigned requests using existing dashboard data.
- Added a secondary metric row using the same existing dashboard values without introducing new calculations or API calls.
- Redesigned status distribution into clean colored rows with count badges and status accents.
- Redesigned transport method distribution into clean rows with transport icons and count badges.
- Redesigned top provinces into a ranked list with trophy icon, blue ranking circles, province names, and request-count badges.
- Polished loading and empty dashboard states visually without changing the underlying branches.

## 4. Behavior Preservation
- Backend unchanged.
- API endpoints and response shapes unchanged.
- Auth/token behavior unchanged.
- Logout still clears `expert_user` and `expert_token` and returns to `/`.
- Routing unchanged.
- Tab state and switching behavior unchanged.
- UserManagement internals unchanged.
- ReferralRulesTab internals unchanged.
- SiteSettingsTab internals unchanged.
- Dashboard data fetching and dashboard calculations unchanged.
- Existing toast and redirect handling unchanged.

## 5. Responsive/RTL Notes
The page keeps `dir="rtl"`, uses a light responsive container, stacks header actions and dashboard sections on mobile, and uses responsive grids for desktop. Cards and rows are constrained and wrapped to avoid horizontal overflow.

## 6. Verification
- `npm.cmd run lint`: passed with existing warnings in shared UI/context files and unrelated pages.
- `npm.cmd run build`: passed.
- `npm.cmd run check:structure`: passed.
- `python -m pytest -q`: blocked because `python` is not available in PATH in this session.
- `git diff --check`: passed.
- Manual smoke checks: blocked because a reliable local dev server/browser smoke path was not available in this session.

## 7. Deferred Items
- UserManagement internal redesign.
- ReferralRulesTab redesign.
- SiteSettingsTab redesign.
- Shared design primitives.
- App-wide theme alignment.
- Backend/reporting changes.
