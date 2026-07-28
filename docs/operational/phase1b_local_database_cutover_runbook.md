# Phase 1B Local Database Cutover Runbook

## Closed status

The localhost Final Cutover completed successfully on 2026-07-27. This
runbook is retained as a historical control record; it is no longer an
executable operator sequence.

The authoritative outcome is recorded in the
[Final Closure Report](phase1b_local_backup_restore_migration_result.md).

```text
PHASE_1B_LOCAL_DATABASE_CUTOVER=CLOSED
LOCAL_ACTIVE_DATABASE=forwarder_db
LOCAL_ACTIVE_HEAD=20260801_route_exception
LOCAL_LEGACY_DATABASE=forwarder_db_legacy_20260727_222328
FINAL_CUTOVER_RERUN=FORBIDDEN
```

## Completed strategy

The legacy `forwarder_db` was never upgraded or stamped. The completed strategy
was:

`fresh active-head database + controlled transfer + atomic local cutover`

DryRun and Rehearsal passed before the Final transfer. The final target reached
`20260801_route_exception`, passed reconciliation and application validation,
and was atomically promoted to `forwarder_db`. The prior database was retained
as `forwarder_db_legacy_20260727_222328`.

## Safety boundary retained after closure

- Final Cutover must not be rerun.
- The retained legacy database must not be deleted, renamed, stamped, upgraded,
  or repurposed.
- Raw Alembic upgrade on the legacy database remains forbidden.
- Backups and the evidence archive must be retained.
- No restore or rollback may occur without a separate approved gate and
  independent validation.
- Server and Production remain outside this completed local gate.
- Deploy and merge were not performed.

## Stable evidence

Evidence:

`D:\1-webapp\_db_backups\15-forwarder\20260727_222328\evidence`

SHA-256 manifest:

`D:\1-webapp\_db_backups\15-forwarder\20260727_222328\evidence\evidence-sha256-manifest.json`

The manifest covers 22 evidence files. Evidence is aggregate-only and records
no row payload.

## Related controls

- [Final Closure Report](phase1b_local_backup_restore_migration_result.md)
- [Mapping Contract](phase1b_local_database_mapping_contract.md)
- [Rollback Runbook](phase1b_local_database_rollback_runbook.md)

Any rollback is a new, explicitly approved operation governed by the rollback
runbook. Any server or Production cutover requires a separate plan.
