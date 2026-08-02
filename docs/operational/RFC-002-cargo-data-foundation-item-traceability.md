# RFC-002: Cargo Data Foundation and Item Traceability

- **RFC ID:** RFC-002
- **Status:** Partially authorized — bounded SLICE-B3/B4 foundation approved for Release 1.6.0 reconciliation
- **Date:** 2026-08-01
- **Review readiness:** Ready for Product and Architecture Review
- **Capabilities:** CAP-013, CAP-002, CAP-003, CAP-007, CAP-009, CAP-010, CAP-006
- **Decision authority:** None. This RFC does not accept PDR-013, approve an ADR, or authorize implementation.
- **Authorization reference:** [Release 1.6.0 Cargo Governance Closure](release-1.6.0-cargo-governance-closure.md). Authority comes from that decision record, not from this RFC.
- **Discovery evidence:** [Discovery and Domain Analysis Report](discovery-cargo-data-and-scroll-analysis-20260801.md); evidence availability does not resolve its Product decisions.

## 1. Problem statement and examples

Forwarder has shipment/request descriptions and operational tracking but no governed cargo taxonomy, service package model, UOM policy, tenant-owned cargo catalog, transactional shipment-item snapshot, unit allocation, or authenticated cross-Project item search. Consequently cargo meaning can drift, allocation cannot be proven quantitatively, and a customer cannot safely answer where the same item appears across its Projects.

The canonical capability is **Cross-Project Cargo Item Search**. Examples are deliberately domain-neutral:

- an automotive brake component with an optional manufacturer part number such as `BRK-42`;
- an industrial machine identified by a serial number;
- a steel coil or other material item measured by weight and an explicit UnitOfMeasure;
- a food pallet identified by batch or lot;
- chemical cargo carrying governed hazard attributes; and
- generic consumer or finished goods described without a specialized identifier.

An authenticated customer should find only authorized matching ShipmentCargoItems and see customer-visible Project/shipment progress without learning another organization’s identifiers, internal notes, declared value, restricted HS code, or hazard details lacking an approved projection. Historical shipment meaning must remain the original snapshot even if catalog display data later changes. Part numbers are optional facts for applicable item classes, and cargo is not assumed to be count-based.

Other examples include one Project accepting transport, customs clearance, and warehousing while different OperationalShipments fulfill different services; one shipment item allocated across several active units in the same shipment; and a closed legacy Project retaining an unclassified free-text cargo description rather than receiving a guessed CargoType.

## 2. Current limitations

- Cargo descriptions are not a governed item identity or immutable transaction snapshot.
- Transport mode and business service lack an approved independent cardinality model.
- Quantity, weight, and volume cannot be relied on when units are implicit or free text.
- No organization-owned catalog/alias boundary supports safe cross-Project matching.
- No allocation invariant prevents concurrent over-allocation.
- Existing public tracking is Project/request scoped and must not become anonymous portfolio search.
- No accepted per-field customer visibility policy exists for cargo search.
- The governed Discovery and Domain Analysis Report is evidence, not authority. PDR-013-D01/D04/D05/D06/D07/D12 and internal-only D11 now have bounded acceptance records; all other Product decisions remain unresolved.

## 3. Scope and domain boundaries

In scope for governance: CargoType, ServiceType, accepted service packages, UnitOfMeasure, CargoCatalogItem and aliases, ShipmentCargoItem snapshots, ExecutionUnitCargoAllocation, tenant-scoped search, legacy adoption, audit, authorization, correction, and phased delivery.

The following boundaries span accepted and still-proposed slices; their authority and status come from their PDR/ADR records, not this RFC:

- CAP-013 governs explicit reference/master data and catalog conventions.
- ShipmentRequest owns requested services; Project owns accepted package; OperationalShipment owns fulfilled-service links and ShipmentCargoItem transaction snapshots.
- CargoCatalogItem is organization-scoped for Release 1.6.0 and is not historical transaction truth.
- ExecutionUnitCargoAllocation links a shipment snapshot item to an eligible unit while preserving OperationalShipment and Project invariants.
- CAP-007 consumes a customer-safe projection; CAP-010 enforces tenant/resource/field authorization; CAP-006 may later consume governed projections.

## 4. Non-goals

This RFC does not implement or approve tables, migrations, endpoints, admin/customer UI, allocation algorithms, conversion, split/merge, public portfolio search, autonomous classification, a generic EAV framework, external search infrastructure, or destructive legacy cleanup. It does not collapse TransportMode, ServiceType, CargoType, HS classification, and UOM into one axis.

## 5. Master-data strategy

The governed strategy uses explicit domain tables sharing immutable codes, bilingual labels/symbols where relevant, activation rather than deletion after use, provenance, ownership, timestamps, audit, and controlled aliases. CargoType and UOM follow their accepted B1 decisions. Release 1.6.0 uses only organization-scoped catalog items; platform-global definitions are deferred.

PDR-013 and ADR-021/022 define which parts are Accepted. Allocation, customer search, and other deferred portions remain proposals.

## 6. Search and security strategy

The candidate search path is authenticated and tenant-first: resolve the principal and authorized organization/resource scope before exact or trigram text matching, paginate and rate-limit, return opaque identifiers, and project only allowlisted customer fields/events. PostgreSQL exact matching plus `pg_trgm` is the initial architecture candidate; an external engine is deferred until measured scale/relevance evidence justifies it. Queries, logs, exports, caches, and AI context must not cross organization boundaries or reveal forbidden-match existence.

Public tracking remains Project-scoped. Anonymous cross-Project item search is out of scope. Internal notes are excluded; declared value and sensitive/customs codes require explicit permission.

## 7. Legacy compatibility and migration principles

Adoption follows expand → migrate → verify → switch → contract. New nullable structures coexist with legacy descriptions. New transactions use accepted structured rules after rollout; old descriptions remain readable. No UOM, CargoType, catalog identity, alias, Project relationship, or allocation is guessed. Valuable open Projects may be manually mapped with audit; closed history remains `UNCLASSIFIED` by default. Rollback disables new writes/projections and preserves new records for reconciliation rather than deleting history.

## 8. Phased rollout and slice candidates

1. **SLICE-B1:** governance conventions and accepted master-data foundation.
2. **SLICE-B2:** CargoType, ServiceType, and UOM administration.
3. **SLICE-B3:** organization catalog and aliases.
4. **SLICE-B4:** ShipmentCargoItem transactional snapshot.
5. **SLICE-B5:** allocation integrity and correction.
6. **SLICE-B6:** authenticated organization-scoped customer search.

Every slice is independently deployable, additive, feature-gated, and blocked on its accepted PDR/ADR set. No slice is authorized by this RFC.

## 9. Success criteria

- Structured new cargo records are never unitless and retain historical meaning.
- Service package and TransportMode remain distinct and traceable across request, Project, and shipment.
- Catalog identity and aliases never disclose across organizations.
- Active allocations cannot exceed item quantity under concurrency and corrections retain history.
- Customer search applies organization authorization before matching and passes negative leakage tests.
- Legacy adoption has zero guessed backfills and every manual mapping is auditable.
- Search relevance, latency, false-match, authorization-denial, and operational rollback evidence meet slice-specific accepted targets.

## 10. Open decisions

Open decisions are PDR-013-D02/D03 service relationships, D08/D09 allocation/delivery/correction, D10 customer search, and the customer/public portion of D11. ADR-023 and ADR-024 remain Proposed. Bounded catalog, alias, shipment snapshot, and internal visibility decisions are closed by PDR-013-D05/D06/D07/internal-D11 and ADR-022.

## 11. Risk analysis

Key risks are taxonomy drift, alias collisions, false catalog correlation, snapshot/catalog confusion, decimal precision error, over-allocation races, lifecycle inconsistency, tenant leakage, search inference, sensitive-field exposure, expensive trigram queries, incomplete legacy analytics, and governance documents being mistaken for implementation authority. Controls are explicit ownership, immutable codes/snapshots, database and transactional invariants, idempotency/versioning, tenant-first filters, allowlisted projections, bounded queries, audit, additive migration, fail-closed flags, and named human approvals.

## 12. Review outcome requested

Future slices must route their still-Proposed PDR/ADR records to named approvers. This RFC never authorizes schema or application work; bounded Release 1.6.0 authority is recorded separately.
