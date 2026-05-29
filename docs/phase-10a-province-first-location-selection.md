# Phase 10A: Province-first Location Selection

## 1. Scope
This phase changes the domestic shipment request location UX to province-first selection. Origin and destination require only province selection; county and city remain available as optional extra details.

## 2. Previous Behavior
The domestic request form displayed province, county, and city selectors for both origin and destination by default. Frontend validation required all six domestic location fields, and backend validation rejected domestic submissions when county or city IDs were missing.

## 3. New Behavior
- Origin province is required.
- Destination province is required.
- Origin county and city are optional.
- Destination county and city are optional.
- Optional county/city selectors are hidden behind `+ جزئیات بیشتر (شهر و شهرستان)` after a province is selected.
- Province-only domestic requests can be submitted.

## 4. Frontend Changes
- `src/components/LocationForm.tsx`
  - Added separate expand/collapse state for origin and destination optional location details.
  - Changed domestic validation to require only origin and destination province.
  - Sends `null` for empty optional county/city IDs while preserving the existing payload keys.
  - Keeps full-detail submission behavior when county/city are selected.
- `src/lib/api.ts`
  - Allows optional domestic county/city payload IDs to be `null`.

## 5. Backend/API Changes
- `backend/services/shipment_service.py`
  - Domestic validation now requires origin and destination province IDs.
  - Domestic county/city IDs are parsed only when provided; blank or `null` values are stored as `NULL`.
  - Existing API response shape and error format are preserved.
- No migration was created because the current `ShipmentRequest` model already defines domestic province/county/city columns as nullable.

## 6. Behavior Preservation
- Domestic request flow is preserved and now accepts province-only locations.
- International request flow was not redesigned or otherwise changed.
- Tracking behavior was not changed.
- API response shape was not changed.
- Admin, expert, customer dashboard, CRM, routing, theme, and landing page service cards were untouched.

## 7. Verification
- `npm.cmd run lint`: blocked by environment permission error while scanning `backend/.pytest_cache` (`EPERM: operation not permitted, scandir`).
- `npm.cmd run build`: passed.
- `npm.cmd run check:structure`: passed.
- `python -m pytest -q`: blocked because `python` is not available in PATH; the project `.venv` points to a missing Python install, and the bundled Python does not have `pytest` installed.
- `git diff --check`: passed.
- Smoke checks: blocked in this session because the dev server did not remain reachable on `127.0.0.1:5173`; backend submission smoke could not be completed without a runnable Python/pytest/backend environment.
