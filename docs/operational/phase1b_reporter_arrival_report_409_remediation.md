# P1B-UAT-006 Reporter arrival 409 root cause and remediation

## Final verification (2026-07-27)

P1B-UAT-006 is `CLOSED_VERIFIED` by targeted token `P1B-UAT-20260727044111047492` and the final full UAT. Browser/Mobile UAT is `YES`; persistent applied is `NO`. Earlier pending status below is historical.

Date: 2026-07-26

## Result

- Status: `PHASE_1B_REPORTER_ARRIVAL_REPORT_409_REMEDIATION_PASS_WITH_NOTES`
- Classification: `TEST_FIXTURE_SELECTION_DEFECT` (RC-A)
- P1B-UAT-006: `RESOLVED_TEST_FIXTURE_ALIGNMENT_PENDING_FULL_UAT`
- Product defect / seed defect / migration-schema change: no
- Test defect: yes; semantic reportable-arrival selection replaces a fixed row
- Browser/Mobile UAT: `NO` (targeted retest only)
- Persistent applied: `NO`
- Commit/stage/push/deploy: none

## Sanitized reproduction and pre-request state

The captured 409 is reproducible when fixed checkpoint sequence 3 has already
been reported. Its code is `INVALID_CHECKPOINT_TRANSITION`: an arrived
checkpoint cannot accept a second distinct arrival report. The old test chose
sequence 3 without checking state/history, and the idempotent seed does not
reset mutable workflow rows. On a genuinely fresh database the same row
returned 200, ruling out product, seed, uniqueness, concurrency, and
idempotency regressions.

| Control | Fresh value |
|---|---|
| Active RoutePlan / revision / status | YES / 1 / active |
| Checkpoint sequence / status | 3 / planned |
| Milestone type / state | checkpoint_arrival / planned |
| Existing report/arrival events | 0 / 0 |
| Checkpoint current/supplied version | 1 / 1 |
| Matching idempotency/audit/outbox | 0 / 0 / 0 |
| Reportable before request | YES |

The repaired helper requires the active plan, checkpoint status `planned` or
`approaching`, arrival milestone state `planned`, zero report/correct/verify
events, and uses the selected row's current version.

## Report semantics

| Scenario | Actual | Side effects | Result |
|---|---|---|---|
| First valid report | 200 | event/audit/outbox 1/1/1; version +1 | PASS |
| Same-key replay | idempotent 200 | duplicate event/audit/outbox 0 | PASS |
| Second distinct report | 409 `INVALID_CHECKPOINT_TRANSITION` | 0 | PASS |
| Stale version | 409 `STALE_MILESTONE_VERSION` | 0 | PASS |
| Reporter Correction | 403 `FORBIDDEN_OPERATION` | 0 | PASS |
| Authorized Correction | 201 | corrected event/audit/outbox 1/1/1 | PASS |

Denied/conflict requests left milestone/checkpoint version and state,
actual/projected values, events, audits, outbox, work items, and idempotency
rows unchanged. The transaction remained clean and reusable.

## Verification

| Test | Collected | Passed | Skipped | Failed |
|---|---:|---:|---:|---:|
| Shipment deduplication (fresh PostgreSQL) | 1 | 1 | 0 | 0 |
| Reporter permission (fresh PostgreSQL) | 1 | 1 | 0 | 0 |
| Correction authorization (fresh PostgreSQL) | 1 | 1 | 0 | 0 |
| Backend full | 410 | 396 | 14 conditional | 0 |
| Frontend reporter/milestone targeted | 18 | 18 | 0 | 0 |

PostgreSQL 18 was UTF8 and loopback-only. The official runner reached
`20260801_route_exception` with zero pending migrations. Seed counts were
organizations 2, users 8, shipments 2, route plans 2, route legs 6,
checkpoints 12, dependencies 12, milestones 36, milestone events 12, and open
work items 2.

## Targeted browser retest

| Control | Desktop | Mobile 390 x 844 | Result |
|---|---|---|---|
| Reporter arrival report | `Arrival recorded.` | persisted | PASS |
| History after reload | reported visible | reported visible | PASS |
| Reporter Correct controls | 0 | 0 | PASS |
| Direct Correction denial | PostgreSQL: 403 | same contract | PASS |
| Horizontal overflow | 0 | 0 | PASS |
| Fatal console / unexpected 5xx | 0 / 0 | 0 / 0 | PASS |

This was not Full Browser/Mobile UAT. That gate must restart from the beginning.
