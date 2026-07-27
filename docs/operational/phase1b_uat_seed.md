# Phase 1B UAT seed

## Final status note (2026-07-27)

The final disposable UAT completed successfully. Browser/Mobile UAT is `YES`; five viewports and 22/22 workflows passed; persistent applied is `NO`. The four repository-local duplicate SQLite artifacts were retired after the local SQLite configuration test passed before and after deletion. Earlier pending statements below are historical chronology only.

## Command and safety boundary

Run only against a fresh, loopback-only disposable PostgreSQL database whose
name begins with `forwarder_phase1b_uat` or `phase1b_uat`:

```text
APP_ENV=uat
FORWARDER_UAT_PASSWORD=<local synthetic password>
python -m backend.operational_cli seed-phase1b-uat --confirm
```

The command rejects missing/production-like environments, non-PostgreSQL
targets, non-loopback database hosts, and database names outside the allow-list.
SQLite is accepted only for an in-memory `TESTING` application. The password is
required but is never included in the result summary.

The seed executes in one transaction and rolls back on failure. Stable identity
keys make reruns idempotent. Existing synthetic users retain their password hash
rather than receiving a new hash on every execution.

## Synthetic graph

The seed creates two isolated organizations and eight synthetic users:

- Organization A: admin, operations manager, reporter, independent verifier,
  read-only, no-Phase-1B-permission, and inactive membership.
- Organization B: independent admin.

Each organization receives an accepted quote, operational shipment, active
route-plan revision 1, three ordered legs, six checkpoints, eighteen checkpoint
milestones, and chain/fan-out/fan-in dependencies. Organization A also includes
two completed checkpoints, deterministic reported/verified event history,
future checkpoints, one blocked checkpoint, and open overdue and
dependency-blocked work items.

No production copy, customer identity, real email, real credential, or real
carrier data is used.

## Validation evidence

On 2026-07-25 a fresh disposable PostgreSQL 18 UTF8 database reached Alembic
head `20260801_route_exception`. Two consecutive seed runs returned the same
summary:

| Entity | Count |
|---|---:|
| Organizations | 2 |
| Users/memberships | 8 |
| Shipments | 2 |
| Active route plans | 2 |
| Route legs | 6 |
| Checkpoints | 12 |
| Dependencies | 12 |
| Milestones | 36 |
| Milestone events | 12 |
| Open work items | 2 |

Direct checks found zero cross-organization work items, zero cross-plan
checkpoint/dependency references, and zero orphan checkpoint milestones.
Focused seed tests cover a fresh database, duplicate-free rerun, failure
rollback, production rejection, remote-host rejection, wrong-name rejection,
wrong-engine rejection, tenant separation, and graph shape.

### Disposable PostgreSQL evidence rerun (2026-07-25)

The Windows recovery rerun used PostgreSQL 18.0 with UTF8 encoding, a unique
loopback-only port, and a token-scoped data directory outside the repository.
`pg_ctl start` used `-w -t 60`, a token-scoped server log, `DEVNULL` stdin, and
ordinary token-scoped files for stdout/stderr; no parent-owned pipe was left
open. A separate startup probe passed and cleaned up before the evidence
cluster was created.

| Phase | Duration | Result |
|---|---:|---|
| Startup probe | 7.495 s | PASS; resources remaining 0 |
| Evidence cluster startup | 8.386 s | PASS |
| Fresh main migration | 6.417 s | PASS; `20260801_route_exception`, pending 0 |
| First seed and direct integrity checks | 4.537 s | PASS |
| Second seed and direct integrity checks | 4.038 s | PASS; counts and canonical IDs stable |
| Fresh rollback-database migration | 5.143 s | PASS |
| Injected failure, rollback checks, and normal seed | 3.366 s | PASS |
| Cleanup | 1.936 s | PASS; resources remaining 0 |

Both successful seed runs contained 2 organizations, 8 users, 8 memberships,
2 shipments, 2 active route plans, 6 route legs, 12 checkpoints, 12
dependencies, 36 milestones, 1 exception-ready work item, and 2 total work
items. Direct PostgreSQL checks found zero duplicate active plans or revisions,
zero cross-organization or cross-plan references, zero orphan milestone foreign
keys, and zero partial graphs. Chain, fan-in, fan-out, completed, future,
blocked, inactive-membership, and empty-permission test data were present.

The controlled failure was injected after partial writes through the seed's
existing creation helper. The seed transaction rolled back to zero rows for
all canonical seed entities, the connection remained usable, and a subsequent
normal seed created the complete graph.

Direct Phase 1B PostgreSQL regression replay, local backend/frontend smoke,
and browser/mobile UAT remain pending. The four repository database artifacts
are tracked and are deferred to Phase 1B final review. Persistent applied = NO.

## Local runtime database boundary

UAT is process-environment-only: it does not automatically load repository
environment files, requires an explicit `DATABASE_URL`, and accepts PostgreSQL
only. It never falls back to the local SQLite runtime database. Local
development uses the platform user-data directory outside the repository when
neither `DATABASE_URL` nor an absolute, external
`FORWARDER_LOCAL_DB_PATH` is supplied. Test applications remain isolated on
their explicit temporary or in-memory databases.
