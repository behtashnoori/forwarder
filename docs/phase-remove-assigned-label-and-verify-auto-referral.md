# Remove Assigned Label and Verify Automatic Referral Rules

## 1. Scope

This phase removes the confusing user-facing assigned wording from admin/expert screens and audits/verifies automatic referral behavior for new shipment requests.

## 2. Product Decision

- Internal `assigned` status remains unchanged.
- Visible `ارجاع شده` / `ارجاع‌شده` wording is removed from admin/expert UI.
- When a user-facing label is needed, `assigned` is shown as `در انتظار بررسی`.

## 3. Assigned Label Changes

- `src/pages/ExpertConsole.tsx`
  - Replaced assigned tab/filter/status label with `در انتظار بررسی`.
  - Kept internal status values and filters as `assigned`.
- `src/pages/RequestDetail.tsx`
  - Replaced assigned status label with `در انتظار بررسی`.
  - Aligned expert action/status labels with the current Persian wording.
- `src/pages/AdminPanel.tsx`
  - Replaced assigned dashboard status label with `در انتظار بررسی`.
  - Aligned related admin status labels used in dashboard summaries.

## 4. Referral Rule Audit

- Referral rule model/table: `ReferralRule` / `referral_rule`.
- Referral rule state table: `ReferralRuleState` / `referral_rule_state`.
- Referral assignment audit table: `ReferralAssignmentLog` / `referral_assignment_log`.
- Admin UI location: `src/pages/AdminPanel.tsx`, tab value `referral-rules`, rendering `src/components/ReferralRulesTab.tsx`.
- Admin API routes: `backend/routes/admin_panel.py`, `/api/admin/referral-rules` and `/api/admin/referral-rules/preview`.
- Backend service for referral-rule CRUD/preview: `backend/services/referral_service.py`.
- Backend assignment engine: `backend/referral_engine.py`.
- Public request trigger point: `backend/services/shipment_service.py` calls `assign_request_with_referral()` after public request creation is committed.
- Matching criteria now used by active referral rules:
  - `shipping_type`
  - `transport_method`, checked against legacy, domestic, and international transport method fields
  - `origin_province`
  - `destination_province`
- Multiple matching rules: active rules are evaluated by ascending `priority`, then `name`; the first matching rule with an assignable expert is used.
- Matching actions:
  - `direct_assign` selects the configured active expert.
  - `pool_assign` selects from configured active experts using `round_robin` or `least_workload`.
- No matching rule: existing global time-based round-robin fallback is preserved.
- No active assignable expert: request remains unassigned.
- Assignment side effects:
  - sets `assigned_to`
  - keeps internal status value as `assigned`
  - creates `ReferralAssignmentLog`
  - creates `ExpertConsoleLog`
  - creates expert notification

## 5. Referral Rule Changes

Automatic referral was already triggered after public request creation, but the engine ignored stored referral rules. This phase updates `backend/referral_engine.py` so active matching `ReferralRule` records are applied before the existing global round-robin fallback.

Tests were strengthened in:

- `backend/tests/test_expert_assignment_referral_contract.py`
- `backend/tests/test_referral_engine.py`

Added/updated coverage:

- matching active referral rule assigns an eligible expert
- public shipment request creation triggers matching referral-rule assignment
- no matching referral rule preserves the existing global round-robin fallback
- referral assignment creates audit/log rows

## 6. Behavior Preservation

- Backend status values unchanged.
- API response shapes unchanged.
- Manual assignment flows preserved.
- Existing global round-robin fallback preserved.
- Admin and expert pages preserved.
- Unrelated pages untouched.
- Priority UI was not reintroduced.

## 7. Verification

- `npm.cmd run lint`: passed with existing warnings in shared UI/context files and `UserManagement.tsx`; no lint errors.
- `npm.cmd run build`: passed. Vite reported the existing Browserslist age notice and chunk-size warning.
- `npm.cmd run check:structure`: passed.
- `python -m pytest -q`: could not run because `python` is not available in this shell. The local virtualenv launcher points to a missing Python install, and the bundled Python does not have `pytest` installed.
- `git diff --check`: passed.
- Bundled Python `py_compile` for changed backend files: passed.
- Static source checks:
  - no visible `ارجاع شده` / `ارجاع‌شده` remains in `src`
  - no priority UI references remain in `src/pages/ExpertConsole.tsx`
- Manual smoke checks: not completed in-browser in this environment.
