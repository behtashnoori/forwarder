# Phase 1B Local Database Cutover — Final Closure Report

Closure date: 2026-07-28 (Asia/Tehran)

Execution evidence date: 2026-07-27
Official domain term: `OperationalShipment`

## 1. Executive Summary

The Phase 1B local database cutover is complete. The legacy database was not
upgraded in place. A fresh database was built at the active migration head,
legacy data was transferred through the approved mapping contract, and the
validated database was promoted by an atomic local rename. DryRun, Rehearsal,
Final transfer, application validation, cutover, and post-cutover validation
all passed.

The active local database is `forwarder_db`. The pre-cutover database is
retained, unchanged in purpose, as
`forwarder_db_legacy_20260727_222328`. Server and Production were not touched.

## 2. Scope

This closure covers only the localhost Phase 1B database transition:

- source assessment and backup;
- restore verification;
- fresh active-head database creation;
- controlled transfer and reconciliation;
- local atomic cutover;
- post-cutover application validation;
- preservation of rollback assets and evidence.

It does not authorize or record a server cutover, Production change, deploy,
merge, or reuse of the Final Cutover workflow.

## 3. Environment

| Item | Final value |
|---|---|
| Environment | Local workstation |
| Database host | `127.0.0.1` |
| Database port | `5432` |
| Active database | `forwarder_db` |
| Active revision | `20260801_route_exception` |
| Retained legacy database | `forwarder_db_legacy_20260727_222328` |
| Server cutover | `NOT_STARTED` |
| Production | `UNTOUCHED` |

## 4. Source Database State

The pre-cutover `forwarder_db` carried legacy migration lineage that was not a
valid ancestor in the active Alembic graph. It was treated as a read-only data
source. It was backed up before transfer and retained after cutover under the
legacy database name. No raw Alembic upgrade, stamp, archived migration, or
manual revision edit was applied to it.

## 5. Migration Graph Assessment

The active graph has one required head:
`20260801_route_exception`. The legacy revision was absent from that graph, so
an in-place upgrade path could not be proven safe. The archived revision was
evidence of historical lineage only and was not execution authority.

Decision:

- direct legacy upgrade: rejected;
- raw Alembic upgrade on the legacy database: forbidden;
- archived migration execution: forbidden;
- active-head target lineage: authoritative.

## 6. Selected Cutover Strategy

The approved strategy was:

`fresh active-head database + controlled transfer + atomic local cutover`

The fresh target reached `20260801_route_exception`, passed mapping,
reconciliation, integrity, and application gates, and only then replaced the
local active database name. The legacy database was retained for rollback.

## 7. DryRun Results

`PASS`

DryRun completed the same pre-write mapping validations used by Rehearsal,
including populated source-only policy, archive policy completeness, target
mapping availability, role support, and required source ID relationships.

## 8. Rehearsal Results

| Gate | Result |
|---|---|
| Rehearsal migration | `PASS` |
| Rehearsal transfer | `PASS` |
| Rehearsal reconciliation | `PASS` |
| Rehearsal application validation | `PASS` |
| Rehearsal cleanup | `PASS` |

The rehearsal database was disposable and was not promoted.

## 9. Final Cutover Results

| Gate | Result |
|---|---|
| Final transfer | `PASS` |
| Final reconciliation | `PASS` |
| Final application validation | `PASS` |
| Atomic local cutover | `PASS` |
| Post-cutover validation | `PASS` |

Final Cutover is complete and must not be rerun.

## 10. Application Validation Results

Rehearsal application validation, Final application validation, and
post-cutover application validation all passed. The active database revision
was confirmed as `20260801_route_exception`. No server or Production
application validation was performed or implied.

## 11. Reconciliation Metrics

| Metric | Final value |
|---|---:|
| Mapping complete | `true` |
| Rejected rows | `0` |
| Orphan foreign keys | `0` |
| Constraint violations | `0` |
| Unexplained variance | `0` |
| Row payload recorded | `false` |

Archive-only rows were counted as explained exclusions and therefore did not
create unexplained variance.

## 12. Mapping Decisions

1. `tenants` → `operational_organization`, with source-to-target ID mapping.
2. `memberships` → `operational_membership`, with organization ID remap and
   preserved/transformed permissions.
3. `tenant_owner` → the closed operational owner permission set. The generic
   `admin` permission was not granted; least privilege remained enforced.
4. `expert_user` → direct transfer. bcrypt compatibility was proven with a
   synthetic verifier; no real password hash was recorded in evidence.
5. `country` → reconciliation by ISO code. The target baseline was preserved,
   dependent foreign keys were remapped, and no duplicate country was created.
6. `alembic_version` → source revision not copied; target active head
   `20260801_route_exception` preserved.

The detailed contract remains in
[Phase 1B Local Database Mapping Contract](phase1b_local_database_mapping_contract.md).

## 13. Archived-Only Datasets

| Dataset | Decision | Closure reason |
|---|---|---|
| `audit_logs` | `ARCHIVE_ONLY` | Three rows retained in the legacy database and backup and recorded as explained exclusions |
| `customer_tenant_links` | `ARCHIVE_ONLY` | No safe direct semantic target in Active Head |
| `export_jobs` | `ARCHIVE_ONLY` | Transient export/file state with no active target |

No populated dataset remained silently classified as `SOURCE_ONLY_REVIEW`.

## 14. Security Exclusions

Transient authentication/security data was excluded according to the mapping
contract. Evidence contains aggregate metadata and sanitized decisions only:
no row payload, password hash, credential, token, DSN, export path, or sensitive
job error content was recorded.

## 15. Backup and Evidence References

Evidence archive:

`D:\1-webapp\_db_backups\15-forwarder\20260727_222328\evidence`

The archive contains 22 evidence files covered by:

`D:\1-webapp\_db_backups\15-forwarder\20260727_222328\evidence\evidence-sha256-manifest.json`

Pre-cutover backup:

`D:\1-webapp\_db_backups\15-forwarder\20260727_222328\forwarder_db_before_phase1b_cutover_20260727_222328.dump`

SHA-256:
`8b5e7b1ba21da3a51189701529386e19777649c1f9acf1caf17ae06355c8bfa4`

Final backup:

`D:\1-webapp\_db_backups\15-forwarder\20260727_222328\forwarder_db_final_20260727_222328.dump`

SHA-256:
`5166d13972582f770786d65fcf495da5b9ec3f22bbb11c7c21d4737897719408`

Both backup hashes were rechecked during documentation closure.

## 16. Active Database

`forwarder_db` is the active local database at
`20260801_route_exception`.

## 17. Retained Legacy Database

`forwarder_db_legacy_20260727_222328` is retained and must not be deleted,
renamed, upgraded, stamped, or repurposed without a separate approved gate.

## 18. Rollback Availability

Rollback remains available through the retained legacy database and verified
backups. It is not automatic after closure and requires a separate decision,
explicit operator approval, a maintenance window, and independent validation.
The controlling document is the
[Phase 1B Local Database Rollback Runbook](phase1b_local_database_rollback_runbook.md).

## 19. Operational Restrictions

```text
FINAL_CUTOVER_RERUN=FORBIDDEN
LEGACY_DATABASE_RETENTION=REQUIRED
BACKUP_RETENTION=REQUIRED
EVIDENCE_RETENTION=REQUIRED
RAW_LEGACY_ALEMBIC_UPGRADE=FORBIDDEN
SERVER_CUTOVER=NOT_STARTED
PRODUCTION=UNTOUCHED
DEPLOY=NOT_PERFORMED
MERGE=NOT_PERFORMED
```

## 20. Server and Production Status

Server access and server cutover did not occur. Production was untouched.
There was no deploy or merge. Any future server or Production transition
requires an independent plan, authorization, evidence set, and rollback gate.

## 21. Final Closure Statement

```text
PHASE_1B_LOCAL_DATABASE_CUTOVER=CLOSED
LOCAL_ACTIVE_DATABASE=forwarder_db
LOCAL_ACTIVE_HEAD=20260801_route_exception
LOCAL_LEGACY_DATABASE=forwarder_db_legacy_20260727_222328
ROLLBACK_AVAILABLE=True
DRYRUN=PASS
REHEARSAL=PASS
FINAL_CUTOVER=PASS
POST_CUTOVER_VALIDATION=PASS
SERVER_CUTOVER=NOT_STARTED
PRODUCTION=UNTOUCHED
```

The Phase 1B local database cutover is formally closed. This status closes the
local gate only and grants no authority for rerun, server cutover, Production
change, deploy, or merge.
