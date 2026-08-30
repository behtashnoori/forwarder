# ADR-043 controlled production deployment runbook

Status: executable preparation only; it does not authorize deployment. Certified application source is `adcc5da2c6f6d696dbad15b9b2cd7900bd96bc9e` (835 passed, 0 failed, 92 skipped, 1 xfailed). ADR-037, ADR-042 and ADR-043 remain controlling: Platform Admin has no tenant-work access; role labels do not establish authority; capability never bypasses tenant fencing; and direct assignment creates no CRM right.

## Release-integrity stop gate

The stale release-builder head guard was corrected locally to `20260907_direct_shipment_responsibility`. The builder materializes a detached worktree from the exact requested 40-character Git object, rejects a dirty materialization, builds `dist` inside it, and embeds `source_commit`/head/file hashes in inner and sidecar manifests. It never copies this worktree. Do not substitute the dirty worktree, package a later evidence commit, or run generic `alembic upgrade head`.

## PHASE 0 — Operator safety / change freeze [READ-ONLY]

```powershell
$ErrorActionPreference='Stop'; $TaskName='Forwarder Backend Production'; $PgBin='C:\Program Files\PostgreSQL\18\bin'; $TargetRevision='20260907_direct_shipment_responsibility'; $CertifiedCommit='adcc5da2c6f6d696dbad15b9b2cd7900bd96bc9e'
Get-ScheduledTask -TaskName $TaskName | Format-List *
Get-ScheduledTaskInfo -TaskName $TaskName
Export-ScheduledTask -TaskName $TaskName | Set-Content -Encoding utf8 "$env:TEMP\Forwarder-Backend-Production.before.xml"
```

Require written deployment/database/operations authorization, maintenance window, rollback owner, and protected evidence location. STOP if the exported task, backend/PID, IIS path, DB identity, or current schema differs from the final preflight.

## PHASE 1 — Immutable release preparation

[READ-ONLY]
```powershell
git -C D:\1-webapp\15-forwarder cat-file -e "$CertifiedCommit^{commit}"
git -C D:\1-webapp\15-forwarder show -s --format='%H%n%s' $CertifiedCommit
```

[MUTATING — REQUIRES SEPARATE OPERATOR AUTHORIZATION]

PRECONDITIONS: fresh output directory; exact Git object only. EXPECTED EFFECT: creates an immutable ZIP/sidecar only. STOP: nonzero gate, manifest SHA mismatch, or source commit mismatch. CONTAINMENT: discard only failed staging artifact.

```powershell
python D:\1-webapp\15-forwarder\scripts\build_release_package.py --repository D:\1-webapp\15-forwarder --authorized-commit $CertifiedCommit --output-directory D:\1-webapp\adr043-release-artifacts --release-label adr043-assigned-work
```

Require manifest `source_commit=$CertifiedCommit`, target head, SHA-256 sidecar, and fresh `dist/index.html`/hashed assets. Use the production Python 3.14 executable to create `$NewRelease\.venv`, then install exactly `requirements.txt` and `requirements-release.txt` without upgrade. The builder’s gate creates its own isolated venv and runs `npm ci`, tests, and `npm run build`; the package contains the resulting same-origin `dist`. The certified delta has no frontend/package/runtime config changes, so no frontend feature change independently requires IIS transition.

## PHASE 2 — Pre-deployment revalidation [READ-ONLY]

Run committed `ops\adr043-production-readonly-preflight.ps1` on the server. Require `PREFLIGHT_COLLECTION_COMPLETE=YES`, `COLLECTION_ERRORS=0`, current schema `20260906_global_logistics_point_materialization`, health/readiness 200, request/authority/child lineage violation counts zero. Direct schema pending is expected. STOP on drift or any security counter.

## PHASE 3 — Fresh backup

[READ-ONLY]
```powershell
& "$PgBin\pg_dump.exe" --version
& "$PgBin\psql.exe" -X -h 127.0.0.1 -p 5432 -U postgres -d forwarder_prod_20260728_161711 -c "SELECT pg_is_in_recovery(),version_num FROM alembic_version;"
```

[MUTATING — REQUIRES SEPARATE OPERATOR AUTHORIZATION]

PRECONDITIONS: primary confirmed, protected writable backup directory, new timestamped name. EXPECTED EFFECT: custom-format backup, no DB writes. STOP: dump/size/catalog/hash failure. CONTAINMENT: retain failed artifact; make no schema change. Enter password only at prompt; never `PGPASSWORD`, CLI password, or `.pgpass`.

```powershell
$Dump="C:\1-webapp\forwarder-backups\forwarder-adr043-predeploy-$(Get-Date -Format 'yyyyMMdd-HHmmssZ').dump"
& "$PgBin\pg_dump.exe" -Fc -h 127.0.0.1 -p 5432 -U postgres -d forwarder_prod_20260728_161711 -f $Dump
if($LASTEXITCODE -ne 0 -or (Get-Item $Dump).Length -le 0){throw 'backup failed'}
& "$PgBin\pg_restore.exe" --list $Dump; if($LASTEXITCODE -ne 0){throw 'catalog failed'}; Get-FileHash $Dump -Algorithm SHA256
```

## PHASE 4 — Release staging

[MUTATING — REQUIRES SEPARATE OPERATOR AUTHORIZATION]

PRECONDITIONS: verified artifact/manifest, non-existent approved release directory. EXPECTED EFFECT: new immutable directory, never an overlay. STOP: manifest/source mismatch or unknown environment-loader. CONTAINMENT: remove only unactivated new directory.

```powershell
$NewRelease='C:\1-webapp\forwarder-production\release-adr043-adcc5da'
Expand-Archive -LiteralPath 'C:\1-webapp\adr043-release-artifacts\Forwarder-adr043-assigned-work-adcc5da.zip' -DestinationPath $NewRelease
Get-Content "$NewRelease\release-manifest.json"
```

Resolve the existing non-secret env-loader from exported task XML before mutation. STOP if it cannot be proved; do not copy or print `production.env`.

## PHASE 5 — Scheduled Task definition preparation (not backend quiescence)

The observed task release bindings and the actual serving release are intentionally treated as separate facts. Current evidence is: task bindings consistently name `release-991d29a-20260829`; the sole observed `127.0.0.1:5101` listener was PID `51476`, with parent PID `51756`, and its Python executable/Waitress command name that same `release-991d29a-20260829`; a separate `release-fdfdd23-20260823` tree (`30760 -> 11028`) is non-listening. Do not infer a backend/IIS release from the non-listening tree.

Changing a Scheduled Task definition is **not** stopping or quiescing the current backend. In particular, the task has been observed `Ready` while the Waitress listener remained alive. `Stop-ScheduledTask` is therefore not certified to terminate the listener and must not be used as the deployment stop procedure.

The established binding contract requires **all three** of WorkingDirectory, `--repo`, and `PYTHONPATH` to point to one immutable release. The task executable remains `C:\Windows\System32\cmd.exe`; the server-managed launcher is `C:\1-webapp\forwarder-runtime\phase1b\_production\_cutover\_runtime.py`. Its exact command and argument order are extracted from live XML and must not be guessed. Its `serve` implementation applies the environment, changes directory, redirects logs, then uses `os.execv` to replace itself with Waitress; it is not a persistent supervisor that can later be stopped as a helper process.

[READ-ONLY]

```powershell
$TaskName='Forwarder Backend Production'
$BeforeXml="$env:TEMP\Forwarder-Backend-Production.before.xml"
Export-ScheduledTask -TaskName $TaskName | Set-Content -LiteralPath $BeforeXml -Encoding utf8
[xml]$TaskXml=Get-Content -Raw -LiteralPath $BeforeXml
$TaskXml.Task.Principals.Principal | Format-List UserId,LogonType,RunLevel
$TaskXml.Task.Triggers.ChildNodes | Format-List *
$TaskXml.Task.Settings | Format-List MultipleInstancesPolicy,ExecutionTimeLimit,RestartOnFailure,StopIfGoingOnBatteries,DisallowStartIfOnBatteries
$TaskXml.Task.Actions.Exec | Format-List Command,Arguments,WorkingDirectory
Get-ScheduledTask -TaskName $TaskName | Select-Object TaskName,State,Principal,Settings
Get-ScheduledTaskInfo -TaskName $TaskName | Format-List *
Get-FileHash $BeforeXml -Algorithm SHA256
```

STOP if command is not `cmd.exe`, arguments do not name the server runtime launcher and `--repo`, or WorkingDirectory/`--repo`/`PYTHONPATH` do not consistently name the old release. The reviewed after XML must preserve principal, triggers, restart/failure, stop-if-running, multiple-instance, execution-time-limit, and all non-release arguments. Change only the three release bindings; retain `cmd.exe` and the same runtime launcher. Verify with `Compare-Object` before registration.

[MUTATING — REQUIRES SEPARATE OPERATOR AUTHORIZATION]

PRECONDITIONS: reviewed XML explicitly names `$NewRelease`; old XML preserved. EXPECTED EFFECT: replaces task definition only. STOP: unexpected XML diff/no release path. CONTAINMENT: re-register exact before XML.

```powershell
Register-ScheduledTask -TaskName $TaskName -Xml (Get-Content -Raw 'C:\approved\Forwarder-Backend-Production.adr043.xml') -Force
Export-ScheduledTask -TaskName $TaskName | Set-Content -Encoding utf8 "$env:TEMP\Forwarder-Backend-Production.after.xml"
Compare-Object (Get-Content $BeforeXml) (Get-Content "$env:TEMP\Forwarder-Backend-Production.after.xml")
```

Registration changes the future task definition only. It does not authorize, stop, signal, kill, or otherwise alter the current listener. After registration, do not run the task until the separate lifecycle gate below has passed.

## PHASE 6 — Backend/writer quiescence and zero-listener gate

**CURRENT STATUS: NO-GO — a production-safe graceful stop/relaunch procedure has not been certified.** The repository's `scripts\backend-service.ps1` verifies one listener by port, executable, and `backend.wsgi:app`, but it is a local port-5001 launcher and its stop action is `Stop-Process -Force`. It is neither evidence of graceful termination nor authorization to control the 5101 Scheduled-Task deployment. Do not adapt it, issue `taskkill`, `Stop-Process`, or terminate a parent/child tree during this deployment.

The following is the required read-only listener identity record, not a stop command. It must show exactly one listener before a lifecycle procedure may be considered, and must bind that listener to the observed release rather than a merely similarly named process:

```powershell
$Port=5101; $ExpectedOldRelease='C:\1-webapp\forwarder-production\release-991d29a-20260829'
$Listeners=@(Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
if($Listeners.Count -ne 1){throw "expected exactly one pre-cutover listener on 127.0.0.1:$Port; found $($Listeners.Count)"}
$Owner=Get-CimInstance Win32_Process -Filter "ProcessId=$($Listeners[0].OwningProcess)"
$Parent=Get-CimInstance Win32_Process -Filter "ProcessId=$($Owner.ParentProcessId)"
$Owner | Select-Object ProcessId,ParentProcessId,ExecutablePath,CommandLine
$Parent | Select-Object ProcessId,ParentProcessId,ExecutablePath,CommandLine
if($Owner.ExecutablePath -notlike "$ExpectedOldRelease\*"){throw 'listener executable is not the recorded current release'}
if($Owner.CommandLine -notmatch '(?i)-m\s+waitress' -or $Owner.CommandLine -notmatch '(?i)backend\.wsgi:app'){throw 'listener is not the expected Waitress WSGI process'}
```

Before a future authorized production attempt, obtain and archive the smallest additional **read-only** evidence needed to establish a governed lifecycle method: (1) the complete exported task XML, including the `cmd.exe` command line; (2) complete `Win32_Process` command lines and parent relationships for the listener and all same-release parent/child processes; (3) the complete on-server runtime-helper source and its hash; and (4) vendor/operating-system or prior approved production evidence showing exactly how the task-owned process receives a graceful stop and how automatic relaunch is disabled/held during a maintenance window. The evidence must identify the control owner, signal/action, bounded wait, and expected exit/port-closure observation. If it does not, the deployment remains NO-GO.

Only after that evidence has been reviewed and a separately authorized lifecycle procedure exists may an operator: prevent task relaunch by its proven mechanism; invoke its proven graceful stop against the verified listener; wait for it to exit; and prove writer quiescence. Writer quiescence requires all of: traffic containment by the approved topology owner; no listener on 5101; no task/restart mechanism able to launch a writer during migration; and an owner-approved read-only database/session observation showing no in-flight application write transaction. Do not use test-data writes, synthetic mutations, or stale-process cleanup as a substitute.

The migration zero-listener gate is mandatory and must be recorded immediately before the migration command:

```powershell
$Listeners=@(Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 5101 -State Listen -ErrorAction SilentlyContinue)
if($Listeners.Count -ne 0){throw "migration blocked: 127.0.0.1:5101 still has $($Listeners.Count) listener(s)"}
```

## PHASE 7 — Schema migration

Migration `20260907_direct_shipment_responsibility` is additive: nullable `operational_shipment.primary_responsible_expert_id`, restrict FK to `expert_user`, index, no backfill. Its downgrade refuses when responsibility evidence exists. Use governed CLI, not generic Alembic.

[READ-ONLY]
```powershell
Set-Location $NewRelease
.\.venv\Scripts\python.exe -m backend.migration_cli current
.\.venv\Scripts\python.exe -m backend.migration_cli check
```

Require current `20260906...`, sole head target, correct sanitized target. STOP otherwise.

[MUTATING — REQUIRES SEPARATE OPERATOR AUTHORIZATION]

PRECONDITIONS: backup verified; Phase 6's certified graceful lifecycle procedure completed; writer-quiescence record and zero-listener gate passed; new task definition configured but not started. EXPECTED EFFECT: target migration only. STOP: any nonzero, listener reappearance, or pending postcheck. CONTAINMENT: no blind downgrade; retain the quiescent state, use only compatibility-proven application rollback or database-owner backup restore.

```powershell
.\.venv\Scripts\python.exe -m backend.migration_cli upgrade 20260907_direct_shipment_responsibility --confirm
.\.venv\Scripts\python.exe -m backend.migration_cli current
.\.venv\Scripts\python.exe -m backend.migration_cli check
```

## PHASE 8 — Post-migration data gate [READ-ONLY]

```powershell
& "$PgBin\psql.exe" -X -h 127.0.0.1 -p 5432 -U postgres -d forwarder_prod_20260728_161711 -c "BEGIN TRANSACTION READ ONLY; SELECT count(*) FILTER (WHERE s.source_type='direct') total_direct_shipments,count(*) FILTER (WHERE s.source_type='direct' AND s.primary_responsible_expert_id IS NULL) missing_primary_responsible,count(*) FILTER (WHERE s.source_type='direct' AND (u.id IS NULL OR NOT u.is_active)) inactive_or_missing_responsible,count(*) FILTER (WHERE s.source_type='direct' AND s.primary_responsible_expert_id IS NOT NULL AND m.id IS NULL) cross_tenant_responsible FROM operational_shipment s LEFT JOIN expert_user u ON u.id=s.primary_responsible_expert_id LEFT JOIN operational_membership m ON m.user_id=s.primary_responsible_expert_id AND m.organization_id=s.organization_id AND m.is_active; COMMIT;"
```

STOP APPLICATION ACTIVATION if any invalid count is nonzero. No bulk repair/backfill is authorized. Membership’s `(organization_id,user_id)` uniqueness means join ambiguity is not representable.

## PHASE 9 — Backend activation and single-listener certification

[MUTATING — REQUIRES SEPARATE OPERATOR AUTHORIZATION]

PRECONDITIONS: backup/migration/data gate pass; reviewed task points to `$NewRelease`; Phase 6 has certified the specific task activation/relaunch behavior; port 5101 has zero listeners. EXPECTED EFFECT: one task-managed new Waitress backend. STOP: missing/multiple listener, a listener before activation, or process command/executable lacks `$NewRelease`. CONTAINMENT: use only the certified lifecycle procedure; restore old XML and activate the old task only after old-app/new-schema compatibility is approved. Do not use a generic process kill.

```powershell
$Before=@(Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 5101 -State Listen -ErrorAction SilentlyContinue)
if($Before.Count -ne 0){throw 'activation blocked: port 5101 is not quiescent'}
# Invoke only the task-start action certified by the Phase 6 lifecycle evidence.
Start-ScheduledTask -TaskName $TaskName
$Deadline=(Get-Date).AddSeconds(60)
do { $After=@(Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 5101 -State Listen -ErrorAction SilentlyContinue); if($After.Count -eq 1){break}; Start-Sleep -Seconds 1 } while((Get-Date) -lt $Deadline)
if($After.Count -ne 1){throw "activation failed: expected exactly one 5101 listener; found $($After.Count)"}
$NewOwner=Get-CimInstance Win32_Process -Filter "ProcessId=$($After[0].OwningProcess)"
$NewOwner | Select-Object ProcessId,ParentProcessId,ExecutablePath,CommandLine
if($NewOwner.ExecutablePath -notlike "$NewRelease\*"){throw 'activation failed: listener executable is not the new immutable release'}
if($NewOwner.CommandLine -notmatch '(?i)-m\s+waitress' -or $NewOwner.CommandLine -notmatch '(?i)backend\.wsgi:app'){throw 'activation failed: listener is not Waitress WSGI'}
```

The `Start-ScheduledTask` line is not an independently certified replacement mechanism. It may be executed only after Phase 6 proves task behavior and task suppression/activation semantics for this server. A `Ready` task state alone is not service-state evidence.

## PHASE 10 — Health/readiness gate [READ-ONLY]

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:5101/api/health
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:5101/api/health/ready
```

Require 200 twice, target migration, expected one listener, no blocking logs.

## PHASE 11 — IIS/frontend

IIS change is **NOT_REQUIRED** for this certified authorization-only delta. Keep existing physical path; do not change IIS merely to make topology visually uniform. Later frontend deployment requires separately reviewed IIS commands and rollback evidence.

## PHASES 12–15 — smoke, Samand, observation, capture

Read-only existing-data smoke: Platform Admin tenant request/shipment denies; Organization Admin allows only existing explicit capability and denies platform diagnostics; Expert allows only own assigned request/child and denies same-tenant unassigned/foreign IDs; `role=admin` does not elevate; a capability does not allow foreign access. Reassignment A→B is `MANUAL_EXISTING_DATA_VALIDATION_REQUIRED` because it mutates state; do not create test data.

Use confirmed `https://samand.logisticmarket.ir` (not unproven `samand.forwarderet.ir`) to validate page/auth/tenant identity/admin and expert flows/browser `/api/*` calls. CORS is `NOT_VERIFIED`; STOP on browser CORS/API failure and do not mutate CORS. Observe owner-approved logs/5xx/health/task restarts, then record hashes, task XML before/after, backup, migration output, aggregate data gate, health/browser evidence.

## Rollback decision tree

| Event | Containment / recovery |
|---|---|
| Before migration | do nothing to current service |
| Cannot prove graceful stop, task suppression, writer quiescence, or zero listener | NO-GO; make no migration or activation change; collect only the specified read-only lifecycle evidence |
| Migration fails pre-commit | preserve the certified quiescent/task-suppressed state; verify revision; escalate |
| Migration succeeds, activation/health/smoke fails | use the certified lifecycle procedure to contain traffic; app rollback only if old/new schema compatibility proved; otherwise DB-owner restore from backup |
| Downgrade refuses due responsibility evidence | forward-fix or verified backup restore; never bypass guard |
| Task targets wrong release | do not start it; re-register before XML; do not restart until lifecycle/compatibility gates pass |
| Stale non-listening `release-fdfdd23-20260823` tree | record only; exclude from cutover and do not stop/kill it. Cleanup requires a separate owner-approved investigation and lifecycle procedure. |
| Later frontend failure | restore previously captured IIS path only under separate approval |

Never equate app rollback with schema rollback or issue blind `alembic downgrade`.
