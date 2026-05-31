# Expert Console Remove Presentational SLA

## 1. Scope

This phase only removes presentational SLA UI and non-functional header controls from `src/pages/ExpertConsole.tsx`.

## 2. Reason

SLA policy behavior is not structurally implemented in this branch, so showing SLA monitoring and deadline priority UI in the Expert Console is misleading.

## 3. Removed UI

- SLA summary card.
- SLA overdue warning strip.
- Request-level SLA due date display.
- Fake/non-functional header chips/buttons.
- Non-functional notification bell.
- Inert profile menu items that did not perform real actions.

## 4. Preserved Behavior

- Backend unchanged.
- API unchanged.
- Request fetching unchanged.
- Search/filter unchanged.
- Priority filter unchanged.
- Refresh unchanged.
- Request actions unchanged.
- RequestDetail navigation unchanged.

## 5. Icon Safety

- All remaining JSX icons are imported.
- Unused icon imports were removed.
- Build verification passed without undefined icon errors.

## 6. Verification

- `npm.cmd run lint`: passed with existing warnings outside this cleanup.
- `npm.cmd run build`: passed.
- `npm.cmd run check:structure`: passed.
- `python -m pytest -q`: could not run because `python` is not on PATH; the project virtualenv points to a missing interpreter, and the bundled Python does not include pytest.
- `git diff --check`: passed.
- Smoke checks: source inspection confirmed the removed SLA/header labels and icon references are no longer present in `ExpertConsole.tsx`; browser-based login smoke was not run because the request did not include credentials/session setup.
