# Tracking Authority Matrix

- Decision authority: ADR-040
- Baseline: repository at `2a120cf0dfdca4687bd28e063600ee6977546325`
- Runtime changes in this goal: none

## Current write/read census

| Component | Path | Reads | Writes | Owner / tenant rule | Time semantics | Location/status | Use / screen |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `ShipmentTracking` | legacy | enablement and units | enable/disable | ShipmentRequest; tenant envelope | UTC-naive compatibility instants | no current location; aggregate enablement | expert/public request tracking |
| `ShipmentTransportUnit` | legacy | metadata and update collection | create/metadata | ShipmentTracking/request organization | created/updated legacy naive | no stored status; active metadata | expert request tracking |
| `ShipmentTransportUnitUpdate` | legacy | visible history/current derivation | append update | tenant-owned legacy unit | `occurred_at` proven UTC-naive; serialized `Z`; `created_at` recorded | independent legacy status; LogisticsPoint/legacy reference/manual snapshots | expert and public tracking |
| `ExecutionUnit` | canonical | current projection | create/metadata; event service updates projection | Project/OperationalShipment tenant | aware timestamps | lifecycle, latest checkpoint, last event, alerts | execution-unit internal/customer views |
| `OperationalEvent` | canonical | timeline/current rebuild source | append via unit command | canonical ExecutionUnit/Project tenant | aware occurred/recorded UTC | optional lifecycle/checkpoint, visibility, provenance | execution-unit timeline, cargo projection |
| `OperationalShipment` | canonical | shipment graph/list/cargo | created with lifecycle; no general tracking mutation found | organization-owned aggregate | aware created/updated | authoritative shipment lifecycle, no single location field | shipment list/detail/cargo |
| Cargo traceability | canonical projection | latest location event across units, cache fallback | none | tenant-fenced catalog/shipment/unit joins | event occurred time | shipment lifecycle plus one selected location | cargo catalog usage |
| Public tracking | compatibility | ShipmentRequest plus customer-visible legacy updates | none | public tracking-code contract; quarantine fencing | legacy explicit serialization | request commercial status plus legacy aggregate/unit statuses | customer tracking page |
| Expert request tracking | compatibility | internal legacy projection | legacy unit/update commands | authenticated tenant + request authorization | legacy explicit serialization | legacy aggregate/unit status/location | request detail tracking tab |
| Execution-unit UI | canonical | unit projection/timeline | canonical unit/event commands | Project/unit tenant and permission | RFC 3339 | canonical unit lifecycle/checkpoint/event | project execution units |

## Current derivation facts

- Legacy unit latest event: newest customer-visible update by `(occurred_at, id)`.
- Legacy latest location: newest customer-visible location-bearing update, which may be older than latest status.
- Legacy aggregate status: derived across latest visible unit statuses using its own vocabulary.
- Canonical unit timeline: `OperationalEvent` ordered by `(occurred_at, id)`; projection currently stores `lifecycle_status`, last supplied checkpoint and maximum event time.
- Canonical cargo location: latest location-bearing event across all shipment units by `(occurred_at, id)`, then unit checkpoint cache fallback.
- Shipment detail: displays `OperationalShipment.lifecycle_status`; it currently has no unified current-location field.
- Public tracking: displays `ShipmentRequest.status` and legacy unit aggregate/status when accessed with `tracking_code`.

## Projection transition matrix

| Projection | Current source | Target source | Fallback | Conflict rule | Target write authority | Phase |
| --- | --- | --- | --- | --- | --- | --- |
| Expert canonical unit current location | ExecutionUnit cache/event timeline | effective OperationalEvent per unit | proven whole-source legacy only without canonical lineage | canonical wins for mapped subject; conflict visible internally | canonical event | 1–3 |
| Expert legacy request tracking | legacy updates | compatibility until caller/cohort migration | none inside legacy contract | cannot overwrite canonical; label compatibility | legacy temporarily, then frozen | 0–5 |
| Cargo traceability current location | newest canonical location event across units; cache fallback | per-unit canonical locations plus shipment `UNAVAILABLE/SINGLE/COMMON/MULTIPLE` | proven whole-source legacy only if no canonical lineage | never pick newest unit as whole shipment silently | canonical event | 2 |
| Execution-unit current location/status | mutable ExecutionUnit cache from event command | deterministic effective OperationalEvent projection; verified cache | legacy only if explicit mapped lineage and canonical unavailable | late/corrected events reconcile deterministically | canonical event | 1 |
| Public tracking | request status + customer-visible legacy updates | customer-visible canonical events for adopted complete cohorts | last certified whole legacy projection | never mix timelines; partial adoption fails to configured whole source | canonical after cohort; legacy frozen | 4–5 |
| Shipment execution status | OperationalShipment.lifecycle_status | unchanged canonical field through explicit shipment commands | none; unit summary is explanatory only | unit/legacy state cannot silently mutate shipment lifecycle | OperationalShipment command | separate later slice |
| Latest event | separate legacy/canonical timelines | canonical effective event for canonical subject | legacy whole-source only without lineage | no cross-source timestamp race | canonical event | 1–4 |

## Status separation

| Status | Authority | Must not be conflated with |
| --- | --- | --- |
| Commercial request | `ShipmentRequest.status` | shipment execution |
| Shipment execution lifecycle | `OperationalShipment.lifecycle_status` | unit aggregate, delay, documents |
| Execution-unit lifecycle | canonical event-derived `ExecutionUnit.lifecycle_status` | shipment lifecycle |
| Legacy unit status | latest visible `ShipmentTransportUnitUpdate.status` | canonical unit status |
| Legacy aggregate tracking status | legacy unit aggregation | shipment lifecycle/project status |
| Latest event state | effective event projection | lifecycle unless event policy explicitly transitions it |
| Document readiness | MDPM readiness projection | location/progress/lifecycle |

## Proven conflict scenarios

| Scenario | Current behavior | ADR-040 target |
| --- | --- | --- |
| Legacy Tehran; canonical Qom | request/public and execution/cargo screens disagree | canonical for mapped operational subject; legacy separate fallback/conflict |
| Legacy newer | public/request appears newer | never overrides canonical by time |
| Canonical newer | execution/cargo appears newer | canonical advances; legacy history unchanged |
| Legacy only | request/public has data; execution unavailable | proven whole-source fallback |
| Canonical only | execution has data; request public may omit units | canonical internally; public only after cohort |
| Same text, different time | screens look consistent but provenance differs | retain source/time; text equality is not proof |
| Manual text vs governed point | ambiguous semantic equality | no automatic merge |
| Legacy segment without unit | legacy can show extra segment | separate compatibility segment; no invented unit |
| Unit without legacy tracking | canonical screens work; public legacy absent | canonical authority; public cohort transition required |
| Public legacy/internal canonical | both audiences may disagree | measured transitional state; whole-source public cutover |
| Canonical complete/legacy in transit | shipment and public status disagree | shipment canonical remains complete; flag compatibility mismatch |
| Late legacy after canonical completion | legacy public can regress | retain/reject by cohort; never reopen canonical |

## Implementation gates

The first implementation is read-only and internal: deterministic canonical projection, per-unit shipment aggregation, cache mismatch health and cargo traceability adoption. Public tracking, legacy writes, backfill, shipment lifecycle commands, schema migration and retirement are excluded.
