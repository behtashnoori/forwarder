# ADR-017: Operational Project Architecture

- Status: Accepted
- Date: 2026-07-31
- Acceptance date: 2026-07-31
- Governance scope: Governs SLICE-001 and subsequent Project-related slices unless superseded by an Accepted ADR.

## 1. Context

The current system separates commercial intake (`ShipmentRequest`) from execution (`OperationalShipment`), but has no business-level coordination boundary for a customer program containing several shipments and many execution units. Treating request, shipment, project, and unit as synonyms would recreate the God-aggregate problem rejected by ADR-002 and obscure commercial, operational, security, and reporting semantics.

## 2. Decision

Introduce `OperationalProject` (domain term: **Project**) as the business-level coordination and customer-visibility boundary. A Project may contain zero or more ShipmentRequests and one or more OperationalShipments once execution begins. A ShipmentRequest may contribute to zero, one, or multiple OperationalShipments; the exact conversion policy is explicit and idempotent rather than inferred from `won` status.

The canonical hierarchy is:

```text
Project
├── ShipmentRequest 0..N (commercial lineage)
└── OperationalShipment 1..N (execution aggregates)
    └── ExecutionUnit 1..N
```

Project is an aggregate root for project identity, ownership, membership, coordination state, aggregate status projection, and alerts. OperationalShipment remains an independent aggregate root for route and shipment execution. ExecutionUnit is an aggregate root for independently concurrent unit execution. Cross-aggregate operations use application services, explicit commands, idempotency, audit, and outbox events; they do not rely on one database transaction spanning an unbounded project.

## 3. Domain definitions

- **Project:** customer-facing and organization-owned coordination boundary grouping related commercial requests and executable shipments.
- **ShipmentRequest:** intake, quotation, and commercial decision record. It is not execution.
- **OperationalShipment:** executable end-to-end shipment with route plans, legs, checkpoints, milestones, and operational lifecycle.
- **ExecutionUnit:** independently tracked and updated physical or logical execution unit belonging to one OperationalShipment at a time.
- **Project status:** rebuildable summary derived from active OperationalShipments and ExecutionUnits, not a replacement for their states.
- **Project alert:** independent derived condition such as delay, stale updates, exceptions, or incomplete documents.

These four concepts are not aliases. APIs, schemas, UI labels, analytics, and AI tools must preserve their distinct meanings.

## 4. Invariants

- Every Project has an opaque immutable `public_id`, an organization-local unique `project_code`, an owning operational organization, and a customer owner/reference.
- Public identifiers are not sequential database identifiers.
- A Project may own multiple ShipmentRequests and OperationalShipments through explicit lineage links.
- An OperationalShipment belongs to exactly one Project after project adoption; legacy rows may temporarily have no Project during additive rollout.
- An ExecutionUnit belongs to exactly one OperationalShipment at a time; moves require an explicit transfer/split/merge workflow and history.
- Project status values are `not_started`, `in_progress`, `partially_delivered`, `completed`, or `cancelled`.
- `attention_required`, delayed units, stale units, and incomplete documents are alerts, never Project lifecycle statuses.
- A Project cannot become `completed` while a non-cancelled active unit is incomplete.
- Customer ownership and operational organization ownership are explicit and must not be inferred from contact text.

## 5. Security implications

All reads and commands are scoped by organization plus Project membership/ownership. Customer access is through an authenticated customer relationship or a high-entropy project public identifier under an approved public policy. Sequential IDs must not authorize access. Project membership cannot broaden document visibility; document-level policy remains authoritative. Cross-project and cross-organization resources fail closed with non-enumerating responses. Sensitive project actions require permission, reason where applicable, and audit.

## 6. Data and migration implications

Future implementation adds Project and explicit lineage tables additively. Existing ShipmentRequest, OperationalShipment, and ShipmentTransportUnit rows remain valid. Backfill groups records only where ownership and lineage are provable; ambiguous rows are quarantined rather than guessed. Initial Project foreign keys may be nullable for legacy compatibility, then tightened only after data gates and deprecation. No database change occurs in this documentation phase.

## 7. API implications

Additive APIs will expose Project create/read/list, explicit link/convert actions, paginated shipment/unit collections, aggregate projection, and alerts. Existing request and operational-shipment endpoints remain supported. Commands require stable contracts, authorization, `Idempotency-Key`, expected aggregate version where state changes, and auditable correlation. A future public Project projection uses an explicit allowlist.

## 8. UI implications

Expert UI gains a Project workspace with summary, shipment list, unit filters, alerts, documents, and reports. Customer UI opens by project identity and lazily navigates shipments and units. Request screens remain commercial; OperationalShipment screens remain execution-focused. Labels must never translate all four concepts into one generic “shipment” term.

## 9. AI-native implications

Project provides a stable observation boundary for AI recommendations. Level 1 agents may read allowlisted projections and explain risks with evidence. Level 2 agents may prepare explicit project/shipment/unit commands for human approval. Level 3 actions require separately approved policy, scoped service identity, idempotency, authorization, and audit. AI never mutates projections or database rows directly.

## 10. Alternatives considered

- Make ShipmentRequest the Project: rejected because it mixes intake and execution and contradicts ADR-002.
- Make OperationalShipment the Project: rejected because one Project must coordinate several shipments.
- Store project code only on ShipmentRequest: rejected because execution can span requests and independent shipments.
- One transaction for all Project children: rejected because project cardinality is unbounded and concurrency would be serialized.
- Create a separate microservice: rejected; ADR-001 keeps a modular monolith until extraction evidence exists.

## 11. Consequences

Business coordination, execution, and unit concurrency become explicit. Reporting and customer navigation become project-centric without changing commercial semantics. The cost is new lineage, projection, permission, and migration complexity.

## 12. Risks

- Incorrect cardinality assumptions during backfill.
- Ambiguous customer ownership across legacy requests.
- Project status drift if projection rules are duplicated.
- Oversized Project payloads if child collections are embedded rather than paginated.
- Terminology drift across Persian/English UI and API documentation.

## 13. Backward compatibility

Legacy ShipmentRequests continue without a Project until adopted. Existing OperationalShipment APIs and IDs remain valid. Existing ShipmentTransportUnit behavior is preserved through the compatibility approach in ADR-018. No immediate breaking API change is required.

## 14. Rollout strategy

Use expand → backfill → verify → shadow projection → feature-flagged writes → cohort reads → deprecation. Begin with internal read-only Project projections, then explicit creation/link commands, then customer projection. Preserve N/N-1 application compatibility and publish mismatch metrics.

## 15. Rollback strategy

Disable Project writes and route reads to existing Request/OperationalShipment views. Stop projectors, preserve all new data, and reconcile before retry. Do not delete Project lineage as an application rollback step. Schema downgrade is separate, rehearsed, and prohibited after irreversible adoption without backup restoration approval.

## 16. Decision disposition and open questions

- Resolved by PDR-001: one primary customer organization owns the Project; other legal parties use typed relationships and receive no implicit authority.
- Resolved by PDR-002: Project authority is role- and state-based, with elevated controls for sensitive actions.
- Resolved by PDR-003: opaque identity, internal ProjectCode, and public TrackingCode remain distinct.
- Resolved by PDR-004: completion follows all non-cancelled active units, while administrative closure remains separate.
- Operations: approved freshness and delay thresholds by mode/service.
- Data Owner: rules for grouping legacy records into Projects.

## 17. Acceptance criteria for approving the ADR

- Product, Operations, Security, and Data owners approve the four distinct domain definitions.
- Cardinalities Project→Request, Project→Shipment, and Shipment→ExecutionUnit are approved.
- Aggregate-root and transaction boundaries are accepted.
- Status and alert rules have one canonical owner and deterministic examples.
- Ownership, non-enumeration, and public identifier policy are approved.
- Additive migration and fallback strategy pass architecture review.
- ADR-018, ADR-019, and ADR-020 use the same identifiers and ownership boundaries.
