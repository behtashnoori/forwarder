# ADR-043 controlled production deployment runbook

Status: written production authorization recorded; execution remains pending mandatory live gates. Certified application source is `adcc5da2c6f6d696dbad15b9b2cd7900bd96bc9e` (835 passed, 0 failed, 92 skipped, 1 xfailed). ADR-037, ADR-042 and ADR-043 remain controlling: Platform Admin has no tenant-work access; role labels do not establish authority; capability never bypasses tenant fencing; and direct assignment creates no CRM right.

## Integrity, current topology, and historical boundary

The release builder materializes a detached worktree from the requested 40-character object, rejects a dirty materialization, builds `dist` there, and records source/head/file hashes. Its guard is `20260907_direct_shipment_responsibility`. Never package this later tooling/runbook commit, substitute the dirty worktree, or run generic `alembic upgrade head`.

Completed read-only preflight supersedes conflicting older lifecycle observations: `PREFLIGHT_COLLECTION_COMPLETE=YES`, `COLLECTION_ERRORS=0`. The latest recorded pre-cutover baseline has one listener on `127.0.0.1:5101`, with the listener command line invoking `C:\1-webapp\forwarder-production\release-991d29a-20260829\.venv314\Scripts\python.exe`; the existing `Forwarder Backend Production` task is `Ready` with working directory `C:\1-webapp\forwarder-production\release-991d29a-20260829`; IIS bindings for Samand/Forwarderet were present; database is `forwarder_prod_20260728_161711` at `20260906_global_logistics_point_materialization`; target is `20260907_direct_shipment_responsibility`; health and readiness are 200. Recorded PIDs are evidence only, never future runtime selection values. Any material drift from this baseline is a stop gate, not permission to restart.

Historical phase1b evidence is only a pattern: identify the listener, hold its scheduler, terminate only verified process scope, prove port closure, then bind and health-check. It does not establish current ports, releases, IIS, origins, DB cutover, or task XML. Do not run historical scripts, blindly use `Stop-Process`, `taskkill`, `Stop-ScheduledTask`, restart, task replacement, or `alembic downgrade`.

## PHASE 0 — Constants and authorization [READ-ONLY]

```powershell
$ErrorActionPreference='Stop'; $TaskName='Forwarder Backend Production'; $Port=5101
$ExpectedOldRelease='C:\1-webapp\forwarder-production\release-991d29a-20260829'
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
$Owner=Get-CimInstance Win32_Process -Filter "ProcessId=$VerifiedPid"
if($null -eq $Owner -or [string]::IsNullOrWhiteSpace($Owner.CommandLine)){throw 'listener identity unavailable'}
$Owner | Select ProcessId,ParentProcessId,ExecutablePath,CommandLine | Tee-Object "$EvidenceDirectory\listener-before-stop.txt"
$ApprovedPython="$ExpectedOldRelease\.venv314\Scripts\python.exe"
$ApprovedPattern='(?i)^\s*"?'+[regex]::Escape($ApprovedPython)+'"?\s+-m\s+waitress\s+--listen=127\.0\.0\.1:5101\s+backend\.wsgi:app(?:\s|$)'
if($Owner.CommandLine -notmatch $ApprovedPattern){throw 'listener is not the exact approved release-local Waitress invocation'}
$Descendants=@(); $Pending=@($VerifiedPid)
while($Pending.Count){$ParentId=$Pending[0]; $Pending=@($Pending|Select -Skip 1); $Children=@(Get-CimInstance Win32_Process -Filter "ParentProcessId=$ParentId"); $Descendants+=$Children; $Pending+=@($Children|ForEach-Object {[int]$_.ProcessId})}
$Descendants | Select ProcessId,ParentProcessId,ExecutablePath,CommandLine | Tee-Object "$EvidenceDirectory\listener-descendants-before-stop.txt"
if(@($Descendants|Where-Object {$_.CommandLine -notmatch $ApprovedPattern}).Count -ne 0){throw 'listener tree has an unproven descendant'}
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

### Latest read-only runtime reconciliation — restored pre-cutover baseline

The latest human-operator read-only snapshot recorded `LISTENER_COUNT=1` and a
fresh listener PID of `51476`. Its command line invoked
`C:\1-webapp\forwarder-production\release-991d29a-20260829\.venv314\Scripts\python.exe`
with `-m waitress`, `--listen=127.0.0.1:5101`, and `backend.wsgi:app`. Windows
reported the base Python executable path, which is not a release-identity gate.
The task release and listener release both resolved to
`C:\1-webapp\forwarder-production\release-991d29a-20260829`; the certified
staged `release-adcc5da-adr043` release was not serving. No operator mutation
caused this change.

Accordingly, the historical `fdfdd23` task/listener mismatch is **not present
in this snapshot**. The earlier `HARD NO-GO` remains historical evidence of
that mismatch and remains controlling if its material conditions recur; it does
not block the restored baseline solely because it once existed. The narrow
`fdfdd23` containment authorization is **historical and not currently
applicable**. It is conditionally available only if `fdfdd23` again becomes the
freshly verified sole listener and every condition in that owner decision is
met; it is not transferable to `991d29a`, another release, or a different
topology.

No new owner decision is required merely to perform the next checkpoint:
**PHASE 3 fresh read-only baseline revalidation**. That checkpoint must freshly
prove the task definition and runtime ownership as separate facts, including
the exact task bindings, one approved listener, no staged listener, no
`fdfdd23` Waitress runtime, no additional `991d29a` Waitress runtime, and no
mixed-runtime ambiguity. It performs no persistent evidence write and grants
no authority for any later mutating phase. Any failure is a NO-GO and requires
owner reassessment before proceeding.

### Latest proven lifecycle condition — ownership oscillation (2026-08-31)

The subsequent no-operator-mutation A -> B -> C observations supersede the
preceding “restored pre-cutover baseline” conclusion. Snapshot A proved the
sole `127.0.0.1:5101` listener in the `fdfdd23` Waitress tree; snapshot B
proved the sole listener in the `991d29a` Waitress tree; and latest snapshot C
again proved the sole listener in the `fdfdd23` tree while the Scheduled Task
remained bound to `991d29a`. This proves **runtime ownership oscillation
between two already-existing Forwarder Waitress process trees** and therefore
proves competing Forwarder runtime trees. It does not prove the handoff
mechanism, initiating component, a Scheduled Task run, or root cause.

`DRIFT_CLASSIFICATION=HARD NO-GO — competing Forwarder runtime trees with
listener-ownership oscillation` is now controlling. A current sole listener is
not evidence that the other Forwarder tree is absent, non-runnable, or outside
lifecycle scope. The prior narrow `fdfdd23` containment authorization is not
sufficient for this topology: it was limited to one freshly verified listener
and expressly excluded the non-listening expected-release tree. It does not
authorize termination of either historical PID, any parent, or either tree
merely because it is currently/non-currently listening.

The next governed checkpoint is a fresh **read-only multi-snapshot ownership
reconciliation**. It must enumerate both release-specific Forwarder Waitress
sets, their ancestry/descendancy, creation times where available, the sole
listener, and the unchanged task definition/state; it must also collect
available Task Scheduler operational events. All Waitress processes on other
ports or without an exact Forwarder release-local Python/Waitress/WSGI command
line are unrelated and excluded. Two or more snapshots can prove a further
observed transition without a corresponding recorded task run, but cannot by
themselves prove that either tree *can* become listener in every future state.

No containment mutation is authorized at this point. After a complete,
error-free read-only checkpoint, an owner must make a new decision explicitly
governing both competing Forwarder trees as one lifecycle-containment
operation, including an approved method, order, exact live scope, race
prevention, and zero-listener proof. That decision is not recorded or granted
by this evidence.

### Accepted multi-snapshot ownership evidence — owner decision required (2026-08-31)

The completed human-operated, read-only observation is accepted. Across three
snapshots over approximately 34 seconds, both exact Forwarder Waitress trees
remained alive: `fdfdd23` (`30760 -> 11028`) and `991d29a` (`51756 -> 51476`).
The sole listener changed from the `fdfdd23` tree to the `991d29a` tree without
operator mutation. The task stayed `Ready`, its release bindings remained
`991d29a`, and its `LastRunTime` did not change. The Operational event query
provided no matching event; this is not evidence that no Task Scheduler event
occurred.

Accordingly, `COMPETING_FORWARDER_TREES_PROVEN=YES`,
`LISTENER_OWNERSHIP_OSCILLATION_PROVEN=YES`, and
`TASK_RUN_CORRELATED_WITH_OBSERVED_HANDOFF=NO`. Root cause remains unproven.
The prior restored-`991d29a` conclusion is invalid. The production state
remains a HARD NO-GO for deployment, migration, activation, task cutover, IIS,
CORS, environment, or configuration mutation.

The required owner decision must govern both freshly classified Forwarder trees
as one containment operation. It must hold the task before termination, prove
the two exact two-process release-local command-line trees and no classified
descendants, then terminate the freshly identified top-level classified root of
each tree with its descendants as one coordinated operation. It must prove zero
listeners, zero classified processes for both releases, an unchanged disabled
task, and a non-serving staged release, then STOP for reassessment. Historical
PIDs remain evidence only. This record is not that owner decision and grants no
mutation.

### Accepted competing-runtime containment outcome — stop point (2026-08-31)

The human-operated containment authorization
`ADR-043-COMPETING-TREES-CONTAINMENT-20260831` is accepted as evidence of the
bounded lifecycle-containment operation only.  The operator reported a fresh
topology-gate PASS, disabled/held `Forwarder Backend Production` task PASS,
final live-topology-gate PASS, termination of both freshly classified
`fdfdd23` and `991d29a` Forwarder runtime trees, and three consecutive
zero-listener/zero-classified-process checks PASS.  The reported final result
is `CONTAINMENT_PROOF=PASS`.

This resolves the immediate competing-runtime **containment** condition.  It
does not identify or resolve the handoff mechanism, supervisor, scheduler, or
other root cause.  Therefore `ROOT_CAUSE_STATUS=UNPROVEN`; no conclusion about
why either historical tree could become listener is authorized from this
evidence.

Expected production state after that accepted result is:

| Gate | Required state for the next checkpoint |
| --- | --- |
| Scheduled Task | `Forwarder Backend Production` is `Disabled`. |
| Listener | No listener on `127.0.0.1:5101`. |
| Classified old runtimes | Zero processes matching either exact Forwarder release-local Waitress/`backend.wsgi:app` classification for `fdfdd23` or `991d29a`. |
| Certified staged release | `C:\1-webapp\forwarder-production\release-adcc5da-adr043` remains present and non-serving. |
| Database | `forwarder_prod_20260728_161711` remains at `20260906_global_logistics_point_materialization` until separately authorized migration. |

No migration was run, no production database write was performed, the staged
release was not started, and IIS, CORS, environment, runtime configuration,
and Scheduled Task definition were not changed by this containment result.
`APPLICATION_ROLLBACK != DATABASE_DOWNGRADE` remains controlling; automatic
Alembic downgrade remains prohibited.

The shortest safe next governed checkpoint is a fresh, error-free,
**read-only pre-cutover integrity and containment gate**.  It is deliberately
not a continuation of the containment authorization and it grants no mutation.
It must stop on any mismatch, missing evidence, listener, classified old
runtime, enabled task, changed staged content, database-identity mismatch,
revision mismatch, or missing target migration.  In particular, a staged
directory or a `source_commit` field alone is insufficient: the staged tree
must be verified against the known release artifact and its per-file manifest
before it can be considered the certified `adcc5da` release.

The release-manifest boundary is the builder's `files` inventory: `assemble()`
copies the selected source, deployment, backend, script, and freshly built
`dist` files, then records every file in that assembled package **before** it
writes `release-manifest.json`.  The staging procedure subsequently creates
the release-local `.venv` and its dependency files; Python imports may also
materialize `__pycache__` directories and `.pyc` files.  Those three classes
are consequently not release payload and are excluded only from the staged
*extra-file* inventory.  They are not exclusions from manifest verification:
every manifest record remains mandatory and is checked for existence, size,
and SHA-256.  No other staged extra is accepted.

Run the following manually on the production server only.  It is inspection
only: it does not start/stop processes, modify Scheduled Tasks, load or print
secrets from `production.env`, run a migration, or write to the database.  The
database queries explicitly use a read-only transaction.  It emits no
production evidence file; the operator must preserve the console output in the
approved evidence location outside this command.

```powershell
$ErrorActionPreference='Stop'; Set-StrictMode -Version Latest
$TaskName='Forwarder Backend Production'; $Port=5101
$StagedRelease='C:\1-webapp\forwarder-production\release-adcc5da-adr043'
$Artifact='C:\Users\Administrator\Desktop\Forwarder-adr043-assigned-work-adcc5da.zip'
$ArtifactSha256='af53fd7cc29f229e51a72fb02a3ffd0b1a9c46260af2fd37b83e993a4bdcea19'
$CertifiedCommit='adcc5da2c6f6d696dbad15b9b2cd7900bd96bc9e'
$CurrentRevision='20260906_global_logistics_point_materialization'
$TargetRevision='20260907_direct_shipment_responsibility'
$ProductionEnv='C:\1-webapp\forwarder-runtime\production.env'
$ExpectedDatabase='forwarder_prod_20260728_161711'
$OldReleases=@('C:\1-webapp\forwarder-production\release-fdfdd23-20260823','C:\1-webapp\forwarder-production\release-991d29a-20260829')
function Require([bool]$Condition,[string]$Message){if(-not $Condition){throw "NO-GO: $Message"}}
function HashText([string]$Text){$sha=[Security.Cryptography.SHA256]::Create();try{($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($Text))|ForEach-Object ToString x2)-join ''}finally{$sha.Dispose()}}
function IsRuntimeMaterializedPath([string]$Path){return $Path -match '(?i)^(?:\.venv(?:/|$)|.*(?:^|/)__pycache__(?:/|$)|.*\.pyc$)'}
function GetCanonicalManifestPath($Record){$path=[string]$Record.path;Require (-not [string]::IsNullOrWhiteSpace($path)) 'manifest record has an empty path';Require ($path -notmatch '[\\\x00]') "manifest path is not slash-normalized: $path";Require ($path -match '^[^/]+(?:/[^/]+)*$' -and $path -notmatch '(^|/)\.{1,2}(/|$)') "manifest path is unsafe: $path";return $path}
Require (Test-Path -LiteralPath $StagedRelease -PathType Container) 'staged release path is absent'
Require (Test-Path -LiteralPath $Artifact -PathType Leaf) 'known release artifact is absent'
Require ((Get-FileHash -LiteralPath $Artifact -Algorithm SHA256).Hash -eq $ArtifactSha256) 'known release artifact hash differs from accepted evidence'
$ManifestPath=Join-Path $StagedRelease 'release-manifest.json'; Require (Test-Path -LiteralPath $ManifestPath -PathType Leaf) 'staged release manifest is absent'
$Manifest=Get-Content -Raw -LiteralPath $ManifestPath|ConvertFrom-Json
Require ($Manifest.manifest_schema -eq 'forwarder-release-content-v2') 'unexpected staged manifest schema'
Require ($Manifest.source_commit -eq $CertifiedCommit) 'staged manifest source commit is not certified SHA'
Require ($Manifest.alembic_head -eq $TargetRevision) 'staged manifest target head is not approved target'
$records=@($Manifest.files); Require ($records.Count -gt 0) 'staged manifest has no file inventory'
$manifestPaths=[System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
$canonical=[Text.StringBuilder]::new()
for($index=0;$index -lt $records.Count;$index++){$record=$records[$index];$relative=GetCanonicalManifestPath $record;Require ($relative -ne 'release-manifest.json') 'manifest must not govern itself';Require (-not (IsRuntimeMaterializedPath $relative)) "manifest record crosses runtime-materialization boundary: $relative";Require ($manifestPaths.Add($relative)) "duplicate manifest path: $relative";if($index -gt 0){Require ([StringComparer]::Ordinal.Compare($records[$index-1].path,$relative) -lt 0) 'manifest records are not sorted by canonical path'};Require ($record.bytes -is [long] -and $record.bytes -ge 0) "manifest byte length is invalid: $relative";$declaredHash=[string]$record.sha256;Require ($declaredHash -match '^[0-9a-f]{64}$') "manifest SHA-256 is invalid: $relative";$path=Join-Path $StagedRelease $relative.Replace('/','\');Require (Test-Path -LiteralPath $path -PathType Leaf) "manifest file missing: $relative";$item=Get-Item -LiteralPath $path;Require ($item.Length -eq [int64]$record.bytes) "manifest size mismatch: $relative";$hash=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant();Require ($hash -eq $declaredHash) "manifest hash mismatch: $relative";[void]$canonical.Append($relative).Append([char]0).Append($declaredHash).Append("`n")}
Require (('sha256:'+ (HashText $canonical.ToString())) -eq $Manifest.content_hash) 'staged content hash differs from manifest'
$actualPayloadPaths=[System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal);$runtimeExcluded=[System.Collections.Generic.List[string]]::new()
Get-ChildItem -LiteralPath $StagedRelease -Recurse -File|ForEach-Object {$relative=$_.FullName.Substring($StagedRelease.Length).TrimStart('\').Replace('\','/');if($relative -eq 'release-manifest.json'){return};if(IsRuntimeMaterializedPath $relative){$runtimeExcluded.Add($relative);return};Require ($actualPayloadPaths.Add($relative)) "duplicate staged payload path: $relative"}
$unexpected=@($actualPayloadPaths|Where-Object {-not $manifestPaths.Contains($_)});Require ($unexpected.Count -eq 0) "non-payload staged file absent from manifest: $($unexpected -join ', ')"
Write-Output 'MANIFEST_GOVERNED_PAYLOAD_BOUNDARY=release-manifest.json files inventory only';Write-Output 'RUNTIME_EXCLUSIONS=.venv/**,**/__pycache__/**,**/*.pyc';Write-Output "RUNTIME_EXCLUDED_FILE_COUNT=$($runtimeExcluded.Count)"
$targetFile=Join-Path $StagedRelease "backend\migrations\versions\$TargetRevision.py"; Require (Test-Path -LiteralPath $targetFile -PathType Leaf) 'target migration is absent from staged release'
$listeners=@(Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort $Port -State Listen -ErrorAction SilentlyContinue); Require ($listeners.Count -eq 0) '127.0.0.1:5101 is not free'
$task=Get-ScheduledTask -TaskName $TaskName; Require ($task.State -eq 'Disabled') 'Scheduled Task is not Disabled'
$procs=@(Get-CimInstance Win32_Process|Where-Object {$_.CommandLine -match '(?i)-m\s+waitress' -and $_.CommandLine -match '(?i)backend\.wsgi:app'})
foreach($old in $OldReleases){$matches=@($procs|Where-Object {$_.CommandLine -like "$old*"});Require ($matches.Count -eq 0) "classified old runtime reappeared: $old"}
$stagedMatches=@($procs|Where-Object {$_.CommandLine -like "$StagedRelease*"});Require ($stagedMatches.Count -eq 0) 'staged release is serving'
Require (Test-Path -LiteralPath $ProductionEnv -PathType Leaf) 'production.env is absent'
$dbLine=Get-Content -LiteralPath $ProductionEnv|Where-Object {$_ -match '^\s*DATABASE_URL\s*='}|Select-Object -First 1;Require ($null -ne $dbLine) 'DATABASE_URL is absent from production.env'
$dbUri=[uri](($dbLine -replace '^\s*DATABASE_URL\s*=\s*','').Trim(' ',"'",'"'));Require ($dbUri.AbsolutePath.Trim('/') -eq $ExpectedDatabase) 'production database identity differs from expected database'
$psql='C:\Program Files\PostgreSQL\18\bin\psql.exe';Require (Test-Path -LiteralPath $psql -PathType Leaf) 'expected psql executable is absent'
& $psql -X -v ON_ERROR_STOP=1 -h $dbUri.Host -p $dbUri.Port -U $dbUri.UserInfo.Split(':')[0] -d $ExpectedDatabase -c "BEGIN TRANSACTION READ ONLY; SELECT current_database() AS database_name, version_num AS alembic_revision FROM alembic_version; COMMIT;";Require ($LASTEXITCODE -eq 0) 'read-only database identity/revision query failed'
Write-Output 'ADR043_PRE_CUTOVER_READONLY_GATE=PASS'
```

The displayed database result must name
`forwarder_prod_20260728_161711` and exactly
`20260906_global_logistics_point_materialization`; otherwise the gate is
`NO-GO`.  A PASS supports an owner decision; it does not itself authorize the
migration, an application start, task enablement, health/readiness probing of a
new runtime, IIS work, CORS work, or configuration change.

If and only if the fresh gate passes, obtain a new written owner decision with
the following exact scope; this text is **proposed, not granted**:

> `ADR-043-CERTIFIED-ADCC5DA-CUTOVER-20260831` authorizes only the following
> sequential operations after accepted fresh read-only pre-cutover evidence:
> (1) execute the explicit migration command targeting
> `20260907_direct_shipment_responsibility` against
> `forwarder_prod_20260728_161711`, then verify current/check and the required
> Direct Shipment data gate; (2) if and only if every migration/data/zero-port
> gate passes, activate the exact integrity-verified staged release
> `C:\1-webapp\forwarder-production\release-adcc5da-adr043` by the reviewed
> task procedure; and (3) if and only if exactly one certified listener is
> proven, perform health and readiness verification.  No generic `alembic
> upgrade head`, runtime helper `migrate`, database downgrade, IIS change,
> CORS change, environment/configuration change, unrelated process action, or
> additional release substitution is authorized.  `APPLICATION_ROLLBACK !=
> DATABASE_DOWNGRADE` remains controlling; an Alembic downgrade is never
> automatic.  Stop and escalate on any gate failure.

The identifier above deliberately scopes three separately gated approvals:
explicit target migration, certified-release activation, and health/readiness
verification.  It does not combine or retroactively extend
`ADR-043-COMPETING-TREES-CONTAINMENT-20260831`.

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
