# ADR-043 Production Readiness and Controlled Release Plan

Date: 2026-08-30. Scope: read-only discovery and planning only. No production
action, deployment, push, database access, migration, restart, IIS change,
Scheduled Task change, configuration change, or secret disclosure occurred.

## Executive gate

| Field | Evidence-based value |
| --- | --- |
| LOCAL_BRANCH | `codex/pr-4a-dms-gate-repair` |
| LOCAL_HEAD | `5002e02f568347c3f4a7ebe88f2937487c2d8f99` |
| LOCAL_HEAD_SUBJECT | `test(auth): isolate shadow telemetry logger state` |
| LOCAL_EXIT_GATE | PASS (835 passed, 92 skipped, 1 xfailed) |
| CERTIFIED_LOCAL_HEAD | **NOT_IDENTIFIED** |
| CURRENT_PRODUCTION_HEAD | NOT_VERIFIED |
| TARGET_ALEMBIC_HEAD | `20260907_direct_shipment_responsibility` |
| PRODUCTION_READINESS | **NOT_READY** |
| DEPLOYMENT_RECOMMENDATION | **NO_GO** |

The local regression included uncommitted authorization, certification, and
test-isolation changes. Therefore the commit named by `LOCAL_HEAD` cannot be
truthfully asserted to contain the certified state. This is a release-integrity
blocker, not an authorization-policy decision.

## Authority and source precedence

The Forwarderet accepted ADR-042/043/037 contracts and their implementation
design package govern this plan. The inspected enterprise ADR material in
`D:\1-webapp\29-lpaf` is draft/skeleton governance and adds no conflicting
adopted release rule. Production behavior, if later observed, is evidence only
and cannot override these contracts.

## Certified release ledger and delta

The last known deployed baseline from repository history is `991d29a`
(`fix(auth): provision logistics read permission for experts`); the historical
filesystem release path was absent and is not proof of deployment. The ordered
candidate ledger is `bc0ecf5` (ADR-042), `7678ce5` (ADR-043), `3863a3e`
(design), `97b775b` (evaluator foundation), `b3385ff` (request scope),
`73deae3` (shipment scope), `746c290` (child scope), `86ea690` (tracking),
`1e57e2c` (readiness), `fda4f4e` (project fail-closed), `8d57713`
(reporting fail-closed), `66470af` (selector baseline removal), `031b653`
(shadow), `872f853` (legacy-admin fallback removal), followed by supporting
migration, tenant, test, and evidence commits through `5002e02`.

Relative to `991d29a`, the repository changes 45 files: one additive migration,
canonical authorization service/integration, tenant-admin semantics, request and
shipment list/detail scope, child lineage enforcement, direct-shipment root
field, fail-closed reporting/project behavior, shadow telemetry, tests and
evidence. No tracked frontend, package, runtime dependency, or configuration
file changes exist in this delta.

| Delta | Classification | Release implication |
| --- | --- | --- |
| `primary_responsible_expert_id` on direct shipments | MIGRATION_DEPENDENT, DATA_DEPENDENT, HIGH_RISK | unassigned/invalid direct roots fail closed for Basic Expert |
| current request assignment and inherited child scope | BEHAVIOR_CHANGE, HIGH_RISK | stale/list/detail access is revoked after reassignment |
| exact active membership/authority and legacy-admin removal | BEHAVIOR_CHANGE, DATA_DEPENDENT | role labels/capabilities alone do not authorize |
| CRM, reporting, project-only work | SAFE_FAIL_CLOSED / HIGH_RISK | no broad CRM grant; reporting/project-only stays denied |
| logistics selector | BEHAVIOR_CHANGE | no automatic Expert baseline; conditional capability required |
| frontend/config/dependencies | NO_FRONTEND_CHANGE / NOT_APPLICABLE | API semantics still require compatibility smoke before release |

## Migration certification

The local Alembic graph has one head: `20260907_direct_shipment_responsibility`.
Its direct parent is `20260906_global_logistics_point_materialization`, then
`20260905_global_logistics_point_adoption`, then the intact global logistics
foundation chain. The ADR-043 migration is additive: nullable FK to
`expert_user` plus index. Downgrade intentionally refuses when any responsibility
evidence exists. Hence database downgrade is **not** the routine rollback plan.

Production current revision and exact production path are NOT_VERIFIED. Once
captured read-only, calculate `PRODUCTION_CURRENT -> ... -> 20260907...`; do
not run an upgrade until the capture, backup, and data gates pass.

## Production baseline, data, tenant, and configuration readiness

The historical release/runtime directories, scheduled task, service process, and
production-host evidence were absent from this machine during read-only discovery.
Accordingly `PRODUCTION_BACKEND_RELEASE`, `PRODUCTION_BACKEND_COMMIT`, frontend
release, Alembic current, Python, service, health, readiness, hostname/CORS,
database data, and Samand Tarabar population are all **NOT_VERIFIED**.

No production database query was attempted because no verified read-only target
or credential-free operational access path was available. Counts for roots,
memberships, capabilities, role/authority mismatches, direct responsibility,
children, and tenant inconsistencies are therefore NOT_VERIFIED, not zero.

### Pre-deployment data action matrix

| Issue | Affected count | Persona/impact | Canonical requirement | Controlled action | Must fix | Rollback relevance |
| --- | ---: | --- | --- | --- | --- | --- |
| Direct shipment lacks valid responsible Expert | NOT_VERIFIED | Expert loses access (fail closed) | current same-tenant responsibility | inventory; explicitly assign or exclude | YES | do not downgrade after evidence |
| Request has no active current assignee | NOT_VERIFIED | Expert work hidden | current root assignment | inventory; controlled reassignment/exclusion | YES | forward rollback retains data |
| orphan/cross-tenant/ambiguous child lineage | NOT_VERIFIED | non-disclosing deny | one certified tenant/root path | quarantine/fix under approved data procedure | YES | block rollout |
| inactive/multiple/mismatched membership or authority | NOT_VERIFIED | all tenant work may deny | exactly one active membership | remediate through approved access process | YES | access rollback only |
| legacy role/capability dependency | NOT_VERIFIED | changed selector/admin access | canonical authority + capability | review and grant no implicit permission | YES | retain boundary denial |

Samand Tarabar impact is NOT_VERIFIED until the same inventory is run under an
approved read-only production connection. Do not infer administrators, experts,
or hostnames from historic notes. Existing CORS evidence (`server.logisticmarket.ir`
vs `samand.forwarderet.ir`) is a mandatory configuration verification item.

## Pre-deployment gates and backup

All mandatory gates are currently FAIL/NOT_VERIFIED except local evidence,
migration graph, rollback design, and smoke-plan design. Required gates are:
certified immutable release commit; verified production baseline/revision;
validated migration path; verified backup/checksum; data-quality pass; tenant
impact review; configuration/CORS/runtime review; frontend compatibility;
rollback rehearsal; smoke and negative-security plans; and no unresolved
critical/high finding.

Before mutation, an operator shall capture: PostgreSQL logical backup named
`forwarderet-prod-YYYYMMDD-HHMMSS-pre-adr043.dump`, SHA-256 manifest, Alembic
revision, deployed commit/artifact hashes, runtime Python/package inventory,
task XML/state, IIS site/binding configuration, health/readiness response, and
redacted configuration-presence manifest. Verify restore metadata/checksum;
never record secret values.

## Controlled deployment runbook

| Step | Action | Mutation | Verify / stop / rollback trigger |
| --- | --- | --- | --- |
| 1 | Freeze exact clean certified commit and artifact | YES later | stop if commit/working tree/test aggregate differs |
| 2 | Capture baseline and backup evidence | NO | stop if any capture/checksum fails |
| 3 | Run approved read-only data inventory and Samand review | NO | stop on any mandatory matrix row |
| 4 | Approve controlled data remediation separately | YES later | stop on unapproved/ambiguous change |
| 5 | Stage release artifact and verify hashes/dependencies | YES later | stop on mismatch |
| 6 | Apply exact Alembic path during approved window | YES later | stop on migration error; use forward-safe restore/rollback |
| 7 | Activate application using existing approved service procedure | YES later | stop on health/readiness/CORS failure |
| 8 | Execute smoke and negative suite | NO/approved disposable data only | rollback on security/access regression |

Application-only/configuration failures roll back the artifact/configuration to
the captured baseline. Migration/data/authorization failures use forward-safe
remediation or verified restore; do not assume downgrade is safe because the
ADR-043 downgrade refuses when responsibility values exist. Severe security
regression requires immediate traffic/service containment by the approved
operations procedure, preserve evidence, then restore the validated baseline.

## Smoke and compatibility plan

No frontend deployment is proven required by tracked changes, so classification
is `BACKEND_ONLY_SAFE` only after the production API/UI smoke verifies current
frontend handling of 403/non-disclosing 404 and filtered collection metadata.
Otherwise `FRONTEND_RECOMMENDED` until verified.

The minimum approved future suite: health/readiness/login; Platform Admin
tenant-work deny; tenant Organization Admin own-tenant/no-platform escalation;
Expert A assigned allow and Expert B hidden; A-to-B reassignment then A deny/B
allow including a known child ID; cross-tenant deny; `role=admin` with
`authority=EXPERT` deny; CRM no implied authority; conditional logistics
selector; and collection count/pagination non-disclosure. Use only approved,
reversible disposable test data.

## Final assessment

`PRODUCTION_BASELINE_VERIFIED = NO`  
`MIGRATION_PATH_VERIFIED = NO`  
`DATA_QUALITY_PASS = NO`  
`TENANT_IMPACT_ACCEPTABLE = NO`  
`CONFIG_READY = NO`  
`FRONTEND_COMPATIBLE = NOT_VERIFIED`  
`BACKUP_PLAN_READY = YES`  
`ROLLBACK_PLAN_READY = YES`  
`SMOKE_PLAN_READY = YES`

Critical findings: 1 — immutable certified release commit is not identified.
High findings: 4 — production baseline, migration revision, data quality/Samand
impact, and configuration/runtime/CORS are unverified. Material medium: 1 —
frontend semantics are unverified. Pre-deployment actions: 14; mandatory: 14.

`OWNER_DECISIONS_REQUIRED = NO`  
`TRUE_BLOCK_REASON = NONE` (the NO-GO conditions are executable evidence and
readiness work, not a new architecture or owner-policy decision).

## Production read-only preflight — 2026-08-30

Read-only inspection was exhausted from this laptop. Historical local server
paths (`C:\1-webapp\forwarder-production`, `C:\1-webapp\forwarder-runtime`
and their D: equivalents), Scheduled Task `Forwarder Backend Production`, and
a local listener on 5101 are absent. Thus no filesystem, process, environment,
database, Scheduled Task, IIS-binding, backup-location, or authenticated data
inspection is available from this host. No credential or production database
connection was used.

External unauthenticated observations are positive but insufficient for release
identity: `https://samand.forwarderet.ir/` and the older hostname return IIS
200; `/api/expert/ping` returns the expected running message; `/api/health`
returns JSON 200. Neither response exposes a release commit or Alembic revision.
The tested API currently returns `Access-Control-Allow-Origin:
https://server.logisticmarket.ir` for a Samand-origin preflight; its OPTIONS
response likewise permits only the older origin. Therefore
`SAMAND_FORWARDERET_CORS_READY = NO` from actual production evidence.

| Field | Result |
| --- | --- |
| CODE_CERTIFIED_HEAD | `adcc5da2c6f6d696dbad15b9b2cd7900bd96bc9e` |
| EVIDENCE_HEAD | `13f0a0eb4b8f7687a1bb872cc03ecd5577c1758d` |
| CURRENT_PRODUCTION_HEAD / backend release | NOT_VERIFIED |
| PRODUCTION_ALEMBIC_CURRENT | NOT_VERIFIED |
| TARGET_ALEMBIC_HEAD | `20260907_direct_shipment_responsibility` |
| MIGRATION_PATH | NOT_VERIFIED (cannot derive without current revision) |
| Production baseline / DB data / Samand audit | NOT_VERIFIED |
| Data quality / Samand impact | NOT_VERIFIED |
| Frontend compatibility | NOT_VERIFIED |
| Backup topology readiness | NOT_VERIFIED |
| CORS configuration | FAIL: active tenant origin not allowed |

`SAMAND_USERS_AT_RISK_OF_ACCESS_LOSS = NOT_VERIFIED`  
`SAMAND_RECORDS_AT_RISK_OF_FAIL_CLOSED = NOT_VERIFIED`  
`SAMAND_USERS_AT_RISK_OF_UNINTENDED_ACCESS_GAIN = NOT_VERIFIED`

### Operator-side read-only inspection package

Run on the production server under the existing read-only database account or
with a PostgreSQL session explicitly set `default_transaction_read_only=on`:

1. Capture release path/commit, runtime Python, scheduled-task XML/state,
   listening PID/command line, IIS bindings, and redacted configuration-presence
   manifest. Never print secrets or full connection strings.
2. Run `SELECT version(); SELECT version_num FROM alembic_version;` and record
   the revision only. Use the local Alembic graph to calculate the path to
   `20260907_direct_shipment_responsibility`; execute no migration.
3. Execute the approved read-only inventory for users, active memberships,
   role/authority mismatch, permission JSON, request current assignees, direct
   shipment responsibility column presence/value/tenant validity, and all
   declared child tenant/parent/root edges. Count null/orphan/cross-tenant/
   inactive/multiple-membership rows only; do not export sensitive payloads.
4. Filter the same counts for organization `1` / `samand-tarabar`; classify
   potential access loss, fail-closed records, and unintended access gain.
5. Capture CORS origins from redacted runtime configuration and IIS hostname
   bindings; repeat the unauthenticated OPTIONS check from the tenant origin.
6. Record backup/restore destination accessibility and task/IIS/config capture
   method, without creating a backup in this phase.

The required concrete output is the revision, aggregate counts, and redacted
runtime identifiers—not data rows, credentials, or secrets. Re-evaluate this
plan only after that package is returned.

`PRODUCTION_BASELINE_VERIFIED = NO`  
`PRODUCTION_ALEMBIC_VERIFIED = NO`  
`MIGRATION_PATH_VERIFIED = NO`  
`DATA_QUALITY_PASS = NO`  
`SAMAND_IMPACT_ACCEPTABLE = NO`  
`CONFIG_READY = NO`  
`FRONTEND_COMPATIBLE = NOT_VERIFIED`  
`BACKUP_PLAN_READY = NO`  
`ROLLBACK_PLAN_READY = YES`  
`SMOKE_PLAN_READY = YES`

Pre-deployment actions: 7; mandatory: 7. Critical findings: 1 (Samand CORS
denial). High findings: 5 (release/revision/data/tenant/frontend-backup
verification unavailable). Material medium findings: 1 (external health lacks
release identity).

`PRODUCTION_READINESS = NOT_READY`  
`DEPLOYMENT_RECOMMENDATION = NO_GO`  
`OWNER_DECISIONS_REQUIRED = NO`  
`TRUE_BLOCK_REASON = production-server read-only access is unavailable from this laptop`

## Server inspection package

The operator-executable package is
`ops\adr043-production-readonly-preflight.ps1`. It is syntax-validated locally
and contains no mutating service, IIS, Scheduled Task, filesystem, Alembic, or
database command; its SQL is `SELECT`/introspection wrapped in read-only
transactions. It redacts secret values, emits only configuration presence and
approved non-secret identity fields, and provides a bounded machine-readable
summary. The direct-responsibility metric is schema-version sensitive and the
script reports collection errors rather than inventing values when a production
schema cannot support a query.
