# ADR-040: Tracking Current Location and Status Authority

- Status: ACCEPTED
- Date: 2026-08-20
- Owners: Architecture, Operations, Product, Security, Data
- Affected domain: OperationalShipment, ExecutionUnit, OperationalEvent, legacy request tracking, public tracking
- Implementation status: Decision only; runtime implementation pending

## Context

Forwarder has two independently writable tracking paths.

The compatibility path is `ShipmentRequest -> ShipmentTracking -> ShipmentTransportUnit -> ShipmentTransportUnitUpdate`. It is enabled only for a tenant-owned won request with a tracking code. An update is append-only, stores a legacy status vocabulary, an occurred time using the proven UTC-naive legacy convention, customer visibility, and at most one location authority: tenant `LogisticsPoint`, retained `TrackingLocationReference`, or manual text. Stored snapshots preserve historical display. Expert request tracking and public `/api/public/track/{tracking_code}` read this path.

The canonical path is `Project -> OperationalShipment -> ExecutionUnit -> OperationalEvent`. `OperationalEvent` is append-only and stores aware `occurred_at` and backend `recorded_at`, status, checkpoint text, visibility, provenance and idempotency. `ExecutionUnit.lifecycle_status`, `latest_checkpoint`, `last_event_at`, delay and attention fields are rebuildable current-state projections. Execution-unit views read these fields and their event timeline. Cargo traceability selects the latest location-bearing `OperationalEvent` across a shipment's units and falls back to an `ExecutionUnit.latest_checkpoint` snapshot.

The paths are not actively bridged. `ExecutionUnit.legacy_unit_id` exists, but runtime creation and event services neither populate nor consume it. A request may produce zero or more operational shipments, a shipment may have zero or more execution units, and legacy segments need not correspond one-to-one with execution units. Current code can therefore accept unrelated updates describing the same real movement. A late canonical event also currently mutates status/checkpoint projection even when `last_event_at` remains the later instant; deterministic reconciliation must precede authority cutover.

This ADR resolves E2E-007. It does not implement the decision.

## Decision

Adopt **domain-specific canonical authority with bounded compatibility fallback**.

1. `OperationalShipment.lifecycle_status` is the authoritative shipment execution lifecycle. It is distinct from request commercial status, unit lifecycle, milestone lifecycle, delay/attention conditions, legacy tracking aggregate status, and document readiness.
2. `ExecutionUnit.lifecycle_status` is the authoritative current lifecycle of one canonical execution unit, but it must be deterministically rebuildable from effective `OperationalEvent` history. Direct projection edits are prohibited.
3. The authoritative current location and latest event of a canonical execution unit come from its effective, non-superseded canonical `OperationalEvent` projection. `ExecutionUnit.latest_checkpoint` and `last_event_at` are caches/snapshots of that projection, never an independent competing fact source.
4. There is no universally valid single current location for a multi-unit `OperationalShipment`. A shipment projection reports one of `UNAVAILABLE`, `SINGLE`, `COMMON`, or `MULTIPLE` and preserves per-unit location. `COMMON` requires all included active units with known locations to resolve to the same governed identity or the same normalized immutable snapshot under an approved comparison rule. The most recently updated unit is not silently declared the shipment's location.
5. `ShipmentTransportUnitUpdate` remains authoritative only for the legacy request-tracking compatibility aggregate and for historical rows. It is not authoritative for canonical OperationalShipment or ExecutionUnit state.
6. Legacy fallback is allowed only when the requested projection has no adopted canonical lineage for that subject/cohort and the legacy request-to-shipment/unit lineage is explicitly proven. Fallback selects the legacy projection as a whole for that subject; canonical and legacy events are not interleaved by timestamp.
7. Where some canonical units exist but legacy segments are unmapped, mapped canonical units remain authoritative. Unmapped legacy segments may be shown in a separately labeled compatibility section with `is_fallback=true`; they do not determine canonical shipment location or status.
8. A source conflict is surfaced as projection health/telemetry and, where operationally useful, a neutral “tracking sources require reconciliation” condition. No source silently overwrites the other. Raw sensitive location values are not placed in metrics.
9. New operational tracking features and writes target canonical ExecutionUnit/OperationalEvent commands only. Legacy write endpoints become compatibility-only, cohort-gated, and frozen after their supported callers move. Permanent independent dual write is prohibited.
10. No automatic canonical-to-legacy or legacy-to-canonical continuous mirror is authorized. A later transactional compatibility projection/outbox may be proposed only if a supported external consumer cannot migrate, with one canonical write and replay-safe derived output; it must never accept reverse writes.

## Authority contracts

### Current location

For one canonical ExecutionUnit:

1. effective location-bearing `OperationalEvent` selected by the approved canonical event reconciliation policy;
2. `ExecutionUnit.latest_checkpoint` only as a verified cache of that same projection;
3. legacy whole-source fallback only when canonical lineage is unavailable and legacy lineage is proven;
4. unavailable.

An event without a location does not erase the last known location unless its governed event type explicitly means “location unknown/cleared.” Free text remains `manual_unverified`; governed identity and immutable snapshot remain distinct from display text.

For an OperationalShipment, aggregate the per-unit results. Do not use a global maximum timestamp to choose one unit's location. Shipments with no ExecutionUnits may use a proven shipment-scoped event/milestone projection in a separately authorized implementation; this ADR does not invent one from route plans.

### Latest event

Canonical latest-event authority is the effective `OperationalEvent` timeline for the subject. Ordering uses `occurred_at`, then `recorded_at`, then immutable event identity, after correction/supersession and source policy. `recorded_at` is not substituted for business occurrence. An out-of-order event may enter history without becoming current state when reconciliation policy says it is older.

Legacy ordering remains `(occurred_at, id)` within legacy compatibility only. Canonical and legacy timestamps are never compared to choose authority. The legacy schema's proven UTC-naive values may be serialized as UTC under its existing column-specific contract; no other naive field inherits that interpretation.

### Status

- Shipment execution status: `OperationalShipment.lifecycle_status` only.
- Execution-unit status: deterministic `ExecutionUnit.lifecycle_status` projection from canonical events.
- Request status: commercial only under ADR-007.
- Legacy unit/aggregate status: compatibility/public-tracking vocabulary only until cohort transition.
- Delay, attention, stale, exception, milestone verification and document readiness: separate conditions/projections, never shipment lifecycle aliases.

Unit status does not automatically mutate shipment lifecycle. A future implementation must define explicit shipment transition commands and completion preconditions; a read projection may summarize units but cannot write lifecycle implicitly.

## Projection provenance

Internal current-state responses use an allowlisted envelope where applicable:

```text
source: operational_event | execution_unit_projection | legacy_tracking | unavailable
source_timestamp: RFC 3339 Instant or null
is_fallback: boolean
projection_state: authoritative | fallback | partial | conflict | unavailable
subject_scope: execution_unit | operational_shipment
```

Internal projections may include an opaque source event ID and unit ID. They do not expose tenant IDs, numeric internal IDs, private notes, or foreign-source existence. User wording uses operational language such as “آخرین موقعیت ثبت‌شده” and “نیازمند تطبیق اطلاعات”; it does not expose architecture jargon.

## Public tracking

`tracking_code` remains the public identity and grants no new authority. Current public tracking continues reading the legacy allowlist until an explicit cohort meets canonical adoption gates.

For an adopted cohort, public tracking reads only customer-visible canonical ExecutionUnits and effective customer-visible OperationalEvents belonging to the authorized lineage. It may fall back to the complete legacy projection only when canonical lineage is unavailable. It must not silently mix canonical and legacy events in one timeline, expose internal provenance, numeric IDs, tenant metadata, internal notes, or the existence of hidden units/events.

Partial canonical adoption fails closed to the configured whole-source compatibility policy and emits safe projection-health telemetry. Public source labels are included only if Product/Security approve a customer-meaningful need; internal provenance remains mandatory. Public response non-enumeration and tracking-code behavior remain unchanged.

## Write authority and divergence prevention

Target write authority is canonical-only for new operational progress, location and unit status. Canonical writes use aggregate authorization, tenant-scoped parent resolution, expected version, idempotency, append-only OperationalEvent, audit/outbox as applicable, and deterministic projection reconciliation.

Legacy writes remain temporarily accepted only for inventoried compatibility callers and cohorts not yet switched. They cannot overwrite or advance canonical projections, create canonical authority by timestamp, or be extended for new capabilities. After cohort cutover, legacy writes for that cohort are rejected or disabled; historical reads remain.

Backfill is one-time, bounded and evidence-driven. It may create source-labeled canonical events only when tenant, request-to-shipment, unit identity, status mapping, location meaning, occurred-time semantics and visibility are proven. Unknowns are quarantined or retained legacy-only. Backfill never fabricates timestamps, silently maps free text, rewrites original rows, or changes shipment lifecycle. Continuous bidirectional synchronization is prohibited.

## Conflict behavior

| Conflict | Decision |
| --- | --- |
| Legacy Tehran, canonical Qom | canonical subject remains authoritative; record conflict, show legacy separately only if unmapped compatibility scope is useful |
| Newer legacy event | does not override canonical authority |
| Newer canonical event | does not rewrite legacy history; canonical projection advances |
| Legacy data, no canonical lineage | whole-source legacy fallback with provenance |
| Canonical data, no legacy | canonical result |
| Same location, different times | retain canonical source time; do not claim reconciliation from display-text equality alone |
| Manual text versus governed point | do not auto-equate; governed canonical identity wins for canonical subject, manual source remains explicit |
| Legacy segment without ExecutionUnit | separate compatibility segment; never silently manufacture an ExecutionUnit |
| ExecutionUnit without legacy tracking | canonical result; no legacy dependency |
| Public legacy, internal canonical | permitted only during measured transition; expose mismatch health internally and migrate public cohort deliberately |
| Canonical shipment complete, legacy in transit | canonical shipment status remains complete; legacy late state cannot reopen it |
| Legacy update after canonical completion | retain as legacy history, flag/reject by cohort policy, never mutate canonical state |

## Tenant, security and time

Resolution begins from trusted active membership or an already-authorized tenant parent. A projection may combine data only when organization ownership and lineage are proven inside the same tenant. Client body/query/header organization values cannot select scope. Foreign, quarantined, inactive, ambiguous and unauthorized subjects fail closed without cross-tenant fallback or existence disclosure.

All new canonical Instants follow ADR-016: timezone-aware UTC storage and RFC 3339 output with `Z` or offset. `occurred_at` and `recorded_at` remain distinct. Cross-source timestamps are comparable only after each column's semantics are proven, and comparability never establishes cross-domain authority. This ADR does not globally reinterpret legacy naive timestamps.

## Options considered

| Option | Assessment |
| --- | --- |
| A. Legacy authoritative until full migration | Low immediate change and easy rollback, but extends a request-owned compatibility aggregate, blocks canonical adoption and preserves divergent internal screens. Rejected as target. |
| B. Canonical authoritative, legacy fallback only | Strong long-term fit and explainability, but too coarse if it collapses shipment/unit/public semantics. Accepted only as refined by Option D. |
| C. Timestamp merge | Superficially simple, but source clocks, late recording, corrections, visibility, different subjects and legacy naive storage make it incorrect and hard to audit. Rejected. |
| D. Domain-specific authority | Canonical shipment/unit state, legacy compatibility/public fallback during phased adoption, explicit provenance and no silent merge. Selected. It costs lineage certification and phased public migration but preserves boundaries and rollback. |

## Transition phases

### Phase 0 — Baseline and instrumentation

Inventory callers/cohorts, publish mismatch/projection-health metrics, certify tenant and lineage rules, and pin current legacy/public behavior. Entry is this Accepted ADR. Rollback is documentation/configuration only.

### Phase 1 — Deterministic canonical projection

Implement correction/supersession-aware OperationalEvent reconciliation and rebuild tests; make `ExecutionUnit` caches verifiably derived; add provenance without changing public tracking. Entry requires event catalog/status mapping and out-of-order policy. Rollback routes canonical reads to existing unit projections and preserves events.

### Phase 2 — Internal canonical reads

Adopt per-unit and shipment aggregate location states for internal execution and cargo projections. Remove “latest unit equals shipment location.” Legacy fallback is feature/cohort gated. Entry requires shadow comparison and conflict tests. Rollback restores prior read projection; no data is deleted.

### Phase 3 — Canonical-only new internal writes

Route adopted internal workflows to canonical commands. Freeze legacy writes for adopted cohorts. Entry requires permissions, idempotency, expected-version, audit/outbox and rollback evidence. Rollback may temporarily reopen the inventoried legacy caller only after reconciliation; canonical events remain.

### Phase 4 — Public canonical cohorts

Serve customer-visible canonical projections under existing tracking codes for cohorts with complete lineage/visibility coverage. No mixed timeline. Entry requires privacy, non-enumeration, parity, partial-adoption and rollback tests. Rollback selects the last certified whole-source legacy projection.

### Phase 5 — Legacy read-only compatibility

Disable all supported legacy writes after caller evidence and observation window. Retain historical/public fallback reads where still contracted. Entry requires zero supported write callers and reconciled late updates. Rollback is a separately authorized temporary compatibility reopening.

### Phase 6 — Retirement

Remove legacy routes/models only after no supported read/write caller, complete retained-history/export policy, verified canonical coverage, public compatibility notice, rollback rehearsal, data reconciliation, governance approval and an additive contract migration plan. Application rollback never deletes either history.

## Rollback

Each phase rolls reads back to the last certified whole-source projection and disables later-phase writes/projectors. Canonical and legacy histories, source identities, lineage links and provenance are retained. Rollback never performs reverse dual write, deletes events, regenerates tracking codes, rewrites snapshots, or changes tenant ownership. Schema downgrade and data retirement require separate authorization and evidence.

## Migration boundary

No migration or backfill is authorized by this decision-only goal. Future schema work must be additive from the then-current sole Alembic head. The first implementation slice requires no schema change if existing OperationalEvent/ExecutionUnit fields suffice; any lineage, projection-health, correction or provenance schema need must be separately planned and may require a migration goal.

## Consequences

Forwarder gains one explainable authority model without pretending every shipment has one point location. Canonical execution can become the operational truth while public and historical compatibility remain reversible. Costs are deterministic projection work, explicit lineage certification, separate status vocabulary mapping, conflict observability and phased caller migration.

## Authorized first implementation slice

The first controlled implementation may only:

1. characterize current OperationalEvent out-of-order/correction behavior;
2. implement a read-only, tenant-fenced canonical projection service for ExecutionUnit current location/latest event and OperationalShipment `UNAVAILABLE/SINGLE/COMMON/MULTIPLE` aggregation;
3. prove `ExecutionUnit.latest_checkpoint` and `last_event_at` are caches of the effective event projection or report mismatch;
4. add internal provenance and projection-health output/metrics;
5. switch cargo traceability to that read-only projection behind compatibility tests.

It must not change public tracking, legacy writes, shipment lifecycle commands, backfill data, add dual writes, remove routes/models, run Production migration, deploy, release or push. A schema migration, if discovered necessary, stops that implementation goal for separate review.

## Supersedes / superseded by

- Supersedes: none
- Complements: ADR-002, ADR-005, ADR-006, ADR-007, ADR-016, ADR-018, ADR-019, ADR-029 and ADR-035
- Superseded by: none

## Status history

- 2026-08-20: ACCEPTED — domain-specific canonical authority, bounded legacy fallback, provenance, divergence prevention, public transition and retirement gates approved; runtime implementation pending.
