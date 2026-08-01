# PDR-013 — Cargo Data Foundation Product Decisions

- **Status:** Proposed
- **Date:** 2026-08-01
- **Target:** EPIC-002 — Cargo Data Foundation
- **Capabilities:** CAP-013 Master Data, CAP-002 Shipment Management, CAP-003 Execution Management, CAP-007 Customer Portal, CAP-009 Administration, CAP-010 Security & Identity
- **Decision authority:** None. Every decision below remains Proposed until its required approvers record acceptance.

## Evidence and protocol

Current evidence is the [Discovery and Domain Analysis Report](discovery-cargo-data-and-scroll-analysis-20260801.md), Platform Constitution v1, Architecture Baseline v1, Canonical Business Object Catalog, Platform Capability Map, Capability Registry, RFC-001, EPIC-001, ADR-001–020, and the current models/APIs. The discovery evidence is available; its recommendations remain non-authoritative and every Product decision below remains Proposed. Recommendations preserve Project, ShipmentRequest, OperationalShipment, ExecutionUnit, TransportMode, organization ownership, additive migration, and deny-by-default authorization.

## PDR-013-D01 — Master Data scope and ownership

- **Decision ID / Topic:** PDR-013-D01 / Master Data scope and ownership.
- **Current evidence:** CAP-013 owns governed reference semantics; existing rules prohibit guessed values and destructive compatibility changes. The governed Discovery and Domain Analysis Report is now available, but approval remains required.
- **Options:** A) explicit domain tables with shared governance conventions; B) generic entity/attribute/value storage; C) unmanaged free text owned independently by each feature.
- **Recommended option:** A. Use explicit tables for significant domains, including CargoType, ServiceType, and UnitOfMeasure, with shared reusable governance conventions and no generic EAV. Product and Data own meaning and stewardship; permission-controlled admin operations enforce immutable codes, activation/deactivation, audit, and deactivation rather than deletion after use.
- **Benefits / Risks:** Strong domain integrity, discoverability, and reusable administration / requires explicit schema evolution and named stewardship for each domain.
- **Operational / Security / Data impact:** Product and Data approve semantics; authorized administrators operate records; foreign keys preserve references; historical use prevents destructive deletion; tenant extensions cannot override canonical meaning.
- **Migration / UX / AI impact:** Additive nullable adoption with no guessed backfill; bilingual selectors retain inactive historical values; AI may propose evidence-backed mappings but cannot create or approve master data.
- **Required approvers / Blocking slice / Fail-safe:** Product, Data, Architecture, Operations / SLICE-B1 / keep structured master-data writes disabled and retain legacy descriptions.
- **Status:** Proposed

## PDR-013-D02 — ServiceType cardinality

- **Decision ID / Topic:** PDR-013-D02 / ServiceType cardinality.
- **Current evidence:** Canonical boundaries distinguish Project coordination, ShipmentRequest commercial intent, OperationalShipment execution, and TransportMode.
- **Options:** A) one service per Project; B) multiple services with one optional primary; C) collapse service and transport mode.
- **Recommended option:** B. A Project may contain multiple services and one may be primary; supporting services coexist. ShipmentRequest records requested services, Project records the accepted service package, and OperationalShipment links to services fulfilled. TransportMode remains separate.
- **Benefits / Risks:** Represents multimodal and supporting work accurately / package consistency rules require governance.
- **Operational / Security / Data impact:** Operations sees accepted scope without conflating road/rail/sea/air with customs, warehousing, loading, or packing; service visibility follows Project scope; explicit many-to-many relationships and primary constraint.
- **Migration / UX / AI impact:** Legacy method fields are not silently remapped; UI separates service package from mode; AI must reason over both axes and may not infer acceptance.
- **Required approvers / Blocking slice / Fail-safe:** Product, Architecture, Operations, Data / SLICE-B2 / expose legacy service text read-only and disable canonical package edits.
- **Status:** Proposed

## PDR-013-D03 — Service package ownership

- **Decision ID / Topic:** PDR-013-D03 / ownership of requested, accepted, and fulfilled service packages.
- **Current evidence:** ShipmentRequest, Project, and OperationalShipment own distinct commercial, coordination, and execution truth.
- **Options:** A) Project owns all service truth; B) each aggregate owns its phase-specific record with explicit lineage; C) derive everything from shipment mode.
- **Recommended option:** B. Requested services belong to ShipmentRequest, accepted package to Project, and fulfillment links to OperationalShipment; changes use audited correction/versioning.
- **Benefits / Risks:** Preserves intent-to-fulfillment lineage / reconciliation is more explicit.
- **Operational / Security / Data impact:** Scope changes become visible operational decisions; mutations require aggregate permission; relationships carry status, validity, source, actor, and timestamps.
- **Migration / UX / AI impact:** Additive links only; compare requested/accepted/fulfilled views; AI can identify gaps but cannot accept or rewrite packages.
- **Required approvers / Blocking slice / Fail-safe:** Product, Architecture, Operations, Security / SLICE-B2 / accepted package mutations disabled.
- **Status:** Proposed

## PDR-013-D04 — UnitOfMeasure policy

- **Decision ID / Topic:** PDR-013-D04 / structured units and conversion.
- **Current evidence:** Structured cargo quantities are absent; data governance requires explicit, quality-controlled reference identities.
- **Options:** A) free-text units; B) explicit UOM table with exact-UOM allocation first; C) immediate universal conversion engine.
- **Recommended option:** B. Immutable code, measurement dimension, bilingual name/symbol, no generic Other, and no structured numeric cargo fact without its required UOM. Governed dimensions include count, weight, volume, length, and other explicitly approved dimensions. First phase permits exact-UOM allocation only; conversion is deferred.
- **Benefits / Risks:** Deterministic validation / initially rejects legitimate cross-unit allocation.
- **Operational / Security / Data impact:** Data owns UOM activation; no special security beyond governed admin permission; quantities use appropriate precision and UOM FK.
- **Migration / UX / AI impact:** Do not infer units from numbers; dimension-filtered selection; AI cannot convert without an accepted conversion policy.
- **Required approvers / Blocking slice / Fail-safe:** Product, Data, Architecture, Operations / SLICE-B1 / reject new structured quantities lacking an active UOM.
- **Status:** Proposed

## PDR-013-D05 — Cargo catalog scope

- **Decision ID / Topic:** PDR-013-D05 / canonical versus organization-owned catalog.
- **Current evidence:** Platform security is tenant-first and CAP-013 supports canonical and governed reference concepts.
- **Options:** A) one shared global item catalog; B) organization-only catalogs; C) hybrid canonical definitions plus organization-owned items.
- **Recommended option:** C. Platform canonical definitions where appropriate, organization-owned items by default, immutable organization-local canonical code, and identical part numbers permitted in separate organizations.
- **Benefits / Risks:** Reuse without cross-customer disclosure / canonical linkage needs stewardship.
- **Operational / Security / Data impact:** Organization administrators own items; organization scope precedes lookup; catalog identity, ownership, lifecycle, provenance, aliases, and optional canonical link are explicit.
- **Migration / UX / AI impact:** Additive opt-in catalog links; organization-local search; AI context is permission-filtered and must not correlate tenants.
- **Required approvers / Blocking slice / Fail-safe:** Product, Data, Security, Architecture / SLICE-B3 / organization catalog and cross-project lookup remain disabled.
- **Status:** Proposed

## PDR-013-D06 — Customer-specific codes and aliases

- **Decision ID / Topic:** PDR-013-D06 / aliases and customer codes.
- **Current evidence:** Catalog governance requires canonical terminology while preserving qualified aliases.
- **Options:** A) overwrite canonical code; B) scoped aliases linked to immutable catalog identity; C) free-text notes.
- **Recommended option:** B. Customer-specific codes and aliases are organization-scoped, typed, validity-aware mappings; they never replace the immutable organization-local canonical code.
- **Benefits / Risks:** Integrations and customer terminology remain traceable / conflicting aliases need uniqueness policy.
- **Operational / Security / Data impact:** Audited alias stewardship; no alias is discoverable outside its organization; normalized value, type, source, validity, and conflict state are stored.
- **Migration / UX / AI impact:** Legacy codes map only with evidence; UI labels alias source; AI may suggest, never auto-approve, mappings.
- **Required approvers / Blocking slice / Fail-safe:** Product, Data, Security / SLICE-B3 / unresolved aliases are quarantined and excluded from matching.
- **Status:** Proposed

## PDR-013-D07 — ShipmentCargoItem required fields

- **Decision ID / Topic:** PDR-013-D07 / transactional cargo item meaning.
- **Current evidence:** OperationalShipment is the executable shipment aggregate; historical truth must not be rewritten by master-data edits.
- **Options:** A) catalog reference only; B) free-text row; C) transactional snapshot with optional catalog link.
- **Recommended option:** C. ShipmentCargoItem belongs to OperationalShipment; quantity, UOM, and display-name snapshot are required; catalog link is optional; part number, HS code, and CargoType snapshots are stored when supplied. Catalog edits never rewrite history.
- **Benefits / Risks:** Durable historical meaning / snapshot duplication requires explicit correction policy.
- **Operational / Security / Data impact:** Cargo declaration sits with shipment execution; field visibility is permission-controlled; immutable snapshot fields and auditable corrections.
- **Migration / UX / AI impact:** New transactions adopt structure; legacy descriptions remain readable; UI distinguishes linked catalog data from snapshot; AI cites snapshot and provenance.
- **Required approvers / Blocking slice / Fail-safe:** Product, Architecture, Operations, Data, Security / SLICE-B4 / no structured item creation until required fields validate.
- **Status:** Proposed

## PDR-013-D08 — Allocation quantity rules

- **Decision ID / Topic:** PDR-013-D08 / ExecutionUnitCargoAllocation invariants.
- **Current evidence:** ExecutionUnit is an independent execution concept under Project; ADR-010 governs locking/idempotency.
- **Options:** A) unconstrained allocation; B) exact-UOM bounded allocation; C) conversion plus split/merge in phase one.
- **Recommended option:** B. Positive quantity, exact UOM, active allocation sum no greater than shipment item quantity, derived unallocated quantity, same Project, same OperationalShipment by default, no inactive/cancelled unit, optimistic concurrency or locking, idempotency, and audited correction/reallocation. No split/merge or conversion initially.
- **Benefits / Risks:** Deterministic integrity / limits cross-shipment consolidation scenarios.
- **Operational / Security / Data impact:** Prevents over-allocation under concurrency; mutation permission and audit required; database constraints plus transaction-level invariant enforcement.
- **Migration / UX / AI impact:** No inferred allocations; UI shows allocated/unallocated exact units; AI may propose but not execute without action authority.
- **Required approvers / Blocking slice / Fail-safe:** Product, Architecture, Operations, Data, Security / SLICE-B5 / allocation writes disabled.
- **Status:** Proposed

## PDR-013-D09 — Delivery, cancellation, and correction rules

- **Decision ID / Topic:** PDR-013-D09 / allocation history across unit lifecycle.
- **Current evidence:** Platform law preserves operational truth and uses correction rather than destructive history edits.
- **Options:** A) delete allocations on change; B) version/correct and retain history; C) freeze forever after first allocation.
- **Recommended option:** B. Delivery freezes fulfilled allocation evidence; cancellation prevents new allocation and requires governed reallocation/correction of remaining quantity; corrections preserve superseded records, actor, reason, expected version, idempotency, and audit.
- **Benefits / Risks:** Traceable inventory meaning / correction workflows are operationally heavier.
- **Operational / Security / Data impact:** Explicit exception handling; elevated correction permissions; effective status and lineage retained.
- **Migration / UX / AI impact:** No destructive cleanup; UI exposes current state and history; AI cannot erase or silently rebalance history.
- **Required approvers / Blocking slice / Fail-safe:** Product, Operations, Architecture, Security, Data / SLICE-B5 / lifecycle-affected allocation mutation denied.
- **Status:** Proposed

## PDR-013-D10 — Customer search access

- **Decision ID / Topic:** PDR-013-D10 / cross-Project item search boundary.
- **Current evidence:** CAP-007 is operational; public tracking is scoped and identifiers are non-enumerable; authorization is backend-enforced.
- **Options:** A) anonymous global search; B) authenticated organization-scoped search; C) staff-only search.
- **Recommended option:** B. Authenticated customer portal only; organization scope is applied before text matching. Public tracking remains Project-scoped. No anonymous cross-Project search and no sequential internal IDs.
- **Benefits / Risks:** Customer traceability without global disclosure / inference and query-abuse risk.
- **Operational / Security / Data impact:** Supportable bounded search; tenant-first authorization, rate limits, audit, pagination; organization-scoped indexes and opaque public identities.
- **Migration / UX / AI impact:** No legacy public widening; authenticated result UX with safe empty states; AI search uses the same filtered endpoint.
- **Required approvers / Blocking slice / Fail-safe:** Product, Security, Architecture, Data / SLICE-B6 / endpoint and UI remain disabled.
- **Status:** Proposed

## PDR-013-D11 — Sensitive-field visibility

- **Decision ID / Topic:** PDR-013-D11 / customer-safe cargo result projection.
- **Current evidence:** Platform truth-separation and least-privilege laws prohibit internal data leakage.
- **Options:** A) return complete internal item/event records; B) allowlisted customer projection; C) hide all item details.
- **Recommended option:** B. Customer-visible events only; internal notes excluded; declared value, HS/sensitive codes, and other classified fields permission-controlled.
- **Benefits / Risks:** Useful traceability / misclassification could leak commercial or customs data.
- **Operational / Security / Data impact:** Previewable visibility policy; per-field backend authorization and negative tests; classification and visibility metadata required.
- **Migration / UX / AI impact:** Legacy fields default hidden; omitted fields are explained without confirming forbidden data; AI receives only the same allowlisted projection.
- **Required approvers / Blocking slice / Fail-safe:** Product, Security, Data, Operations / SLICE-B6 / deny and omit any field lacking an accepted visibility rule.
- **Status:** Proposed

## PDR-013-D12 — Legacy classification policy

- **Decision ID / Topic:** PDR-013-D12 / adoption of legacy cargo descriptions.
- **Current evidence:** ADR-006 and Constitution prohibit guessed backfill and require additive evolution.
- **Options:** A) automated guessed backfill; B) additive nullable adoption with audited manual mapping; C) mandatory full historical remediation.
- **Recommended option:** B. Preserve legacy description; require structure for new transactions; manually classify valuable open Projects; leave historical closed Projects `UNCLASSIFIED` by default; audit all manual mapping.
- **Benefits / Risks:** Safe adoption and readable history / incomplete historical analytics.
- **Operational / Security / Data impact:** Prioritized review queue; mapping permissions and audit; nullable links, provenance, confidence/source, and reconciliation status.
- **Migration / UX / AI impact:** Expand-migrate-verify without destructive rewrite; clearly label unclassified history; AI may recommend evidence-backed mappings but cannot write them automatically.
- **Required approvers / Blocking slice / Fail-safe:** Product, Data, Operations, Architecture / SLICE-B1 / retain legacy read path and do not classify.
- **Status:** Proposed

## Register consequence

No decision in this register authorizes implementation. SLICE-B1 is blocked on D01, D04, and D12 plus ADR-021 acceptance; later slices remain blocked as identified above.
