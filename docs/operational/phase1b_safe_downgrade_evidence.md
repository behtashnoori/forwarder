# Phase 1B safe-downgrade evidence

Validation date: 2026-07-25. Environment: system Python 3.13.9, process-local UTF-8, isolated localhost-only PostgreSQL 18.0 UTF8. The public PostgreSQL service was identified and excluded.

## Migration chain

| Order | Revision | Down revision | Scope |
|---:|---|---|---|
| 1 | `20260729_operational_vertical_slice` | `20260728_add_quote_customer_response` | Phase 1A operational baseline |
| 2 | `20260730_multileg_route` | `20260729_operational_vertical_slice` | Multi-leg, replan, checkpoint, dependency, projected timeline, scoped idempotency |
| 3 | `20260801_route_exception` | `20260730_multileg_route` | Exception transition history and replay response |

Alembic reported one head: `20260801_route_exception`.

## Upgrade and empty downgrade

- Official-runner fresh base-to-head upgrade: passed.
- Phase 1A-to-head upgrade with a preserved Phase 1A organization row: passed.
- Empty head-to-`20260730` downgrade: passed.
- Empty `20260730`-to-Phase-1A downgrade: passed.
- Phase 1A schema equivalence: passed. The only raw dump difference was whitespace formatting in the restored `phase1a_validate_work_item_scope_v1()` body; object semantics and signatures were unchanged.
- Re-upgrade to head: passed.

## Guard defect and correction

Validation-first probes proved that non-null replay responses and non-default scoped-idempotency identity were previously removable. The existing revisions were changed only in downgrade predicates, before all DDL. Upgrade schema and domain behavior were not changed.

The final guard matrix covers RoutePlan versions/provenance, RouteLeg projected/actual state, checkpoints, dependencies, milestone ownership/projection, work-item linkage and transition state, scoped idempotency and replay responses, timeline reconciliation, replan provenance, and related audit/outbox transactions.

Rejected downgrades preserved Alembic revision, table/column/index/constraint/trigger/function counts, organization/idempotency row counts, and connection usability.

## Test and skip evidence

- PostgreSQL Phase 1A: 1 passed.
- PostgreSQL Phase 1B baseline: 1 passed.
- Exception race: 2 passed.
- Direct safe downgrade: 2 passed.
- Backend full: 357 passed, 12 skipped.
- Frontend: 10 passed.
- Lint: 0 errors, 12 warnings.
- Build: passed.

All 12 backend skips have explicit environment reasons. The PostgreSQL Phase 1A, Phase 1B, race, and safe-downgrade skips were directly covered on the disposable cluster.

Persistent database applied: **NO**.
