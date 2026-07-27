# Migration and rollback

## Supported migration-head inspection

Use the repository's configured, metadata-only command:

```text
python -m alembic -c backend/migrations/alembic.ini heads
```

The verified result is exactly one head: `20260801_route_exception`. This command does not apply migrations. Upgrade and downgrade remain restricted to the supported `backend.migration_cli` workflow; raw `alembic upgrade` is not allowed. Persistent applied remains `NO`.

`20260730_multileg_route` is the single child of the Phase 1A head. It enriches route plans/legs and creates checkpoint/dependency tables with explicit constraints. Existing plans receive active status and version 1 via server defaults; there is no startup backfill.

The database strategy uses stable composite parent tuples and foreign keys:

- checkpoint `(route_leg_id, route_plan_id)` references the same plan's leg;
- dependency predecessor and successor tuples reference checkpoints in the declared plan;
- milestone `(checkpoint_id, route_plan_id)` references a checkpoint in the same plan;
- route-exception shipment/organization, plan/shipment, and checkpoint/plan tuples are database-enforced.

The core migration was validated on a disposable PostgreSQL 18.0 cluster on 2026-07-24. The follow-up `20260801_route_exception` revision was validated on 2026-07-25 through fresh supported-runner upgrades of two guard-compatible disposable databases. Alembic reported one head and `current=head`.

The follow-up revision adds transition-history and idempotent-response fields. Its downgrade rejects populated reconciliation history or replay responses with `SAFE_DOWNGRADE_GUARD`. The final safe-downgrade gate passed on disposable PostgreSQL 18; no persistent database migration was applied.

The historical core-revision downgrade is fail-closed when Phase 1B operational data exists. Its guard runs before destructive DDL and covers checkpoint/dependency state, replan provenance, projected/actual leg state, timeline reconciliation, changed plan versions, Phase 1B milestone/work-item ownership, and scoped idempotency. The follow-up guard covers exception transition history and stored replay responses. Direct PostgreSQL rejection tests leave revision, schema-object counts, data counts, and connection usability unchanged.

The supported fresh-bootstrap path is `python -m backend.migration_cli upgrade --confirm`; it widens the historical Alembic version table before applying revisions. Raw historical Alembic bootstrap can encounter the legacy `alembic_version varchar(32)` capacity limit and is not the supported runner. Historical migrations were not speculatively rewritten.

## Persistent rollback procedure

1. Identify the exact environment and database; obtain independent approval for any persistent target.
2. Require a tested backup and restore path. The fail-closed guard is not a backup substitute.
3. Quiesce application writers and verify active sessions according to the environment change plan.
4. Run `python -m backend.migration_cli current` and confirm the expected revision before any change.
5. Distinguish an empty/Phase-1A-compatible downgrade from a data-bearing downgrade. Data-bearing Phase 1B downgrade is intentionally rejected.
6. Before a real rollback, export, migrate, or obtain explicit approval to remove every Phase 1B-only data category. Do not bypass the guard with `DROP ... CASCADE`.
7. After prerequisites and approval, use Alembic one revision at a time: `20260801_route_exception` to `20260730_multileg_route`, then to `20260729_operational_vertical_slice`.
8. After each step verify Alembic current, tables, columns, indexes, constraints, triggers, functions, row counts, and application transaction usability.
9. If a downgrade fails, stop. PostgreSQL transactional DDL and the pre-DDL guards should preserve revision/schema/data; verify that evidence before retrying.
10. The re-upgrade path is the supported runner: `python -m backend.migration_cli upgrade --confirm`, followed by schema verification, reconciliation, and smoke tests.

No command in this runbook was executed against a persistent, integration, staging, production, or server database during the final gate.
