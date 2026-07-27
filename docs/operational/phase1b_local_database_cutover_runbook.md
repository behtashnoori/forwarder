# Phase 1B Local Database Cutover Runbook

This is an operator-run, localhost-only fresh-database cutover. It never
upgrades or stamps the legacy `forwarder_db`. The operator harness creates a
verified custom-format backup, restores it to a disposable validation database,
builds a fresh rehearsal database at `20260801_route_exception`, completes
metadata-driven mapping/transfer/reconciliation and application gates, then
repeats the work from zero for the final database.

## Safety boundary

- Host and port are fixed to `127.0.0.1:5432`.
- The source name is fixed to `forwarder_db`.
- Target names are token-scoped and allow-listed.
- Source SQL uses explicit read-only transactions.
- Password input uses `Read-Host -AsSecureString`; plaintext exists only in
  memory and is supplied to each native child as process-local `PGPASSWORD`.
- Logs and JSON evidence contain aggregates only, never row payloads or DSNs.
- Security/transient authentication tables are excluded.
- Mapping blockers, rejected rows, FK/constraint failures, or unexplained
  variance stop execution before rename.
- Backups, evidence, and the retained legacy database are never deleted.

## Operator sequence

Run DryRun first, then Rehearsal, and only then Final:

```powershell
Set-Location "D:\1-webapp\15-forwarder"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\db_cutover\phase1b_local_cutover.ps1" -Mode DryRun

Set-Location "D:\1-webapp\15-forwarder"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\db_cutover\phase1b_local_cutover.ps1" -Mode Rehearsal

Set-Location "D:\1-webapp\15-forwarder"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\db_cutover\phase1b_local_cutover.ps1" -Mode Final -ConfirmCutover
```

Each invocation uses a unique run token. Final mode performs its own fresh
rehearsal before creating its fresh final target; an earlier rehearsal database
is never promoted. Evidence is written below
`%LOCALAPPDATA%\Temp\forwarder-phase1b-local-cutover-<token>` and backups below
`D:\1-webapp\_db_backups\15-forwarder\<token>`.

Final mode renames `forwarder_db` to
`forwarder_db_legacy_<timestamp>` and the validated final target to
`forwarder_db`. If post-cutover validation fails, it renames the new database
to `forwarder_db_failed_<timestamp>` and restores the retained legacy name.
There is no automatic retry.
