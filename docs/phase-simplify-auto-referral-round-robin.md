# Simplify Automatic Referral Round Robin

## 1. Scope

This phase simplifies the user-facing wording around assignment/referral and verifies that new shipment requests are automatically distributed between active experts in round-robin order.

No SLA, priority, reporting, export, migration, public-page redesign, API response shape, or database value rename is included in this phase.

## 2. Product Decision

- Referral means automatic distribution among active experts.
- The default assignment method is round-robin.
- Internal `assigned` remains unchanged.
- Visible `ارجاع شده` / `ارجاع‌شده` is removed from admin/expert UI.
- User-facing `assigned` labels use `در انتظار بررسی`.

## 3. UI Changes

- `src/pages/AdminPanel.tsx`
  - Renamed the tab from `قوانین ارجاع` to `توزیع خودکار درخواست‌ها`.
  - Reworded admin dashboard copy from referral-focused wording to automatic assignment/distribution wording.
  - Replaced unassigned/referral labels with `بدون کارشناس` and `در انتظار تخصیص خودکار یا دستی`.
- `src/components/ReferralRulesTab.tsx`
  - Renamed the section to `توزیع خودکار درخواست‌ها`.
  - Added simple helper text explaining that new requests are automatically and cyclically distributed between active experts.
  - Removed wording that suggests admins must define complex matching rules for normal operation.
- `src/pages/ExpertConsole.tsx`
  - Replaced user-facing assignment action/toast wording with `اختصاص`.
  - `assigned` remains displayed as `در انتظار بررسی`.
- `src/pages/RequestDetail.tsx`
  - Replaced assignment timeline label with `تخصیص`.
  - `assigned` remains displayed as `در انتظار بررسی`.

## 4. Backend Behavior

- Active experts are selected in `backend/referral_engine.py` by `ExpertUser.is_active == True` and role in `expert` or `business_expert`, ordered by `ExpertUser.id`.
- Global round-robin state is derived from `ReferralAssignmentLog.assigned_at`: the expert with the oldest last assignment is selected, and experts with no assignment history are preferred first. `ReferralAutoAssignState(id=1)` is still created/locked for concurrency compatibility.
- Public request creation triggers automatic assignment through `backend/services/shipment_service.py`, which calls `assign_request_with_referral()` after the request is committed.
- Assignment sets `ShipmentRequest.assigned_to` and keeps internal status as `assigned`.
- Inactive experts are skipped by the assignable expert query and by pool filtering.
- If no active expert exists, the request remains unassigned with status `new`; public request creation still succeeds.
- Existing logs/notifications are preserved: automatic assignment creates `ReferralAssignmentLog`, `ExpertConsoleLog`, `ExpertConsoleNotification`, and the existing gamification workflow step when applicable.
- Manual assignment remains preserved through the existing manual assignment endpoint/tests.

## 5. Tests Added or Updated

- `backend/tests/test_expert_assignment_referral_contract.py`
  - Added public request creation coverage for global round-robin: request 1 goes to expert 1 and request 2 goes to expert 2.
  - Added inactive expert skip coverage.
  - Added no-active-expert fallback coverage, including unchanged public API response shape and no assignment side effects.
  - Existing tests continue to cover matching referral-rule assignment, fallback assignment, logs/notifications, internal `assigned`, and manual assignment contracts.

## 6. Behavior Preservation

- API response shapes unchanged.
- Internal status values unchanged.
- Internal `assigned` database value preserved.
- Manual assignment preserved.
- Admin/expert request pages still compile.
- Public/customer pages untouched except for inspecting the request creation trigger path.
- SLA, priority, reporting, and export behavior not changed.
- No migrations created.

## 7. Verification

- `npm.cmd run lint`: passed with 10 existing warnings.
- `npm.cmd run build`: passed with existing Browserslist/chunk-size warnings.
- `npm.cmd run check:structure`: passed.
- `python -m pytest -q`: blocked in this shell because `python` is not on PATH, the local `.venv` launcher points to a missing base Python install, and the bundled Python does not include `pytest`.
- Targeted backend pytest attempted with `.venv\Scripts\python.exe` and bundled Python; both were blocked by the same Python environment issue.
- `git diff --check`: passed; Git reported CRLF normalization warnings only.

## Manual Smoke Checks

Not run in this session because backend pytest/dev-server Python execution is blocked by the local Python environment. Manual verification should confirm:

1. AdminPanel loads.
2. Visible `ارجاع شده` / `ارجاع‌شده` is gone.
3. Referral section wording is clear as automatic request distribution.
4. Two new requests distribute to expert 1 then expert 2.
5. Inactive experts are skipped.
6. ExpertConsole loads and shows `در انتظار بررسی` where an assigned label is needed.
7. RequestDetail opens without console errors.
