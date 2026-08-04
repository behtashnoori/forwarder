# Operational Execution Domain Matrix

- **Status:** Governance Accepted
- **Date:** 2026-08-04
- **Implementation authority:** YES — bounded scope; Not Implemented; Evidence deferred
- **Deployment:** Not Deployed
- **Migration:** Identifier Pending Security Track

Production relevance means relevance to the last repository-verified Production baseline (1.6.1); it does not claim live inspection.

| Concept | Classification | Model / migration | API / UI / tests | FDD / Production relevance / debt | 1.9.0 disposition |
| --- | --- | --- | --- | --- | --- |
| Project | Implemented and reusable | `Project`; 20260805 | v2 Project/unit surfaces; Project views/tests | FDD-001-006; deployed lineage; mixed Project/Shipment lineage remains | Parent configuration/source boundary |
| ProjectService | Implemented and reusable | `ProjectService`; 20260811 | configuration CRUD/UI/component tests | FDD-001-029; candidate only; not deployed | No direct execution row; source summary only |
| ProjectLogisticsPoint | Implemented and reusable | model; 20260810 | internal CRUD/select/reorder UI/tests | FDD entry; not deployed | Expected-point source; snapshot/reference |
| ProjectDocumentRequirement | Implemented and reusable | model; 20260811 | configuration CRUD/UI/tests | FDD-001-030; not deployed; no enforcement/snapshot | Completion indicator source only |
| ProjectMilestoneDefinition | Implemented and reusable | model; 20260811 | configuration CRUD/reorder/UI/tests | FDD-001-031; not deployed | Initialization source, never execution row |
| OperationalShipment | Implemented and reusable | model; 20260729 then Project FK 20260805 | `/api/operational-shipments`; list/detail UI/tests | FDD; deployed foundation; numeric legacy APIs | Execution aggregate parent; opaque IDs normative |
| ShipmentRequest | Implemented but semantically different | legacy commercial model; initial migrations | request/customer/expert APIs/UI/tests | FDD; deployed; commercial/operational coupling debt | Lineage only, not execution aggregate |
| RoutePlan / RouteLeg | Implemented and reusable | models; 20260729/20260730 | plan/leg/replan/timeline APIs; detail UI; extensive tests | FDD; deployed foundation; numeric IDs | Preserve route ownership and compatibility |
| OperationalCheckpoint | Implemented and reusable | model; 20260730 | checkpoint commands/UI/tests | FDD; deployed foundation; hard-coded catalog/status | Stage/location container, not milestone synonym |
| Operational Milestone (`Milestone`) | Partially implemented | `operational_milestone`; 20260729/30 | report/verify/correct and checkpoint commands/UI/tests | FDD-001-011; deployed; type constraint and verification-only lifecycle | Extend; do not create duplicate instance model |
| MilestoneEvent | Partially implemented | append-only model; 20260729 | nested report/correct/verify; UI recent events; tests | ADR-009/FDD; deployed; numeric IDs, narrow types, no source/location/evidence | Specialized transition/fact history base |
| OperationalEvent | Implemented but semantically different | ExecutionUnit envelope; 20260806 | v2 unit event/timeline and public projection; tests | FDD-001-008/ADR-019; deployed bounded model | Optional canonical projection, not milestone aggregate |
| Timeline | Partially implemented | read projections over milestones/events/audits | shipment timeline plus ExecutionUnit timeline; UIs/tests | ADR-019; deployed; several parallel views/order semantics | Reconcile into business timeline contract |
| RouteException | Implemented but semantically different | `OperationalRouteException`; 20260801 | reconcile/list/resolve UI/tests | operational docs; deployed foundation; fixed types/severity/free text | Preserve; do not relabel as governed exception |
| Delay | Partially implemented | calculated checkpoint delay and boolean flags | timeline/detail/unit summary/tests | FDD/ADR-019; deployed; no reason/interval entity | Add independent governed condition/history |
| Status | Contradictory/fragmented | Shipment, RouteLeg, Checkpoint, Milestone verification, ExecutionUnit statuses | multiple command/UI paths/tests | ADR-007; deployed; overlapping vocabularies | Add smallest milestone lifecycle; do not derive Shipment |
| Evidence | Deferred | no canonical Evidence model/link | no operational evidence API/UI/test authorized | ADR-020 remains Proposed; none in Production | Excluded from 1.9.0 implementation pending ADR-020 acceptance |
| Document / Attachment | Partially implemented | DocumentDefinition, CaseDocumentRequirement/File; 20260804 | case document API/UI/tests | ADR-020 Proposed; deployed candidate lineage unclear; numeric/request scope | Compatibility source; artifact/link decision required |
| TrackingUpdate | Implemented but semantically different | legacy/unit update models | public/project tracking API/UI/tests | FDD legacy bridge; deployed | Do not reuse as milestone event authority |
| Audit / actor identity | Implemented and reusable | OperationalAudit plus domain audit rows | audit summaries/indirect UI/tests | FDD; deployed; audit is not timeline | Reuse actor/audit, keep purposes separate |
| Permissions | Partially implemented | membership JSON permissions | `require_permission`, `OperationalPermission`, negative tests | FDD/security docs; deployed; route codes inconsistent | Add bounded codes through existing mechanism |
| Organization isolation | Implemented and reusable with debt | organization FKs and scoped services | foreign-tenant 404 tests | security/FDD; deployed; numeric endpoint exposure | Organization-first lookup and opaque identities |
| Correction / verification | Implemented and reusable | superseding `MilestoneEvent`, version checks | correct/verify APIs/UI/tests | ADR-009; deployed; correction targets latest event broadly | Preserve original, target explicit event, reverify correction |
| DelayReason / ExceptionReason | Missing | none | none | ADR-028 classifies equivalent lookups; none | Separate admin-managed catalogs; zero seeded rows |
| OperationalEvidenceLink | Deferred / ADR-020 Proposed | none | none authorized | ADR-020; none | No 1.9.0 implementation; future link must not duplicate binary |
| OperationalProgressSummary | Missing as bounded read model | none | fragments in detail/unit summaries | reporting readiness only | Calculated response, no mutable table/dashboard |

## Duplicate/conflict controls

- Do not add `OperationalMilestoneInstance`; extend `Milestone`.
- Do not make `ProjectMilestoneDefinition` mutable execution state.
- Do not collapse `MilestoneEvent`, `OperationalEvent`, `OperationalAudit`, or `OperationalOutbox` into one table.
- Do not rename route reconciliation exceptions into operational exceptions.
- Do not copy CaseDocumentFile binaries into evidence storage.
- Do not make delay replace milestone lifecycle state.
