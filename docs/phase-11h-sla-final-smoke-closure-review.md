# Phase 11H: SLA Final Smoke & Closure Review

## 1. Scope

This phase is verification and closure review only. No runtime code, backend behavior, frontend behavior, API response shape, migration, UI, endpoint, priority override, or reporting feature was changed in this phase.

## 2. SLA Track Summary

| Phase | Result |
| --- | --- |
| 11A audit | Current SLA fields, calculation paths, priority behavior, and display gaps were audited. |
| 11B characterization | Existing SLA/priority behavior was locked with backend characterization tests and documentation. |
| 11C backend SLA policy foundation | Added `SlaPolicy`, migration, admin SLA policy service/API, fallback behavior, tests, and OpenAPI coverage. |
| 11D priority rules backend | Added initial priority service and public request integration based on `pickup_date`. |
| 11E policy-to-assignment integration | Wired SLA policies into assigned status transitions, direct assignment, request list/detail SLA status, and KPI counts. |
| 11F AdminPanel SLA UI | Added AdminPanel `SLA / مهلت پاسخ‌گویی` tab for list/create/edit/enable/disable. |
| 11G ExpertConsole SLA visibility | Added clearer SLA KPI card, request SLA badges, remaining-time display, and local SLA filter. |

## 3. Final Architecture

The SLA flow now works as follows:

1. Public request creation determines initial `priority` from `pickup_date`.
2. Admins define SLA policies with priority/status/shipping/transport scopes.
3. Assignment or status transition to `assigned` calculates `sla_due_at` from the best active policy.
4. If no matching active policy exists, the legacy 120-minute fallback is used.
5. Existing `sla_due_at` is preserved and not overwritten.
6. Expert APIs calculate SLA status centrally.
7. Expert Console shows SLA counts, per-request badges, and frontend-calculated remaining time.

## 4. Verification Results

| Check | Result |
| --- | --- |
| `npm.cmd run lint` | Passed with the existing 10 warnings. |
| `npm.cmd run build` | Passed with existing browserslist age and bundle-size warnings. |
| `npm.cmd run check:structure` | Passed. |
| `python -m pytest -q` | Blocked because `python` is not available in PATH in this environment. |
| `git diff --check` | Passed with line-ending warnings only. |

Commands for local completion:

```powershell
npm.cmd run lint
npm.cmd run build
npm.cmd run check:structure
python -m pytest -q
git diff --check
```

## 5. Migration/Database Review

The SLA migration exists at `backend/migrations/versions/20250529_add_sla_policy_table.py` in the normal migration directory.

Review result:

- Creates only the `sla_policy` table.
- Adds indexes for active flag, priority scope, and sort/name order.
- Uses `sa.BigInteger().with_variant(sa.Integer(), "sqlite")` for SQLite-compatible primary key behavior.
- Uses `Text` for `request_status_scope`, avoiding SQLite JSON portability issues.
- Uses standard SQLAlchemy column types that are compatible with SQLite tests and PostgreSQL-style deployments by inspection.
- Does not alter `shipment_request`.
- No `shipment_request.sla_policy_id` traceability column was added; this remains deferred.

## 6. Admin SLA Smoke

Live UI smoke was not completed because this environment does not provide a reachable full dev stack with admin authentication/backend data.

Static review confirmed:

- AdminPanel has an `SLA / مهلت پاسخ‌گویی` tab.
- The tab uses existing endpoints:
  - `GET /api/admin/sla-policies`
  - `POST /api/admin/sla-policies`
  - `PUT /api/admin/sla-policies/<id>`
  - `PATCH /api/admin/sla-policies/<id>/disable`
  - `PATCH /api/admin/sla-policies/<id>/enable`
- The UI supports list, empty state, create, edit, enable, and disable.
- Frontend validation covers missing name, positive response time, positive threshold, threshold not exceeding response time, status selection, and integer sort order.
- Existing AdminPanel tabs remain present: dashboard, users, referral rules, site settings.

Local smoke commands/checks to complete:

- Login as admin.
- Open AdminPanel.
- Open `SLA / مهلت پاسخ‌گویی`.
- Create normal and urgent policies.
- Edit one policy.
- Disable and enable one policy.
- Verify invalid minute/name validation.
- Switch through all non-SLA AdminPanel tabs.

## 7. Priority Smoke

Live request creation smoke was not completed in this environment.

Static/test review confirmed:

- `priority_service` maps missing, blank, or invalid pickup/loading date to `normal`.
- Pickup date today, past, or within 24 hours maps to `urgent`.
- Pickup date within 72 hours but beyond 24 hours maps to `high`.
- Pickup date beyond 72 hours maps to `normal`.
- `low` remains reserved for future manual/admin assignment.
- `shipment_service` calls `determine_initial_priority(normalized, now=timestamp)` during public request creation.

Relevant tests are present in `backend/tests/test_priority_service_contract.py` and `backend/tests/test_shipment_request_contract.py`.

## 8. SLA Assignment Smoke

Live assignment smoke was not completed in this environment.

Static/test review confirmed:

- Expert status update to `assigned` calls `sla_policy_service.assign_sla_due_at_if_needed`.
- Direct assignment calls `sla_policy_service.assign_sla_due_at_if_needed`.
- Existing `sla_due_at` is preserved by the service.
- Disabled policies are ignored by policy resolution.
- If no active matching policy exists, the 120-minute fallback is used.
- KPI/list/detail status calculation uses centralized SLA policy service paths.

Relevant tests are present in `backend/tests/test_sla_policy_contract.py` and `backend/tests/test_expert_assignment_referral_contract.py`.

## 9. Expert Console Smoke

Live Expert Console smoke was not completed in this environment.

Static review confirmed:

- `مهلت پاسخ‌گویی` card uses `kpis.sla.overdue` and `kpis.sla.due_soon`.
- Calm positive state renders when both counts are zero.
- Request cards render SLA badges for overdue, due soon, on time, and missing SLA.
- Remaining time is calculated from `request.sla_due_at` on the frontend.
- Local SLA filter supports `همه مهلت‌ها`, `نزدیک به مهلت`, and `گذشته از مهلت` without adding backend query params.
- Existing search, status filter, priority filter, refresh, and request actions remain in place.

Local smoke checks to complete:

- Login as expert.
- Open Expert Console.
- Verify card, badges, remaining time, local SLA filter, existing filters, refresh, and `مشاهده / خلاصه`.
- Check browser console for errors.
- Check mobile width for horizontal overflow.

## 10. RequestDetail Smoke

Live RequestDetail smoke was not completed in this environment.

Review status:

- RequestDetail was not changed in phases 11F-11H.
- Prior RequestDetail phase included null-safe location/cargo/SLA-style rendering.
- Expert Console still navigates to `/expert/requests/${request.id}` for `مشاهده / خلاصه`.

Local smoke checks to complete:

- Open RequestDetail from Expert Console.
- Verify SLA due date/status rendering.
- Verify null `sla_due_at` does not crash.
- Verify missing province/county/city details do not crash.
- Verify notes and status change behavior if practical.

## 11. Behavior Preservation

Review result:

- Public request submission behavior remains covered by existing contract tests by inspection.
- Domestic province-only submission remains covered by the prior contract test.
- International flow was not modified in this phase.
- Tracking was not modified in the SLA phases reviewed here.
- Admin user/referral/settings tabs remain wired in AdminPanel.
- ExpertConsole request actions remain wired.
- RequestDetail notes/status behavior was not modified in this phase.
- API response shapes were preserved; frontend typing was only made null-safe for already optional SLA values.

## 12. Known Deferred Items

- Priority manual override.
- Admin priority-rule management UI.
- Request-to-policy audit link.
- Advanced SLA reports.
- Real-time countdown/polling.
- Backend SLA status filter if needed later.
- Customer quote acceptance workflow.

## 13. Closure Decision

Decision: `SLA_TRACK_CODE_COMPLETE_PENDING_ENV_SMOKE`

Reason:

- Code review and static implementation review are clean.
- Frontend build/lint/structure checks pass.
- `git diff --check` passes.
- Pytest and meaningful end-to-end UI/API smoke could not be completed in this environment because `python` is unavailable in PATH and no full authenticated local stack/backend data is available.

The SLA track should not be marked `SLA_TRACK_CLOSED` until `python -m pytest -q` and the admin/expert/request-detail smoke checks pass in a local environment with the backend, database, and admin/expert login data available.
