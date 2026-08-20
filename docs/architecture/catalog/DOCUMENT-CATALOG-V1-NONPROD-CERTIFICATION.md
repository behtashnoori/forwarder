# Document Catalog V1 Non-Production PostgreSQL Certification

Status: CERTIFIED — PRODUCTION APPLY NOT AUTHORIZED

Repository starting HEAD: `20678dee13e631532cff7b99813b256ea0477ef2`

## Reviewed package

- Package: `backend/reference_data/documents/document-catalog-international-v1.0.0.json`
- Schema version: `1`
- Catalog version: `1.0.0`
- Definitions: 46
- Checksum, verified twice: `sha256:de5ffaa0f3535bdbd9c0401ff60bd892f04fd2746e96221ab4bc2b63ef1e5998`
- Reviewed package modifications: none

## CLI contract and harness repair

Successful CLI APPLY output is one JSON object with top-level `run_id` and `status`, plus the plan fields `catalog_name`, `catalog_version`, `schema_version`, `checksum`, `environment`, `database_fingerprint`, `planned_count`, `created_count`, `updated_count`, `unchanged_count`, `conflict_count`, and `definitions`.

The prior ephemeral certification harness incorrectly read `apply_output["run"]`. The repaired strict parser reads mandatory top-level `run_id` and `status`, rejects nested `run`, rejects missing fields, and requires `status == "succeeded"`. A focused integration test feeds the parser actual CLI APPLY JSON.

## Disposable PostgreSQL identity and migration

- Host classification: loopback/local
- Server address: `127.0.0.1/32`
- Port: 5432
- PostgreSQL version: 18.0
- Recovery replica: no
- Disposable database: `forwarder_doc_catalog_cert_14bc2ec933a9`
- Database was newly created and not the persistent developer database.
- Migration start: unversioned/new database
- Migration final head: `20260901_document_catalog_runs`
- Tables after migration: 121

## Fresh read-only PLAN

- Environment: `testing`
- CREATE: 46
- NO_CHANGE: 0
- UPDATE_COMPATIBLE: 0
- CONFLICT: 0
- Fingerprint: `sha256:b622ec3df2e4735bfbc6d461700d5bfc1cca6fd84260c165d0205bf175d1105d`
- PLAN checksum matched the reviewed package.
- Every captured catalog, audit, policy, requirement, file, and association count was unchanged by PLAN.

## Governed APPLY

- CLI exit code: 0
- Status: `succeeded`
- Run ID: `ec19c35d-39a9-4e86-a04c-df7f017ce0a9`
- CREATE: 46
- NO_CHANGE: 0
- UPDATE_COMPATIBLE: 0
- CONFLICT: 0
- Intent was bound to the reviewed checksum, fresh fingerprint, explicit `testing` environment, unique idempotency key, certification operator, test-only approval reference, and explicit confirmation.

## Package/database equivalence

- Definitions: 46
- Scalar metadata comparison: PASS
- Fresh plan equivalence: 46 NO_CHANGE
- Aliases: expected 1, actual 1
- Jurisdictions: expected 46, actual 46
- Modes: expected 46, actual 46
- Stages: expected 0, actual 0
- Business scopes: expected 0, actual 0
- Provenance: expected 46, actual 46
- Active definitions: 0
- Lifecycle outcome: `SOURCE_CONFIRMED`, non-active
- `GATE_PASS`, `BARFARABARAN_REFERENCE`, `QUARANTINE_CERTIFICATE`, and `BANKING_IMPORT_DOCUMENT`: absent

## Protected-domain side effects

All apply-induced deltas were zero:

- `OrganizationDocumentRequirement`: 0
- `ProjectDocumentRequirement`: 0
- `CaseDocumentRequirement`: 0
- `OperationalDocumentRequirement`: 0
- `CaseDocumentFile`: 0
- `ArtifactAssociation`: 0

No requirement, policy, snapshot, file, association, external-reference, or ExecutionUnit document ownership was created.

## Replay and convergence

- Same idempotency key and identical request returned the original run safely.
- Definition, alias, provenance, audit, run, and revision counts did not change.
- Post-apply PLAN: CREATE 0, NO_CHANGE 46, UPDATE_COMPATIBLE 0, CONFLICT 0.
- New-key NO_CHANGE apply completed successfully without definition, audit, or revision mutation; one additional successful run record was created as designed.
- Converged fingerprint: `sha256:82336b4c12384efebc49b2254a0cf956f36c22eaf44b4ad804d7c01bbf7509eb`

## Negative controls

| Control | Result | Database mutation |
|---|---|---:|
| Wrong expected checksum | Rejected with `PackageApplyError` | 0 |
| Modified package with old checksum | Rejected with `PackageValidationError` | 0 |
| Stale plan fingerprint | Rejected with `PackageApplyError` | 0 |
| Same idempotency key with different intent | Rejected with `PackageApplyError` | 0 |
| Missing confirmation | Rejected with `PackageApplyError` | 0 |
| Missing operator | Rejected with `PackageApplyError` | 0 |
| Missing approval reference | Rejected with `PackageApplyError` | 0 |

## Transactional rollback

A synthetic package and post-write failure hook were used without modifying the reviewed package. The synthetic definition and all child relations were absent after rollback; definition and catalog-audit counts were unchanged. One sanitized failed-run record remained, matching the engine contract, and contained no injected failure detail.

Final reviewed-package PLAN remained CREATE 0, NO_CHANGE 46, UPDATE_COMPATIBLE 0, CONFLICT 0.

## Regression and cleanup

- Focused catalog/package/policy tests: 27 passed
- Full backend suite: 778 passed, 82 skipped, 1 xfailed
- Python compile: PASS
- Ruff changed scope: PASS
- `git diff --check`: PASS
- Alembic sole head: `20260901_document_catalog_runs`
- Architecture governance: PASS
- Repository secret scan: PASS, 0 findings
- Disposable database drop: PASS
- No `forwarder_doc_catalog_cert_*` database from the run remains.

Production apply, production access, deployment, push, tag, and release were not performed.
