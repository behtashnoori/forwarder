# ADR-027 — Project Configuration Aggregate Boundaries

- **Status:** Accepted — bounded Release 1.8.0 scope
- **Date:** 2026-08-03
- **Decision authority:** Product, Architecture, Operations, Data, and Security where authorization is affected
- **Implementation state:** Release 1.8.0 bounded Slice implemented — not deployed

## Context

Release 1.8.0 discovery proposes reusable Project services, document requirements, milestone definitions, and simple target durations while existing OperationalShipment, RoutePlan, Checkpoint, Milestone, OperationalEvent, Document, and cargo snapshots own execution and history. Without an explicit boundary, configuration edits could silently rewrite or generate operational records.

The accepted boundary is now implemented in the Release 1.8.0 candidate. This factual status update does not alter the decision or authorize publication, deployment, Seed, reporting, visibility, defaults, snapshots, or automation.

## Decision

1. Project is the configuration aggregate owner. ProjectService, ProjectDocumentRequirement, ProjectMilestoneDefinition, and milestone target fields are Project Configuration children.
2. ProjectLogisticsPoint remains the accepted Project Configuration association defined by ADR-025.
3. Configuration creates no OperationalShipment, RoutePlan, Checkpoint, Milestone, Document, event, work item, or status transition.
4. ProjectDocumentRequirement references the existing governed DocumentDefinition category by numeric foreign key internally. DocumentDefinition receives an immutable UUIDv4 `public_id`; new APIs use only that opaque identity. Existing numeric case-document APIs are temporarily tolerated for compatibility and are not normative. ProjectDocumentRequirement is not a Document, Attachment, Evidence, receipt, validity proof, or execution block. ProjectMilestoneDefinition is not an operational Milestone; a target is not measured SLA performance.
5. Configuration edits never rewrite existing operational records or historical evidence.
6. OperationalShipment, RoutePlan, Checkpoint, Operational Milestone, and OperationalEvent are not modified automatically. A later accepted creation command may snapshot selected active configuration into a new OperationalShipment. Snapshot shape, timing, lineage, and correction are not authorized by this ADR.
7. All configuration is organization-scoped through the parent Project. Authorization occurs before lookup or serialization. Numeric database IDs are never exposed.
8. Used records are deactivated, not hard-deleted. Optimistic version checks guard concurrent edits.
9. No generic rules/EAV/JSON settings architecture, workflow engine, or hidden cross-aggregate side effect is permitted.

## Consequences

The boundary preserves history, allows additive adoption, and supports later reporting, but it intentionally postpones automatic inheritance and enforcement. APIs must represent explicit configuration commands. UI must label configuration separately from live operations. The authorized additive migration is `20260811_project_configuration` after `20260810_logistics_network`. It may add, populate, uniquely constrain, and make non-null an immutable UUIDv4 `document_definition.public_id` while preserving numeric keys and semantics, then create the approved tables. This identity population is not Seed. No migration execution or Production change is authorized here.

## Alternatives rejected for this proposal

- Reusing operational Milestone rows as templates: lifecycle and ownership conflict.
- Automatically generating execution from Project edits: hidden cross-aggregate effects and historical ambiguity.
- Storing arbitrary settings in JSON/EAV: weak validation, reporting, and governance.
- Treating a target duration as a complete SLA: omits calendar, scope, measurement, and accountability semantics.

## Fail-safe

Until accepted and separately implemented, the platform continues current behavior. Missing configuration never blocks existing shipment flows, and no operational record is inferred or generated.
