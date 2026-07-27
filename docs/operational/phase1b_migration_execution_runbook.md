# Phase 1B persistent migration execution runbook

## Authorization boundary

This is a plan only. It does not authorize execution. The current gate selected no target and performed no database operation. Raw Alembic upgrade, direct DDL/DML, seed execution, and startup-time migration remain prohibited.

## Required change record

Before scheduling, record:

- environment and sanitized target fingerprint;
- exact deployed application commit and compatibility statement;
- business, technical, and database owners;
- migration operator and independent verifier;
- maintenance start, maximum downtime, expected backup/migration/verification durations, rollback deadline, and communication channel;
- approved credential source and read-only/write authority boundaries;
- verified backup artifact and successful restore rehearsal;
- current revision, expected path, drift result, aggregate precheck results, and Go/No-Go approval.

## Execution sequence

1. Freeze application, schema, configuration, and migration changes.
2. Verify the exact target fingerprint and deployed application commit.
3. Run the approved read-only inventory and confirm a single supported linear migration path.
4. Confirm zero unexplained drift and passing aggregate prechecks.
5. Enter maintenance mode or stop all writers; verify the agreed connection/drain condition.
6. Take and verify the approved backup/snapshot; do not continue on warning or incomplete evidence.
7. Reconfirm revision and target fingerprint immediately before change.
8. Execute only the official runner from the approved Phase 1B artifact:

   ```text
   python -m backend.migration_cli upgrade --confirm
   ```

9. Stop on any non-zero exit, timeout, unexpected revision, lock condition, or sanitized error boundary. Do not retry automatically.
10. Verify revision equals `20260801_route_exception`, pending revisions are zero, and expected schema metadata exists.
11. Run the bounded post-migration integrity checks in the verification plan.
12. Start the application only after database verification passes.
13. Run the approved minimal application smoke; use synthetic or designated test records and prevent unintended production mutations.
14. Observe the 15-minute monitoring window and obtain Go/No-Go confirmation.
15. Close maintenance mode, communicate completion, and continue monitoring at one hour and 24 hours.

## Rollback strategy

### Level 1: application rollback

Prefer restoring the previously approved application artifact when the new schema is backward compatible. Disable the Phase 1B feature or keep traffic stopped if compatibility is uncertain. Application rollback does not imply database downgrade.

### Level 2: database recovery

| Revision | Downgrade available | Data-loss risk | Recommended rollback |
|---|---|---|---|
| `20260801_route_exception` | YES, guarded | HIGH if response/reconciliation history exists | Application rollback first; verified restore if the guard rejects or history exists; downgrade only after explicit evidence/approval |
| `20260730_multileg_route` | YES, guarded and structurally destructive | HIGH/BLOCKER when Phase 1B operational data exists | Verified restore is the default; downgrade only for proven Phase-1A-compatible state after rehearsal |

Trigger rollback evaluation on migration failure, unexpected revision/drift, integrity count above zero, sustained 5xx/database errors, lock/connection saturation, cross-organization violation, duplicate shipment display, or failed critical smoke. The database owner and Go/No-Go authority choose application rollback, guarded downgrade, or restore before the documented decision deadline.

If downgrade or restore fails, keep writers stopped, preserve sanitized logs/evidence, and escalate. Never bypass guards, use `DROP ... CASCADE`, improvise a raw Alembic upgrade, or retry blindly.

## No-Go conditions

- target fingerprint, owner, approval, or window mismatch;
- unverified backup/restore or insufficient capacity;
- unsupported PostgreSQL version, unknown/diverged revision, multiple heads, or version-table issue without an approved plan;
- unexplained schema drift or failing aggregate precheck;
- active writers outside the approved condition;
- missing monitoring, rollback, or communication coverage.
