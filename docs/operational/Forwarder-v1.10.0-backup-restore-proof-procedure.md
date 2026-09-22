# Forwarder v1.10.0 Fresh Backup and Restore-Proof Procedure

Status: **BACKUP AND RESTORE PROOF COMPLETE / CORRECTED READ-ONLY RECONCILIATION PENDING**

This procedure consumed the successful r3 live read-only preflight. The returned backup and isolated restore proof are now evidence inputs to corrected collector `r5`; they do not by themselves authorize Production validate-only, migration, or deployment. Codex does not access Production. A human operator runs every server command locally on `SRV8756807400`.

## Fixed identities

- Product version: `1.10.0`
- Current Production application commit: `e97338661d7dfa40766a5a1dce1f0f2e1cdc9bc4`
- Target application source: `e36ee7cee157657c97dc42a539eaf1909f510a33`
- Current database revision: `20260921_shipment_evidence_ownership`
- Target database revision: `20260926_fixed_shipment_responsible_expert`
- Qualified Product package SHA256: `2fdef076516273f82044c9b5aa1b2ad03bb8a97423de6c4f7bcb0adec2b0eacf`
- `REFERENCE_IMPACT=NONE`

## Phase A — Production server backup

Copy only:

`D:\1-webapp\forwarder-production-releases\Forwarder-v1.10.0-Backup-Restore-Proof-Toolkit-e36ee7cee157-r1\server\New-ForwarderV110PreDeploymentBackup.ps1`

to:

`C:\1-webapp\forwarder-production-preflight\v1.10.0-backup-r1\New-ForwarderV110PreDeploymentBackup.ps1`

Run exactly:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\1-webapp\forwarder-production-preflight\v1.10.0-backup-r1\New-ForwarderV110PreDeploymentBackup.ps1" -EnvironmentFile "C:\1-webapp\forwarder-runtime\production.env" -ApprovedBackupRoot "C:\1-webapp\forwarder-backups" -PsqlPath "C:\Program Files\PostgreSQL\18\bin\psql.exe" -PgDumpPath "C:\Program Files\PostgreSQL\18\bin\pg_dump.exe" -PgRestorePath "C:\Program Files\PostgreSQL\18\bin\pg_restore.exe" -ExpectedComputerName "SRV8756807400" -RestoreOwner "$env:USERDOMAIN\$env:USERNAME" -RetentionDays 30 -CreateBackup -ConfirmBackup
```

The command reads the established environment file without printing it, accepts the proven `postgresql+psycopg2://` URL shape, proves PostgreSQL 18/PRIMARY/exact baseline revision, creates a new custom-format dump, checks nonzero size and `pg_restore --list`, records SHA256 and retention/provenance metadata, and emits one sanitized result. It does not stop the application, migrate the database, or deploy.

Expected outputs use one shared UTC token:

- `C:\1-webapp\forwarder-backups\forwarder-v1.10.0-predeploy-<UTC>.dump`
- `C:\1-webapp\forwarder-backups\forwarder-v1.10.0-predeploy-<UTC>.dump.list.txt`
- `C:\1-webapp\forwarder-backups\forwarder-v1.10.0-predeploy-<UTC>.dump.sha256.txt`
- `C:\1-webapp\forwarder-backups\Forwarder-v1.10.0-PreDeploymentBackup-<UTC>.json`

Return only the sanitized JSON to chat. Do not return the dump, environment file, catalog contents, credentials, logs, or business rows.

## Phase B — protected transfer decision

After the JSON passes review, a named backup/restore owner must approve a protected operator channel and an access-controlled local destination outside Git, cloud-sync, public shares, and the repository. Transfer the exact dump and sanitized JSON through that channel. Recalculate SHA256 locally and require an exact match before restore.

If no protected channel and controlled PostgreSQL 18 destination are approved, stop with `FRESH_BACKUP_RESTORE_PROOF=PENDING`. Backup existence alone is not restore proof.

## Phase C — isolated restore and five-migration rehearsal

Keep the toolkit `restore` directory on the controlled laptop. Create or select an empty, access-controlled evidence directory and an owned work root. Run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "D:\1-webapp\forwarder-production-releases\Forwarder-v1.10.0-Backup-Restore-Proof-Toolkit-e36ee7cee157-r1\restore\Invoke-ForwarderV110ProductionRestoreProof.ps1" -BackupEvidencePath "<exact protected local path to Forwarder-v1.10.0-PreDeploymentBackup-UTC.json>" -DumpPath "<exact protected local path to forwarder-v1.10.0-predeploy-UTC.dump>" -PackagePath "D:\1-webapp\forwarder-production-releases\Forwarder-Production-v1.10.0-e36ee7cee157.zip" -ExpectedPackageSha256 "2fdef076516273f82044c9b5aa1b2ad03bb8a97423de6c4f7bcb0adec2b0eacf" -EvidenceDirectory "<exact access-controlled evidence directory>" -WorkRoot "<exact owned disposable work root>" -PgBin "C:\Program Files\PostgreSQL\18\bin" -LocalHost "127.0.0.1" -LocalPort 5432 -LocalAdminUser "postgres" -LocalMaintenanceDatabase "postgres" -MaximumBackupAgeHours 8 -Execute -ConfirmDisposableRestore
```

The operator enters only the **local disposable PostgreSQL** password at the secure prompt. The command never requests or uses Production credentials. It:

1. verifies backup evidence, freshness, byte size, and SHA256;
2. verifies the frozen Production package and exact source/head identity;
3. creates one uniquely named disposable local database;
4. restores with `--exit-on-error --single-transaction --no-owner --no-privileges`;
5. proves PostgreSQL 18, the exact baseline revision, aggregate table/Shipment/Quote counts, all baseline compatibility checks, and zero ADR-047 unresolved categories;
6. uses the qualified package runtime to apply exactly `20260922` through `20260926`;
7. proves target current/head, one head, and no pending migration;
8. runs every governed post-migration assertion plus the ADR-047 classifier;
9. removes the generated disposable database and extracted work directory; and
10. writes `<dump filename>.restore-evidence.json` containing only hashes, revisions, aggregate counts, PASS states, and sanitized identities.

The restore tool fails closed and refuses cleanup unless the generated database name matches its private `forwarder_v110_restoreproof_<timestamp>_<random>` pattern.

## Required closure

Do not advance to Production validate-only until all are evidenced:

```text
FRESH_PRODUCTION_BACKUP=PASS
BACKUP_SHA256_RECORDED=YES
PG_RESTORE_CATALOG_VALID=YES
ISOLATED_RESTORE=PASS
PRODUCTION_DERIVED_MIGRATION_REHEARSAL=PASS
TARGET_MIGRATION_HEAD=20260926_fixed_shipment_responsible_expert
ADR047_PRODUCTION_DATA=PASS
PRODUCTION_DATABASE_MUTATED=NO
PRODUCTION_DEPLOYMENT_PERFORMED=NO
```

## Phase D — authoritative read-only reconciliation

Place the exact restore-evidence JSON beside its source dump on the protected Production backup root, preserving the required `<dump filename>.restore-evidence.json` name. Run only the qualified `r5` read-only collector. It independently calculates the latest dump SHA256 and requires exact agreement across the dump, hash sidecar, backup evidence, and restore evidence. It also requires the fixed source revision, target revision, application source, package SHA256, PostgreSQL major, migration rehearsal, post-migration assertions, ADR-047 result, disposable cleanup, and zero-Production-mutation declarations.

The pre-Execute gate is closed only when the returned sanitized result contains:

```text
collector_status=PASS
collection_errors=0
backup_readiness.pre_execute_backup_restore_proof_status=PASS
backup_readiness.pre_execute_backup_restore_proof_ready=true
backup_readiness.restore_evidence.state=VERIFIED_EXACT_DUMP
deployment_prerequisite_status=READY_FOR_SEPARATE_GO_REVIEW
production_mutation_performed=false
```

`fresh_deployment_window_backup_present=false` remains correct at this read-only phase. It describes a separate checkpoint that the deployer must create after writer containment and before migration. The deployer records that checkpoint's exact identity and refuses migration if its timing, baseline revision, size, hash, catalog, ownership, retention, or mutation declarations fail.

Until Phase D passes, `PRE_EXECUTE_BACKUP_RESTORE_PROOF=PENDING_RECONCILIATION`. Even after Phase D passes, `DEPLOYMENT_WINDOW_BACKUP=PENDING_EXECUTE_AFTER_WRITER_CONTAINMENT` and separate human GO remain required.
