# Phase 0.1 Runtime and Migration Safety

## Purpose and scope

Phase 0.1 separates application construction and process startup from schema and seed changes. It does not implement `OperationalShipment`, `RouteLeg`, `Milestone`, pricing, CRM, or customer workflow changes.

## Previous behavior and root cause

Historically `create_app`, `backend.wsgi`, and `backend.run` could reach startup helpers that pinged the database, ran Alembic, seeded reference data, or created fallback tables. Alembic also obtained application state through Flask, which made imports capable of re-entering startup and nested Alembic contexts.

## Current contract

- `backend.create_app()` configures extensions and routes; normal startup never migrates, seeds, or backfills.
- `create_app(skip_startup=True)` additionally suppresses the test-only `db.create_all()` compatibility behavior.
- `backend.runtime.create_runtime_app()` rejects truthy `AUTO_MIGRATE_ON_STARTUP` before app construction.
- Production startup performs only read-only readiness inspection and fails fast when the database is unavailable, migrations are pending, or critical tables are missing.
- Non-production may start non-ready, but emits a generic warning.
- Alembic `env.py` imports metadata and configuration directly; it does not construct Flask.
- Schema changes are allowed only through `python -m backend.migration_cli upgrade --confirm`.

## Read-only inspection and credentials

`current`, `check`, and readiness use `MigrationContext`, `ScriptDirectory`, `SELECT 1`, and SQLAlchemy inspection. They do not create the Alembic version table or domain tables. Public health payloads contain only aggregate state, revision identifiers, and missing critical-table names. Passwords, complete URLs, raw SQL, stack traces, and driver messages are not returned. CLI targets omit username, password, query, and fragment.

## Health contracts

- `/api/health/ping`: process liveness only; no database dependency.
- `/api/health`: one controlled database `SELECT 1`; HTTP 200 or 503.
- `/api/health/ready`: database, current/head revisions, pending state, and critical-table inspection; HTTP 200 or 503; no writes.

## Foreign-key decision

The candidate `20260729_deduplicate_foreign_keys` migration was removed after review. Repository migrations create exactly one named `ON DELETE SET NULL` FK for each `shipment_request.iran_entry_port_id` and `iran_entry_province_id`. No schema inventory or incident evidence proves a general duplicate. A global irreversible sweep was therefore unsafe. If a specific environment later proves duplication, use an allowlisted, dry-run-first repair tool backed by `pg_constraint` evidence; do not reintroduce a global migration.

## Decision log

| Finding | Source | Decision | Action / verification |
|---|---|---|---|
| `skip_startup` still allowed test schema creation | Startup reviewer | Accepted | Gate compatibility `create_all`; regression test |
| CLI contract lacked direct coverage | Startup/Test reviewers | Accepted | Test 0/1/2 codes, confirmation and masking |
| Health mixed DB and table readiness | Health reviewer | Accepted | Keep health DB-only; readiness owns table checks |
| Revision IDs absent from readiness | Health reviewer | Accepted | Add sanitized current/head arrays |
| Ports 8000/5000/5001 conflicted | Entrypoint reviewer | Accepted | Canonical default and bindings are 5001 |
| Windows process control was not ownership-safe | Entrypoint reviewer | Accepted | Add PS 5.1 launcher with port/executable/command checks |
| Global FK cleanup lacked evidence | FK reviewer | Accepted | Remove candidate migration and related tests |
| Six canonical documents absent | Documentation reviewer | Accepted | Create this document set; remove superseded drafts |

## Validation limits

- PostgreSQL disposable cycle: `NOT_RUN_ENVIRONMENT_UNAVAILABLE` on the Phase 0.1 workstation.
- Docker runtime validation: `NOT_RUN_DOCKER_CLI_UNAVAILABLE`; Compose/Docker files receive static validation only.
- SQLite cannot validate the full historical chain because `20240920_add_transport_method_to_shipment_request` uses unsupported historical `ALTER COLUMN` behavior.
- No Phase 0.1 change or migration has been applied to Production.

## Evidence and related documents

Code: `backend/__init__.py`, `backend/runtime.py`, `backend/migration_runtime.py`, `backend/migration_cli.py`, `backend/migrations/env.py`, and `backend/routes/health.py`.

- [Database revision runbook](phase0_1_database_revision_runbook.md)
- [Backend entrypoint](phase0_1_backend_entrypoint.md)
- [ADR-011](adr/ADR-011-explicit-migration-execution.md)
