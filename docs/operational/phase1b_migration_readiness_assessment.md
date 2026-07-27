# Phase 1B migration readiness assessment

## Gate result

**Status:** `PHASE_1B_PERSISTENT_TARGET_SELECTION_BLOCKED`

Repository preflight passed at commit `795edd778b4a7d4247c84d1f1a24a8b5429df230` on branch `feature/forwarder-multileg-route-orchestration-phase1b`, synchronized with its upstream. The working tree and stage were clean before these documentation changes, and the current-tree secret scan reported zero findings.

The canonical local Alembic metadata reports one head:

```text
20260801_route_exception (head)
```

The recent linear graph is:

```text
20260729_operational_vertical_slice
  -> 20260730_multileg_route
  -> 20260801_route_exception
```

No persistent target was selected and read-only access was not approved, so target revision, schema drift, server version, encoding, extensions, size, and connection load remain unknown. No migration, seed, DDL, DML, backup, or restore was executed.

## Target inventory result

| Control | Result |
|---|---|
| Read-only enforced | NOT ATTEMPTED; target/approval absent |
| PostgreSQL version | UNKNOWN |
| Encoding/collation/timezone | UNKNOWN |
| Current revision | UNKNOWN |
| Expected revision | `20260801_route_exception` |
| Pending revisions | UNKNOWN |
| Multiple local heads | NO |
| Schema drift | NOT ASSESSED |
| Database size class | UNKNOWN |
| Active connections class | UNKNOWN |
| Extensions | UNKNOWN |

## Migration-gap classification

Target classification is not possible until the selected target's `alembic_version` metadata is read under an enforced read-only session. Permitted outcomes are `UP_TO_DATE`, `BEHIND_LINEAR`, `BEHIND_WITH_DATA_RISK`, `DIVERGED`, `UNKNOWN_REVISION`, `VERSION_TABLE_MISSING`, or `MULTIPLE_HEADS`.

Only `UP_TO_DATE` or a reviewed linear-behind state may proceed. Divergence, an unknown revision, multiple heads, an unsupported server, or unexplained schema drift is a No-Go.

## Source-based migration risk

| Revision | Operation summary | Lock risk | Data risk | Rollback | Decision |
|---|---|---|---|---|---|
| `20260730_multileg_route` | Creates checkpoint/dependency structures; adds and alters route-plan, leg, milestone, work-item, and idempotency columns/constraints/indexes; performs milestone/work-item updates; replaces a PostgreSQL validation function | HIGH until target size/load is known | HIGH: backfill, new uniqueness/FKs/checks, non-null transitions, and compatibility assumptions require aggregate prechecks | Downgrade exists but is destructive and fail-closed when Phase 1B data exists; verified backup/restore is preferred | BLOCKED pending target inventory and prechecks |
| `20260801_route_exception` | Adds response and reconciliation columns plus a check constraint; `occurrence_count` is non-null with a constant default | MEDIUM until PostgreSQL version/table size is known | MEDIUM: existing rows receive default semantics and constraint validity must be checked | Downgrade exists but fails closed if reconciliation history or stored responses exist | BLOCKED pending target inventory and prechecks |

## Read-only inventory contract for a later approved gate

The approved operator must open a bounded PostgreSQL session with `default_transaction_read_only=on`, statement timeout 30 seconds, and lock timeout 5 seconds, then prove both transaction read-only settings are `on`. The session may inspect only catalog metadata and aggregate estimates.

Required inventory:

- server version, encoding, collation, timezone, database fingerprint, role capabilities, extension names;
- current Alembic revision and version-table shape;
- schema/table/column/index/constraint/function/trigger metadata;
- catalog row estimates, aggregate database size, and aggregate active-connection count;
- expected Phase 1A and Phase 1B object presence and unexpected manual objects.

No `SELECT *`, operational row output, user/customer/shipment identifiers, unbounded count, or credential/DSN logging is permitted.

## Aggregate precheck plan

Run only after target selection and read-only approval. Each query must return counts or booleans, be bounded, and emit no row identity.

| Risk | Planned aggregate check | Required result |
|---|---|---|
| New unique constraints | Count duplicate candidate key groups for plan version, checkpoint sequence, dependency edges, milestone ownership, open route exceptions, and scoped idempotency | Zero duplicate groups |
| Non-null transitions/backfill | Count null source values required to populate milestone plan/projected values and work-item detection timestamps | Zero unresolved rows |
| Foreign keys | Count orphan or cross-scope shipment/organization, plan/shipment, leg/plan, checkpoint/plan, milestone, dependency, and work-item relationships | Zero |
| Status/check constraints | Count values outside the source-defined plan, leg, checkpoint, milestone, verification, work-item, and resolution-source domains | Zero |
| Active RoutePlan integrity | Count shipments with invalid active-plan cardinality or non-linear version/provenance relationships | Zero |
| Shipment duplication | Count duplicate operational-shipment mappings under the canonical business key | Zero |
| Version table capacity | Inspect metadata for `alembic_version.version_num` and use only the official runner, which handles the historical width issue | Compatible before upgrade |

## Schema-drift comparison plan

After approval, compare sanitized catalog manifests against migration-defined expected objects. Record counts and object names only.

| Object group | Expected | Target | Drift |
|---|---:|---:|---|
| Tables | Derive from canonical migration graph | UNKNOWN | NOT ASSESSED |
| Columns | Derive from canonical migration graph | UNKNOWN | NOT ASSESSED |
| Foreign keys | Derive from canonical migration graph | UNKNOWN | NOT ASSESSED |
| Unique constraints | Derive from canonical migration graph | UNKNOWN | NOT ASSESSED |
| Indexes | Derive from canonical migration graph | UNKNOWN | NOT ASSESSED |
| Check constraints | Derive from canonical migration graph | UNKNOWN | NOT ASSESSED |

Any unexplained missing, extra, renamed, or semantically different object blocks migration application.

## Readiness gaps

- exactly one persistent target is not selected;
- environment/database owners and read-only approval are absent;
- actual engine version and current revision are unknown;
- schema drift and pre-migration data risks are unmeasured;
- backup destination, capacity, encryption, retention, RPO/RTO, and restore test are unapproved;
- maintenance window, downtime budget, communication channel, and Go/No-Go authority are unset.

The next action is a human target-selection and access-approval decision, not migration execution.
