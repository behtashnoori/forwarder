# PDR-015 — Forwarder Domain Development Roadmap

- **Status:** Accepted as strategic direction
- **Accepted:** 2026-08-02
- **Date:** 2026-08-02
- **Decision scope:** Strategic direction only; no implementation authorization
- **Target horizon:** Post-1.6.1 platform evolution
- **Architecture view:** DA-1.0 — [FDM-001](FDM-001-forwarder-domain-map.md)
- **Owners:** Product and Architecture
- **Approvals recorded:** Product, Architecture, Operations, Data; Security consulted where applicable
- **Evidence:** [Platform Constitution](platform_constitution_v1.md), [Architecture Baseline](architecture_baseline_v1.md), [Canonical Business Object Catalog](canonical_business_object_catalog.md), [Capability Map](platform_capability_map_v1.md), [PDR-013](PDR-013-cargo-data-foundation.md), [PDR-014](PDR-014-initial-reference-data-catalog.md), [RFC-002](RFC-002-cargo-data-foundation-item-traceability.md), [ADR-021 through ADR-024](adr/ADR-021-master-data-governance-explicit-domain-tables.md), [EPIC-002](EPIC-002-cargo-data-foundation.md), and release evidence through 1.6.1

## 1. Purpose and authority boundary

This roadmap provides a stable system-level map for maturing Forwarder from operational data capture into governed analytics and, later, optimization. It is not an implementation plan, backlog commitment, release authorization, or acceptance of every capability named below. Each future Slice requires its own Product decision, applicable ADR/PDR acceptance, bounded scope, and readiness evidence.

This PDR accepts only the strategic direction. It does not change ADR-023 or ADR-024, authorize allocation, customer search, reports, dashboards, or AI, or override a more specific accepted decision.

## 2. Roadmap principles

- Structured operational data must precede dashboards.
- Master Data must precede standardized reporting.
- Project configuration must precede repeatable execution.
- Transaction snapshots preserve historical meaning.
- Free-text fields remain only where evidence cannot yet be structured.
- New complexity must be justified by operational maturity.
- The platform remains usable in low-maturity operating conditions.
- The model may support future growth without forcing advanced workflows now.
- Reporting and AI consume governed operational facts rather than infer missing structure.
- Each future Slice maps to a defined roadmap layer and governance decision.

## 3. Target domain layers

| Layer | Domain and examples | Purpose |
| --- | --- | --- |
| 1 | **Reference Data:** CargoType, ServiceType, UnitOfMeasure, proposed LogisticsPointType, other controlled dictionaries | Standard vocabulary, stable codes, bilingual labels, activation/deactivation, reporting dimensions |
| 2 | **Master Data:** CargoCatalogItem, CargoItemAlias, proposed LogisticsPoint, Organization, Customer, Carrier, TransportMethod, reusable physical/business entities | Reuse, duplicate prevention, governed naming, organization scope |
| 3 | **Project Configuration:** Project, proposed ProjectLogisticsPoint, project route structure, service configuration, required documents, SLA configuration, project rules | Turn a descriptive Project into reusable operating configuration |
| 4 | **Operational Execution:** OperationalShipment, ExecutionUnit, RoutePlan, Checkpoint, Milestone, OperationalEvent, ShipmentCargoItem, and a later bounded cargo-to-unit link | Capture what actually happened |
| 5 | **Evidence and Traceability:** event timestamps, status history, documents, actor audit, transaction snapshots, exceptions, operational evidence | Preserve auditability and historical reliability |
| 6 | **Analytics and Reporting:** project/cargo visibility, delays, dwell, bottlenecks, point/service/customer performance, management dashboards | Derive reports from standardized facts |
| 7 | **Optimization and Intelligence:** ETA/delay prediction, route/carrier recommendation, capacity optimization, anomaly detection, AI assistance | Use mature operational data for decision support |

These layers are maturity stages, not a mandatory immediate implementation order in every detail. A bounded Slice may touch adjacent layers, but it must name its primary layer, dependencies, and authority.

## 4. Current maturity position

| Layer | Assessment | Repository evidence and restraint |
| --- | --- | --- |
| Reference Data | Foundation implemented | Release 1.4.0 provides governed tables and Release 1.5.0 records the initial catalog. Taxonomy breadth remains deliberately bounded. |
| Master Data | Partially implemented | CargoCatalogItem and CargoItemAlias are bounded Release 1.6.0 capabilities; organization/customer/location-related records exist, but a governed LogisticsPoint master and complete reusable entity governance do not. |
| Project Configuration | Partially implemented | Project and route foundations exist, but a governed project network, ProjectLogisticsPoint, reusable required-evidence configuration, and complete service/rule configuration are absent or unresolved. |
| Operational Execution | Substantially implemented | OperationalShipment, ExecutionUnit, revisioned RoutePlan/legs/checkpoints/milestones, events, and ShipmentCargoItem foundations exist. This does not imply every workflow or allocation is mature. |
| Evidence and Traceability | Partially implemented | Append-only milestone/event patterns, audit/outbox, timestamps, documents, snapshots, and exceptions exist, but coverage and standardized cross-domain projections are incomplete. |
| Analytics and Reporting | Limited; not standardized | Some administrative reporting exists, but the repository does not evidence standardized point/cargo/project operational analytics built on the proposed network structure. |
| Optimization and Intelligence | Deferred | AI foundations are recommendation-oriented; no governed operational maturity evidence authorizes predictive or autonomous optimization. |

The [Production Deployment State 1.6.1](production-deployment-state-1.6.1.md) records verified Production application version **1.6.1**, IIS release `release-v1.6.1-20260802`, and database revision **`20260809_cargo_catalog_items`**. Reference Data Seed was not executed, and visible UI version display remains unresolved.

## 5. Recommended development priorities

1. **Complete operational standardization:** LogisticsPointType, LogisticsPoint, ProjectLogisticsPoint, later limited cargo-to-ExecutionUnit linkage, removal of avoidable free text, and preservation of simple workflows.
2. **Improve Project configuration:** project-specific network, ordered logistics points, route patterns only when justified, required evidence/documents, and responsibility boundaries.
3. **Internal visibility and search:** find cargo across authorized Projects and OperationalShipments; show current status, linked ExecutionUnit when later authorized, current/last LogisticsPoint, and enforce organization isolation.
4. **Initial reporting:** project/shipment counts and status, point-type dwell, delayed milestones, cargo visibility, and basic operational KPIs.
5. **Advanced allocation and optimization:** proceed only when operational maturity and separately accepted decisions require them.

Internal search is distinct from customer search. The latter remains blocked by PDR-013-D10/customer-facing D11 and Proposed ADR-024.

## 6. Explicitly deferred complexity

Advanced allocation balancing; over-allocation integrity engine; partial-delivery accounting; split/merge workflows; inventory reservation; packaging hierarchy; GIS platform; geofencing; live traffic; weather; automated ETA prediction; AI route optimization; capacity optimization; digital twin; complex event choreography; generic workflow engine; and generic EAV metadata architecture are deferred. Deferral means absent or fail-safe, not implicitly approved.

## 7. Roadmap governance contract

Every future capability must identify:

- roadmap layer and owning capability;
- Product decision and architecture impact;
- data ownership and security boundary;
- migration and reporting impacts;
- backward compatibility; and
- operational-maturity justification.

The Slice must additionally identify explicit in/out scope, acceptance evidence, rollback, target version, and owners under the Constitution. PDR-015 remains a guiding roadmap; it neither automatically accepts future ADRs nor authorizes later Slices.

## 8. Decision request and fail-safe

Product, Architecture, Operations, and Data accept this maturity roadmap as strategic direction, with Security consulted where applicable. This acceptance does not authorize a future Slice automatically. Every Slice still requires separate scope, applicable governance authority, readiness evidence, and release approval. Advanced allocation, dashboards, and AI remain deferred.
