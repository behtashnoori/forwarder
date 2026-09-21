# Forwarder v1.10.0 Production Operator Tooling Evidence — 2026-09-21/22

## A. LPAF Governance Gate

LPAF v2.2 governed this Level B tooling mission, with the reviewed v2.3 Product Integration `REFERENCE_IMPACT` discipline applied. `REFERENCE_IMPACT=NONE`; no Product/reference truth, runtime behavior, migration, or accepted test was changed.

| Control | Identification |
|---|---|
| Mission | Prepare and qualify laptop-side tooling for a later operator-mediated Forwarder v1.10.0 Production release |
| Outcome | Frozen read-only preflight and separately held deployment bundles |
| Scope | Release tooling, tooling tests, evidence, and operator handoff only |
| Release owner | Human release authority |
| Deployment owner | Human Windows Production operator |
| Database owner | Human DBA/database owner |
| Runtime owner | Human Windows/IIS/Scheduled Task owner |
| Backup owner | Human DBA/backup owner |
| Rollback owner | Release authority with deployment and database owners |
| Source of truth | Canonical tooling baseline plus frozen accepted application source |
| Application source | `e36ee7cee157657c97dc42a539eaf1909f510a33` |
| Production operator model | Codex prepares; human copies/runs locally on server; human returns sanitized evidence |
| Version contract | Product remains `1.10.0` |
| Package contract | Production-stage immutable ZIP, complete inventories/checksums, pinned runtime, no mutable data/secrets |
| Database contract | Start at one `20260921_shipment_evidence_ownership`; explicitly target `20260926_fixed_shipment_responsible_expert` |
| Config contract | Presence/safe allowlisted values only; no secret values emitted; startup migration disabled |
| Launcher contract | System `cmd.exe`, explicit `PYTHONPATH`, release-local Python, governed external wrapper, Waitress `backend.wsgi:app` |
| IIS contract | Preserve site/app pool/bindings/TLS/ARR/rewrite/cache; change only governed physical path |
| Backup contract | Fresh verified custom dump with catalog, SHA256, capacity, retention, and restore owner before database migration |
| Rollback contract | Explicit A/B/C containment; no automatic downgrade or restore |
| Validate-only contract | All hard gates, zero Production mutation, no bypass |
| Mutation boundary | No Production action in this goal; future mutation requires returned evidence and separate authorization |
| Stop conditions | Identity/hash/revision mismatch, hard ADR-047 count, drift, config/capacity/backup/topology/ownership/migration/assertion/health/cutover failure |

## B. Operator-Mediated Deployment Model

Codex ran only on the laptop. No SSH, WinRM, RDP, SMB, PowerShell Remoting, remote database connection, remote copy, credential discovery, or Production command was used. The next gate is human execution of the read-only collector locally on the Production server.

## C. Target Product Identity

- Product version: `1.10.0`
- Accepted Product baseline: `a742628293359379cb476b782a2fe27e61a8db1f`
- Frozen application/release source: `e36ee7cee157657c97dc42a539eaf1909f510a33`
- Before database revision: `20260921_shipment_evidence_ownership`
- Target database revision: `20260926_fixed_shipment_responsible_expert`
- Alembic heads: one
- UAT tag/source cross-check: `forwarder-uat-v1.10.0` points to the frozen source

## D. Preserved Blocked Preflight Evidence

Historical BLOCKED evidence remains unmerged and preserved on local-only branch `codex/production-readiness-v1.10.0`, commit `92413e7b45ee1b5aef8b39e1178e7e9952e1ada8`. Its deployment plan and readiness preflight were read as authoritative tooling inputs, not converted into a live PASS claim.

## E. Production Deployment Pattern

The tooling preserves the established Windows topology: Scheduled Task to system `cmd.exe`, explicit `PYTHONPATH`, immutable release working directory, release-local Python, external governed wrapper `C:\1-webapp\forwarder-runtime\phase1b_production_cutover_runtime.py`, Waitress `backend.wsgi:app`, historical loopback `127.0.0.1:5101`, and IIS/ARR same-origin entry. The live collector must confirm the current topology.

## F. Production Package Design

The application payload is built from a clean detached checkout at the frozen application source, not from canonical or the tooling commit. Stage-specific scripts and metadata come from the bounded tooling branch. Runtime archive `Forwarder-Windows-Runtime-S7-RC-a257669-r4.zip` is pinned by SHA256 `f4a8f108aa89a78d7986f01fb8f6aa8af5e2d35e00617a8453eb1f15df945070` and verified against its complete manifest.

## G. Production Package Identity

- Path: `D:\1-webapp\forwarder-production-releases\Forwarder-Production-v1.10.0-e36ee7cee157.zip`
- Size: `23396431` bytes
- SHA256: `2fdef076516273f82044c9b5aa1b2ad03bb8a97423de6c4f7bcb0adec2b0eacf`
- Stage: `Production`
- Application commit/release source: `e36ee7cee157657c97dc42a539eaf1909f510a33`
- Target database head: `20260926_fixed_shipment_responsible_expert`
- Exact independent build A/B ZIP hash match: PASS
- Package inventory and application inventory exact match: PASS

## H. Read-Only Collector

`scripts/production/v1.10.0/Collect-ForwarderV110ProductionReadOnly.ps1` collects bounded host, task, listener/process, IIS, config presence/safe values, manifest/release identity, health, database identity/revision, migration compatibility, ADR-047 counts, capacity, external storage, bounded log health, and backup readiness. Every SQL payload uses `BEGIN TRANSACTION READ ONLY` and a defensive mutation-keyword guard. A controlled missing-infrastructure rehearsal returned BLOCKED, a sanitized JSON, `secret_values_emitted=false`, and `production_mutation_performed=false`.

## I. Secret Redaction

The collector never emits `production.env`, database URLs, passwords, signing secrets, tokens, private keys, or provider credentials. Database and role names are hashed. Command/log text is bounded and redacted. The package secret policy passed with only the repository-governed exact historical credential migration exception, whose remediation ancestry and hashes are declared and verified.

## J. ADR-047 Classifier

`sql/adr047-production-classifier.sql` is byte-for-byte the approved preserved classifier, SHA256 `16a50c18a4e824ce35564beca18ea11131ed105d3d0d13f51e08ca021c780bae`. It adds no `is_active`, Request-assignee, Admin/Manager, creator, Project, or latest-Expert fallback. PostgreSQL 18 rehearsal proved already-valid and deterministic-repair PASS plus fail-closed ambiguous lineage, persisted contradiction, missing accepted Quote, and invalid Direct owner cases.

## K. Migration Compatibility Checker

`sql/migration-compatibility-readonly.sql` checks the exact five-revision path, current revision, source relations/columns/types, historical Quote values and relationships, outbox/cargo prerequisites, target absence/collisions, constraint/index names, and pre-migration owner guard absence. The clean PostgreSQL 18 before-state returned all PASS.

## L. Schema Drift Checker

Compatibility results are reduced to bounded reason-coded `SCHEMA_DRIFT_BLOCKER_COUNT`. Only objects relevant to the pending path are compared. No remediation is attempted. The deployer blocks any nonzero count.

## M. Backup Readiness Checker

The collector reports mechanism, destination, tooling, latest sanitized metadata, restore evidence, and capacity. `New-ForwarderV110PreDeploymentBackup.ps1` defaults to validate-only; future creation requires `-CreateBackup -ConfirmBackup` and a named restore owner, then verifies dump success/size, restore catalog, SHA256, capacity, retention, and sanitized identity.

## N. Validate-Only Contract

`Deploy-ForwarderV110Production.ps1 -ValidateOnly` verifies package/hash/manifest/source/version/revisions, fresh collector schema/age/host, ADR-047 counts, drift, config, disk, backup readiness, live task/IIS/listener continuity, exact process ownership, and target absence. Fixture proof confirmed byte-identical state and absent target before/after validate-only.

## O. Production Deployer

The v1.10-specific deployer has no force/ignore switch. It stages an immutable release, captures prior task/IIS state, contains only the proven listener, creates/verifies the fresh backup, invokes the exact governed migration target, runs read-only post-migration assertions, rewrites only approved task release/runtime tokens, verifies the new listener and health, changes only IIS physical path, then runs the post-deploy verifier.

## P. Migration Contract

Startup migration is disabled. The deployer calls `python -m backend.migration_cli upgrade 20260926_fixed_shipment_responsible_expert --confirm`, followed by `current` and `check`. It does not stamp, use raw repair SQL, or call an uncontrolled generic head target. PostgreSQL 18 rehearsal upgraded explicitly from `20260921_shipment_evidence_ownership` through all five revisions to the one target head.

## Q. Runtime / Launcher

Task parsing requires one Exec action, system `cmd.exe`, the governed external wrapper, exact release-local Python, release working directory/PYTHONPATH agreement, `serve`, `127.0.0.1:5101`, and `backend.wsgi:app`. Broad Python termination is absent. Actual packaged runtime rehearsal on an alternate owned loopback port returned health 200 and readiness 200.

## R. IIS Cutover

The deployer imports the existing IIS configuration and changes only the named site's root physical path after new-backend health. The collector records site/app pool/bindings/HTTPS/rewrite/proxy/SPA facts. No IIS configuration was accessed or changed in Production.

## S. Post-Deploy Verifier

`Verify-ForwarderV110PostDeploy.ps1` is read-only except for its sanitized evidence file. It checks package/manifest, immutable target, task/runtime/listener, local/public health/readiness, frontend/login, tracking denial, target head, post-migration assertions, IIS path, and document storage continuity. Fixture execution passed; actual local packaged runtime health/readiness and both tracking denial probes passed.

## T. Rollback / Containment

`Invoke-ForwarderV110RollbackContainment.ps1` exposes explicit A/B/C checkpoints. Checkpoint A alone may restore the verified prior application definition. B/C contain writers and require human/DBA decisions. Automatic Alembic downgrade and database restore are explicitly reported `NO`. Tests prove prior-app restore is rejected after migration.

## U. Local Production-Like Rehearsal

Owned disposable PostgreSQL 18 on loopback only: 9 passed, 0 failed. The cluster was stopped. The final packaged Windows runtime migrated a fresh owned database first to the before revision and then through the exact target, reported pending=no, served locally, returned health/readiness 200, and denied numeric/invalid tracking with 404. No Product rows were created for smoke verification.

## V. Production Package Qualification

- Frozen-source backend: `1333 passed, 106 skipped, 0 failed`
- Frontend: `72 files passed; 357 tests passed`
- TypeScript `tsc --noEmit`: PASS
- ESLint: PASS with `0 errors, 13 existing warnings`
- Production frontend build: PASS twice; 2547 modules transformed
- Alembic graph: one head, exact target
- Secret policy: PASS
- Package verifier: PASS
- Independent exact ZIP equivalence: PASS

## W. Tooling Tests

Laptop fixture suite: `21 passed`. It covers PowerShell parsing, live collector execution in a controlled missing-infrastructure fixture, read-only/mutation/secret rules, exact ADR-047 classifier hash, package/bundle identity, valid and bad hashes, wrong head, ambiguous/contradictory/unresolved history, drift, config, capacity, backup, collision, exact listener ownership, zero-mutation validate-only, execute transitions, pre/post-migration failure injection, and rollback checkpoints. PostgreSQL tooling plus existing ADR-047 tests: `9 passed`.

## X. Read-Only Transfer Bundle

- Expanded: `D:\1-webapp\forwarder-production-releases\Forwarder-v1.10.0-Read-Only-Preflight-Bundle-e36ee7cee157\`
- ZIP: `D:\1-webapp\forwarder-production-releases\Forwarder-v1.10.0-Read-Only-Preflight-Bundle-e36ee7cee157.zip`
- Size: `13700` bytes
- SHA256: `b975bf5933d65916d2eb7228bbe22b5f2c30d0463eb2096d6ea760b7fcbca940`
- Contains only collector, two read-only SQL payloads, README, manifest, inventory, and checksums; no deployable ZIP.

## Y. Deployment Bundle

- Expanded: `D:\1-webapp\forwarder-production-releases\Forwarder-v1.10.0-Production-Deployment-Bundle-e36ee7cee157\`
- ZIP: `D:\1-webapp\forwarder-production-releases\Forwarder-v1.10.0-Production-Deployment-Bundle-e36ee7cee157.zip`
- Size: `23012478` bytes
- SHA256: `acf45576c82bc04fa3a3dd02b12500690d4efeeba32c9ffb1e47322227919dbb`
- Held on laptop until returned live preflight and separate GO.

## Z. Operator Handoff

`docs/operational/Forwarder-v1.10.0-operator-mediated-production-handoff.md` defines the twelve operator phases, one-command first server step, exact return file, hard gates, and A/B/C containment decisions.

## AA. Remaining Live Production Evidence

Laptop qualification cannot establish current live runtime/task/IIS agreement, real Production database head/content, ADR-047 Production counts, schema compatibility/drift, safe config presence, disk/backup capacity, recent log health, or backup evidence. These remain intentionally BLOCKED pending the returned sanitized collector JSON. Therefore this evidence does not claim `PRODUCTION_PREFLIGHT_STATUS=PASS`.

## AB. Reference Re-check

No architecture, Product, security, operational policy, runtime behavior, migration, or reference-data truth changed. The work adds only bounded release tooling, tests, evidence, and handoff. `REFERENCE_IMPACT_FINAL=NONE`.

## AC. Verdict

PASS — FORWARDER v1.10.0 OPERATOR-MEDIATED PRODUCTION TOOLING READY

```text
PRODUCTION_OPERATOR_TOOLING_STATUS=READY
OPERATOR_MEDIATED_DEPLOYMENT_MODEL=YES
CODEX_DIRECT_PRODUCTION_ACCESS_REQUIRED=NO
TARGET_PRODUCT_VERSION=1.10.0
TARGET_RELEASE_SOURCE_SHA=e36ee7cee157657c97dc42a539eaf1909f510a33
TARGET_DATABASE_HEAD=20260926_fixed_shipment_responsible_expert
PRODUCTION_ARTIFACT_BUILT=YES
PRODUCTION_ARTIFACT_QUALIFIED=YES
PRODUCTION_ARTIFACT_STAGE=Production
PRODUCTION_READ_ONLY_COLLECTOR=READY
ADR047_PRODUCTION_CLASSIFIER=READY
PRODUCTION_SCHEMA_COMPATIBILITY_CHECKER=READY
PRODUCTION_SCHEMA_DRIFT_CHECKER=READY
PRODUCTION_BACKUP_READINESS_CHECKER=READY
PRODUCTION_VALIDATE_ONLY=READY
PRODUCTION_DEPLOYER=READY
PRODUCTION_POST_DEPLOY_VERIFIER=READY
PRODUCTION_ROLLBACK_CONTAINMENT_TOOL=READY
PRODUCTION_LIKE_LOCAL_REHEARSAL=PASS
PRODUCTION_ACCESSED=NO
PRODUCTION_CHANGED=NO
PRODUCTION_DATABASE_CHANGED=NO
PRODUCTION_DEPLOYMENT_PERFORMED=NO
REFERENCE_IMPACT_FINAL=NONE
PRODUCTION_PACKAGE_FILENAME=Forwarder-Production-v1.10.0-e36ee7cee157.zip
PRODUCTION_PACKAGE_SHA256=2fdef076516273f82044c9b5aa1b2ad03bb8a97423de6c4f7bcb0adec2b0eacf
PRODUCTION_PACKAGE_SIZE=23396431
READ_ONLY_PREFLIGHT_BUNDLE=D:\1-webapp\forwarder-production-releases\Forwarder-v1.10.0-Read-Only-Preflight-Bundle-e36ee7cee157.zip
DEPLOYMENT_BUNDLE=D:\1-webapp\forwarder-production-releases\Forwarder-v1.10.0-Production-Deployment-Bundle-e36ee7cee157.zip
```
