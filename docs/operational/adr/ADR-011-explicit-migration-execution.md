# ADR-011: Explicit Migration Execution

- Status: Accepted
- Date: 2026-07-22

## Context

Application imports and normal startup previously reached migration, seed, fallback DDL, DB ping, and Flask-backed Alembic paths. That made startup nondeterministic and could create nested Alembic contexts or alter schema before backup and approval.

## Decision

Normal startup has no schema or data writes. `current` and `check` are read-only. Migration runs only through `python -m backend.migration_cli upgrade [revision] --confirm`. Truthy `AUTO_MIGRATE_ON_STARTUP` is rejected. Production uses a read-only fail-fast readiness gate.

## Alternatives considered

- Automatic migration on every startup: rejected because multi-worker starts, rollback and authorization are unsafe.
- Opt-in startup migration: rejected as the recommended path because environment drift can silently enable it.
- Flask CLI/Alembic environment constructing the app: rejected because it re-enters runtime startup.

## Consequences

Deployments require a separate migration step, backup gate, exit-code handling, and readiness verification. Startup becomes deterministic and horizontally safe. Pending revisions block Production rather than being silently ignored.

## Risks and controls

Operators may skip the explicit step; `check` exit 2 and readiness 503 expose that state. Credentials may appear in driver errors; the CLI and public probes suppress complete URLs and exception details. Rollback is never automatic and requires rehearsal and backup.

## Revisit triggers

Revisit only if a deployment orchestrator provides a single-leader migration job, auditable approval, backup/restore integration, and equivalent secret redaction.

## Related documents

- [Runtime migration safety](../phase0_1_runtime_migration_safety.md)
- [Database revision runbook](../phase0_1_database_revision_runbook.md)

