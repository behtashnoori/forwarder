# ADR-043 controlled production deployment runbook

Status: written production authorization recorded; execution remains pending mandatory live gates. Certified application source is `adcc5da2c6f6d696dbad15b9b2cd7900bd96bc9e` (835 passed, 0 failed, 92 skipped, 1 xfailed). ADR-037, ADR-042 and ADR-043 remain controlling: Platform Admin has no tenant-work access; role labels do not establish authority; capability never bypasses tenant fencing; and direct assignment creates no CRM right.

## Integrity, current topology, and historical boundary

The release builder materializes a detached worktree from the requested 40-character object, rejects a dirty materialization, builds `dist` there, and records source/head/file hashes. Its guard is `20260907_direct_shipment_responsibility`. Never package this later tooling/runbook commit, substitute the dirty worktree, or run generic `alembic upgrade head`.

Completed read-only preflight supersedes conflicting older lifecycle observations: `PREFLIGHT_COLLECTION_COMPLETE=YES`, `COLLECTION_ERRORS=0`. The current listener is PID `51476` on `127.0.0.1:5101`, running `C:\1-webapp\forwarder-production\release-991d29a-20260829`; the existing `Forwarder Backend Production` task is `Ready` with working directory `C:\1-webapp\forwarder-production\release-991d29a-20260829`; IIS bindings for Samand/Forwarderet were present; database is `forwarder_prod_20260728_161711` at `20260906_global_logistics_point_materialization`; target is `20260907_direct_shipment_responsibility`; health and readiness are 200. Any material drift from this baseline is a stop gate, not permission to restart.

Historical phase1b evidence is only a pattern: identify the listener, hold its scheduler, terminate only verified process scope, prove port closure, then bind and health-check. It does not establish current ports, releases, IIS, origins, DB cutover, or task XML. Do not run historical scripts, blindly use `Stop-Process`, `taskkill`, `Stop-ScheduledTask`, restart, task replacement, or `alembic downgrade`.

## PHASE 0 — Constants and authorization [READ-ONLY]

```powershell
$ErrorActionPreference='Stop'; $TaskName='Forwarder Backend Production'; $Port=5101
$KnownListenerPid=51476; $ExpectedOldRelease='C:\1-webapp\forwarder-production\release-991d29a-20260829'
$TaskRecordedRelease='C:\1-webapp\forwarder-production\release-991d29a-20260829'
$PgBin='C:\Program Files\PostgreSQL\18\bin'; $Database='forwarder_prod_20260728_161711'
$TargetRevision='20260907_direct_shipment_responsibility'; $CertifiedCommit='adcc5da2c6f6d696dbad15b9b2cd7900bd96bc9e'
$BeforeXml='C:\approved\Forwarder-Backend-Production.before.xml'; $AfterXml='C:\approved\Forwarder-Backend-Production.adr043.xml'
$EvidenceDirectory='C:\approved\adr043-evidence'; New-Item -ItemType Directory -Force -Path $EvidenceDirectory | Out-Null
```

Require written deployment/database/operations authorization, maintenance window, traffic-containment owner, rollback owner, and protected evidence storage. Re-run committed `ops\adr043-production-readonly-preflight.ps1`; stop unless collection is complete/error-free, all supplied authorization/lineage counters are zero, current schema is correct, health/readiness are 200, and the PID/release/task/IIS facts above still agree. Never print `production.env` or connection strings.

## Recorded production authorization — current controlled window

`PRODUCTION_DEPLOYMENT_AUTHORIZED=YES`. The owner authorizes **only** the ADR-043 controlled production deployment governed by this runbook, subject to every mandatory live gate, STOP condition, backup requirement, explicit migration gate, post-migration data gate, runtime-ownership gate, health gate, Samand validation gate, and rollback rule below. Recording this authorization performs **no production mutation**.

| Control | Authorized value / status |
| --- | --- |
| Certified application SHA | `adcc5da2c6f6d696dbad15b9b2cd7900bd96bc9e` — exact SHA only; no current HEAD, later tooling/evidence commit, or branch tip substitution |
| Target migration | `20260907_direct_shipment_responsibility` — explicit target only; never generic Alembic head |
| Production database | `forwarder_prod_20260728_161711` |
| Authorized scope | ADR-043 controlled production deployment only |
| Fresh backup status | **PASS — FRESH VERIFIED PRODUCTION BACKUP RECORDED.** This satisfies the fresh-backup prerequisite for the **current ADR-043 deployment window only**; it does not make migration, deployment, Direct Shipment post-migration, runtime transition, or CORS PASS. |
| Migration status | **PENDING — NOT PASS.** |
| Deployment status | **PENDING — NOT COMPLETE.** |
| CORS status | **NOT_VERIFIED.** Runtime/browser evidence is required; this authorization does not make CORS PASS. |

This authorization does not authorize unrelated application changes; packaging a later tooling/evidence commit as the release; speculative IIS or CORS changes; modification of unrelated processes; cleanup or termination of stale non-listening process trees; unrelated database changes; production test-data mutation; blind migration to generic Alembic head; blind Scheduled Task restart; blind process termination; or automatic database downgrade as part of application rollback.

Before proceeding, the immediately-before-change ownership and task gates must be re-run and agree with the supplied successful baseline: collection complete/error-free; one `127.0.0.1:5101` listener; verified listener/release/task identity; task state and bindings; current revision `20260906_global_logistics_point_materialization`; target revision above; health/readiness 200; supplied membership, ShipmentRequest-root, child-lineage, and legacy-authority audit counters all zero; and pending-schema Direct Shipment readiness classified only as `NOT_COMPUTABLE_BEFORE_TARGET_SCHEMA`. Writer quiescence and zero-listener gates remain mandatory where required. After migration, Direct Shipment readiness/data quality must pass before activation; after activation exactly one listener from the certified release, both health endpoints, and Samand production validation must pass.

STOP and reassess on any material baseline drift, ambiguous runtime ownership, unexpected listener, task-identity drift, migration discrepancy, failed writer-quiescence/zero-listener gate, Direct Shipment gate failure, authorization-smoke failure, health/readiness failure, Samand validation failure, or material CORS failure. A CORS failure authorizes no speculative configuration change. Application rollback remains separate from database downgrade: downgrade requires its own compatibility decision and every existing protection; it is never automatic.

The fresh verified production backup checkpoint is recorded as PASS below. The next operational checkpoint is **PHASE 1 — exact certified application materialization and staging**, using only `adcc5da2c6f6d696dbad15b9b2cd7900bd96bc9e`; do not substitute a later tooling/evidence commit or proceed directly to migration. No migration, deployment, runtime, database, Scheduled Task, IIS, or CORS action is performed by this evidence record.

### Fresh verified production backup evidence — current ADR-043 deployment window

| Evidence item | Recorded value |
| --- | --- |
| Fresh backup status | **PASS** |
| Database | `forwarder_prod_20260728_161711` |
| Backup path | `C:\1-webapp\forwarder-backups\forwarder_prod_20260728_161711_20260830_231533_PRE_ADR043.dump` |
| Backup bytes | `827999` |
| Backup SHA256 | `f4b8b8696a94bdc43b07255fc0395f9a2e34ace07fde3f61588cac5a26be5fd6` |
| Catalog path | `C:\1-webapp\forwarder-backups\forwarder_prod_20260728_161711_20260830_231533_PRE_ADR043.list.txt` |
| Hash path | `C:\1-webapp\forwarder-backups\forwarder_prod_20260728_161711_20260830_231533_PRE_ADR043.dump.sha256.txt` |
| Certified application SHA | `adcc5da2c6f6d696dbad15b9b2cd7900bd96bc9e` — application identity remains this exact SHA; no later tooling/evidence commit is substituted. |
| Target migration | `20260907_direct_shipment_responsibility` |
| Observed operation result | `MIGRATION_PERFORMED=NO`; `PRODUCTION_TASK_CHANGED=NO`; `BACKEND_RESTARTED=NO`; `IIS_CHANGED=NO`; `CORS_CHANGED=NO` |

This backup satisfies the fresh-backup prerequisite for the **current ADR-043 deployment window only**. It does **not** mark migration PASS, deployment complete, the Direct Shipment post-migration gate PASS, runtime transition PASS, or CORS PASS. `APPLICATION_ROLLBACK != DATABASE_DOWNGRADE` remains controlling.

## PHASE 1 — Build and stage the exact application

### Production-host artifact integrity and non-serving staging evidence — current ADR-043 deployment window

The exact certified release artifact was independently built and verified locally, then manually copied to the production host. The following production-host checkpoint is **PASS** for artifact integrity and non-serving materialization only. It records neither a runtime transition nor a deployment completion.

| Evidence item | Recorded value |
| --- | --- |
| Certified application SHA | `adcc5da2c6f6d696dbad15b9b2cd7900bd96bc9e` — this exact SHA remains the application identity. No later tooling/evidence commit, current HEAD, or branch tip is treated as the application identity. |
| Release artifact | `D:\1-webapp\adr043-release-artifacts\Forwarder-adr043-assigned-work-adcc5da.zip` |
| Release artifact SHA256 | `af53fd7cc29f229e51a72fb02a3ffd0b1a9c46260af2fd37b83e993a4bdcea19` |
| Production artifact path | `C:\Users\Administrator\Desktop\Forwarder-adr043-assigned-work-adcc5da.zip` |
| Expected SHA256 | `af53fd7cc29f229e51a72fb02a3ffd0b1a9c46260af2fd37b83e993a4bdcea19` |
| Actual SHA256 | `af53fd7cc29f229e51a72fb02a3ffd0b1a9c46260af2fd37b83e993a4bdcea19` |
| Artifact integrity | **PASS** |
| Staging status | **PASS — NON-SERVING STAGED RELEASE ONLY** |
| Staged release path | `C:\1-webapp\forwarder-production\release-adcc5da-adr043` |
| Staged file count | `387` |
| Target migration | `20260907_direct_shipment_responsibility` |
| Target migration file | `C:\1-webapp\forwarder-production\release-adcc5da-adr043\backend\migrations\versions\20260907_direct_shipment_responsibility.py` |
| Runtime/task disposition | The staged release is **NOT serving traffic**. The Scheduled Task still points to the existing production release `C:\1-webapp\forwarder-production\release-991d29a-20260829`; it has not been changed. |
| No-runtime-mutation record | `PRODUCTION_TASK_CHANGED=NO`; `BACKEND_RESTARTED=NO`; `MIGRATION_PERFORMED=NO`; `IIS_CHANGED=NO`; `CORS_CHANGED=NO`. |

### Production-host release-local dependency preparation evidence — current ADR-043 deployment window

The remaining PHASE 1 runtime prerequisites and isolated release-local dependency preparation are **PASS**. This was an import-only/dependency verification of the staged release; it did not load or modify `C:\1-webapp\forwarder-runtime\production.env`, invoke a migration CLI operation, start the backend, or cause the staged release to serve traffic.

| Evidence item | Recorded value |
| --- | --- |
| Runtime prerequisite inspection | **PASS** — the production Python/runtime prerequisites and existing non-secret environment-loader proof were inspected successfully. |
| Release Python | `C:\1-webapp\forwarder-production\release-adcc5da-adr043\.venv\Scripts\python.exe` |
| Release Python version | `Python 3.14.3` (exit `0`) |
| Dependency check | **PASS** — `pip check` returned `No broken requirements found.` |
| PostgreSQL driver check | **PASS** — `psycopg2-binary` version `2.9.11` imported from the release-local environment. |
| Migration CLI import | **PASS** — `backend.migration_cli` import-only verification succeeded; no `current`, `check`, or `upgrade` operation was run. |
| Informational import output | `[startup] No .env file found in project root or backend/ - using process env only` — informational only; it does not fail this gate because the governed external `production.env` was deliberately neither loaded nor modified. |
| Release venv preparation | **PASS** — isolated release-local environment only; the existing `release-991d29a-20260829.venv314` was not modified or reused as the new release environment. |
| Serving/runtime disposition | `STAGED_RELEASE_SERVING=NO`; `CURRENT_LISTENER_PID=51476`; the existing release remains serving. |
| No-runtime-mutation record | `MIGRATION_PERFORMED=NO`; `BACKEND_STARTED=NO`; `PRODUCTION_TASK_CHANGED=NO`; `IIS_CHANGED=NO`; `CORS_CHANGED=NO`. |

All PHASE 1 gates required by this runbook are now satisfied: the exact artifact was verified, staged non-serving, checked against the production Python/runtime prerequisites, and prepared in its own release-local dependency environment. **PHASE 1 is PASS.** The staged release remains non-serving until all subsequent controlled phases pass.

The fresh-backup gate for the current window is already recorded PASS. The next outstanding operational checkpoint is **PHASE 3 — Export, inspect, and review the existing Scheduled Task and live runtime bindings**: re-run the immediately-before-change ownership/task facts, export and inspect the task XML, and stop on any drift. This checkpoint is **READ-ONLY**; task replacement/hold is a later separately authorized mutating step, followed by the ownership, writer-containment, and zero-listener gates. Do not proceed directly to migration.

This evidence does **not** mark migration PASS, Direct Shipment post-migration PASS, runtime transition PASS, deployment complete, or CORS PASS. `APPLICATION_ROLLBACK != DATABASE_DOWNGRADE` remains controlling.

[READ-ONLY]
```powershell
git -C D:\1-webapp\15-forwarder cat-file -e "$( $CertifiedCommit )^{commit}"
git -C D:\1-webapp\15-forwarder show -s --format='%H%n%s' $CertifiedCommit
```

[MUTATING — REQUIRES SEPARATE OPERATOR AUTHORIZATION]
```powershell
python D:\1-webapp\15-forwarder\scripts\build_release_package.py --repository D:\1-webapp\15-forwarder --authorized-commit $CertifiedCommit --output-directory D:\1-webapp\adr043-release-artifacts --release-label adr043-assigned-work
$NewRelease='C:\1-webapp\forwarder-production\release-adr043-adcc5da'
if(Test-Path -LiteralPath $NewRelease){throw 'approved new release directory already exists'}
Expand-Archive -LiteralPath 'C:\1-webapp\adr043-release-artifacts\Forwarder-adr043-assigned-work-adcc5da.zip' -DestinationPath $NewRelease
$Manifest=Get-Content -Raw -LiteralPath "$NewRelease\release-manifest.json" | ConvertFrom-Json
if($Manifest.source_commit -ne $CertifiedCommit){throw 'staged manifest is not the certified commit'}
```

Require matching sidecar/hash, target head, fresh `dist`, and package tests. Create the release venv using production Python and install exactly packaged requirements without upgrade. Resolve the existing non-secret environment loader from task XML; stop if it cannot be proved. Never overlay an old release.

## PHASE 2 — Fresh backup gate

[READ-ONLY]
```powershell
& "$PgBin\pg_dump.exe" --version
& "$PgBin\psql.exe" -X -h 127.0.0.1 -p 5432 -U postgres -d $Database -c "SELECT pg_is_in_recovery(),version_num FROM alembic_version;"
```

[MUTATING — REQUIRES SEPARATE OPERATOR AUTHORIZATION]
```powershell
$Dump="C:\1-webapp\forwarder-backups\forwarder-adr043-predeploy-$(Get-Date -Format 'yyyyMMdd-HHmmssZ').dump"
& "$PgBin\pg_dump.exe" -Fc -h 127.0.0.1 -p 5432 -U postgres -d $Database -f $Dump
if($LASTEXITCODE -ne 0 -or (Get-Item -LiteralPath $Dump).Length -le 0){throw 'backup failed'}
& "$PgBin\pg_restore.exe" --list $Dump; if($LASTEXITCODE -ne 0){throw 'backup catalog failed'}
Get-FileHash -LiteralPath $Dump -Algorithm SHA256 | Tee-Object "$EvidenceDirectory\backup-sha256.txt"
```

Confirm primary and protected writable destination. The dump has no DB writes. Enter password only at prompt; never use `PGPASSWORD`, CLI password, or `.pgpass`.

## PHASE 3 — Export, inspect, review, then hold the existing task

Task definition and current listener are separate facts. The immediately-before-change gate must prove the current `991d29a` task and listener bindings again; a blind restart remains prohibited. Changing a definition is not backend quiescence.

[READ-ONLY]
```powershell
Export-ScheduledTask -TaskName $TaskName | Set-Content -LiteralPath $BeforeXml -Encoding utf8
[xml]$TaskXml=Get-Content -Raw -LiteralPath $BeforeXml
$TaskXml.Task.Principals.Principal | Format-List UserId,LogonType,RunLevel
$TaskXml.Task.Triggers.ChildNodes | Format-List *
$TaskXml.Task.Settings | Format-List MultipleInstancesPolicy,ExecutionTimeLimit,RestartOnFailure,StopIfGoingOnBatteries,DisallowStartIfOnBatteries
$TaskXml.Task.Actions.Exec | Format-List Command,Arguments,WorkingDirectory
Get-ScheduledTask -TaskName $TaskName | Select TaskName,State,Principal,Settings
Get-ScheduledTaskInfo -TaskName $TaskName | Format-List *
Get-FileHash -LiteralPath $BeforeXml -Algorithm SHA256 | Tee-Object "$EvidenceDirectory\task-before-sha256.txt"
```

Stop unless the export proves `cmd.exe`, the reviewed server runtime launcher, and consistent `991d29a` bindings in WorkingDirectory, `--repo`, and `PYTHONPATH`. Construct `$AfterXml` from that export; change **only** those three bindings to `$NewRelease`. Preserve executable, every other argument, principal, triggers, restart/failure settings, execution limit, and multiple-instance policy. Do not guess launcher argument order.

```powershell
[xml]$BeforeTask=Get-Content -Raw -LiteralPath $BeforeXml; [xml]$AfterTask=Get-Content -Raw -LiteralPath $AfterXml
$BeforeTask.Task.Actions.Exec | Format-List Command,Arguments,WorkingDirectory
$AfterTask.Task.Actions.Exec | Format-List Command,Arguments,WorkingDirectory
if($BeforeTask.Task.Principals.OuterXml -ne $AfterTask.Task.Principals.OuterXml -or $BeforeTask.Task.Triggers.OuterXml -ne $AfterTask.Task.Triggers.OuterXml -or $BeforeTask.Task.Settings.OuterXml -ne $AfterTask.Task.Settings.OuterXml){throw 'replacement changes task controls'}
if((Get-Content -Raw $AfterXml) -notmatch [regex]::Escape($NewRelease) -or (Get-Content -Raw $AfterXml) -match [regex]::Escape($TaskRecordedRelease)){throw 'replacement XML release bindings are unsafe'}
```

[MUTATING — REQUIRES SEPARATE OPERATOR AUTHORIZATION]
```powershell
Register-ScheduledTask -TaskName $TaskName -Xml (Get-Content -Raw -LiteralPath $AfterXml) -Force
Disable-ScheduledTask -TaskName $TaskName
if((Get-ScheduledTask -TaskName $TaskName).State -ne 'Disabled'){throw 'task hold was not established'}
Export-ScheduledTask -TaskName $TaskName | Set-Content -LiteralPath "$EvidenceDirectory\Forwarder-Backend-Production.held.xml" -Encoding utf8
if((Get-Content -Raw "$EvidenceDirectory\Forwarder-Backend-Production.held.xml") -notmatch [regex]::Escape($NewRelease)){throw 'held task does not target certified release'}
```

This changes future task behavior only and explicitly prevents automatic re-launch during migration; it does not stop the listener.

## PHASE 4 — Ownership gate and controlled current-runtime stop

The only permitted termination is the exact verified listener PID and its enumerated descendants. It never kills a parent. Historical root-tree termination is deliberately not reused: no current parent/supervisor identity is supplied, and no parent is required to close the listener.

```powershell
$Listeners=@(Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
if($Listeners.Count -ne 1){throw "expected one listener on 127.0.0.1:$Port; found $($Listeners.Count)"}
$VerifiedPid=[int]$Listeners[0].OwningProcess
if($VerifiedPid -ne $KnownListenerPid){throw "listener PID changed: expected $KnownListenerPid, got $VerifiedPid"}
$Owner=Get-CimInstance Win32_Process -Filter "ProcessId=$VerifiedPid"
if($null -eq $Owner -or [string]::IsNullOrWhiteSpace($Owner.ExecutablePath)){throw 'listener identity unavailable'}
$Owner | Select ProcessId,ParentProcessId,ExecutablePath,CommandLine | Tee-Object "$EvidenceDirectory\listener-before-stop.txt"
if($Owner.ExecutablePath -notlike "$ExpectedOldRelease\*"){throw 'listener executable is not the verified current release'}
if($Owner.CommandLine -notmatch '(?i)-m\s+waitress' -or $Owner.CommandLine -notmatch '(?i)backend\.wsgi:app'){throw 'listener is not Forwarder Waitress WSGI'}
$Descendants=@(); $Pending=@($VerifiedPid)
while($Pending.Count){$ParentId=$Pending[0]; $Pending=@($Pending|Select -Skip 1); $Children=@(Get-CimInstance Win32_Process -Filter "ParentProcessId=$ParentId"); $Descendants+=$Children; $Pending+=@($Children|ForEach-Object {[int]$_.ProcessId})}
$Descendants | Select ProcessId,ParentProcessId,ExecutablePath,CommandLine | Tee-Object "$EvidenceDirectory\listener-descendants-before-stop.txt"
if(@($Descendants|Where-Object {$_.ExecutablePath -and $_.ExecutablePath -notlike "$ExpectedOldRelease\*"}).Count -ne 0){throw 'listener tree has a non-release executable'}
if((Get-ScheduledTask -TaskName $TaskName).State -ne 'Disabled'){throw 'task is not held; refusing runtime stop'}
```

[MUTATING — REQUIRES SEPARATE OPERATOR AUTHORIZATION]
```powershell
& "$env:SystemRoot\System32\taskkill.exe" /PID $VerifiedPid /T /F
if($LASTEXITCODE -ne 0){throw 'verified listener termination failed'}
$Deadline=(Get-Date).AddSeconds(60)
do {$Remaining=@(Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort $Port -State Listen -ErrorAction SilentlyContinue); if($Remaining.Count -eq 0){break}; Start-Sleep 1} while((Get-Date)-lt $Deadline)
if($Remaining.Count -ne 0){throw 'listener did not close'}
if((Get-ScheduledTask -TaskName $TaskName).State -ne 'Disabled'){throw 'task hold was lost after stop'}
```

Require approved traffic containment and DB-owner read-only confirmation of no in-flight application write transaction before migration.

### Recorded owner decision — ADR-043 runtime-drift containment checkpoint (2026-08-31)

The preceding PHASE 3/4 baseline is superseded **only for this containment
checkpoint** by the owner's written runtime-drift reconciliation decision.  The
decision records a material mismatch: the `Forwarder Backend Production` task
continues to bind `C:\1-webapp\forwarder-production\release-991d29a-20260829`,
while the one observed `127.0.0.1:5101` listener was served from
`C:\1-webapp\forwarder-production\release-fdfdd23-20260823`.  The staged
certified release remains non-serving at
`C:\1-webapp\forwarder-production\release-adcc5da-adr043`.

`DRIFT_CLASSIFICATION=HARD NO-GO — material lifecycle/runtime-ownership drift`
remains the governing classification for migration, activation, task
replacement, application cutover, IIS, CORS, and configuration work.  The
owner has supplied the separate decision required to authorize **only** the
following bounded recovery checkpoint:

1. Re-query and prove exactly one live listener and its ownership immediately
   before mutation.
2. Revalidate the known task definition: `cmd.exe`, a `991d29a` working
   directory, and consistent `991d29a` values in both `--repo` and
   `PYTHONPATH`; the task must be `Ready`, not already running or disabled.
3. Prove the listener is the `fdfdd23` release's Waitress
   `backend.wsgi:app` process, prove the staged `adcc5da` release is not
   serving, and enumerate every listener descendant.  The listener identity is
   its **anchored exact command-line invocation** of
   `C:\1-webapp\forwarder-production\release-fdfdd23-20260823.venv314\Scripts\python.exe`,
   followed by `-m waitress`, `--listen=127.0.0.1:5101`, and
   `backend.wsgi:app` (with only later arguments permitted).  Do not use an
   unanchored release-path substring.  Windows Python 3.14 may report the
   listener `ExecutablePath` as its base/system Python executable even when
   that command line invoked the release-local venv interpreter; therefore an
   `ExecutablePath`-under-release requirement is invalid and is not a gate.
   Each descendant must independently satisfy that same anchored approved
   release-local Python command-line identity; otherwise containment scope is
   unsafe.  No parent or arbitrary ancestor is in scope.
4. Disable (hold) the existing task **without registering, replacing, or
   otherwise modifying its definition**.  Re-query the task and listener;
   fail closed unless the hold is `Disabled` and the listener PID, executable,
   release, command line, and descendant scope are unchanged.
5. Invoke the existing runbook-governed `taskkill /PID <fresh listener PID> /T
   /F` method for that freshly approved listener only, prove zero listeners on
   `127.0.0.1:5101`, prove the task remains disabled, and stop.

Historical PIDs (`11028`, `30760`, `51476`, and `51756`) are evidence only and
must never be used as live selection values.  In particular, do not infer that
a missing historical parent must be stopped, and do not stop the non-listening
expected-release tree.  A task-definition mismatch, a listener count other
than one, ambiguous ownership, a release/Waitress/WSGI mismatch, a staged
release listener, a changed post-hold topology, an unproven descendant, or a
lost task hold, or a descendant that cannot independently prove the exact
release-local Python invocation is a no-go: stop immediately and escalate
without terminating a process.

This decision authorizes no migration, database connection or write, generic
Alembic operation, staged-release start, task cutover or replacement, health or
readiness validation of the staged release, IIS change, CORS change,
`production.env` change, or rollback.  `APPLICATION_ROLLBACK !=
DATABASE_DOWNGRADE` remains controlling.  After the zero-listener proof, stop
and reassess; the next checkpoint has not been authorized by this decision.

## PHASE 5 — Target migration and Direct Shipment gate

The migration is additive: nullable `operational_shipment.primary_responsible_expert_id`, restrict FK to `expert_user`, and index, with no backfill. Its downgrade refuses when responsibility evidence exists; application rollback is not database downgrade.

[READ-ONLY]
```powershell
Set-Location $NewRelease
.\.venv\Scripts\python.exe -m backend.migration_cli current
.\.venv\Scripts\python.exe -m backend.migration_cli check
```

Require `20260906_global_logistics_point_materialization`, sole target head, fresh backup, zero listener, and disabled task. With separate authorization:

```powershell
.\.venv\Scripts\python.exe -m backend.migration_cli upgrade 20260907_direct_shipment_responsibility --confirm
.\.venv\Scripts\python.exe -m backend.migration_cli current
.\.venv\Scripts\python.exe -m backend.migration_cli check
if(@(Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort $Port -State Listen -ErrorAction SilentlyContinue).Count -ne 0){throw 'migration gate failed: listener reappeared'}
& "$PgBin\psql.exe" -X -h 127.0.0.1 -p 5432 -U postgres -d $Database -c "BEGIN TRANSACTION READ ONLY; SELECT count(*) FILTER (WHERE s.source_type='direct') total_direct_shipments,count(*) FILTER (WHERE s.source_type='direct' AND s.primary_responsible_expert_id IS NULL) missing_primary_responsible,count(*) FILTER (WHERE s.source_type='direct' AND (u.id IS NULL OR NOT u.is_active)) inactive_or_missing_responsible,count(*) FILTER (WHERE s.source_type='direct' AND s.primary_responsible_expert_id IS NOT NULL AND m.id IS NULL) cross_tenant_responsible FROM operational_shipment s LEFT JOIN expert_user u ON u.id=s.primary_responsible_expert_id LEFT JOIN operational_membership m ON m.user_id=s.primary_responsible_expert_id AND m.organization_id=s.organization_id AND m.is_active; COMMIT;"
```

Stop activation if any invalid count is nonzero. No repair/backfill is authorized.

## PHASE 6 — Exact certified start and health [MUTATING — REQUIRES SEPARATE OPERATOR AUTHORIZATION]

```powershell
if(@(Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort $Port -State Listen -ErrorAction SilentlyContinue).Count -ne 0){throw 'activation blocked: port 5101 is not free'}
if((Get-ScheduledTask -TaskName $TaskName).State -ne 'Disabled'){throw 'task was not held'}
Enable-ScheduledTask -TaskName $TaskName; Start-ScheduledTask -TaskName $TaskName
$Deadline=(Get-Date).AddSeconds(60)
do {$After=@(Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort $Port -State Listen -ErrorAction SilentlyContinue); if($After.Count -eq 1){break}; Start-Sleep 1} while((Get-Date)-lt $Deadline)
if($After.Count -ne 1){throw "activation failed: expected one listener; found $($After.Count)"}
$NewOwner=Get-CimInstance Win32_Process -Filter "ProcessId=$($After[0].OwningProcess)"
$NewOwner | Select ProcessId,ParentProcessId,ExecutablePath,CommandLine | Tee-Object "$EvidenceDirectory\listener-after-start.txt"
if($NewOwner.ExecutablePath -notlike "$NewRelease\*" -or $NewOwner.CommandLine -notmatch '(?i)-m\s+waitress' -or $NewOwner.CommandLine -notmatch '(?i)backend\.wsgi:app'){throw 'listener is not certified Forwarder Waitress'}
(Invoke-WebRequest -UseBasicParsing http://127.0.0.1:5101/api/health).StatusCode
(Invoke-WebRequest -UseBasicParsing http://127.0.0.1:5101/api/health/ready).StatusCode
```

Require 200 twice, target revision, one certified listener, and no blocking logs. IIS change is **NOT_REQUIRED**; no IIS configuration change is authorized by this runbook.

## PHASE 7 — Browser, authorization smoke, and evidence [READ-ONLY]

Use confirmed `https://samand.logisticmarket.ir` (not unproven `samand.forwarderet.ir`) for page/auth/tenant identity/admin and expert flows plus browser `/api/*` calls. CORS remains `NOT_VERIFIED` until runtime/browser evidence proves it; stop on CORS/API failure and make no CORS change.

Existing-data smoke must prove: Platform Admin tenant request/shipment denies; Organization Admin allows only existing explicit capability and denies platform diagnostics; Expert permits only own assigned request/child and denies unassigned/foreign IDs; `role=admin` does not elevate; capability cannot allow foreign access. Reassignment A→B is `MANUAL_EXISTING_DATA_VALIDATION_REQUIRED`, because it mutates state; do not create test data. Record XML before/after, release manifest, backup hash, migration output, Direct Shipment gate, listener identities, health, browser/Samand, and CORS status.

## Rollback decision tree

| Event | Containment / recovery |
|---|---|
| Before task replacement | Do nothing to current service. |
| XML/ownership/hold/zero-listener gate fails | NO-GO; re-register exact before XML if changed, and do not touch listener. |
| Verified stop fails | Keep task disabled and evidence; escalate. Never kill a parent or generic restart. |
| Migration fails before commit | Keep task disabled/quiescent; verify revision and escalate. |
| Migration succeeds, activation/health/smoke fails | Disable task. Roll app back only if old-app/new-schema compatibility is approved; otherwise DB owner restores verified backup. |
| Wrong release observed | Disable task, do not start it, re-register exported before XML, then re-evaluate compatibility. |
| Downgrade refuses | Forward-fix or verified backup restore; never bypass guard. |
| Frontend/IIS issue | No IIS rollback is included; it needs separately approved IIS evidence. |

Never equate application rollback with schema downgrade or issue blind `alembic downgrade`.
