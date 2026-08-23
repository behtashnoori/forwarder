# Global Logistics Network Production rollout plan

Status: **TOOLING CERTIFIED — Production execution not authorized**

Plan date: 2026-08-23 (Asia/Tehran)

Source commit: `6eb46b1754778f0ed7cc13f18428e3fc7cf24a0b`

Production product commit: `85fbd78b46a544367ab40144fdf8d51d422f8dcc`

Migration: `20260903_external_operational_references` → `20260906_global_logistics_point_materialization`

This is a planning and certification record. It authorizes no Production access, deployment, migration, seed, activation, service restart, IIS change, or push. Commands under P2–P15 are templates for a separately authorized change window. Replace every `<...>` value from approved operator evidence; never infer it.

## Release decision and certified prerequisites

The local tooling prerequisites are implemented and certified:

1. `backend/global_logistics_point_catalog.py` and `backend/global_logistics_point_catalog_cli.py` provide strict checksum-pinned, exact-nine-row PLAN/APPLY behavior, Platform Admin enforcement, atomic catalog writes, conflict refusal, convergence, and `ReferenceDataSeedRun` evidence.
2. `scripts/build_release_package.py` builds from a clean detached worktree at an explicit full authorized commit and produces fresh `dist`; `scripts/verify_release_artifact.py` verifies the ZIP, sidecar artifact identity, internal content manifest, and required structure.

Production remains blocked pending separate owner/operator approval and an authorized change window. The approved package explicitly says `production_seed_authorized: false`; package and tooling certification are not execution approval.

The importer must create all package rows as `DRAFT / UNVERIFIED`. ADR-041 and the owner decision require Platform Admin transitions `REVIEW → VERIFY → ACTIVATE`; the package does not establish a pre-reviewed activation path. Only one owner-selected point is to be activated for smoke. No bulk activation is implied.

## P0 — Release preparation

Authorization gate: release engineer may perform local read/build/test work only. Production access remains forbidden.

### Repository preflight result

| Check | Certified result |
|---|---|
| Repository | `D:/1-webapp/15-forwarder` |
| Branch | `codex/pr-4a-dms-gate-repair` |
| Initial HEAD | `6eb46b1754778f0ed7cc13f18428e3fc7cf24a0b` |
| Required HEAD | match |
| Worktree | dirty before this plan; unrelated tracked/untracked files preserved |
| Deployed commit ancestry | `85fbd78...` is an ancestor of HEAD |
| Alembic heads | sole head `20260906_global_logistics_point_materialization` |
| Architecture governance | PASS: `python scripts/check_architecture_governance.py` |
| Approved package | exists |
| Canonical package checksum | PASS: `sha256:08a7ca1fb17ae79964930cd47c019261b6952aa9542b2fc48ee09c7564690c7c` |
| Approved count | PASS: 9 |
| Package validator | PASS: `python scripts/validate_global_logistics_point_catalog_v1.py --approved-baseline` |

The checksum above is the package's canonical JSON checksum: UTF-8 JSON, keys sorted, compact separators, and the top-level `checksum` field excluded. It is deliberately different from the SHA-256 of the pretty-printed file bytes. Both the canonical checksum and the artifact/file hash must be recorded; never substitute one for the other.

The Phase commits are all ancestors of HEAD: architecture `37d4d15c`, foundation `2c6f506a`, platform governance `4c63ee33`, organization adoption `93f1a8c0`, materialization `32d1907a`, operational certification `6331ed95`, catalog preparation `862d8041`, and approved baseline `6eb46b17`.

### Release delta inventory

The audited ancestry contains nine commits: release-document baseline alignment (`7848edc7`), ADR-041, foundation, Platform governance, organization adoption, materialization, operational certification, catalog preparation, and baseline approval. No unrelated application feature was found.

| Class | Delta |
|---|---|
| Migrations | Three revisions `20260904`–`20260906` |
| Backend runtime | models, routes, services, model registration |
| Frontend runtime | Platform and Organization Global Network tabs, API client, admin integration |
| Authorization | Platform-only global CRUD/governance; tenant-derived Organization Admin adoption/materialization |
| GlobalLogisticsPoint | catalog identity, aliases, modes, external codes, corridor tags, sources |
| Platform governance | draft/review/verify/activate/deprecate state machine and audit behavior |
| Organization adoption | browse/adopt/update/deactivate/reactivate with tenant isolation |
| Materialization | explicit, idempotent creation of tenant `LogisticsPoint` with provenance |
| Operational certification | selector, project, tracking and snapshot tests |
| Reference data | 39-row review catalog and approved 9-row subset |
| Documentation/tests only | ADR, decisions, reconciliation evidence, tests, release-doc alignment |

### Exact migration delta

All three upgrades run under Alembic's PostgreSQL transactional DDL. They contain no seed, backfill, legacy rewrite, `TrackingLocationReference` mutation, project rewrite, or historical tracking rewrite.

`20260904_global_logistics_point_foundation` creates six empty tables: `global_logistics_point`, `_alias`, `_mode`, `_external_code`, `_corridor_tag`, and `_source`. It adds public/immutable/facility uniqueness, lifecycle/verification/border/coordinate/version checks, catalog/name/geography/alias/mode/external-code/corridor indexes, child cascade foreign keys, and restrictive links to point type, geography and expert users. No existing table is altered and no data is inserted. Downgrade drops all six tables and has **no retained-data guard**; therefore it is allowed only after proving every global table is empty or after an explicitly approved destructive restore decision.

`20260905_global_logistics_point_adoption` creates `organization_global_logistics_point_adoption`, its organization/status and global-point indexes, public/logical/composite uniqueness, lifecycle/version checks, and restrictive organization/global-point/user foreign keys. It inserts nothing and alters no existing table. Downgrade refuses while any adoption row exists.

`20260906_global_logistics_point_materialization` alters the existing `logistics_point` table by adding nullable `global_logistics_point_id` and `global_adoption_id`, restrictive provenance foreign keys (including organization consistency), uniqueness of `global_adoption_id`, and an index on `global_logistics_point_id`. It performs no backfill. Downgrade refuses while any LogisticsPoint retains global/adoption provenance.

### Local build gates

Run from a clean detached worktree at the authorized source commit; do not use this dirty working directory for artifact creation and do not upgrade dependencies.

```powershell
git rev-parse HEAD
git status --short
git merge-base --is-ancestor 85fbd78b46a544367ab40144fdf8d51d422f8dcc HEAD
python -m pip install --require-hashes -r <approved-locked-python-requirements>  # prerequisite if no hash lock exists
npm ci
python -m pytest
npm run test:frontend
npx tsc --noEmit
npm run lint
$env:VITE_API_URL='__FORWARDER_SAME_ORIGIN__'; npm run build
python -m compileall -q backend
python scripts/check_architecture_governance.py
python scripts/scan_repository_secrets.py
python scripts/validate_global_logistics_point_catalog_v1.py --approved-baseline
python -m alembic -c backend/migrations/alembic.ini heads
git diff --check
```

Required results: no test/type/lint/build/compile/governance/secret/diff failures; exactly one Alembic head; `dist/index.html` and its referenced hashed JS/CSS exist. Record Python, pip, Node and npm versions plus hashes of `requirements.txt` and `package-lock.json`.

### Disposable PostgreSQL 18 certification

A fresh loopback-only PostgreSQL 18.0 cluster was initialized for this plan. A database was migrated from base to `20260903`, verified pending, upgraded explicitly with `python -m backend.migration_cli upgrade 20260906_global_logistics_point_materialization --confirm`, and verified current with no pending revisions. PostgreSQL reported transactional DDL. Application construction passed with 342 routes. Before/after counts were `logistics_point=0` and `tracking_location_reference=64`; after upgrade the global and adoption counts were zero. A focused SQLite/runtime suite covering governance, adoption, materialization, logistics network and operational selectors passed 29 tests.

The disposable PostgreSQL data was synthetic and does not certify Production contents. The governed importer is separately certified on PostgreSQL 18 for fresh PLAN, APPLY, converged re-PLAN, idempotent reapply, conflict refusal, normalized children and persisted evidence. The disposable cluster is destroyed after evidence collection.

### Artifact contract and certified commands

Proposed immutable filename: `Forwarder-global-logistics-6eb46b1.zip`. Build from an isolated clean checkout of the full 40-character source commit. Include `backend/` excluding tests/caches, all migrations and Alembic configuration, `manage.py`, pinned requirements, current `dist/`, runtime configuration templates without values, migration CLI/tooling, the governed importer, the exact approved baseline JSON, and runtime-required documentation/scripts.

```powershell
python scripts/build_release_package.py --repository 'D:\1-webapp\15-forwarder' --authorized-commit '<40-character-approved-commit>' --output-directory '<new-output-directory>' --release-label 'global-logistics'
python scripts/verify_release_artifact.py --artifact '<candidate.zip>' --manifest '<candidate.zip.manifest.json>'
```

The internal content manifest cannot contain the final ZIP hash without self-reference. Therefore `release-manifest.json` records the content hash and complete file inventory, while the immutable sidecar `.zip.manifest.json` records the final artifact filename, byte size and SHA-256. Transfer and verify both files.

Exclude `.git`, `.env*`, secrets, credentials, logs, test/build caches, source maps unless explicitly required, local database directories, prior releases/ZIPs, evidence artifacts, and unrelated worktree files.

The generated `release-manifest.json` must record source commit/tree, build timestamp, toolchain fingerprints, every packaged file's byte size and SHA-256, sorted aggregate package hash, artifact byte size/SHA-256, frontend entry assets, requirements/lock hashes, migration from/to and migration-file hashes, baseline path/catalog/canonical checksum/count/raw-file SHA-256, importer version, and rollback release. Build twice in clean directories and require identical content manifest (timestamp excluded from the content-hash definition). After transfer, calculate the ZIP SHA-256, compare it with independently transferred evidence, extract to a new directory, verify every manifest entry and reject any extra/missing file, run the packaged secret scanner, and verify frontend entry assets.

## P1 — Artifact verification

Authorization gate: release owner approves only the immutable artifact for preflight; no service or DB mutation.

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath '<artifact>'
Get-Item -LiteralPath '<artifact>' | Select-Object Length
Expand-Archive -LiteralPath '<artifact>' -DestinationPath '<new-verification-dir>'
python '<new-verification-dir>/verify_release_manifest.py' --strict
python '<new-verification-dir>/verify_package_secrets.py' '<new-verification-dir>'
```

STOP on hash, size, manifest, source commit, migration range, baseline canonical checksum/count, secret scan, or frontend asset mismatch.

## P2 — Production preflight

Authorization gate: approved read-only Production preflight only. Do not reveal URLs, passwords, tokens, or connection strings in evidence.

Record: current IIS site/app-pool/static physical path; backend scheduled task name, executable, arguments and working directory; backend PID/executable/port; sanitized DB server/database/user identity; PostgreSQL version and `pg_is_in_recovery()` result; current Alembic revision; free disk; approved backup and rollback paths; maintenance ticket/window/decision owners; and immutable old release path.

Run read-only identity queries through the approved DBA channel:

```sql
SELECT current_database(), current_user, pg_is_in_recovery();
SELECT version_num FROM alembic_version;
SELECT id, username, authority, is_active FROM expert_user WHERE username IN ('platformadmin','tarabar');
-- Use the established membership tables/views to prove user 19 belongs only to samand-tarabar.
-- Prove user 26 needs no tenant membership; do not add one.
```

Expected identities: `platformadmin`, user 26, active, `PLATFORM_ADMIN`, no tenant membership required; `tarabar`, user 19, active, `ORGANIZATION_ADMIN`, organization `samand-tarabar`. Verify each login path without recording passwords. Expected DB is the approved primary (not recovery) at revision `20260903_external_operational_references`.

Capture exact counts of every existing critical table selected by the DBA/application owner, at minimum `logistics_point`, `tracking_location_reference`, project/configuration, tracking update/snapshot, user, organization, and shipment/operational aggregate tables. These are before/after invariants because the three migrations do not mutate their rows.

## P3 — Maintenance/freeze

Authorization gate: change manager explicitly authorizes maintenance mutation.

1. Announce the window and reject new public traffic at the approved gateway/IIS control point.
2. Drain in-flight requests; record completion.
3. Stop the scheduled backend writer using its captured exact name/action.
4. Verify the captured process exited and the captured backend port has no listener.
5. Keep public traffic closed until P8 succeeds.

STOP if traffic cannot be stopped, writers remain, identity/authority/revision differs, rollback assets are absent, or the window/approvers are not current.

## P4 — Final frozen backup

Authorization gate: DBA authorizes final frozen backup while all writers remain stopped.

Create a custom-format `pg_dump` to a new timestamped, access-controlled path using a process-supplied credential (never command history). Record command version and exit code. Run `pg_restore --list <dump>` and require a complete readable catalog. Calculate SHA-256 and byte size, copy evidence to the approved protected location, preserve the old immutable application directory, export the scheduled task/action definition, and run the approved IIS configuration backup command. Do not reuse/overwrite an older backup.

STOP on dump/list/hash/copy failure, zero or implausible size, writer/listener reappearance, insufficient disk, or missing old release/task/IIS backup.

## P5 — Migration

Authorization gate: DBA and change manager authorize this exact target after P4 evidence acceptance.

```powershell
python -m backend.migration_cli current
python -m backend.migration_cli check
python -m backend.migration_cli upgrade 20260906_global_logistics_point_materialization --confirm
python -m backend.migration_cli check
python -m backend.migration_cli current
```

The pre-upgrade `check` must report pending/non-zero with current `20260903`; the post-upgrade check must report `pending=no`/zero and current `20260906`. Re-run existing critical-table counts and require equality. Verify the six global tables, adoption table, new nullable LogisticsPoint columns, named indexes, foreign keys, check constraints and uniqueness constraints. Do not demand nonzero rows in new tables.

Immediately verify:

```sql
SELECT count(*) FROM global_logistics_point;                         -- 0
SELECT count(*) FROM organization_global_logistics_point_adoption; -- 0
SELECT count(*) FROM logistics_point WHERE global_logistics_point_id IS NOT NULL OR global_adoption_id IS NOT NULL; -- 0
```

Require unchanged `logistics_point` and `tracking_location_reference` counts and no historical project/tracking mutation. STOP if the global/adoption catalog is pre-populated or any invariant differs.

## P6 — Backend cutover

Authorization gate: application owner authorizes new backend activation after P5 passes.

Extract into a new immutable release directory; never overlay the old one. Create an isolated venv with the approved Python runtime, install exactly the packaged/pinned requirements without upgrading, and verify installed-package inventory. Apply the existing secret environment by reference, not by copying it into the release. Run packaged manifest, compile, import/startup and migration-current checks.

If topology permits a no-writer shadow instance, bind it only to an unused loopback port and run `/api/health`, `/api/health/ready`, and `/api/health/ping`; otherwise skip shadowing and record why. Stop it before switching. Update the scheduled task/action atomically to the new venv, working directory and launch command; start once and require one expected process/listener. Preserve the old task export and release directory.

## P7 — IIS/public cutover

Authorization gate: web/platform owner authorizes public/static switch after local backend readiness passes.

Switch the IIS static physical path to the new release's verified `dist` using the established configuration mechanism. Do not edit generated assets. Start/enable the approved app pool/site as applicable, leaving rollback configuration intact. Verify `/`, the manifest-recorded JS and CSS assets, and same-origin API routing locally before restoring traffic.

## P8 — Health/readiness

Authorization gate: change manager authorizes reopening traffic only after all checks pass.

Require HTTP 200 locally and publicly for `/api/health` and `/api/health/ready`, HTTP 200 for `/` and manifest JS/CSS, expected cache headers, and no repeated 500s or release-blocking backend/IIS/PostgreSQL log errors. Reopen traffic gradually using the established mechanism. Record timestamps, status codes, response release identity, and log windows without secrets.

## P9 — Global baseline PLAN

Authorization gate: data owner and Platform owner authorize PLAN only. PLAN is read-only and must not automatically invoke APPLY.

The certified read-only command is:

```powershell
python -m backend.global_logistics_point_catalog_cli plan `
  --package backend/reference_data/global-logistics-points-china-iran-v1.0.0-approved-baseline.json `
  --catalog-version china-iran-global-logistics-points-1.0.0-approved-baseline `
  --expected-checksum sha256:08a7ca1fb17ae79964930cd47c019261b6952aa9542b2fc48ee09c7564690c7c
```

PLAN emits version, canonical checksum, environment, planned/create/unchanged/conflict counts and all nine candidate codes. Fresh expected result: planned/create 9, unchanged 0, conflicts 0. STOP on any difference, including an existing identity matched only by name.

## P10 — Global baseline APPLY

Authorization gate: a second, explicit data owner + Platform owner approval after reviewing P9 evidence.

The certified APPLY command must be used only after a separate Production authorization:

```powershell
python -m backend.global_logistics_point_catalog_cli apply `
  --package backend/reference_data/global-logistics-points-china-iran-v1.0.0-approved-baseline.json `
  --catalog-version china-iran-global-logistics-points-1.0.0-approved-baseline `
  --expected-checksum sha256:08a7ca1fb17ae79964930cd47c019261b6952aa9542b2fc48ee09c7564690c7c `
  --operator platformadmin --actor-user-id 26 `
  --approval-reference '<approved-execution-reference>' `
  --confirm --confirm-production
```

APPLY verifies user 26 is active `PLATFORM_ADMIN` and username `platformadmin`, executes catalog writes atomically, and persists a `ReferenceDataSeedRun` record with operator identity, approval reference, package/version/checksum/count, timestamps, result counts, and sanitized failure/refusal details. It creates `DRAFT / UNVERIFIED` rows only.

Expected apply: created 9, unchanged 0, conflicts 0; database count 9. A new PLAN must then report created 0, unchanged 9, conflicts 0. STOP and do not hand-edit rows if apply or convergence differs.

## P11 — Platform smoke

Authorization gate: Platform owner authorizes login and read-only UI smoke; each lifecycle mutation requires separate owner selection/approval.

As `platformadmin` user 26: log in; verify the Global Logistics Network screen is visible; exactly nine expected codes appear; filters and detail work; no numeric database IDs are exposed; each imported row shows `DRAFT / UNVERIFIED`; an Organization Admin cannot reach Platform routes. Review logs for authorization failures or 500s.

For one explicitly owner-selected point (suggested `GLP-IR-SARAKHS`), record its opaque public ID/version and separately authorize each transition: `DRAFT/UNVERIFIED → DRAFT/REVIEWED → DRAFT/VERIFIED → ACTIVE/VERIFIED`. Prove activation is rejected before verification. Do not activate the other eight.

## P12 — Organization smoke

Authorization gate: tenant owner authorizes one adoption mutation by `tarabar` user 19 in `samand-tarabar`.

Browse the Global Network, see the single active point as AVAILABLE, adopt it once, and verify adoption `ACTIVE`. Query by organization scope and prove no other tenant can see the adoption. Verify no `LogisticsPoint` was automatically created. Do not change user, membership or tenant identity.

## P13 — Materialization/operational smoke

Authorization gate: tenant owner separately authorizes one materialization and, separately, any operational write.

Materialize the one adoption with a reviewed tenant-local immutable code. Verify the resulting `LogisticsPoint` belongs to `samand-tarabar`, records both global-point and adoption provenance, is unique per adoption, and behaves like an ordinary tenant point. Repeating materialize must converge/idempotently return the same point, not create a duplicate.

Safe read smoke: confirm the point appears in ordinary LogisticsPoint, expert tracking, and project selectors under `samand-tarabar`, does not appear cross-tenant, and does not alter historical snapshots. A project selection or tracking update is data-changing: perform it only on a designated owner-approved test project/shipment/unit and record cleanup/retention policy. If no designated object exists, stop at read-only selector verification; never mutate real shipment history merely for smoke.

## P14 — Final evidence and success criteria

Authorization gate: release owner accepts evidence; no additional mutation is implied.

Collect: approvals; artifact/manifest hashes and sizes; sanitized topology; frozen-backup/list/hash evidence; before/after revisions and critical counts; health/frontend responses; log excerpts; baseline PLAN/APPLY/re-PLAN run IDs; opaque IDs and states for the one activated/adopted/materialized point; tenant-isolation proof; operational read/write classification; task/IIS/release rollback paths.

Success requires current `20260906`, readiness/public health/frontend 200, Platform login and governance UI, converged 9-row package apply, Organization browse, the authorized one-point adoption/materialization (if authorized), tenant isolation, no release-blocking errors, and intact rollback assets. If mutation smoke is not authorized, deployment may not claim that criterion; the decision owner must explicitly accept deferral or keep the release incomplete.

## P15 — Rollback

Authorization gate: incident commander chooses the branch; DBA + business/data owner authorize any destructive DB action.

### A. Failure before new data is used

Keep traffic closed; stop the new backend; capture logs. If no global rows, adoption rows, or LogisticsPoint provenance exist, the preferred low-risk response is application rollback while retaining the additive schema **only after** compatibility testing proves the old `85fbd78...` application starts and operates against `20260906`. That backward-compatibility proof has not been completed by this Goal, so it is a prerequisite to choosing this path.

If exact schema rollback is required, verify all six global tables empty, adoption count zero and provenance count zero. Downgrade `20260906 → 20260905` and `20260905 → 20260904` will enforce their guards; `20260904 → 20260903` has no guard and must be authorized only after the explicit emptiness proof. Verify current `20260903`, critical counts, then restore the old scheduled task/action and IIS static path and run old-release health checks before reopening traffic.

### B. Failure after new Phase 3/4 data exists

Do not downgrade: the `20260905` and `20260906` guards refuse retained-data loss, while the foundation downgrade could destructively drop global data. First attempt forward repair or keep the new schema and roll back only the application **if** certified backward-compatible. Otherwise keep traffic/writers stopped and restore the final frozen backup to a separately prepared target, validate it, then perform the approved atomic DB/application cutover. A restore discards every post-freeze write, including baseline, adoption, materialization and legitimate operational writes. The incident commander, DBA, business owner and data owner must explicitly accept that loss window. Never delete or rewrite provenance to make a downgrade pass.

### Universal STOP conditions

STOP on artifact/manifest/checksum mismatch; wrong DB; recovery/replica DB; unexpected starting revision; backup/list/hash failure; migration failure; readiness or frontend failure; unexpected pre-populated global/adoption data; baseline conflict or nonconvergence; Platform authorization failure; tenant leakage; repeated HTTP 500; unexpected mutation/count drift; invalid downgrade assumptions; missing rollback assets; failed tooling verification; or loss of an authorization gate.

## Final report

- A. Initial HEAD: `6eb46b1754778f0ed7cc13f18428e3fc7cf24a0b`
- B. Final HEAD: recorded after documentation commit
- C. Commit: recorded after documentation commit
- D. Files changed: this runbook only; pre-existing user changes preserved
- E. Governance: architecture check PASS; no Production authority granted
- F. Release source: `6eb46b1754778f0ed7cc13f18428e3fc7cf24a0b`
- G/H. Migration: `20260903_external_operational_references` → `20260906_global_logistics_point_materialization`
- I. Migration delta: additive global/adoption schema plus nullable LogisticsPoint provenance; no automatic data rewrite
- J. PostgreSQL certification: migration/startup/count checks PASS; importer certification BLOCKED
- K/L/M. Package: approved baseline JSON; canonical checksum `08a7...c7c`; 9 rows
- N/O. Importer exists: YES; certified module and explicit CLI included
- P. Artifact: explicit-commit isolated builder plus strict ZIP/manifest verifier included
- Q/R. Backup/maintenance: frozen verified custom dump with stopped writers and preserved app/task/IIS rollback assets
- S/T. Migration/cutover: explicit CLI migration, immutable release directory, isolated venv, controlled task/IIS switches
- U/V/W/X. Smoke: Platform governance; one authorized adoption; one authorized materialization; read-first operational selector smoke
- Y. Before use: app-only rollback only after compatibility proof; guarded empty-schema downgrade permitted with approval
- Z. After use: no downgrade; forward repair or approved frozen-backup restore
- AA/AB. STOP and success criteria: defined above
- AC. Production accessed? NO
- AD. Production changed? NO
- AE. Production migrated? NO
- AF. Production seeded? NO
- AG. Deployment? NO
- AH. Push? NO
- AI. Next controlled step: obtain separate owner/operator authorization for Production execution

GLOBAL LOGISTICS NETWORK PRODUCTION ROLLOUT BLOCKED — RELEASE PREREQUISITE REQUIRED
