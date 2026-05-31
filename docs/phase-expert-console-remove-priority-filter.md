# Expert Console Remove Priority Filter

## 1. Scope

This phase only removes priority-related UI and filtering from `src/pages/ExpertConsole.tsx`.

## 2. Reason

The business flow in this branch does not use request priority. Showing a priority filter or priority labels in the Expert Console is misleading because experts should work from the active request status, search, and request details instead.

## 3. Removed UI

- Priority dropdown
- Priority dropdown options
- Priority-only decorative request badge
- Priority-only local state, request parameter handling, and helper functions

## 4. Preserved Behavior

- Backend unchanged
- API unchanged
- Request fetching unchanged, except priority is no longer sent as a filter
- Search unchanged
- Status filters unchanged
- Refresh unchanged
- Pagination unchanged
- Request actions unchanged
- RequestDetail navigation unchanged

## 5. Verification

- `npm.cmd run lint`: passed with existing warnings in shared UI/context files and `UserManagement.tsx`; no lint errors.
- `npm.cmd run build`: passed. Vite reported the existing Browserslist age notice and chunk-size warning.
- `npm.cmd run check:structure`: passed.
- `python -m pytest -q`: could not run because `python` is not available in this shell. Both local virtualenv launchers point to a missing Python install, and the bundled Python does not have `pytest` installed.
- `git diff --check`: passed.
- Static ExpertConsole check: passed; no priority labels, priority options, priority state, priority request parameter, or priority helper functions remain in `src/pages/ExpertConsole.tsx`.
- Browser smoke checks: attempted against the local dev server at `http://127.0.0.1:8080/expert`, but the in-app browser automation runtime failed to start in this Windows sandbox. Manual browser confirmation is still needed.
