# Phase 1B reporter shipment-detail permission remediation

## Final verification (2026-07-27)

P1B-UAT-003 is `CLOSED_VERIFIED` by the final full UAT. Browser/Mobile UAT is `YES`; persistent applied is `NO`. Earlier pending status below is historical.

Status: `PHASE_1B_REPORTER_PERMISSION_REMEDIATION_PASS_WITH_NOTES`

## Root cause

P1B-UAT-003 was `RC-A — Seed Permission Missing`. Shipment detail itself
required `operational_shipment.read`, which Reporter already had. The page also
loads route plans, timeline, and exception history concurrently. Those
read-only endpoints require `route_plan.read` and `route_exception.read`.
Reporter and Verifier lacked both, so a nested 403 collapsed the page.

## Least-privilege change

Only `route_plan.read` and `route_exception.read` were added to the Reporter
and Verifier Phase 1B seed memberships. No wildcard, admin, verify-for-Reporter,
replan, timeline mutation, exception management, or manual-resolution right
was added. Backend endpoint guards and frontend runtime code were unchanged.

| Role | View detail | Report | Verify | Replan | Timeline reconcile | Exception reconcile / resolve |
|---|---|---|---|---|---|---|
| Reporter | ALLOW | ALLOW | DENY | DENY | DENY | DENY |
| Verifier | ALLOW | DENY | ALLOW | DENY | DENY | DENY |
| Read-only | ALLOW | DENY | DENY | DENY | DENY | DENY |
| No permission | DENY | DENY | DENY | DENY | DENY | DENY |
| Inactive | DENY | DENY | DENY | DENY | DENY | DENY |

## Validation

- PostgreSQL 18.0, UTF8, loopback-only, canonical disposable database.
- Two official seed runs returned identical counts.
- Direct PostgreSQL permission/lifecycle and shipment-dedup tests: 2 passed,
  zero skipped.
- Backend full: 395 passed, 14 skipped. The added explicit-DSN test is the one
  new generic-suite skip and passed in the direct PostgreSQL gate.
- Frontend: 22 tests passed; lint 0 errors/11 warnings; build passed.
- Browser: Reporter detail/report desktop and 390px mobile passed; Verifier
  verify passed; Read-only view passed; No-permission and Inactive denied.
- Fatal console errors and unexpected 5xx: zero. React Router future-flag
  warnings remain notes.

P1B-UAT-003 is `FIXED_PENDING_FULL_UAT`. P1B-UAT-001 and P1B-UAT-002 retain
their prior statuses. Full Browser/Mobile UAT remains `NO`; persistent applied
remains `NO`. No migration, commit, push, or persistent application occurred.
