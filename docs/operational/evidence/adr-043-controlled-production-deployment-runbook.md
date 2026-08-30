# ADR-043 controlled production deployment runbook

Status: executable preparation only; it does not authorize deployment. Certified application source is `adcc5da2c6f6d696dbad15b9b2cd7900bd96bc9e` (835 passed, 0 failed, 92 skipped, 1 xfailed). ADR-037, ADR-042 and ADR-043 remain controlling: Platform Admin has no tenant-work access; role labels do not establish authority; capability never bypasses tenant fencing; and direct assignment creates no CRM right.

## Release-integrity stop gate

`scripts/build_release_package.py` is the repository’s governed immutable Git-worktree package builder, but it hard-codes Alembic head `20260906_global_logistics_point_materialization`. The certified ADR-043 commit has sole head `20260907_direct_shipment_responsibility`; the current builder will reject it. No versioned Scheduled Task launcher/XML exists either. Therefore: `EXECUTABLE_RUNBOOK_STATUS=READY_WITH_BLOCKERS`; `PRODUCTION_DEPLOYMENT_ELIGIBILITY=NO_GO`. Do not substitute the dirty worktree, package a later evidence commit, or run generic `alembic upgrade head`.

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

PRECONDITIONS: a reviewed builder update accepts precisely `20260907_direct_shipment_responsibility`; fresh output directory; exact Git object only. EXPECTED EFFECT: creates an immutable ZIP/sidecar only. STOP: nonzero gate, manifest SHA mismatch, or source commit mismatch. CONTAINMENT: discard only failed staging artifact.

```powershell
python D:\1-webapp\15-forwarder\scripts\build_release_package.py --repository D:\1-webapp\15-forwarder --authorized-commit $CertifiedCommit --output-directory D:\1-webapp\adr043-release-artifacts --release-label adr043-assigned-work
```

This is currently expected to stop at the documented builder-head mismatch. After repair, require manifest `source_commit=$CertifiedCommit`, target head, SHA-256 sidecar, and fresh `dist/index.html`/hashed assets. The certified delta has no frontend/package/runtime config changes, so no frontend feature change independently requires IIS transition.

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

## PHASE 5 — Scheduled Task/runtime preparation

The current task targets `release-991d29a-20260829`, while backend/IIS are `release-fdfdd23-20260823`; never restart before correction. Create a reviewed copy of the exported XML that changes only verified release Python/working-directory/action references and preserves triggers/principal/settings.

[MUTATING — REQUIRES SEPARATE OPERATOR AUTHORIZATION]

PRECONDITIONS: reviewed XML explicitly names `$NewRelease`; old XML preserved. EXPECTED EFFECT: replaces task definition only. STOP: unexpected XML diff/no release path. CONTAINMENT: re-register exact before XML.

```powershell
Register-ScheduledTask -TaskName $TaskName -Xml (Get-Content -Raw 'C:\approved\Forwarder-Backend-Production.adr043.xml') -Force
Export-ScheduledTask -TaskName $TaskName | Set-Content -Encoding utf8 "$env:TEMP\Forwarder-Backend-Production.after.xml"
```

## PHASE 6 — Schema migration

Migration `20260907_direct_shipment_responsibility` is additive: nullable `operational_shipment.primary_responsible_expert_id`, restrict FK to `expert_user`, index, no backfill. Its downgrade refuses when responsibility evidence exists. Use governed CLI, not generic Alembic.

[READ-ONLY]
```powershell
Set-Location $NewRelease
.\.venv\Scripts\python.exe -m backend.migration_cli current
.\.venv\Scripts\python.exe -m backend.migration_cli check
```

Require current `20260906...`, sole head target, correct sanitized target. STOP otherwise.

[MUTATING — REQUIRES SEPARATE OPERATOR AUTHORIZATION]

PRECONDITIONS: backup verified; writers stopped/traffic contained; new task configured but stopped. EXPECTED EFFECT: target migration only. STOP: any nonzero or pending postcheck. CONTAINMENT: no blind downgrade; keep stopped, use only compatibility-proven application rollback or database-owner backup restore.

```powershell
.\.venv\Scripts\python.exe -m backend.migration_cli upgrade 20260907_direct_shipment_responsibility --confirm
.\.venv\Scripts\python.exe -m backend.migration_cli current
.\.venv\Scripts\python.exe -m backend.migration_cli check
```

## PHASE 7 — Post-migration data gate [READ-ONLY]

```powershell
& "$PgBin\psql.exe" -X -h 127.0.0.1 -p 5432 -U postgres -d forwarder_prod_20260728_161711 -c "BEGIN TRANSACTION READ ONLY; SELECT count(*) FILTER (WHERE s.source_type='direct') total_direct_shipments,count(*) FILTER (WHERE s.source_type='direct' AND s.primary_responsible_expert_id IS NULL) missing_primary_responsible,count(*) FILTER (WHERE s.source_type='direct' AND (u.id IS NULL OR NOT u.is_active)) inactive_or_missing_responsible,count(*) FILTER (WHERE s.source_type='direct' AND s.primary_responsible_expert_id IS NOT NULL AND m.id IS NULL) cross_tenant_responsible FROM operational_shipment s LEFT JOIN expert_user u ON u.id=s.primary_responsible_expert_id LEFT JOIN operational_membership m ON m.user_id=s.primary_responsible_expert_id AND m.organization_id=s.organization_id AND m.is_active; COMMIT;"
```

STOP APPLICATION ACTIVATION if any invalid count is nonzero. No bulk repair/backfill is authorized. Membership’s `(organization_id,user_id)` uniqueness means join ambiguity is not representable.

## PHASE 8 — Backend activation

[MUTATING — REQUIRES SEPARATE OPERATOR AUTHORIZATION]

PRECONDITIONS: backup/migration/data gate pass, reviewed task points to `$NewRelease`. EXPECTED EFFECT: task-managed new backend. STOP: missing/multiple listener or process command/executable lacks new release. CONTAINMENT: stop new task; restore old XML; start old task only after old-app/new-schema compatibility is approved.

```powershell
Stop-ScheduledTask -TaskName $TaskName; Start-ScheduledTask -TaskName $TaskName
Get-NetTCPConnection -LocalPort 5101 -State Listen | Select-Object -First 1 | ForEach-Object {Get-CimInstance Win32_Process -Filter "ProcessId=$($_.OwningProcess)" | Select ProcessId,ExecutablePath,CommandLine}
```

## PHASE 9 — Health/readiness gate [READ-ONLY]

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:5101/api/health
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:5101/api/health/ready
```

Require 200 twice, target migration, expected one listener, no blocking logs.

## PHASE 10 — IIS/frontend

IIS change is **NOT_REQUIRED** for this certified authorization-only delta. Keep existing physical path; do not change IIS merely to make topology visually uniform. Later frontend deployment requires separately reviewed IIS commands and rollback evidence.

## PHASES 11–14 — smoke, Samand, observation, capture

Read-only existing-data smoke: Platform Admin tenant request/shipment denies; Organization Admin allows only existing explicit capability and denies platform diagnostics; Expert allows only own assigned request/child and denies same-tenant unassigned/foreign IDs; `role=admin` does not elevate; a capability does not allow foreign access. Reassignment A→B is `MANUAL_EXISTING_DATA_VALIDATION_REQUIRED` because it mutates state; do not create test data.

Use confirmed `https://samand.logisticmarket.ir` (not unproven `samand.forwarderet.ir`) to validate page/auth/tenant identity/admin and expert flows/browser `/api/*` calls. CORS is `NOT_VERIFIED`; STOP on browser CORS/API failure and do not mutate CORS. Observe owner-approved logs/5xx/health/task restarts, then record hashes, task XML before/after, backup, migration output, aggregate data gate, health/browser evidence.

## Rollback decision tree

| Event | Containment / recovery |
|---|---|
| Before migration | do nothing to current service |
| Migration fails pre-commit | keep new task stopped; verify revision; escalate |
| Migration succeeds, activation/health/smoke fails | contain traffic; app rollback only if old/new schema compatibility proved; otherwise DB-owner restore from backup |
| Downgrade refuses due responsibility evidence | forward-fix or verified backup restore; never bypass guard |
| Task targets wrong release | stop it; re-register before XML; do not restart |
| Later frontend failure | restore previously captured IIS path only under separate approval |

Never equate app rollback with schema rollback or issue blind `alembic downgrade`.
