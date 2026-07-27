# Phase 1B selected local persistent target inventory

## Superseding authenticated inventory result — 2026-07-27

The later owner-verified read-only inventory established PostgreSQL 18.0/UTF8,
32 application tables, 321 columns, 252 constraints, 48 indexes, database size
10,794,687 bytes, zero non-inspection active/idle connections, zero long
transactions, and revision `54ea21ea0d9f`. The revision is absent from the
executable Alembic graph and exists only in the deprecated root-migration
archive. Classification is `UNKNOWN_REVISION`; local/server persistent applied
remain `NO`, and no server endpoint was accessed.

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

## Scope and owner selection

Inspection date: 2026-07-27 (Asia/Tehran). Behtash Noori, acting as business, technical and database owner and read-only approver, selected `127.0.0.1:5432/forwarder_db` as the local persistent `INTERNAL_UAT` target. The server target remains deferred.

This gate authorized endpoint readiness and authenticated read-only metadata inspection only. It did not authorize migration, seed, DDL, DML, backup, restore, database/role creation, service changes, server access, deploy, merge, commit, or push.

**Gate result:** `PHASE_1B_LOCAL_READONLY_OPERATOR_EXECUTION_REQUIRED`.

## Selected instance

| Control | Result |
|---|---|
| Host tested | `127.0.0.1` |
| Port | `5432` |
| Database requested | `forwarder_db` |
| PostgreSQL accepting | YES (`pg_isready`) |
| Binary version | PostgreSQL 18.0 |
| Listener PID | `7456` |
| Executable path | `C:\Program Files\PostgreSQL\18\bin\postgres.exe` |
| Data directory | `C:\Program Files\PostgreSQL\18\data` |
| Windows service | `postgresql-x64-18`, Running |
| Selected by owner | YES |
| Server endpoint contacted | NO |

The same listener is bound to `0.0.0.0` and `::`. This is a security note; no bind, port, firewall, service, or process setting was changed.

The installed `psql`, `pg_dump`, `pg_restore`, and `pg_isready` tools all report PostgreSQL 18.0. Six separate Phase 1B temporary instances remain running on loopback ports and were not contacted or changed.

## Credential and execution contract

| Credential source | Present | Approved class | Value exposed |
|---|---|---|---|
| Interactive operator input | CONFIRMED by owner/manual connection | YES | NO |
| Codex interactive prompt | NOT AVAILABLE in this execution channel | YES | NO |

The owner reports a successful manual authenticated connection as role `postgres`, with `current_database=forwarder_db` and server version 18.0. The password was not disclosed. Because this execution channel cannot service the required `psql -W` prompt, Codex did not repeat the authenticated connection and did not run inventory queries. The approved SQL and exact operator command are preserved in `phase1b_local_forwarder_db_readonly_verification.md`.

## Database metadata

| Candidate ID | Instance | Database fingerprint | Encoding | Revision | Project match | Decision |
|---|---|---|---|---|---|---|
| DB-01 | PG-01 | `fp-forwarder-db-local-5432` | UNKNOWN | UNKNOWN | Owner-selected; manual identity confirmation only | OPERATOR EXECUTION REQUIRED |

| Control | Result |
|---|---|
| Environment | `INTERNAL_UAT` |
| Host | Local laptop |
| Engine/version | PostgreSQL 18.0 endpoint |
| Read-only enforced | NOT ESTABLISHED by Codex; interactive run required |
| Database identity via SQL | NOT VERIFIED |
| Encoding/collation/timezone | UNKNOWN |
| Current revision | UNKNOWN |
| Expected head | `20260801_route_exception` |
| Pending revisions | UNKNOWN |
| Schema drift | NOT ASSESSED |
| Database size/active connections | UNKNOWN |
| Production-data indicators | UNKNOWN |
| Persistent applied | NO |

## Isolation record

- Database/role creation or deletion: NO
- Authenticated SQL/row-data access: NO
- Migration/seed/DDL/DML: NO
- Backup/restore: NO
- Service/process/config change: NO
- Server access: NO
- Deploy/merge/commit/push: NO
- Credential or DSN exposed: NO
- `.backend-port`: `57065` (unchanged)
