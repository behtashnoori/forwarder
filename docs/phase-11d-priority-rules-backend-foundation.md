# Phase 11D: Priority Rules Backend Foundation

## 1. Scope

This phase adds a backend foundation for automatic initial shipment request priority assignment.

No frontend code, AdminPanel UI, ExpertConsole UI, RequestDetail UI, customer-facing UI, manual priority override UI/API, priority-rule management UI, migration, or SLA policy API behavior was changed.

## 2. Problem

Experts should not have to manually classify every request one by one. The backend now has a small priority service that can assign an initial priority from request urgency while preserving the existing normal fallback.

## 3. Source Data Review

- Public shipment payload already supports `pickup_date`.
- `LocationForm.tsx` sends `pickup_date` when the user provides a pickup/loading date.
- `backend/services/shipment_service.py` already parses `pickup_date` with `parse_date_or_none`.
- `ShipmentRequest` already stores `pickup_date` as a nullable `Date`.
- The field is optional, so missing/blank/invalid dates must safely fall back to `normal`.

This is reliable enough for v1 automatic initial priority because it is already part of the public request data path and database model.

## 4. Priority Rule Design

Implemented v1 rules:

- missing pickup/loading date -> `normal`
- pickup/loading date today, in the past, or within 24 hours -> `urgent`
- pickup/loading date within 72 hours but beyond 24 hours -> `high`
- pickup/loading date beyond 72 hours -> `normal`
- `low` is preserved as an allowed value but reserved for future manual/admin assignment

Supported service inputs:

- `datetime`
- `date`
- ISO date string such as `2026-05-30`
- ISO datetime string such as `2026-05-31T12:00:00`
- mapping payload keys: `pickup_date`, `loading_date`, `requested_pickup_date`

Invalid or blank date values return `normal`.

## 5. Backend Changes

- Added `backend/services/priority_service.py`.
- Integrated automatic initial priority assignment into `backend/services/shipment_service.py`.
- Replaced the hardcoded request creation priority with `priority_service.determine_initial_priority(normalized, now=timestamp)`.
- Added focused priority service tests.
- Added shipment request creation tests for no-date normal fallback and near-date automatic priority.

## 6. Behavior Preservation

- No frontend changed.
- No AdminPanel UI changed.
- No ExpertConsole UI changed.
- No RequestDetail UI changed.
- No API response shape changed.
- Existing no-date request creation remains `normal`.
- Far-future pickup date request creation remains `normal`.
- Priority filter behavior is preserved by existing Phase 11B exact-match tests.
- SLA policy APIs from Phase 11C are unchanged.
- Existing SLA deadline calculation is not connected to priority in this phase.

## 7. Deferred Items

- Manual priority override API.
- Admin priority-rule UI.
- Priority override audit log.
- Connecting SLA due date calculation to policies based on priority.
- ExpertConsole SLA filter/display changes.
- Automatic `low` priority rule if product needs it later.
- Admin-managed priority rule configuration.

## 8. Verification

- Backend Python compile check for updated files: passed using bundled Codex Python.
- `npm.cmd run lint`: passed with 10 existing warnings and 0 errors. Warnings are the existing React fast-refresh/shared-export warnings plus the existing `UserManagement.tsx` hook dependency warning.
- `npm.cmd run build`: passed. Vite reported the existing browserslist age notice and chunk-size warning.
- `npm.cmd run check:structure`: passed.
- `python -m pytest -q`: blocked because `python` is not available in PATH.
- `git diff --check`: passed. Git emitted line-ending notices, but no whitespace errors.
