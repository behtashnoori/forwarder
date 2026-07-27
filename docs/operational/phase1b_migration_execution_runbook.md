# Phase 1B persistent migration execution runbook

## Final closure — database cutover deferred (2026-07-27)

Phase 1B product implementation and UAT are complete. This runbook remains a future cutover plan and was not executed persistently. Main remains unchanged at legacy revision `54ea21ea0d9f`; no active candidate is canonically equivalent, so stamp and legacy-marker approaches are rejected. The future path is a fresh active-head database at `20260801_route_exception` followed by separately authorized controlled data transfer.

The disposable assessment proved source read-only/rollback, successful target migration, valid target inventory hash, an accepted explained migration/system baseline, and complete cleanup. Automated mapping stopped at `NATIVE_FAIL:ANALYSIS:1` and is deferred. No transfer, persistent migration, stamp, deploy, seed, Main write, or server change occurred.

Final decisions: `PHASE_1B_IMPLEMENTATION_COMPLETE`, `PHASE_1B_DATABASE_CUTOVER_DEFERRED`, `FRESH_TRANSFER_REQUIRED`, `AUTOMATED_MAPPING_DEFERRED`, `MAIN_DATABASE_UNCHANGED`, `SERVER_UNCHANGED`.

## Candidate materialization evidence hold — 2026-07-27

Execution remains prohibited. The five manifest-declared candidate fingerprint
outputs and SHA-256 companions are absent, so no target active revision or
bridge topology can be selected. The next action is a separately authorized
disposable evidence run followed by read-only comparison; it is not a stamp or
persistent migration. Local/server persistent application remains `NO` / `NO`.

`PHASE_1B_BRIDGE_TOPOLOGY_DECISION_BLOCKED`

## Current execution status — 2026-07-27

This runbook was not executed. The verified source revision `54ea21ea0d9f` is
absent from the executable Alembic graph and is retained only as an archived
deprecated root-only migration. The mandatory supported-linear-path condition
failed with `UNKNOWN_REVISION`; migration attempt count is zero and both local
and server persistent application remain `NO`.

`PHASE_1B_LOCAL_PERSISTENT_MIGRATION_GRAPH_BLOCKED`

## Canonical blocked-evidence record

- Target: `127.0.0.1:5432/forwarder_db`
- Source revision: `54ea21ea0d9f`
- Expected active head: `20260801_route_exception`
- Active graph: source revision absent; archive reference is evidence only and is not execution authorization.
- Migration classification: `UNKNOWN_REVISION`
- Go/No-Go: `LOCAL_PHASE1B_MIGRATION_GO=NO`
- Backup executed: `NO`; restore database created: `NO`
- Migration attempt count: `0`; seed executed: `NO`
- Persistent applied local/server: `NO` / `NO`
- Server access/deploy: `NO` / `NO`
- Credential or DSN recorded: `NO`
- Prohibited without an independent gate: Alembic stamp, raw Alembic upgrade, archived migration execution, manual `alembic_version` editing, and schema repair.

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
