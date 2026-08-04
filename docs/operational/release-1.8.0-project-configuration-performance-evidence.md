# Release 1.8.0 PostgreSQL Migration and Performance Evidence

- Execution: 2026-08-04 08:49–09:00 +03:30
- PostgreSQL: 18.0, `C:\Program Files\PostgreSQL\18\bin`
- Candidate/parent: `20260811_project_configuration` / `20260810_logistics_network`
- Decision: **SAME-PROJECT DATABASE INTEGRITY FIX VERIFIED** (supersedes the
  original rejected run documented below)

## Disposable environment

The newly initialized cluster used
`C:\Users\pc\AppData\Local\Temp\forwarder-r180-pg18-019fcb2d`, listened only on
`127.0.0.1:55418`, and contained only `forwarder_r180_fresh` and
`forwarder_r180_upgrade`. Preflight found no database- or Production-related
environment-variable names and no prior listener. Every migration command was
given an explicit loopback disposable `DATABASE_URL`. The repository loader
reported loading `.env`, but the explicit process URL remained the loopback
target; no Production URL or credential was used or printed.

## Migration matrix and UUID backfill

A raw `alembic upgrade head` initially failed at the historical
`20240917_initial_schema -> 20240918_add_shipment_request_log` transition because
the raw initial version table is `varchar(32)`. The database was dropped and
recreated. The repository-supported runner, which safely prepares the version
table, passed:

```powershell
$env:DATABASE_URL='postgresql+psycopg2://postgres@127.0.0.1:55418/forwarder_r180_fresh'
.\.venv\Scripts\python.exe -m backend.migration_cli upgrade head --confirm
.\.venv\Scripts\python.exe -m backend.migration_cli current
```

Fresh result: current/head `20260811_project_configuration`, `pending=no`, one
head, and zero automatic MilestoneType rows.

The second database was migrated to `20260810_logistics_network`. Three sanitized
DocumentDefinition rows with IDs 101, 205 and 999 were inserted, then the supported
runner upgraded to head. Results: total 3, non-null UUID 3, distinct UUID 3; each
was UUIDv4 and independent of its numeric ID. Numeric IDs and legacy values were
unchanged. The numeric `case_document_requirement.source_definition_id ->
document_definition.id` FK was unchanged. A new ORM row received UUIDv4
`0061eb41-ca5d-4b1b-b47e-a9b5b2d3c7f0` in the disposable fixture.

Downgrade to the parent removed the four tables and public-ID column, retained
IDs 101/205/999 and the legacy numeric FK, and reached the parent. Re-upgrade
restored the four tables, backfilled new UUIDv4 values, reached the sole head,
and inserted zero MilestoneType rows.

## Schema inventory

All four tables use bigint primary keys, 36-character opaque public identity,
active lifecycle, integer optimistic version and audit FKs/timestamps.

| Table | Principal constraints/indexes |
| --- | --- |
| `milestone_type` | unique public ID/code; positive version; active/order index |
| `project_service` | unique Project+ServiceType; partial unique active primary; order/version checks |
| `project_document_requirement` | unique Project+DocumentDefinition; level/order/version checks |
| `project_milestone_definition` | unique Project+MilestoneType; partial unique active sequence; sequence/duration/version checks |

`document_definition.public_id` is unique and non-null. Project-leading unique
and partial indexes support bounded child lookup.

## Fixture and measurements

No Seed/catalog command ran. Direct synthetic fixture SQL created 2 organizations,
102 Projects, 102 ProjectServices, 510 ProjectDocumentRequirements, 1,020
ProjectMilestoneDefinitions and 102 ProjectLogisticsPoints, with mixed lifecycle,
filters, ordering and two tenant boundaries.

Times are local observations, not a Production SLA. SQL counts include auth,
session, permission, membership, owner, count, data and relationship statements.

| Observation | Status | Rows | SQL | Bytes | ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| Services filtered, first page | 200 | 0 | 10 | 56 | 172.364 |
| Services inactive, later page | 200 | 0 | 10 | 56 | 43.876 |
| Documents REQUIRED | 200 | 2 | 11 | 944 | 58.325 |
| Documents inactive/later | 200 | 0 | 10 | 55 | 39.839 |
| Milestones active | 200 | 5 | 12 | 2,728 | 89.781 |
| Milestone reference/later | 200 | 0 | 10 | 55 | 41.209 |
| Service selector search | 200 | 2 | 6 | 346 | 39.276 |
| Document selector/later | 200 | 3 | 6 | 366 | 31.518 |
| Milestone selector/later | 200 | 5 | 6 | 808 | 31.199 |
| Point selector search | 200 | 1 | 10 | 188 | 46.952 |
| Aggregate services | 200 | 1 | 11 | 403 | 39.217 |
| Aggregate documents | 200 | 5 | 11 | 2,301 | 39.954 |
| Aggregate milestones | 200 | 10 | 12 | 5,399 | 47.031 |
| Reorder 10 active milestones | 200 | 10 | 35 | 5,354 | 128.195 |

Aggregate load used 34 statements across three independently authenticated calls.
List/selector reads did not grow per result row. Reorder used 15 bounded reads and
20 versioned two-phase writes for ten rows in one transaction.

## Query-loading correction and N+1 result

The first run found milestone list HTTP 500: wildcard `selectinload("*")` traversed
the reused logistics graph into dynamic `ShipmentRequest.quotes`. It also caused
projection reloads after reorder. The bounded fix loads only relationships used by
the response and reloads reordered rows explicitly. A focused list regression was
added. Afterward, milestone lists returned 200 at 12 statements for both five and
ten rows; no per-row read N+1 remained. Focused tests passed 13 tests.

## EXPLAIN/index findings

- Document and milestone child lists used bitmap heap scans on Project-leading
  logical/partial indexes (2 and 10 actual rows).
- Active milestone reorder lookup used the partial active sequence index.
- ProjectService used a bounded nested-loop plan for one Project.
- Selector search, primary lookup and public-ID lookup used sequential scans over
  tiny 3-, 102- and 10-row relations; this was a rational planner choice.
- No material sequential scan occurred over the 510/1,020-row child relations.

## Tenant and negative tests

The PostgreSQL-backed API returned 404 for a foreign Project and 200 for its owner.
Inactive governed references and wrong-Project/foreign-organization logistics
points returned 404 through the service. PostgreSQL rejected invalid writes with:

- `uq_project_service_logical`
- `uq_project_service_active_primary`
- `uq_project_document_requirement_logical`
- `uq_project_milestone_definition_logical`
- `uq_project_milestone_active_sequence`
- `ck_project_milestone_target`

### Blocking data-integrity failure

A rollback-only PostgreSQL probe inserted a milestone for Project `10001` that
referenced ProjectLogisticsPoint `16102`, owned by Project `10102` in Organization
`8002`. PostgreSQL accepted it:

```text
project_id=10001 | referenced_point_project=10102 | referenced_point_org=8002
```

The probe was rolled back. The service rejects the same attempt, but the migration
has only a numeric FK to `project_logistics_point.id`; it lacks the required
composite same-Project constraint. This is the blocking data-integrity failure.

## Automatic creation, gates and limitations

Fresh migration inserted zero MilestoneType rows. Fixture/API operations created
zero OperationalShipment, RoutePlan, operational Milestone and OperationalEvent
rows. No Production Seed or catalog apply ran.

Focused command:

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests\test_project_configuration.py backend\tests\test_project_configuration_openapi.py backend\tests\test_alembic_version_table.py -q
```

Result: `13 passed` with existing datetime deprecation warnings. Measurements are
synthetic local observations and not a Production SLA. The supported migration
runner is required for the historical long-revision chain.

Focused Python compilation passed. Ruff 0.15.21 passed for the three changed Python
files. The current-tree secret scan reported zero findings, the Alembic graph
reported only `20260811_project_configuration`, and `git diff --check` passed.

Cleanup completed: both disposable databases were dropped, the isolated server was
stopped, listener count on port 55418 was zero, and the exact temporary data and log
paths were deleted. No disposable runtime or credential file remains.

## Same-Project integrity fix rerun — 2026-08-04

The original run correctly rejected the candidate because PostgreSQL accepted a
milestone-to-point reference across Projects. The accepted bounded correction adds
the parent candidate key `uq_project_logistics_point_project_id_id` on
`project_logistics_point(project_id, id)` and replaces the unsafe point-ID FK with
`fk_project_milestone_definition_project_point` on
`project_milestone_definition(project_id, project_logistics_point_id)`. The point
column remains nullable; PostgreSQL `MATCH SIMPLE` semantics preserve null rows.

A newly initialized PostgreSQL 18.0 cluster at loopback-only `127.0.0.1:55419`
used two disposable databases. The supported fresh chain reached the sole
`20260811_project_configuration` head. The previous-head database reached
`20260810_logistics_network`, upgraded, downgraded cleanly to the parent, and
re-upgraded to the head. Three DocumentDefinition rows (numeric IDs 101, 205 and
999) remained present and unchanged while receiving three distinct, non-null UUIDv4
public IDs. Re-upgrade again produced zero automatic MilestoneType rows.

Raw SQL inserted a valid same-Project point reference and a null point reference.
Both succeeded. A same-organization cross-Project reference and a
cross-organization reference each failed with
`fk_project_milestone_definition_project_point`. Catalog inventory returned both
named constraints and found zero single-column FKs from the milestone table to
`project_logistics_point`. Mapper configuration and the composite relationship
passed; existing governed service 404 behavior remains covered by focused tests.

The representative rerun fixture contained 2 organizations, 105 Projects (102 new),
102 ProjectServices, 510 ProjectDocumentRequirements, 1,022
ProjectMilestoneDefinitions (1,020 new), and 105 ProjectLogisticsPoints (102 new).
The milestone list used `uq_project_milestone_active_sequence` and returned ten rows
in 0.084 ms; the document list used
`uq_project_document_requirement_logical` and returned five rows in 0.067 ms. The
composite relationship join completed in 0.058 ms. Its sequential scan covered only
105 parent rows while the 1,022-row child lookup remained indexed. No material
regression was observed. Prior HTTP SQL counts, payload sizes and N+1 conclusions
remain applicable because query-loading/API code did not change. These local figures
are development evidence, not a Production SLA.

The fixture created zero operational shipments, route plans, operational milestones
or operational events. No Seed or catalog apply ran. Both disposable databases were
dropped, the server stopped, the listener closed, and the exact temporary cluster
directory removed after the quality gates.

**Final decision: SAME-PROJECT DATABASE INTEGRITY FIX VERIFIED.**
