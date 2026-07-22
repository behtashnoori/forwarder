# Phase 0.1 Database Revision Runbook

## Safety contract

Startup, liveness, health, readiness, `current`, and `check` never change schema or data. Only an explicit, reviewed `upgrade --confirm` may write schema. A verified backup is a precondition for Production migration; this document does not authorize Production access.

## Commands and exit codes

Commands work from any current directory when the repository package is importable; Alembic paths are resolved from `backend/migration_runtime.py`.

| Command | Outcome | Exit |
|---|---|---:|
| `python -m backend.migration_cli current` | inspection succeeds | 0 |
| `current` | connection/runtime failure | 1 |
| `python -m backend.migration_cli check` | current equals all heads | 0 |
| `check` | pending revisions | 2 |
| `check` | connection/runtime failure | 1 |
| `python -m backend.migration_cli upgrade` | missing confirmation; no write | 2 |
| `python -m backend.migration_cli upgrade [revision] --confirm` | success | 0 |
| confirmed upgrade | runtime failure | 1 |

Output identifies only dialect, host, and database. It never prints username, password, query, complete URL, raw driver error, or stack trace.

## Procedure

1. Verify repository branch/commit and protected backup.
2. Run `current`, save sanitized output, and run `check`.
3. If check returns 2, review repository heads and the exact target revision.
4. Rehearse upgrade/downgrade/upgrade on a newly created disposable PostgreSQL database whose name clearly contains `phase01_test`.
5. Inspect `alembic_version`, critical tables and relevant `pg_constraint` rows.
6. Only after change approval, run the confirmed command against the explicitly reviewed target.
7. Re-run `current`, `check`, and readiness.

Never use an existing, unknown, or Production database for rehearsal. Delete only a disposable database created by the same rehearsal.

## Current FK disposition

Repository head is `20260728_add_quote_customer_response`. Candidate `20260729_deduplicate_foreign_keys` was removed because no repository evidence proved duplicates and its global irreversible sweep was unsafe. If an environment-specific duplicate is demonstrated, inventory it first and build an allowlisted dry-run repair; do not apply a generic cleanup.

## Rollback

Prefer application rollback when migrations are backward compatible. A database downgrade needs a verified backup, explicit approval, exact target, and a successful disposable rehearsal. After downgrade, verify the revision and schema read-only before restarting. Never improvise around the historical SQLite chain: `20240920_add_transport_method_to_shipment_request` contains `ALTER COLUMN`, so SQLite is not proof of full migration portability.

## Environment limitation

For Phase 0.1 on this workstation, PostgreSQL rehearsal is `NOT_RUN_ENVIRONMENT_UNAVAILABLE`; neither `psql`, Docker nor Podman is available. No migration is Production-validated.

## Related documents

- [Runtime migration safety](phase0_1_runtime_migration_safety.md)
- [ADR-011](adr/ADR-011-explicit-migration-execution.md)
- [Windows deployment runbook](phase0_1_deployment_runbook_windows.md)

