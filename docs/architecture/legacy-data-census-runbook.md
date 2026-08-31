# Legacy data census runbook

`LEGACY_CENSUS_DATA_REQUIRED=true`

This runbook is the fail-closed handoff for MT-1 Legacy Tenant Ownership Census.
The 2026-08-12 discovery found only explicitly synthetic retained database
artifacts. No configured census DSN existed, and the running local PostgreSQL
service had no approved dataset provenance, so it was not contacted. No census
counts were produced.

## Obtain an approved non-Production clone

The data owner must create or designate a PostgreSQL clone outside Production.
The approval record must identify the source environment, backup identifier and
creation time, clone restore time, custodian, approval authority, retention
window, and confirmation that analysis on the clone is permitted. A database
name, loopback address, or developer assertion alone is not provenance.

Do not copy document binaries unless separately required and approved; the
ownership analyzer reads relational metadata only. Store neither the backup nor
raw database content in Git.

## Isolate and enforce read-only access

Use a dedicated census login with `LOGIN` and no ownership, membership in a
write-capable role, `CREATEDB`, `CREATEROLE`, replication, or bypass privileges.
Grant only `CONNECT`, schema `USAGE`, and `SELECT` on the required tables and
sequences. Configure the role and database with default read-only transactions.
Restrict the endpoint to the approved clone and approved operator network.

Before analysis, connect using credentials supplied outside the repository and
record sanitized results of:

```sql
SELECT current_database(), version(), current_user;
SHOW transaction_read_only;
SELECT version_num FROM alembic_version ORDER BY version_num;
```

The expected Alembic revision is the repository's sole head
`20260822_mt1c1_census_fence`. Stop if the revision differs; do not migrate the
clone during this run.

Prove database-enforced read-only behavior in a transaction using a harmless
temporary-object attempt, then roll back:

```sql
BEGIN READ ONLY;
SHOW transaction_read_only;
CREATE TEMP TABLE legacy_census_read_only_probe(id integer);
ROLLBACK;
```

The `SHOW` result must be `on`, and PostgreSQL must reject the `CREATE` with a
read-only transaction error. Stop if either proof fails. Do not attempt a write
against an application table.

## Run the canonical analyzer

Use [mt1a_legacy_ownership_analyzer.py](../../scripts/mt1a_legacy_ownership_analyzer.py)
without a mapping file for the initial census. Do not add precedence, fallback,
default tenant, or speculative evidence rules.

Set the approved clone DSN only in the operator process, never in a file or
shell history retained as evidence. From the repository root run:

```powershell
python scripts/mt1a_legacy_ownership_analyzer.py `
  --database-url $env:LEGACY_CENSUS_APPROVED_CLONE_URL `
  --quarantine-matrix docs/architecture/mt-1b-quarantine-exclusion-matrix.json `
  --postgresql-evidence docs/architecture/mt-1c2-postgresql-evidence.json `
  --output .codex/legacy-census/raw-analyzer-result.json
```

The analyzer is the existing SELECT-only MT-1A/B fixpoint and readiness
evaluator. It must cover the roots and remaining ambiguous entities declared in
[tenant-ownership-inventory.yaml](tenant-ownership-inventory.yaml), preserve
`CONFLICT`, `UNRESOLVED`, and `INVALID_LINEAGE`, and report readiness rather than
having readiness set manually.

## Sanitize evidence

Keep raw analyzer output in an access-controlled, untracked working directory.
Create committed evidence containing only entity type, stable internal ID,
candidate organization IDs, lineage path IDs or concise structural error,
classification, and mechanically proven activity state. Exclude names, email,
phone, address, document content, credentials, tokens, and free-text notes.

Produce counts per entity type and platform totals for `DETERMINISTIC`,
`CONFLICT`, `UNRESOLVED`, and `INVALID_LINEAGE`. Report `ACTIVE`,
`INACTIVE_OR_HISTORICAL`, or `ACTIVITY_CLASSIFICATION_UNPROVEN`; do not invent an
activity policy.

If adjudication is required, prepare a separate sanitized review package based
on [legacy-tenant-mapping.schema.json](legacy-tenant-mapping.schema.json). Every
entry must remain `PENDING_REVIEW`; no `target_organization_id` may be invented
or applied. Conflict evidence paths and exact invalid-lineage defects must be
preserved for reviewers. Because the current schema requires a target ID, do
not represent undecided candidates as a schema-valid active mapping: retain
them as a sanitized census review package until humans make and independently
review an actual decision.

## Review and cleanup

An independent read-only reviewer must verify clone provenance, database and
session read-only proofs, revision compatibility, analyzer identity, fixpoint
behavior, conflict/invalid-lineage preservation, absence of invented mappings,
PII minimization, readiness evaluation, and Production non-access. The verdict
must be `LEGACY CENSUS REVIEW — PASS` or `LEGACY CENSUS REVIEW — BLOCK`.

After review, revoke or expire clone credentials and remove only run-owned raw
outputs and disposable clone resources according to the approved retention
record. Preserve sanitized evidence and review records. Never delete or alter
the source backup.

## Absolute prohibitions

Do not connect to Production or an ambiguous database. Do not migrate schema,
run seeds, publish a census, assign tenants, apply mappings, deploy, push, move
`v1.9.1`, resume MT-1, or implement MT-2/MT-3 as part of census analysis.
