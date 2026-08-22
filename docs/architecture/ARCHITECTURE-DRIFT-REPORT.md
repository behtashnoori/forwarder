# Forwarder Architecture Drift Report

Status: Baseline evidence for Forwarder Architecture Governance v1
Repository baseline: Forwarder v1.9.5.1 at `b9a5d71916d99407a5762a2532939af12f2c130d`

## Purpose

This report records differences between the target architecture and the current repository before any runtime change. It authorizes no refactor, migration, seed, deployment, or Production access. The governance task that created it changes documentation and checks only.

## Canonical architecture already present

- ADR-017 and ADR-018 define `Project -> OperationalShipment -> ExecutionUnit`.
- ADR-002 keeps `ShipmentRequest` commercial and `OperationalShipment` operational.
- Organization ownership, membership permissions, opaque public identity, tenant-safe foreign keys, and quarantine fences are implemented across the newer operational modules.
- Cargo uses organization-owned `CargoCatalogItem` and immutable `ShipmentCargoItem` snapshots.
- Project and shipment document policy use explicit requirement and artifact-association records.
- New operational, cargo, logistics, project-configuration, MDPM, OIP, and economics timestamps are timezone-aware.

## Intentional legacy compatibility

| Area | Legacy state | Canonical target/bridge | Governance treatment |
| --- | --- | --- | --- |
| Commercial intake | `ShipmentRequest` contains historical route, cargo, assignment and tracking fields | Explicit lineage into `OperationalShipment` | Preserve compatibility; add no new execution ownership to the request without an Accepted ADR. |
| Tracking | `ShipmentTracking`, `ShipmentTransportUnit`, `ShipmentTransportUnitUpdate` | `OperationalShipment`, `ExecutionUnit`, `OperationalEvent` | Read/bridge only for new work unless an ADR explicitly authorizes a legacy change. |
| Locations | Current expert tracking selection uses tenant `LogisticsPoint`; `TrackingLocationReference` remains a legacy compatibility selector/history | `LogisticsPoint` is organization master data; `CanonicalLocation` is the route bridge/snapshot identity; ADR-041 adds a pending global/adoption target | Preserve snapshots and legacy reads; reviewed legacy/global mapping remains pending and must not be inferred by name. |
| Global logistics network | Phase 1 implements an empty platform `GlobalLogisticsPoint` schema and Platform-Admin-only read API; no adoption or catalog population | ADR-041 accepts tenant adoption and optional organization representation as later phases | Do not seed legacy rows, expose unadopted points to Experts, or weaken `LogisticsPoint` tenant ownership. |
| Time | Many legacy `DateTime()` columns store naive values | UTC Instant plus `timestamptz` and RFC 3339 offset | Preserve until each source contract is proven; never guess historical timezone. |
| Documents | `CaseDocumentFile` is request-owned | `OperationalDocumentRequirement` and `ArtifactAssociation` bind exact files to a shipment | Keep binary ownership and contextual use separate. |

## Accidental duplication or ambiguity

1. `TrackingLocationReference` and `LogisticsPoint` both present selectable logistics-place concepts but have different ownership and APIs.
2. Legacy `ShipmentTransportUnit` and canonical `ExecutionUnit` overlap in user language and tracking responsibility.
3. Workload has more than one definition: displayed workload counts `assigned` and `in_progress`, while referral documentation and rule capacity logic use broader active-assignment concepts.
4. Timestamp serializers return a mixture of explicit UTC, explicit offsets, and offset-less strings.
5. Project document requirements, request files, and shipment artifact associations use similar document terminology despite different ownership.

## High-risk drift

- Multi-unit tracking converts browser local time to UTC, removes timezone information for its legacy database column, then serializes without an offset. A browser may interpret the returned UTC wall-clock value as local time.
- Organization-owned legacy tables can contain quarantined or incomplete ownership; bypassing tenant/query fences would expose cross-tenant data.
- Cargo is shipment-scoped but has no accepted `ExecutionUnit` allocation implementation. Inferring unit quantities would invent operational truth.
- No direct `ExecutionUnit` document ownership exists. Adding a nullable unit foreign key to files would contradict the proposed attachment architecture and MDPM boundaries.
- The expert tracking selector now consumes tenant `LogisticsPoint` under ADR-035 while compatibility clients and historical updates may still use `TrackingLocationReference`; the catalogs remain distinct.
- ADR-041 Phase 1 provides only the empty platform catalog/read boundary. Platform global point -> Organization adoption -> Expert consumption remains unavailable until later controlled phases.

## Items that must not be auto-fixed here

- No timestamp data conversion or column alteration.
- No location catalog merge, backfill, selector switch, or deletion.
- No cargo allocation model.
- No document ownership change or file movement.
- No request/tracking/unit model removal.
- No workload algorithm change.
- No CRM permission or role change.
- No migration, seed, release artifact, deployment, tag, or push.

## Required follow-up governance

Each high-risk item needs a bounded Accepted ADR or an Accepted amendment naming compatibility, tenant/security, migration, rollback, and validation consequences. Until then the current compatibility behavior remains authoritative even where imperfect.
