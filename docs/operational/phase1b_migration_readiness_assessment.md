# Phase 1B selected-target migration readiness assessment

## Final closure decision — 2026-07-27

Phase 1B product implementation and UAT are complete. Database cutover remains deferred. The main legacy database remains unchanged at revision `54ea21ea0d9f`; no active candidate is canonically equivalent to Main, and both stamp and a legacy marker are rejected. The approved future strategy is a fresh database at active head plus controlled data transfer under a separate gate.

The final operational evidence records successful source read-only confirmation, source inventory hashing, and rollback. Its disposable target migrated successfully to `20260801_route_exception`; target inventory hashing and baseline classification passed. The accepted baseline contained only explained migration/system occupancy, with zero unexpected business tables and zero unknown tables.

Automated mapping did not complete. The exact failure recorded by the allowed evidence is `NATIVE_FAIL:ANALYSIS:1`: the native analysis child exited `1` after `MAPPING_STARTED`. The allowed evidence contains no more specific inner analysis error. This is a known limitation and deferred work.

Cleanup completed with exit `0` and `disposable_remaining=false`. The evidence also records `main_database_targeted_for_write=false`, `server_targeted=false`, and `seed_executed=false`. No data transfer, persistent migration, stamp, deploy, or server change was performed.

- `PHASE_1B_IMPLEMENTATION_COMPLETE`
- `PHASE_1B_DATABASE_CUTOVER_DEFERRED`
- `FRESH_TRANSFER_REQUIRED`
- `AUTOMATED_MAPPING_DEFERRED`
- `MAIN_DATABASE_UNCHANGED`
- `SERVER_UNCHANGED`

## Candidate materialization evidence gate — 2026-07-27

The five candidate fingerprint outputs and SHA-256 companions declared by run
token `36f64cadd4a4` are absent. Candidate final revisions, cleanup, structural
deltas, equivalence ranking, and a safe bridge topology are therefore
unverified. The operator-reported runner exit code `0` is insufficient to
advance readiness. Persistent application remains local/server `NO` / `NO`.

See `phase1b_candidate_materialization_comparison.md`. No database operation,
migration, stamp, product change, commit, or push was performed by this gate.

`PHASE_1B_BRIDGE_TOPOLOGY_DECISION_BLOCKED`

## Superseding migration gate result — 2026-07-27

The authenticated read-only inventory subsequently reported target revision
`54ea21ea0d9f`. Alembic still reports exactly one head,
`20260801_route_exception`, but `54ea21ea0d9f` is not in the executable graph;
it is an archived deprecated root-only migration requiring manual DBA review.
No supported linear pending path can therefore be produced. Final
classification is `UNKNOWN_REVISION`, `LOCAL_PHASE1B_MIGRATION_GO=NO`, and no
backup, restore, migration, seed, or application smoke was executed.

`PHASE_1B_LOCAL_PERSISTENT_MIGRATION_GRAPH_BLOCKED`

## Canonical blocked-evidence record

- Target: `127.0.0.1:5432/forwarder_db`
- Source revision: `54ea21ea0d9f`
- Expected active head: `20260801_route_exception`
- Active graph: source revision absent; archive reference is evidence only and is not execution authorization.
- Migration classification: `UNKNOWN_REVISION`
- Go/No-Go: `LOCAL_PHASE1B_MIGRATION_GO=NO`
- Backup executed: `NO`; restore database created: `NO`
- Migration attempt count: `0`; seed executed: `NO`
- Persistent applied local/server: `NO` / `NO`
- Server access/deploy: `NO` / `NO`
- Credential or DSN recorded: `NO`
- Prohibited without an independent gate: Alembic stamp, raw Alembic upgrade, archived migration execution, manual `alembic_version` editing, and schema repair.

## Gate result

**Status:** `PHASE_1B_LOCAL_READONLY_OPERATOR_EXECUTION_REQUIRED`

The repository preflight passed on branch `feature/forwarder-multileg-route-orchestration-phase1b` at expected commit `d03ddbe8c040bcb9d4a1395794161264096fd656`, synchronized with upstream. The stage was empty, existing changes were limited to the four approved operational documents, `git diff --check` passed, the current-tree secret scan reported zero findings, and `.backend-port` remained `57065`.

The owner-selected endpoint `127.0.0.1:5432/forwarder_db` accepts connections and is served by PostgreSQL 18.0 through Windows service `postgresql-x64-18`. The owner confirmed a successful manual authenticated connection using role `postgres`; no credential was exposed. This Codex channel cannot service the required interactive `psql -W` prompt, so the approved read-only inventory was not executed and the full gate stopped as required.

## Migration graph and target gap

The local canonical Alembic graph has exactly one head:

```text
20260729_operational_vertical_slice
  -> 20260730_multileg_route
  -> 20260801_route_exception (head)
```

| Control | Result |
|---|---|
| Local heads | ONE |
| Expected head | `20260801_route_exception` |
| Target revision | UNKNOWN |
| Migration-gap classification | `UNKNOWN_REVISION` pending interactive operator run |
| Read-only session/settings | NOT ESTABLISHED |
| Database identity/project schema | NOT VERIFIED |
| Encoding/collation/timezone | UNKNOWN |
| Schema drift | NOT ASSESSED |
| Database size/active connections | UNKNOWN |
| Production indicators | UNKNOWN |
| Persistent applied | NO |

## Gate decision

The independent backup and migration application gate cannot begin. The operator must run the preserved command interactively, enter the password only at the `psql -W` prompt, and return sanitized output. The transaction must prove read-only mode and end in `ROLLBACK` before identity, revision, encoding, schema metadata/drift, bounded size, aggregate connections, and production indicators can be classified.

No migration, seed, DDL, DML, backup, restore, database/role operation, service change, server access, deploy, merge, commit, or push was performed. Product, test, migration, and configuration files were not changed.
