# Forwarder v1.10.0 Operator-Mediated Production Handoff

Status: laptop-side tooling qualified; live Production preflight not yet run.

This handoff does not authorize deployment. Codex did not access Production. A human operator must run the read-only collector locally on the Windows Production server and return its sanitized JSON before a release authority can decide GO/NO-GO.

## Phase 1 — Copy and run the read-only Production collector

Copy the contents of:

`D:\1-webapp\forwarder-production-releases\Forwarder-v1.10.0-Read-Only-Preflight-Bundle-e36ee7cee157\`

to this temporary, non-release directory on the Production server:

`C:\1-webapp\forwarder-production-preflight\v1.10.0-20260921\`

The copied directory must contain:

- `Collect-ForwarderV110ProductionReadOnly.ps1`
- `BUNDLE-MANIFEST.json`
- `BUNDLE-INVENTORY.json`
- `README-FIRST.md`
- `SHA256SUMS.txt`
- `sql\adr047-production-classifier.sql`
- `sql\migration-compatibility-readonly.sql`

Run exactly one command locally on the Production server:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\1-webapp\forwarder-production-preflight\v1.10.0-20260921\Collect-ForwarderV110ProductionReadOnly.ps1" -OutputDirectory "C:\1-webapp\forwarder-production-preflight\v1.10.0-20260921"
```

This command is read-only except for creating its sanitized result file in the specified temporary tooling directory. It does not stage a release, create a backup, migrate the database, stop a process, or change IIS or Scheduled Tasks.

## Phase 2 — Bring sanitized output back

Return the single newly created file matching:

`C:\1-webapp\forwarder-production-preflight\v1.10.0-20260921\Forwarder-v1.10.0-Production-ReadOnly-Preflight-<UTC>.json`

Do not return `production.env`, credentials, connection strings, raw customer data, logs, or database dumps.

## Phase 3 — Evaluate GO/NO-GO

The release authority reviews the returned collector result. GO requires exact runtime/task/IIS agreement, one database revision at `20260921_shipment_evidence_ownership`, zero schema-drift blockers, and these ADR-047 values:

- `fixed_owner_ambiguous_count=0`
- `fixed_owner_contradiction_count=0`
- `fixed_owner_other_unresolved_count=0`

Any collector error, identity disagreement, unexpected database revision, unsafe configuration, insufficient capacity, missing backup readiness, or nonzero hard ADR-047 blocker is NO-GO.

## Phase 4 — Only after GO, transfer the qualified Production package

Keep the deployment bundle on the laptop until a separate GO:

`D:\1-webapp\forwarder-production-releases\Forwarder-v1.10.0-Production-Deployment-Bundle-e36ee7cee157.zip`

Qualified package identity:

- Product version: `1.10.0`
- Application source: `e36ee7cee157657c97dc42a539eaf1909f510a33`
- Target database head: `20260926_fixed_shipment_responsible_expert`
- Package: `Forwarder-Production-v1.10.0-e36ee7cee157.zip`
- Package SHA256: `2fdef076516273f82044c9b5aa1b2ad03bb8a97423de6c4f7bcb0adec2b0eacf`
- Package size: `23396431` bytes

## Phase 5 — Run validate-only on the server

After an approved deployment bundle transfer, the operator runs `Deploy-ForwarderV110Production.ps1 -ValidateOnly` with the exact returned preflight JSON, package path, package SHA256, and a new absent immutable target release path. Validate-only performs zero Production mutation and has no safety-bypass switch.

## Phase 6 — Explicit human authorization

Validate-only PASS is not deployment authorization. The release authority, deployment owner, database owner, runtime owner, backup owner, and rollback owner must explicitly approve execution and the maintenance window.

## Phase 7 — Maintenance window

The operator confirms the live topology has not changed since collection, prevents concurrent operator activity, preserves the prior Scheduled Task XML and IIS physical path, and uses only the governed v1.10.0 deployer.

## Phase 8 — Fresh backup

The governed backup tool creates a custom-format dump under the approved backup root only after explicit confirmation. It verifies nonzero size, `pg_dump` success, `pg_restore --list`, SHA256, capacity, retention, sanitized database identity, and named restore owner. A failed or unverified backup blocks migration.

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
