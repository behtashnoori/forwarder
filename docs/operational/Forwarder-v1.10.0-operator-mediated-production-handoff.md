# Forwarder v1.10.0 Operator-Mediated Production Handoff

Status: two human-run Execute attempts stopped safely during writer containment and before deployment-window backup or migration. Revision `r4` fixed the first attempt's Windows PowerShell 5.1 `$pid`/`$PID` collision. The second attempt proved a distinct defect: the exact Waitress listener may outlive its Scheduled Task/wrapper parent briefly, while `r4` performed a single immediate socket check after `Stop-Process`. Checkpoint A restored the prior application after each failure. A fresh `r5` read-only collection after the second failure proved the prior release active, health/readiness 200, database revision `20260921_shipment_evidence_ownership`, one Alembic head, zero schema-drift blockers, and zero hard ADR-047 blockers. Deployment tooling `r5` closes only the asynchronous listener-teardown defect with a bounded, exact-PID, replacement-aware wait. It retains two non-interchangeable gates: (1) an exact, fresh Production dump with hash-bound isolated restore and five-migration proof before validate-only or Execute authorization; and (2) a newer rollback checkpoint created by Execute only after writer containment and before migration.

This handoff does not authorize deployment. Codex did not access Production. A human operator must run the read-only collector locally on the Windows Production server and return its sanitized JSON before a release authority can decide GO/NO-GO.

## Current operator stop point

Do not assume the current pre-Execute backup/restore evidence remains within its eight-hour freshness gate. Hold deployment bundle `r5` on the laptop. Rerun collector `r5`; if the proof is stale, repeat the full governed Production backup, protected transfer, isolated PostgreSQL 18 restore, exact five-migration rehearsal, restore-evidence sidecar return, and collector `r5`. Obtain a separate READY review, then perform final validate-only with a third, newly generated absent target path. Preserve both failed targets as inactive evidence and never reuse or manually delete them. No Execute command or authority is supplied here.

`POST_FAILURE_LIVE_PRODUCTION_READ_ONLY_PREFLIGHT=PASS`

`PRE_EXECUTE_BACKUP_RESTORE_PROOF=FRESH_REPLACEMENT_REQUIRED`

`DEPLOYMENT_WINDOW_BACKUP=PENDING_EXECUTE_AFTER_WRITER_CONTAINMENT`

The following collector instructions apply only after the fresh backup and exact isolated restore proof have been completed and returned to the approved backup root.

## Qualified r5 collector rerun procedure

Copy the contents of:

`D:\1-webapp\forwarder-production-releases\Forwarder-v1.10.0-Read-Only-Preflight-Bundle-e36ee7cee157-r5\`

to this temporary, non-release directory on the Production server:

`C:\1-webapp\forwarder-production-preflight\v1.10.0-r5\`

The copied directory must contain:

- `Collect-ForwarderV110ProductionReadOnly.ps1`
- `Invoke-ForwarderV110ReadOnlySql.py`
- `legacy-production-witness.json`
- `BUNDLE-MANIFEST.json`
- `BUNDLE-INVENTORY.json`
- `README-FIRST.md`
- `SHA256SUMS.txt`
- `sql\adr047-production-classifier.sql`
- `sql\migration-compatibility-readonly.sql`

Run exactly one command locally on the Production server:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\1-webapp\forwarder-production-preflight\v1.10.0-r5\Collect-ForwarderV110ProductionReadOnly.ps1" -OutputDirectory "C:\1-webapp\forwarder-production-preflight\v1.10.0-r5"
```

This command is read-only except for creating its sanitized result file in the specified temporary tooling directory. It does not stage a release, create a backup, migrate the database, stop a process, or change IIS or Scheduled Tasks.

## Phase 2 — Bring sanitized output back

Return the single newly created file matching:

`C:\1-webapp\forwarder-production-preflight\v1.10.0-r5\Forwarder-v1.10.0-Production-ReadOnly-Preflight-<UTC>.json`

Do not return `production.env`, credentials, connection strings, raw customer data, logs, or database dumps.

## Phase 3 — Evaluate GO/NO-GO

The release authority reviews the returned collector result. GO requires exact runtime/task/IIS agreement, one database revision at `20260921_shipment_evidence_ownership`, zero schema-drift blockers, and these ADR-047 values:

- `fixed_owner_ambiguous_count=0`
- `fixed_owner_contradiction_count=0`
- `fixed_owner_other_unresolved_count=0`

Any collector error, identity disagreement, unexpected database revision, unsafe configuration, insufficient capacity, nonzero hard ADR-047 blocker, stale backup, dump/evidence/hash mismatch, incomplete restore proof, or aggregate state other than `READY_FOR_SEPARATE_GO_REVIEW` is NO-GO. The collector must report `restore_evidence.state=VERIFIED_EXACT_DUMP` and `pre_execute_backup_restore_proof_status=PASS`. It must continue to report `fresh_deployment_window_backup_present=false`, because that second checkpoint can exist only inside a later authorized Execute run after writer containment.

## Phase 4 — Only after GO, transfer the qualified Production package

Keep the deployment bundle on the laptop until a separate GO:

`D:\1-webapp\forwarder-production-releases\Forwarder-v1.10.0-Production-Deployment-Bundle-e36ee7cee157-r5.zip`

- Deployment bundle SHA256: `dc836c66abf5eaa3c2cd2fab16d31fcc27c3eadf9a0caeddebc9251824701ade`
- Authoritative deployer SHA256: `2e6d2e169732786be56ac803d67a6c4dc33d005d395120a526d0124b7245c219`
- Writer-containment bound: 15 seconds maximum, 250 ms polling, and a continuous 2-second quiet period; a replacement PID fails closed and is not terminated.

Qualified package identity:

- Product version: `1.10.0`
- Application source: `e36ee7cee157657c97dc42a539eaf1909f510a33`
- Target database head: `20260926_fixed_shipment_responsible_expert`
- Package: `Forwarder-Production-v1.10.0-e36ee7cee157.zip`
- Package SHA256: `2fdef076516273f82044c9b5aa1b2ad03bb8a97423de6c4f7bcb0adec2b0eacf`
- Package size: `23396431` bytes

## Phase 5 — Run validate-only on the server

After an approved deployment bundle transfer, the operator runs `Deploy-ForwarderV110Production.ps1 -ValidateOnly` with the exact returned `r5` preflight JSON, package path, package SHA256, and a new absent immutable target release path. Validate-only refuses any aggregate other than `READY_FOR_SEPARATE_GO_REVIEW`, rechecks the exact pre-Execute restore-proof identity contract, performs zero Production mutation, and has no safety-bypass switch.

## Phase 6 — Explicit human authorization

Validate-only PASS is not deployment authorization. The release authority, deployment owner, database owner, runtime owner, backup owner, and rollback owner must explicitly approve execution and the maintenance window.

## Phase 7 — Maintenance window

The operator confirms the live topology has not changed since collection, prevents concurrent operator activity, preserves the prior Scheduled Task XML and IIS physical path, and uses only the governed v1.10.0 deployer.

## Phase 8 — Fresh backup

Only after writer containment, the governed backup tool creates a second custom-format dump under the approved backup root. The deployer verifies nonzero size, `pg_dump` success, `pg_restore --list`, SHA256 and sidecar agreement, exact baseline revision, capacity, retention, sanitized database identity, and named restore owner. It records the evidence path, dump path, SHA256, size, creation time, and containment time in the deployment baseline before migration. A missing, pre-containment, failed, or unverified checkpoint blocks migration.

The earlier exact-dump isolated restore proves recoverability and the Production-derived migration path before Execute authorization. The newer deployment-window backup is the closest rollback checkpoint. Existing v1.10.0 policy does not label that newer dump as independently restored; if a release authority requires restore of those exact newer bytes, writers must remain contained and migration must not begin until that separate proof is completed and reviewed.

## Phase 9 — Migration

Migration is explicit and operator-controlled. Startup migration must remain disabled. The only target is:

`python -m backend.migration_cli upgrade 20260926_fixed_shipment_responsible_expert --confirm`

No stamp, generic uncontrolled `upgrade head`, raw data repair, automatic downgrade, or automatic restore is permitted.

## Phase 10 — Runtime and IIS cutover

The deployer stages a new immutable release, switches only the governed Scheduled Task release/runtime references, proves exact listener ownership, starts Waitress on the returned and approved loopback topology, and changes only the IIS physical release path. It does not recreate IIS, alter bindings/TLS/ARR rules, or broadly terminate Python processes.

## Phase 11 — Read-only post-deploy smoke

The verifier checks package/manifest identity, database head, task/runtime/listener ownership, local and public health/readiness, frontend/login reachability, numeric and invalid tracking denial, document storage continuity, IIS physical path, and read-only post-migration assertions. It creates no Product data.

## Phase 12 — Declare v1.10.0 current Production version

Only after all future live gates pass may the release authority declare Forwarder `1.10.0` current in Production and separately authorize any Production Product tag. This laptop-side tooling goal does not create that tag.

## Rollback and containment

- Checkpoint A, before migration: abandon the candidate and restore the verified prior application definition if necessary.
- Checkpoint B, after migration and before traffic: contain writers; require a release-owner/DBA forward-repair or separate restore decision.
- Checkpoint C, after Production traffic: stop new writes, prefer roll-forward, and require explicit data-loss acceptance before any restore decision.

The tooling never automatically downgrades Alembic or restores a Production database.

The abandoned targets `C:\1-webapp\forwarder-production\release-20260922060617-20260926_fixed_shipment_responsible_expert` and `C:\1-webapp\forwarder-production\release-20260922081228-20260926_fixed_shipment_responsible_expert` are preserved as failed-attempt evidence. No governed cleanup action exists in this release contract, and the deployer requires the target path to be absent. Therefore neither target may be deleted manually or reused; the final future validate-only must generate a third timestamped path that is completely absent.
