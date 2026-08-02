# PDR-013 — Cargo Data Foundation Product Decisions

- **Status:** Partially Accepted (D01, D04, D05, D06, D07, internal-only D11, and D12)
- **Date:** 2026-08-01
- **Target:** EPIC-002 — Cargo Data Foundation
- **Capabilities:** CAP-013 Master Data, CAP-002 Shipment Management, CAP-003 Execution Management, CAP-007 Customer Portal, CAP-009 Administration, CAP-010 Security & Identity
- **Decision authority:** The SLICE-B1 final review contract accepts D01, D04, and D12. The [Release 1.6.0 Cargo Governance Closure](release-1.6.0-cargo-governance-closure.md) accepts D05, D06, D07, and only the internal visibility boundary of D11 for bounded SLICE-B3/B4. D02, D03, D08-D10, and the customer/public portion of D11 remain Proposed.

## Evidence and protocol

Current evidence is the [Discovery and Domain Analysis Report](discovery-cargo-data-and-scroll-analysis-20260801.md), Platform Constitution v1, Architecture Baseline v1, Canonical Business Object Catalog, Platform Capability Map, Capability Registry, RFC-001, EPIC-001, accepted ADRs, and the current models/APIs. Discovery recommendations remain non-authoritative. Decision status is recorded individually below and in the applicable acceptance record. Project, ShipmentRequest, OperationalShipment, ExecutionUnit, TransportMode, organization ownership, additive migration, and deny-by-default authorization remain distinct.

## PDR-013-D01 — Master Data scope and ownership

- **Decision ID / Topic:** PDR-013-D01 / Master Data scope and ownership.
- **Current evidence:** CAP-013 owns governed reference semantics; existing rules prohibit guessed values and destructive compatibility changes. The governed Discovery and Domain Analysis Report is now available, but approval remains required.
- **Options:** A) explicit domain tables with shared governance conventions; B) generic entity/attribute/value storage; C) unmanaged free text owned independently by each feature.
- **Recommended option:** A. Use explicit tables for significant domains, including CargoType, ServiceType, and UnitOfMeasure, with shared reusable governance conventions and no generic EAV. Product and Data own meaning and stewardship; permission-controlled admin operations enforce immutable codes, activation/deactivation, audit, and deactivation rather than deletion after use.
- **Benefits / Risks:** Strong domain integrity, discoverability, and reusable administration / requires explicit schema evolution and named stewardship for each domain.
- **Operational / Security / Data impact:** Product and Data approve semantics; authorized administrators operate records; foreign keys preserve references; historical use prevents destructive deletion; tenant extensions cannot override canonical meaning.
- **Migration / UX / AI impact:** Additive nullable adoption with no guessed backfill; bilingual selectors retain inactive historical values; AI may propose evidence-backed mappings but cannot create or approve master data.
- **Required approvers / Blocking slice / Fail-safe:** Product, Data, Architecture, Operations / SLICE-B1 / keep structured master-data writes disabled and retain legacy descriptions.
- **Status:** Accepted
- **Accepted:** 2026-08-01, for SLICE-B1 canonical Master Data Governance Foundation only.

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
- **Status:** Accepted
- **Accepted:** 2026-08-01, for SLICE-B1 UnitOfMeasure governance; allocation and conversion behavior remain deferred to their governed slices.

## PDR-013-D05 — Cargo catalog scope

- **Decision ID / Topic:** PDR-013-D05 / canonical versus organization-owned catalog.
- **Current evidence:** Platform security is tenant-first and CAP-013 supports canonical and governed reference concepts.
- **Options:** A) one shared global item catalog; B) organization-only catalogs; C) hybrid canonical definitions plus organization-owned items.
- **Accepted option:** B for Release 1.6.0. CargoCatalogItem is organization-scoped; platform-global, customer-global/shared, and canonical/global definition linkage are deferred. Its opaque public ID is external identity. Its immutable code is unique by `(organization_id, immutable_code)` and cannot change after creation. Same Part Number may exist in different organizations.
- **Required fields:** CargoType. Default UnitOfMeasure, Part Number, customer item code, HS Code, brand, model, and description are optional.
- **Operational / Security / Data impact:** Items support activation/deactivation; used items cannot be hard-deleted. Organization scope precedes lookup and cross-organization visibility is prohibited.
- **Migration / UX / AI impact:** Additive organization-owned records only; no global definition link or cross-organization correlation.
- **Required approvers / Blocking slice / Fail-safe:** Product, Data, Architecture, Security; Operations consulted / SLICE-B3 / deny access when organization ownership cannot be proven.
- **Status:** Accepted for Release 1.6.0 bounded SLICE-B3
- **Accepted:** 2026-08-02 under the [Release 1.6.0 Cargo Governance Closure](release-1.6.0-cargo-governance-closure.md).

## PDR-013-D06 — Customer-specific codes and aliases

- **Decision ID / Topic:** PDR-013-D06 / aliases and customer codes.
- **Current evidence:** Catalog governance requires canonical terminology while preserving qualified aliases.
- **Options:** A) overwrite canonical code; B) scoped aliases linked to immutable catalog identity; C) free-text notes.
- **Accepted option:** B. An alias belongs to exactly one CargoCatalogItem, inherits organization scope, and stores alias text, deterministic normalized alias, language, alias type, active state, and audit metadata. Normalized alias is unique within its parent item. Part Number and customer item code remain explicit item fields.
- **Accepted values:** Alias types `COMMON_NAME`, `CUSTOMER_TERM`, `ABBREVIATION`, `LEGACY_TERM`, `OTHER_GOVERNED`; languages `fa`, `en`, `und`.
- **Operational / Security / Data impact:** Cross-organization alias access is prohibited. Inactive aliases remain readable but are excluded from new matching. Aliases authorize internal search preparation only, not public/customer search.
- **Migration / UX / AI impact:** Normalization follows [Cargo alias normalization v1](cargo-alias-normalization-v1.md); ambiguous collisions are rejected rather than merged.
- **Required approvers / Blocking slice / Fail-safe:** Product, Data, Security; Architecture consulted / SLICE-B3 / reject ambiguous normalization collisions.
- **Status:** Accepted for Release 1.6.0 bounded SLICE-B3
- **Accepted:** 2026-08-02 under the [Release 1.6.0 Cargo Governance Closure](release-1.6.0-cargo-governance-closure.md).

## PDR-013-D07 — ShipmentCargoItem required fields

- **Decision ID / Topic:** PDR-013-D07 / transactional cargo item meaning.
- **Current evidence:** OperationalShipment is the executable shipment aggregate; historical truth must not be rewritten by master-data edits.
- **Options:** A) catalog reference only; B) free-text row; C) transactional snapshot with optional catalog link.
- **Accepted option:** C. ShipmentCargoItem is a transactional child of OperationalShipment. Catalog linkage is optional and manual creation is permitted.
- **Required fields:** Parent OperationalShipment, shipment-unique line number, CargoType, positive quantity, UnitOfMeasure, and display-name snapshot.
- **Snapshot policy:** At creation, snapshot display name, CargoType code/titles, UOM code/symbol, and supplied Part Number, customer item code, HS Code, brand, model, and description. Later catalog/CargoType/UOM edits and ordinary line updates never silently regenerate snapshots. Destructive historical rewriting is prohibited; correction/revision/supersession implementation is deferred.
- **Operational / Security / Data impact:** Linked catalog items must be active and belong to the authorized organization when selected. Historical links remain readable after deactivation. Allocation, delivered quantity, and UOM conversion are excluded.
- **Migration / UX / AI impact:** Existing ShipmentRequest cargo fields remain readable and unchanged; no automatic conversion, mapping, or backfill.
- **Required approvers / Blocking slice / Fail-safe:** Product, Architecture, Operations, Data, Security / SLICE-B4 / reject creation or update when ownership or snapshot evidence is inconsistent.
- **Status:** Accepted for Release 1.6.0 bounded SLICE-B4
- **Accepted:** 2026-08-02 under the [Release 1.6.0 Cargo Governance Closure](release-1.6.0-cargo-governance-closure.md).

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
- **Accepted internal boundary:** Explicitly permitted internal administrators may administer catalog items; permitted operational users may read/select them where needed. ShipmentCargoItem visibility derives from authorization to its parent OperationalShipment. Responses use the field allowlists in the [Release 1.6.0 Cargo Governance Closure](release-1.6.0-cargo-governance-closure.md).
- **Not accepted:** Public APIs, customer cargo projection, customer cross-Project search, public sensitive-field exposure, and customer dashboards/reports.
- **Operational / Security / Data impact:** Never expose numeric database IDs, cross-tenant identifiers, unrestricted actor internals, or fields unauthorized for the role.
- **Migration / UX / AI impact:** Unauthorized and cross-organization access is non-disclosing, normally `404` where consistent with existing security architecture.
- **Required approvers / Blocking slice / Fail-safe:** Product, Security, Data, Operations; Architecture consulted / bounded internal B3/B4 only / deny or omit when authorization is not proven.
- **Status:** Partially Accepted — internal Release 1.6.0 boundary only; customer/public projection remains Proposed
- **Accepted:** 2026-08-02 under the [Release 1.6.0 Cargo Governance Closure](release-1.6.0-cargo-governance-closure.md).

## PDR-013-D12 — Legacy classification policy

- **Decision ID / Topic:** PDR-013-D12 / adoption of legacy cargo descriptions.
- **Current evidence:** ADR-006 and Constitution prohibit guessed backfill and require additive evolution.
- **Options:** A) automated guessed backfill; B) additive nullable adoption with audited manual mapping; C) mandatory full historical remediation.
- **Recommended option:** B. Preserve legacy description; require structure for new transactions; manually classify valuable open Projects; leave historical closed Projects `UNCLASSIFIED` by default; audit all manual mapping.
- **Benefits / Risks:** Safe adoption and readable history / incomplete historical analytics.
- **Operational / Security / Data impact:** Prioritized review queue; mapping permissions and audit; nullable links, provenance, confidence/source, and reconciliation status.
- **Migration / UX / AI impact:** Expand-migrate-verify without destructive rewrite; clearly label unclassified history; AI may recommend evidence-backed mappings but cannot write them automatically.
- **Required approvers / Blocking slice / Fail-safe:** Product, Data, Operations, Architecture / SLICE-B1 / retain legacy read path and do not classify.
- **Status:** Accepted
- **Accepted:** 2026-08-01, for additive/no-backfill adoption in SLICE-B1 and later governed adoption unless superseded.

## Register consequence

### Release 1.6.0 bounded decision closure (2026-08-02)

The authoritative [Release 1.6.0 Cargo Governance Closure](release-1.6.0-cargo-governance-closure.md) accepts D05, D06, D07, and the internal-only portion of D11 for bounded SLICE-B3/B4. Customer/public projection, allocation, delivery, cancellation/correction implementation, cross-Project search, dashboards, reports, and seed changes remain deferred.

D01, D04, and D12 remain accepted for SLICE-B1 together with ADR-021. D05, D06, D07, and internal-only D11 authorize only the bounded Release 1.6.0 B3/B4 foundation together with ADR-022. D02, D03, D08-D10, and customer/public D11 remain Proposed with their fail-safe behavior.
