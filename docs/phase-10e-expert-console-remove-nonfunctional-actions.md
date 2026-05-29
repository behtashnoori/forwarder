# Phase 10E: Expert Console Remove Non-functional Header Actions

## 1. Scope
This phase only removed or neutralized non-functional header actions from the Expert Console. No backend, API, routing, auth, request list, filters, status tabs, or request actions were changed.

## 2. Problem
The Expert Console header included dashboard-style chips/buttons that looked clickable but had no real behavior. This could mislead users into expecting customer, tariff, notification, or view-switching features that were not implemented.

## 3. Items Reviewed
| Item label | Current behavior | Decision | Reason |
|---|---|---|---|
| داشبورد | Looked like a button, no action | Convert to label | It only described the current page context. |
| درخواست‌ها | Looked clickable, no action | Remove | Real request filtering already exists in status tabs below. |
| مشتریان | Looked clickable, no action | Remove | No real tab, route, or handler exists. |
| تعرفه‌ها | Looked clickable, no action | Remove | No real tab, route, or handler exists. |
| Notification bell | Looked clickable, no notification behavior | Remove | No notification action was wired. |
| Refresh | Calls `loadRequests` | Keep | Real refresh behavior exists. |
| Expert selector/menu | Opened a menu with non-functional items | Convert to label | Kept expert identity visible without fake menu actions. |

## 4. Changes Made
- Removed non-functional header chips for `درخواست‌ها`, `مشتریان`, and `تعرفه‌ها`.
- Removed the presentational notification bell.
- Converted `داشبورد` into a non-clickable `داشبورد درخواست‌ها` label.
- Converted the expert dropdown into a non-clickable expert identity label.
- Preserved the real refresh button.
- Preserved `PageNav` navigation/logout behavior.

## 5. Behavior Preservation
- Backend unchanged.
- API unchanged.
- Auth unchanged.
- Request fetching unchanged.
- Filters/search unchanged.
- Status tabs unchanged.
- Refresh unchanged.
- Request actions unchanged.

## 6. Verification
- `npm.cmd run lint`: passed with existing unrelated warnings.
- `npm.cmd run build`: passed.
- `npm.cmd run check:structure`: passed.
- `python -m pytest -q`: blocked because `python` is not available in PATH in this session.
- `git diff --check`: passed.
- Manual smoke checks: blocked because a reliable local dev server/browser smoke path was not available in this session.
