# P1B-UAT-005 milestone correction authorization remediation

## Final verification (2026-07-27)

P1B-UAT-005 is `CLOSED_VERIFIED` by the final full UAT. Browser/Mobile UAT is `YES`; persistent applied is `NO`. Earlier pending status below is historical.

## Result

- Status: `PASS_WITH_NOTES`
- Root cause: RC-A and RC-B/service-path enforcement
- Canonical correction permission: `milestone.correct`
- Backend guard before/after: `checkpoint.report` / `milestone.correct`
- Frontend guard before/after: `checkpoint.report` / `milestone.correct`
- Permission escalation: none
- Migration/schema: none
- Commit/stage/push/deploy: none
- Browser/Mobile UAT: `NO` (targeted retest only)
- P1B-UAT-005: `FIXED_PENDING_FULL_UAT`
- Persistent applied: `NO`

## Permission contract

| Action | Canonical permission | Reporter | Correct-capable role |
|---|---|---|---|
| Report | `checkpoint.report` | ALLOW | As granted |
| Correct | `milestone.correct` | DENY | ALLOW |
| Verify/re-verify | `checkpoint.verify` | DENY self | As separately granted |
| Replan | `route_plan.replan` | DENY | As separately granted |
| Exception action | `route_exception.manage` | DENY | As separately granted |

The official seed grants Reporter `checkpoint.report` but not
`milestone.correct`. It grants the seeded Verifier both `checkpoint.verify` and
`milestone.correct`. Correction does not imply verification or any other
permission.

## Zero-side-effect denial

| Control | Before defect | After remediation |
|---|---:|---:|
| Reporter Correct controls | 6 | 0 |
| Reporter correction response | success | 403 `FORBIDDEN_OPERATION` |
| Corrected event delta | 1 | 0 |
| Correction audit delta | 1 | 0 |
| Outbox delta | not recorded | 0 |
| Version delta | not recorded | 0 |
| Actual/projected delta | not recorded | 0 |
| Idempotency rows | not recorded | 0 |
| Reporter privileged mutations | 1 | 0 |

The backend permission check occurs before shipment lookup, locking,
idempotency reservation, validation, event creation, audit/outbox creation, or
commit. Tenant isolation, inactive membership failure, self-verification
denial, reason validation, stale-version behavior, and append-only history are
unchanged.

## Validation

| Test | Passed | Skipped | Failed |
|---|---:|---:|---:|
| Targeted backend correction authorization | 2 | 0 | 0 |
| Seeded PostgreSQL Reporter boundary + shipment dedup | 2 | 0 | 0 |
| Backend full | 396 | 14 | 0 |
| Frontend behavioral | 31 | 0 | 0 |
| ESLint | 0 errors | n/a | 0 |
| Build | PASS | 0 | 0 |
| Secret scan | findings 0 | 0 | 0 |

The 14 backend skips are the existing conditional baseline; the explicit
PostgreSQL tests were run separately and had zero skips. ESLint reported the
existing 11 unrelated warnings. The Vite build retained its existing chunk-size
warning.

## Targeted browser retest

| Control | Desktop 1440 x 900 | Mobile 390 x 844 |
|---|---|---|
| Reporter Correct controls | 0 | 0 |
| Reporter Report | PASS | visible |
| Refresh/direct URL | Correct remains 0 | Correct remains 0 |
| Direct correction denial | 403; all side-effect deltas 0 | same backend contract |
| Correct-capable Correct control | 6 initially | 5 after one valid correction |
| Missing reason | denied | contract retained |
| Valid correction | PASS; exactly one event/audit | control usable |
| Page overflow/off-viewport action | 0 | 0 |
| Fatal console errors / unexpected 5xx | 0 / 0 | 0 / 0 |

Evidence files are numbered `30` through `34` in
`docs/operational/evidence/phase1b_browser_mobile_uat/`.

## Defect status and next step

| ID | Current |
|---|---|
| P1B-UAT-001 | `FIXED_PENDING_FULL_UAT` |
| P1B-UAT-002 | `RESOLVED_HARNESS_ALIGNMENT_PENDING_FULL_UAT` |
| P1B-UAT-003 | `FIXED_PENDING_FULL_UAT` |
| P1B-UAT-004 | `FIXED_PENDING_FULL_UAT` |
| P1B-UAT-005 | `FIXED_PENDING_FULL_UAT` |

This gate is not the full Browser/Mobile UAT. The full UAT must restart from
the beginning. No persistent database was contacted or changed.

`PHASE_1B_MILESTONE_CORRECTION_AUTHORIZATION_REMEDIATION_PASS_WITH_NOTES`
