# Canonical Tracking Projection Implementation

- Authority: ADR-040 phases 1–2
- Runtime scope: internal read projection and Cargo Catalog shipment traceability
- Schema migration: none
- Public tracking and tracking writes: unchanged

## Effective event reconciliation

`OperationalEvent.occurred_at` is the business instant. Effective events are ordered descending by `occurred_at`, then `recorded_at`, then immutable `public_id`. The final identity tie-break makes equal-time events deterministic without treating insertion order as business time. Events referenced by another event's `supersedes_event_id` are excluded; the appended correcting event remains in the effective timeline. Events are never updated or deleted by the projection.

A late-recorded event with an older occurrence instant remains history and does not replace newer current state. A latest event without a checkpoint does not erase the last effective location-bearing event. Status is independently selected from the latest effective status-bearing event. This exposes existing insertion-order cache drift without repairing it.

## Execution-unit projection

`backend/services/tracking_projection_service.py` batch-loads tenant-owned units and their canonical events. Each unit returns current location, latest event, event-derived lifecycle status, UTC provenance, fallback state, projection state, subject scope, and reconciliation health. No database writes or cache mutation occur.

OperationalEvent currently stores a checkpoint snapshot string and has no governed location identity. Location equality therefore uses exact immutable checkpoint snapshot equality; no route point, planned origin/destination, document, external reference, or cargo allocation is inferred.

## Shipment aggregation

Only active ExecutionUnits belonging to a tenant-owned OperationalShipment are included:

- `UNAVAILABLE`: no included unit has an effective canonical location.
- `SINGLE`: exactly one included unit exists and it has one effective location.
- `COMMON`: multiple included units exist and every known location has the same exact snapshot. Units without a known location do not fabricate a conflict.
- `MULTIPLE`: included units have more than one distinct known location. `current_location` is null.

The shipment's latest event is the maximum canonical unit event under the same effective ordering. Shipment lifecycle remains `OperationalShipment.lifecycle_status`; unit status never mutates it.

## Cache reconciliation

`ExecutionUnit.latest_checkpoint` and `last_event_at` are inspected only as caches:

- `CONSISTENT`: cached timestamp and location equal the canonical projections.
- `CACHE_MISSING`: a required derived cache value is absent.
- `CACHE_STALE`: a cache value matches an older effective event rather than current state.
- `CACHE_CONFLICT`: a populated cache cannot be reconciled to effective events.
- `NOT_APPLICABLE`: no canonical event-derived cache is expected and no cache is populated.

The shipment reports the highest-severity unit health. This phase performs no repair.

## Provenance and fallback boundary

The projection emits allowlisted `source`, `source_timestamp`, `is_fallback`, `projection_state`, and `subject_scope` fields. Sources are `operational_event` or `unavailable` in this implementation.

ADR-040 permits legacy whole-source fallback only after complete lineage and cohort adoption are explicitly proven. The current runtime has no certified shipment/unit mapping policy: `legacy_unit_id` is optional and request segments need not map one-to-one. Consequently this implementation does not activate legacy fallback and never merges canonical and legacy fields. A later controlled lineage/cohort goal may add a feature-gated whole-source compatibility projection.

## Cargo traceability adoption

Cargo Catalog reverse shipment usage now consumes the shared shipment projection. Cargo ownership, line snapshots, quantity, UOM, filters, pagination, tenant permission, and active-only behavior are unchanged. The response additively includes `location_state`, `is_fallback`, and `reconciliation_health`; existing `current_location`, `location_source`, and `latest_event_at` remain. `MULTIPLE` and `UNAVAILABLE` return a null `current_location`.

## Performance and remaining phases

Shipment projection is batch-oriented: shipment resolution, active-unit resolution, and event loading are bounded set queries rather than per-shipment/per-unit queries. Existing event indexes support unit/event lookup; no correctness or acceptable-performance migration was identified.

Public `/api/public/track/...`, legacy tracking reads/writes, canonical event commands, backfill, write freeze, dual write, deployment, and Production are unchanged. ADR-040 phases 3–6 remain controlled future work: canonical-only adopted writes, public canonical cohorts, legacy read-only compatibility, and retirement.
