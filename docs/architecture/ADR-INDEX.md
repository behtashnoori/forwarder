# Forwarder ADR Index

This is the canonical discovery index for architecture decisions. The ADR body remains the decision source. Status wording in older ADR bodies is normalized here without rewriting historical records.

## Status vocabulary

- **PROPOSED**: under review; not implementation authority.
- **ACCEPTED**: approved and authoritative within its stated scope, whether implementation is pending, partial, or complete.
- **SUPERSEDED**: replaced by a named Accepted ADR.
- **DEPRECATED**: still present for compatibility but not valid for new design.
- **REJECTED**: considered and not approved.

Only an explicitly authorized architecture owner/process may change status. Implementation completion or release publication does not itself change ADR status.

## Decisions

| ADR | Title | Status | Domain | Supersedes / superseded by | Related implementation | Authoritative? |
| --- | --- | --- | --- | --- | --- | --- |
| [001](../operational/adr/ADR-001-modular-monolith.md) | Modular Monolith | ACCEPTED | System shape | none / none | Flask app, routes, services | Yes |
| [002](../operational/adr/ADR-002-request-operation-separation.md) | Request / Operation separation | ACCEPTED | Shipment | none / none | `ShipmentRequest`, `OperationalShipment`, shipment service | Yes |
| [003](../operational/adr/ADR-003-operational-shipment-terminology.md) | OperationalShipment terminology | ACCEPTED | Shipment | none / none | operational models/APIs | Yes |
| [004](../operational/adr/ADR-004-route-leg-milestone-model.md) | RouteLeg and Milestone model | ACCEPTED | Execution | none / refined by ADR-029 | `RoutePlan`, `RouteLeg`, `Milestone`, route services | Yes, with ADR-029 |
| [005](../operational/adr/ADR-005-canonical-location.md) | Canonical location and snapshots | ACCEPTED | Location | none / none | `CanonicalLocation`, route snapshots | Yes |
| [006](../operational/adr/ADR-006-additive-migration.md) | Additive migration | ACCEPTED | Data lifecycle | none / none | Alembic migrations, migration CLI | Yes |
| [007](../operational/adr/ADR-007-commercial-operational-status.md) | Commercial/operational status separation | ACCEPTED | Status | none / none | request and operational statuses | Yes |
| [008](../operational/adr/ADR-008-control-tower-work-queue.md) | Control Tower work queue | ACCEPTED | Attention/work | none / complemented by ADR-031 | `OperationalWorkItem`, OIP projection | Yes |
| [009](../operational/adr/ADR-009-milestone-verification.md) | MilestoneEvent verification | ACCEPTED | Milestones | none / refined by ADR-029 | `MilestoneEvent`, operational services | Yes, with ADR-029 |
| [010](../operational/adr/ADR-010-idempotency-locking.md) | Idempotency and locking | ACCEPTED | Mutation safety | none / none | idempotency tables/services, versions | Yes |
| [011](../operational/adr/ADR-011-explicit-migration-execution.md) | Explicit migration execution | ACCEPTED | Deployment safety | none / none | `migration_cli`, startup/readiness | Yes |
| [012](../operational/adr/ADR-012-versioned-backend-entrypoint.md) | Versioned backend entrypoint | ACCEPTED | Runtime | none / none | `backend.wsgi:app`, launch scripts | Yes |
| 013 | Reserved; no ADR file exists | — | — | — | — | No |
| [014](../operational/adr/ADR-014-no-install-time-environment-side-effects.md) | No install-time side effects | ACCEPTED | Supply chain/runtime | none / none | setup scripts/package install | Yes |
| [015](../operational/adr/ADR-015-repository-secret-scanning.md) | Repository secret scanning | ACCEPTED | Security | none / none | secret scan tooling/CI | Yes |
| [016](../operational/adr/ADR-016-time-and-timezone-architecture.md) | Time, timezone, session continuity | ACCEPTED | Time | none / none | aware operational models, time helpers | Yes; business-policy phases remain open |
| [017](../operational/adr/ADR-017-operational-project-architecture.md) | Operational Project | ACCEPTED | Project | none / none | `Project`, project services | Yes |
| [018](../operational/adr/ADR-018-execution-unit-architecture.md) | Execution Unit | ACCEPTED | Unit execution | none / none | `ExecutionUnit`, execution-unit service | Yes |
| [019](../operational/adr/ADR-019-unified-timeline-operational-event-model.md) | Unified operational event timeline | ACCEPTED | Events/timeline | none / none | `OperationalEvent`, timeline projections | Yes |
| [020](../operational/adr/ADR-020-document-attachment-visibility-architecture.md) | Document attachment and visibility | PROPOSED | Documents | none / none | future attachment scopes; MDPM is narrower | No implementation authority |
| [021](../operational/adr/ADR-021-master-data-governance-explicit-domain-tables.md) | Explicit master-data tables | ACCEPTED | Master data | none / narrowed by ADR-028 for population | CargoType, ServiceType, UOM, domain tables | Yes, with ADR-028 |
| [022](../operational/adr/ADR-022-cargo-catalog-transaction-snapshot.md) | Cargo catalog and snapshots | ACCEPTED | Cargo | none / none | `CargoCatalogItem`, `ShipmentCargoItem` | Yes |
| [023](../operational/adr/ADR-023-cargo-allocation-integrity-concurrency.md) | Cargo allocation integrity | PROPOSED | Cargo allocation | none / none | no allocation model implemented | No implementation authority |
| [024](../operational/adr/ADR-024-tenant-scoped-postgresql-cargo-search.md) | Tenant-scoped cargo search | PROPOSED | Cargo search | none / none | catalog search is narrower than proposal | No implementation authority |
| [025](../operational/adr/ADR-025-logistics-network-aggregate-boundaries.md) | Logistics Network boundaries | ACCEPTED | Logistics | none / none | `LogisticsPoint`, `ProjectLogisticsPoint` | Yes |
| [026](../operational/adr/ADR-026-logistics-point-region-contract-gap.md) | Logistics Point region contract | ACCEPTED | Logistics/geography | none / none | Logistics Point geography fields/service | Yes |
| [027](../operational/adr/ADR-027-project-configuration-aggregate-boundaries.md) | Project configuration boundaries | ACCEPTED | Project config | none / none | project service/document/milestone config | Yes |
| [028](../operational/adr/ADR-028-administrator-managed-reference-data.md) | Administrator-managed reference data | ACCEPTED | Reference data | supersedes mandatory-seed interpretations of PDR-014/ADR-021 / none | admin master-data APIs, optional catalog tooling | Yes |
| [029](../operational/adr/ADR-029-operational-milestone-event-boundaries.md) | Operational milestone/event boundaries | ACCEPTED | Milestones/events | refines ADR-004/009/019 / none | operational execution service/models | Yes |
| [030](../operational/adr/ADR-030-mdpm-document-readiness-policy.md) | MDPM document readiness | ACCEPTED | Documents | bounded use of proposed ADR-020 concepts / none | MDPM models/readiness service | Yes within MDPM scope |
| [031](../operational/adr/ADR-031-oip-deterministic-attention.md) | Deterministic OIP attention | ACCEPTED | OIP | complements ADR-008 / none | OIP facts/signals/situations | Yes |
| [032](../operational/adr/ADR-032-oip-projection-health-lifecycle.md) | OIP projection health | ACCEPTED | OIP | none / none | OIP projection state/history | Yes |
| [033](../operational/adr/ADR-033-shipment-economics-core.md) | Shipment Economics Core | ACCEPTED | Economics | none / none | economics models/service | Yes; release promotion is separate |
| [034](../operational/adr/ADR-034-optional-commercial-lineage-single-operational-shipment.md) | Optional commercial lineage, one shipment aggregate | ACCEPTED | Shipment/customer | refines ADR-002/017 creation shapes / none | `OperationalShipment.source_type/customer_id` | Yes |
| [035](../operational/adr/ADR-035-logistics-point-expert-tracking-convergence.md) | LogisticsPoint convergence for expert tracking locations | ACCEPTED | Logistics/tracking | none / none | future tenant selector and legacy tracking bridge | Yes |
| [036](../operational/adr/ADR-036-governed-document-master-catalog.md) | Governed Document Master Catalog metadata and lifecycle | ACCEPTED | Documents/reference data | none / none | future additive metadata, catalog review and optional apply tooling | Yes |
| [037](../operational/adr/ADR-037-crm-expert-request-context-access.md) | CRM expert request-context access | ACCEPTED | CRM/customer authorization | none / none | request-parented expert projection pending; no runtime change in acceptance | Yes; bounded implementation only |
| [038](../operational/adr/ADR-038-shipment-request-opaque-public-identity.md) | ShipmentRequest opaque public identity | ACCEPTED | Request identity/API security | none / none | additive UUID v4 identity and migrations pending | Yes; bounded implementation only |
| [039](../operational/adr/ADR-039-external-operational-reference-architecture.md) | External Operational Reference Architecture | ACCEPTED | Operational references/search | none / none | governed type plus bounded shipment/unit value model pending | Yes; bounded implementation only |
| [040](../operational/adr/ADR-040-tracking-current-location-status-authority.md) | Tracking Current Location and Status Authority | ACCEPTED | Tracking/location/status authority | none / none | deterministic canonical projection and compatibility transition pending | Yes; bounded implementation only |
| [041](../operational/adr/ADR-041-platform-global-logistics-point-catalog-and-organization-adoption.md) | Platform Global Logistics Point Catalog and Organization Adoption | ACCEPTED | Logistics/location governance | none / none | Phase 1 foundation and Phase 2 governance implemented locally; Phase 3 organization adoption implemented locally without operational consumption | Yes; bounded implementation only |

## Usage rules

1. Read this index and the baseline before design or implementation.
2. Read every affected Accepted ADR in full.
3. Proposed ADRs are constraints and context only; they do not authorize implementation.
4. A later ADR supersedes an earlier one only when it explicitly names it and reconciles compatibility, migration, security, rollback, and validation.
5. If an ADR body and this index disagree, stop and resolve the governance conflict before implementation.
