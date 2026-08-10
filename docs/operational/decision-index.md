# Architecture and Governance Decision Index

## Release 1.9.1 accepted architecture records

Implementation state: **Slice 1 contract only — runtime implementation not started; not published; not deployed**. Production 1.9.0 remains immutable.

| ID | Title | Status | Domain | Date | Authority |
| --- | --- | --- | --- | --- | --- |
| ADR-034 | [Optional Commercial Lineage and One OperationalShipment Aggregate](adr/ADR-034-optional-commercial-lineage-single-operational-shipment.md) | Accepted | Operations / Commercial lineage | 2026-08-10 | Slices 2–8 bounded by contract |
| R191-S1 | [Forwarder 1.9.1 Acceptance-Correction Architecture Contract](release-1.9.1-acceptance-correction-architecture-contract.md) | Accepted architecture; implementation not started | Operations / Location / Release identity | 2026-08-10 | Contract authority only |

## Release 1.9.0 accepted records

Implementation reconciliation: **Implemented — Not Published — Not Deployed**; migration `20260812_operational_execution` descends from `security_credential_remediation`.

| ID | Title | Status | Domain | Date | Authority |
| --- | --- | --- | --- | --- | --- |
| PDR-018 | [Operational Execution Foundation](PDR-018-operational-execution-foundation.md) | Partially Accepted; D11–D12 Deferred | Operational Execution | 2026-08-04 | Bounded YES |
| ADR-029 | [Operational Milestone and Event History Boundaries](adr/ADR-029-operational-milestone-event-boundaries.md) | Accepted | Operational Execution | 2026-08-04 | Bounded YES |
| R19 | [Operational Execution Slice Contract](release-1.9.0-operational-execution-slice-contract.md) | Authorized for bounded implementation | Operational Execution | 2026-08-04 | Bounded YES |
| R19-GC | [Operational Execution Governance Closure](release-1.9.0-operational-execution-governance-closure.md) | Accepted | Operational Execution | 2026-08-04 | Bounded YES |
| SEC-HEAD | [Security Track Completion](../security/forwarder_security_track_completion_20260804.md) | Complete; accepted parent `security_credential_remediation` | Security / Migration | 2026-08-04 | YES |

State is **Governance Accepted — Implementation Authorized — Not Implemented — Not Deployed**. Evidence is Deferred pending ADR-020. Security Track is complete; the Release 1.9.0 migration identifier remains unassigned until implementation, and its parent is fixed as `security_credential_remediation`. PDR-017 terminology remains authoritative.

- **Status:** Living index; source documents remain authoritative
- **Date:** 2026-08-02
- **Architecture version:** DA-1.0

Blank/TBD dates mean the source does not state a reliable decision date. Index inclusion never changes status.

## Product Decision Records

| ID | Title | Status | Domain | Decision date | Implementation release | Governing scope | Authoritative file | Supersession | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PDR-001 | Project customer/party model | Accepted | Project | 2026-07-31 | 1.2.0 lineage | Project party ownership | [Register](phase0_5_product_decision_register.md) | — | Combined register |
| PDR-002 | Project authority | Accepted | Project/Security | 2026-07-31 | 1.2.0 lineage | Role/state authority | [Register](phase0_5_product_decision_register.md) | — | Bounded by Slice |
| PDR-003 | Project identity/tracking | Accepted | Project | 2026-07-31 | 1.2.0 lineage | Public/internal identity | [Register](phase0_5_product_decision_register.md) | — | — |
| PDR-004 | Project completion | Accepted | Project | 2026-07-31 | Foundation | Completion semantics | [Register](phase0_5_product_decision_register.md) | — | Forced closure separate |
| PDR-005 | ExecutionUnit code | Accepted | Execution | 2026-07-31 | 1.2.0 | Unit identity | [Register](phase0_5_product_decision_register.md) | — | — |
| PDR-006 | Execution lifecycle | Accepted | Execution | 2026-07-31 | 1.2.0 | Shared lifecycle | [Register](phase0_5_product_decision_register.md) | — | — |
| PDR-007 | Split/merge lineage | Proposed | Execution | TBD | None | Advanced lineage | [Register](phase0_5_product_decision_register.md) | — | Deferred |
| PDR-008 | Attachment visibility | Proposed | Documents | TBD | None | Visibility policy | [Register](phase0_5_product_decision_register.md) | — | ADR-020 also Proposed |
| PDR-009 | Customer document actions | Proposed | Documents | TBD | None | Upload/replacement | [Register](phase0_5_product_decision_register.md) | — | — |
| PDR-010 | Operational thresholds | Accepted | Operations | 2026-07-31 | 1.2.0 | Versioned threshold policy | [Register](phase0_5_product_decision_register.md) | — | Bulk/ZIP excluded |
| PDR-011 | Retention/legal hold | Proposed | Compliance | TBD | None | Retention/purge/signature | [Register](phase0_5_product_decision_register.md) | — | — |
| PDR-012 | Forwarder Command Center | Accepted/delivered scope | Experience | 2026-08-01 | 1.3.0 | Portal landing/navigation | [PDR-012](PDR-012-forwarder-command-center.md) | — | — |
| PDR-013 | Cargo Data Foundation | Mixed per D01–D12 | Cargo | 2026-08-01/02 | 1.4.0/1.6.0 bounded | Cargo master/snapshot/search/allocation | [PDR-013](PDR-013-cargo-data-foundation.md) | — | D08–D10/customer D11 unresolved |
| PDR-014 | Initial Reference Data Catalog | Accepted | Reference Data | 2026-08-01 | 1.5.0 | Initial cargo/service/UOM values | [PDR-014](PDR-014-initial-reference-data-catalog.md) | — | Production Seed not executed |
| PDR-015 | Domain Development Roadmap | Accepted strategic direction | Platform | 2026-08-02 | N/A | Maturity layers | [PDR-015](PDR-015-forwarder-domain-development-roadmap.md) | — | No automatic Slice authority |
| PDR-016 | Logistics Network Foundation | Accepted D01–D10 | Logistics Network | 2026-08-02 | 1.7.0 | Types, points, Project association | [PDR-016](PDR-016-logistics-network-foundation.md) | — | Bounded implementation complete; not deployed |

## Architecture Decision Records

| ID | Title | Status | Domain | Decision date | Implementation release | Governing scope | Authoritative file | Supersession | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ADR-001 | Modular Monolith | Accepted | Platform | 2026-07-22 | Foundation | Application architecture | [ADR-001](adr/ADR-001-modular-monolith.md) | — | — |
| ADR-002 | Request/Operation Separation | Accepted | Shipment | TBD | Foundation | Commercial vs operational | [ADR-002](adr/ADR-002-request-operation-separation.md) | — | — |
| ADR-003 | OperationalShipment Terminology | Accepted | Shipment | TBD | Foundation | Canonical execution term | [ADR-003](adr/ADR-003-operational-shipment-terminology.md) | — | — |
| ADR-004 | RouteLeg/Milestone Model | Accepted | Routing | TBD | Operational foundation | Route planning/evidence | [ADR-004](adr/ADR-004-route-leg-milestone-model.md) | — | — |
| ADR-005 | Canonical Location/Snapshot | Accepted | Geography | TBD | Foundation | Location references | [ADR-005](adr/ADR-005-canonical-location.md) | — | LogisticsPoint remains separate |
| ADR-006 | Additive Migration | Accepted | Data | TBD | All | Expand-first migration | [ADR-006](adr/ADR-006-additive-migration.md) | — | — |
| ADR-007 | Commercial/Operational Status | Accepted | Lifecycle | TBD | Foundation | Status ownership | [ADR-007](adr/ADR-007-commercial-operational-status.md) | — | — |
| ADR-008 | Control Tower Work Queue | Accepted | Operations | TBD | Operational foundation | Actionable work | [ADR-008](adr/ADR-008-control-tower-work-queue.md) | — | — |
| ADR-009 | Milestone Verification | Accepted | Evidence | TBD | Operational foundation | Verified event history | [ADR-009](adr/ADR-009-milestone-verification.md) | — | — |
| ADR-010 | Idempotency/Locking | Accepted | Concurrency | TBD | All commands | Concurrency/idempotency | [ADR-010](adr/ADR-010-idempotency-locking.md) | — | — |
| ADR-011 | Explicit Migration Execution | Accepted | Operations | 2026-07-22 | All | No startup migration | [ADR-011](adr/ADR-011-explicit-migration-execution.md) | — | — |
| ADR-012 | Versioned Backend Entrypoint | Accepted | Runtime | 2026-07-22 | Foundation | Entrypoint identity | [ADR-012](adr/ADR-012-versioned-backend-entrypoint.md) | — | — |
| ADR-013 | No repository record | N/A | N/A | N/A | N/A | Identifier unoccupied | — | — | Deliberately not fabricated |
| ADR-014 | No Install-Time Side Effects | Accepted | Runtime | TBD | Foundation | Environment safety | [ADR-014](adr/ADR-014-no-install-time-environment-side-effects.md) | — | — |
| ADR-015 | Repository Secret Scanning | Accepted | Security | TBD | Foundation | Secret prevention | [ADR-015](adr/ADR-015-repository-secret-scanning.md) | — | — |
| ADR-016 | Time/Timezone Architecture | Accepted/phased | Time | TBD | Phased | Instant/local-date rules | [ADR-016](adr/ADR-016-time-and-timezone-architecture.md) | — | — |
| ADR-017 | Operational Project Architecture | Accepted | Project | 2026-07-31 | 1.2.0 | Project aggregate | [ADR-017](adr/ADR-017-operational-project-architecture.md) | — | — |
| ADR-018 | ExecutionUnit Architecture | Accepted | Execution | 2026-07-31 | Existing foundation | Unit aggregate | [ADR-018](adr/ADR-018-execution-unit-architecture.md) | — | — |
| ADR-019 | Unified OperationalEvent | Accepted | Evidence | 2026-07-31 | Existing foundation | Event/timeline envelope | [ADR-019](adr/ADR-019-unified-timeline-operational-event-model.md) | — | — |
| ADR-020 | Document Visibility Architecture | Proposed | Documents | 2026-07-31 | None | Document boundaries | [ADR-020](adr/ADR-020-document-attachment-visibility-architecture.md) | — | — |
| ADR-021 | Explicit Master Data Tables | Accepted | Master Data | 2026-08-01 | 1.4.0 | Governed domain tables | [ADR-021](adr/ADR-021-master-data-governance-explicit-domain-tables.md) | — | — |
| ADR-022 | Cargo Catalog/Snapshot | Accepted bounded | Cargo | 2026-08-02 | 1.6.0 | Catalog and transaction snapshot | [ADR-022](adr/ADR-022-cargo-catalog-transaction-snapshot.md) | — | — |
| ADR-023 | Allocation Integrity | Proposed | Cargo/Execution | 2026-08-01 | None | Allocation concurrency | [ADR-023](adr/ADR-023-cargo-allocation-integrity-concurrency.md) | — | Deferred |
| ADR-024 | Tenant Cargo Search | Proposed | Search/Security | 2026-08-01 | None | Customer cargo search | [ADR-024](adr/ADR-024-tenant-scoped-postgresql-cargo-search.md) | — | Unauthorized |
| ADR-025 | Logistics Network Boundaries | Accepted | Logistics Network | 2026-08-02 | 1.7.0 candidate | Type/master/config/plan/evidence separation | [ADR-025](adr/ADR-025-logistics-network-aggregate-boundaries.md) | — | — |
| ADR-026 | Logistics Point Region Contract | Accepted | Logistics Network | 2026-08-03 | 1.7.0 | Governed Country and optional Province/City; `region_name` deferred | [ADR-026](adr/ADR-026-logistics-point-region-contract-gap.md) | — | Security consulted; future region requires a separate decision and additive migration |

## RFCs

| ID | Title | Status | Domain | Decision date | Implementation release | Governing scope | Authoritative file | Supersession | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RFC-001 | Multi-Execution Operational Project | Draft | Project/Execution | 2026-07-31 | Foundation candidates | Problem/options | [RFC-001](RFC-001-multi-execution-operational-project.md) | — | Non-authoritative |
| RFC-002 | Cargo Foundation/Traceability | Partially authorized | Cargo | 2026-08-01/02 | 1.6.0 bounded | B3/B4 authorized; later slices not | [RFC-002](RFC-002-cargo-data-foundation-item-traceability.md) | — | RFC itself grants no authority |

## EPICs

| ID | Title | Status | Domain | Decision date | Implementation release | Governing scope | Authoritative file | Supersession | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EPIC-001 | Project Aggregate Foundation | Draft plan | Project | 2026-07-31 | 1.2.0 lineage | Project/Execution slices | [EPIC-001](EPIC-001-project-aggregate-foundation.md) | — | No decision authority |
| EPIC-002 | Cargo Data Foundation | In progress/mixed | Cargo | 2026-08-01 | 1.4.0–1.6.0 bounded | B1/B3/B4 delivered; others unauthorized | [EPIC-002](EPIC-002-cargo-data-foundation.md) | — | No decision authority |

## Release 1.8.0 accepted governance records

| ID | Title | Status | Domain | Decision date | Implementation release | Governing scope | Authoritative file | Supersession | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PDR-017 | Canonical Operational Taxonomy | Accepted | Platform/Project Configuration | 2026-08-03 | Slice-specific | Vocabulary and conceptual boundaries | [PDR-017](PDR-017-canonical-operational-taxonomy.md) | — | Terminology only; no automatic capability authority; unevidenced terms remain TBD |
| ADR-027 | Project Configuration Aggregate Boundaries | Accepted bounded | Project Configuration | 2026-08-03 | 1.8.0 authorized | Configuration/execution/history separation | [ADR-027](adr/ADR-027-project-configuration-aggregate-boundaries.md) | — | No hidden side effects; bounded Slice authority only |
| R18 | Project Configuration Foundation | Implementation Complete — Not Published — Not Deployed | Project Configuration | 2026-08-03 | 1.8.0 | Services, existing network integration, document requirements, milestone definitions, elapsed targets | [1.8.0 Contract](release-1.8.0-project-configuration-slice-contract.md) | — | D01–D15 Accepted; Production unchanged; Seed not executed |
| R18-C | Project Configuration Governance Closure | Accepted / Implemented — Not Deployed | Project Configuration | 2026-08-03 | 1.8.0 | Closure and explicit implementation authority | [Closure](release-1.8.0-project-configuration-governance-closure.md) | — | DocumentDefinition reused; MilestoneType catalog prepared, not applied |
| R18-A1 | DocumentDefinition Identity Amendment | Accepted / Implemented — Not Deployed | Project Configuration/Documents | 2026-08-03 | 1.8.0 | Opaque DocumentDefinition identity, technical backfill, migration amendment | [Identity Amendment](release-1.8.0-document-definition-identity-amendment.md) | — | Legacy numeric APIs temporarily tolerated; no new numeric disclosure |

| ADR-028 | Administrator-Managed Reference Data | Accepted | Platform/Reference Data | 2026-08-04 | Permanent policy | Deployment-independent administrator ownership, empty catalogs, optional import/export/Seed | [ADR-028](adr/ADR-028-administrator-managed-reference-data.md) | Supersedes deployment-dependent interpretations of PDR-014/ADR-021 | No release depends on population |

## Slice contracts

| ID | Title | Status | Domain | Decision date | Implementation release | Governing scope | Authoritative file | Supersession | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SLICE-001 | Project Aggregate Foundation | Delivered foundation per release evidence | Project | 2026-07-31 onward | 1.2.0 lineage | Project aggregate | [EPIC-001](EPIC-001-project-aggregate-foundation.md) | — | Source combines candidate slices |
| SLICE-B1 | Master Data Governance Foundation | Delivered | Master Data | 2026-08-01 | 1.4.0 | CargoType/ServiceType/UOM governance | [EPIC-002](EPIC-002-cargo-data-foundation.md) | — | — |
| SLICE-B3/B4 | Cargo Catalog/ShipmentCargoItem | Delivered/deployed lineage | Cargo | 2026-08-02 | 1.6.0 | Bounded catalog and snapshot | [1.6.0 Closure](release-1.6.0-cargo-governance-closure.md) | — | — |
| R17 | Logistics Network Foundation | Accepted / implemented | Logistics Network | 2026-08-02 | 1.7.0 | Type, point, Project association | [1.7.0 Contract](release-1.7.0-logistics-network-slice-contract.md) | — | R17-D01–D10 Accepted; bounded source implementation complete; not deployed |
