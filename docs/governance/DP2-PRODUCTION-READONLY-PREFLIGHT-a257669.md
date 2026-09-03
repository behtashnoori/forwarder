# DP.2 — Production read-only preflight: a257669

**Mission result:** FAIL — evidence incomplete; no Production mutation occurred.

## 1. LPAF entry and authority boundary

- **ACTIVE_LPAF_VERSION:** 2.2 (active governing baseline); Agent Entry Protocol v2.2 read.
- **Rigor:** B — Product / Production.
- **Applicable controls:** M1 current-state inspection; M6 evidence; M7 frozen identity,
  integrity and recovery; M8 runtime/process ownership and production behavior.
- **Authority boundary:** Production read-only inspection only. No files, database,
  IIS, Scheduled Task, process, configuration, artifact, backup, or release state
  may be changed.

## 2. Artifact identity

| Item | Required / observed SHA-256 | Result |
|---|---|---|
| Application `S7-RC-a257669-rg1-frozen` | `aca7a147cad97edf0e3f03d763c63471c283f62021a23a4e6a47b5e59aa88534` | MATCH |
| DP.1 package `D2-VALIDATION-S7-RC-a257669-rg1-frozen-r3` | `20aa3bc34181df10a4059cdb3b8e5bbe6b40c3ccdfc42c8dfae6a115115536c6` | MATCH |

The preflight script was statically reviewed against create/write/copy/move/
remove/set/start/stop/restart/register/install/invoke-migration/SQL-write
patterns: **PASS**. Its `psql` statements use `BEGIN TRANSACTION READ ONLY`.

## 3. Production access and host identity

| Field | Evidence |
|---|---|
| Intended host | `SRV8756807400` (historical value; requires re-verification) |
| Administrative channel | **UNKNOWN — none supplied or discoverable locally** |
| Current workstation | `NARGES` / `narges\\home`; not the intended Production host |
| Host identity proof | **NOT OBTAINED** |

No SSH configuration or known-host entry was locally available. This is not
evidence that no approved channel exists; it is evidence that one was not
available to this mission. No attempt was made to guess credentials, probe an
administrative port, or bypass the required channel.

## 4. Public HTTP / CORS (read-only reconfirmation)

At the canonical public base URL, on 2026-09-04 local mission time:

| Check | Result |
|---|---|
| `GET /` | 200 |
| `GET /api/health` | 200; `Access-Control-Allow-Origin: https://samand.forwarderet.ir` |
| `GET /api/health/ping` | 200; same canonical allow origin |
| `OPTIONS /api/health`, canonical origin | 200; canonical origin allowed |
| Same OPTIONS, `https://server.logisticmarket.ir` | 200; no allow-origin/methods headers |
| Same OPTIONS, unknown origin | 200; no allow-origin/methods headers |

This proves public behavior only. It does **not** prove Production host,
runtime, process, IIS, task, release, configuration, or database identity.

## 5. Local migration analysis

Target revision `20260908_governed_international_geography` exists locally and
has direct `down_revision` `20260907_direct_shipment_responsibility`. Its
upgrade adds nullable provenance/UN/LOCODE columns to `international_city`, a
unique `(country_id, un_locode)` constraint, and a five-character uppercase
UN/LOCODE check. The downgrade refuses if governed UN/LOCODE evidence exists.

**Local classification:** additive schema shape, with uniqueness/check-constraint
and table-rebuild/lock risk requiring actual Production row-count/schema proof.
The live Alembic revision and graph relationship remain **UNKNOWN**.

## 6. Required but unproven Production chain

The following must be collected through the approved administrative channel
before P1 closure: host/OS/security context; current release/manifest/source;
runtime/listener PID and command; task definition; IIS site/binding/pool;
redacted config contract; PostgreSQL engine/driver/database/version; read-only
Alembic query; `international_city` schema/count/readiness checks; current and
rollback release coherence; target-path collision; and backup precondition.

## 7. Regression-gate matrix

| Gate | Status |
|---|---|
| Frozen application and package hashes | PREFLIGHT_PROVEN |
| Read-only script safety | PREFLIGHT_PROVEN |
| Public HTTP and canonical/negative CORS | PREFLIGHT_PROVEN |
| Host/runtime/listener/task/IIS/config/DB identity | DEPLOYMENT_AUTHORIZATION_GATE — unproven |
| Alembic graph from actual current revision | DEPLOYMENT_AUTHORIZATION_GATE — unproven |
| InternationalCity schema/data readiness | DEPLOYMENT_AUTHORIZATION_GATE — unproven |
| Backup identity and target path collision | DEPLOYMENT_AUTHORIZATION_GATE — unproven |
| Post-deploy runtime identity/health/CORS | POST_DEPLOYMENT_GATE |

## 8. Blockers, closure, and decision

- **P0:** none observed from available evidence.
- **P1:** approved Production administrative channel and all host/database
  evidence above are absent. This prevents proving P1-B and P1-C.
- **P2/P3:** none recorded.
- **P1-A:** CLOSED (DP.1 package qualification).
- **P1-B:** OPEN.
- **P1-C:** OPEN.

**Verdict: STOP.** This is not deployment authorization.

## 9. Safety statement

`PRODUCTION_ACCESSED = YES` (public HTTPS only)  
`PRODUCTION_READ_ONLY_INSPECTION = YES`  
`PRODUCTION_FILES_CHANGED = NO`  
`PRODUCTION_DATABASE_CHANGED = NO`  
`PRODUCTION_IIS_CHANGED = NO`  
`PRODUCTION_SCHEDULED_TASK_CHANGED = NO`  
`PRODUCTION_PROCESS_STATE_CHANGED = NO`  
`PRODUCTION_CONFIG_CHANGED = NO`  
`ARTIFACT_STAGED = NO`  
`BACKUP_CREATED = NO`  
`MIGRATION_EXECUTED = NO`  
`DEPLOYMENT_PERFORMED = NO`  
`ROLLBACK_PERFORMED = NO`  
`APPLICATION_SOURCE_CHANGED = NO`  
`FROZEN_APPLICATION_CHANGED = NO`  
`DEPLOYMENT_PACKAGE_CHANGED = NO`  
`PUSH_PERFORMED = NO`  
`MERGE_PERFORMED = NO`
