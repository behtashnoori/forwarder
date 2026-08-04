# PDR-014 — Initial Reference Data Catalog

> **Current policy (ADR-028):** This historical catalog/tooling decision does not make population installation or deployment work. Reference Data is created through Admin UI; Seed/apply remains optional migration tooling and no release depends on it.

- **Status:** Accepted for Release 1.5.0
- **Date:** 2026-08-01
- **Accepted:** 2026-08-01 by Product, Data, Architecture, Operations, and Security
- **Target:** Forwarder 1.5.0 — Reference Data Initial Catalog
- **Capabilities:** CAP-013 Master Data; CAP-009 Administration; supporting CAP-002 Shipment Management and CAP-003 Execution Management
- **Decision owners:** Product and Data
- **Required reviewers:** Architecture and Operations; Security consulted for administration and execution controls
- **Evidence:** Platform Constitution, Architecture Baseline, Canonical Business Object Catalog, Capability Map and Registry, Discovery Cargo Data Report, PDR-013, RFC-002, ADR-021 through ADR-024, EPIC-002, Cargo approval matrix, SLICE-B1 final review, current B1 implementation, current request/admin UI, migrations, tests, reports, translations, and seed mechanisms.
- **Authority:** The named cross-functional decision accepts D01-D10 and the reviewed row decisions for the bounded Release 1.5.0 implementation. Authorization is limited to `ReferenceDataSeedRun`, the approved initial catalog, explicit plan/apply CLI, verification, and tests. Production execution and later cargo capabilities remain unauthorized.

## Acceptance reconciliation

- `CARGO_GENERAL_GOODS` remains Deferred. The other thirteen ordinary CargoTypes are Accepted as proposed; `CARGO_OTHER` and `CARGO_UNCLASSIFIED` are Accepted with their governed selection policies.
- Dangerous, perishable, and temperature-controlled properties remain deferred cross-cutting attributes.
- `SERVICE_PROJECT_LOGISTICS` remains Deferred. Loading, Unloading, and Packing/Repacking are ServiceTypes only when explicitly sold or coordinated. Road, rail, sea, and air remain TransportMode concepts.
- The nine UOMs and exact symbols recorded in D04 are Accepted; packaging, handling-unit, and container concepts remain excluded.
- ADR-021 remains Accepted and is clarified to include a dedicated `ReferenceDataSeedRun` table as bounded master-data governance infrastructure.
- No authorization is granted for CargoCatalogItem, ShipmentCargoItem, PackagingType, cargo attributes, allocations, customer search, reporting, dashboards, ProjectService relationships, or Production execution.

## Boundary and confirmed decision status

At this Release 1.5.0 decision's acceptance, PDR-013-D01, D04, and D12 and ADR-021 were Accepted only for bounded B1; all later cargo decisions were then Proposed. The later [Release 1.6.0 Cargo Governance Closure](release-1.6.0-cargo-governance-closure.md) independently accepts bounded D05/D06/D07, internal-only D11, and ADR-022 without expanding this PDR's seed authority. This PDR still does not authorize ExecutionUnitCargoAllocation, service relationships, customer search, reporting, dashboards, or any new seed values.

## D01 — Code convention

- **Options:** A) domain-prefixed uppercase ASCII snake case (`CARGO_*`, `SERVICE_*`, `UOM_*`); B) unprefixed uppercase snake case; C) preserve display-derived or database-generated identifiers.
- **Recommendation:** A. Codes are immutable, semantic, underscore-separated ASCII and independent of labels. Maximum length remains the implemented 64 characters.
- **Evidence:** The B1 service uppercases codes and makes them immutable but does not enforce ASCII/snake case; existing TransportMethod has no code. The implementation contract requires uppercase ASCII with underscores.
- **Benefits:** Collision resistance across exports/logs, readable authority, stable integrations.
- **Risks:** Longer codes and a validation tightening compared with B1's current acceptance of arbitrary uppercase text.
- **Migration impact:** No existing B1 values are known from repository seed/migrations; manually created environment values must be inventoried before validation is tightened.
- **UX/reporting impact:** Admin form should explain the format; reports and references use code, never labels.
- **Required approvers:** Product, Data, Architecture.
- **Fail-safe:** Do not create executable catalog files or strengthen runtime validation.
- **Status:** Accepted.

## D02 — CargoType depth and initial values

- **Options:** A) one broad, flat cross-industry level; B) broad parents plus children; C) deep industry taxonomy.
- **Recommendation:** A for 1.5.0. Candidate values are documented in `reference-data-initial-catalog-review-20260801.md`. Dangerous and temperature-control are excluded from CargoType; ambiguous candidates remain unseeded.
- **Evidence:** The repository has only free-text cargo description plus unitless weight/volume and no recurring product vocabulary. PDR-013 does not approve a taxonomy.
- **Benefits:** Low overlap, cross-industry usability, and an upgrade path through the existing hierarchy.
- **Risks:** Limited analytical detail and continuing manual classification.
- **Migration impact:** Additive seed only after approval; no legacy mapping or backfill.
- **UX/reporting impact:** One flat selector; inactive historical values remain readable; analytics must label coverage and unclassified data.
- **Required approvers:** Product, Data, Architecture, Operations.
- **Fail-safe:** Keep tables empty/manual and legacy description readable.
- **Status:** Accepted with reviewed row decisions.

## D03 — ServiceType initial values

- **Options:** A) mode-neutral sold/coordinated services; B) duplicate road/rail/sea/air as ServiceTypes; C) composite domestic/international/mode packages.
- **Recommendation:** A. TransportMode stays separate. Domestic/international is shipment/project scope. Candidate service values and exclusions are in the review artifact. This decision does not accept service cardinality or relationships from PDR-013-D02/D03.
- **Evidence:** Current TransportMethod values and UI fallbacks are transport modes with naming duplicates; there is no current ServiceType or service-package evidence.
- **Benefits:** Avoids redundant axes and keeps commercial service vocabulary stable.
- **Risks:** Some marketed packages need later decomposition and relationship policy.
- **Migration impact:** No automatic conversion of TransportMethod strings.
- **UX/reporting impact:** Future service selectors must be visually distinct from mode; no service reporting until relationships are approved.
- **Required approvers:** Product, Data, Architecture, Operations.
- **Fail-safe:** Seed no ServiceType values.
- **Status:** Accepted with reviewed row decisions.

## D04 — UOM initial values and symbols

- **Options:** A) minimal SI/logistics units; B) include packaging/handling units; C) add conversion factors now.
- **Recommendation:** A, without conversion. Candidate values are piece (`pcs`), gram (`g`), kilogram (`kg`), metric ton (`t`), cubic meter (`m³`), liter (`L`), centimeter (`cm`), meter (`m`), and kilometer (`km`). Packaging and handling concepts are deferred.
- **Evidence:** PDR-013-D04 accepts explicit dimensions and exact-UOM behavior, but not a concrete list. Current UI/report labels implicitly assume kg and m³ while persistence stores no UOM.
- **Benefits:** Deterministic symbols and clear dimensions.
- **Risks:** Piece/item semantics and precision require explicit review; no cross-unit calculation is available.
- **Migration impact:** No inference for legacy weight/volume and no conversion records.
- **UX/reporting impact:** Dimension-filtered selection; symbols are Unicode-safe; existing implicit labels remain legacy-only.
- **Required approvers:** Product, Data, Architecture, Operations.
- **Fail-safe:** Seed no UOM values and reject any new structured quantity lacking an approved active UOM.
- **Status:** Accepted.

## D05 — Other and Unclassified policy

- **Options:** A) separate governed values; B) one combined catch-all; C) neither.
- **Recommendation:** Separate them. `CARGO_OTHER` is user-selectable only when a later transactional form requires an explanation. `CARGO_UNCLASSIFIED` is system-owned, non-user-selectable, and used only under the accepted no-guessed-backfill policy. No generic UOM Other is allowed. A ServiceType Other remains a proposed controlled fallback and must require explanation when transactional behavior is approved.
- **Evidence:** PDR-013-D12 accepts no guessed classification and ADR-021 names reserved system records; SLICE-B1 explicitly left reserved values undecided for seed.
- **Benefits:** Distinguishes known exception from unknown legacy state.
- **Risks:** B1 schema has no `system_owned` or `user_selectable` field, so mandatory enforcement cannot be represented today.
- **Migration impact:** A schema/policy gap must be separately approved before these values become executable.
- **UX/reporting impact:** Other explanation and Unclassified suppression require future form/projection work, not this release.
- **Required approvers:** Product, Data, Architecture, Operations.
- **Fail-safe:** Do not seed either value.
- **Status:** Accepted.

## D06 — Dangerous/perishable treatment

- **Options:** A) exclusive CargoTypes; B) cross-cutting cargo attributes; C) duplicate both.
- **Recommendation:** B in a later governed slice. Dangerous-goods status and temperature control can coexist with any commodity category and therefore are not initial CargoTypes.
- **Evidence:** Discovery describes hazard/perishable indicators as optional item attributes; no current structured field or accepted item model exists.
- **Benefits:** Avoids mutually exclusive classification errors and duplicate semantics.
- **Risks:** These characteristics remain free text/unstructured until their future model is accepted.
- **Migration impact:** None in 1.5.0.
- **UX/reporting impact:** No new selector/report; future regulated fields require security/compliance review.
- **Required approvers:** Product, Data, Architecture, Operations; Security/Compliance for future fields.
- **Fail-safe:** Exclude both from executable CargoType data.
- **Status:** Accepted.

## D07 — Seed ownership

- **Options:** A) Product/Data-owned canonical catalog applied by Operations; B) Engineering-owned defaults; C) environment-local administrator values only.
- **Recommendation:** A. Product approves meaning, Data owns quality/source/checksum, Architecture approves execution contract, Operations executes approved plan/apply, and Security reviews environment/permission controls.
- **Evidence:** PDR-013-D01 assigns meaning/stewardship to Product/Data; SLICE-B1 final review explicitly leaves seed ownership undecided.
- **Benefits:** Clear accountability and reproducibility.
- **Risks:** Requires an approval ledger and operational handoff not currently modeled.
- **Migration impact:** None until approved.
- **UX/reporting impact:** Admin should not imply that manual values are canonical seed values.
- **Required approvers:** Product, Data, Architecture, Operations.
- **Fail-safe:** No executable catalog.
- **Status:** Accepted.

## D08 — Translation ownership

- **Options:** A) Product authors/Data validates; B) developer translation; C) administrator-local translation.
- **Recommendation:** Product owns business wording; Data validates terminology, normalization, and uniqueness; a named Persian/English domain reviewer signs off before checksum publication.
- **Evidence:** B1 requires both labels but stores no translation authority; current repository output also exposes evidence of historical encoding corruption in some files.
- **Benefits:** Stable bilingual meaning and fewer display-derived conflicts.
- **Risks:** Review availability and corrections require a governed update process.
- **Migration impact:** Label corrections must use an approved update mode; normal seed apply fails closed on drift.
- **UX/reporting impact:** Both labels remain required and reports select labels by locale without changing code.
- **Required approvers:** Product and Data; Operations consulted.
- **Fail-safe:** Do not publish executable bilingual catalog.
- **Status:** Accepted.

## D09 — Approval and change workflow

- **Options:** A) versioned PDR/catalog review plus explicit conflict-resolving update mode; B) silent upsert; C) manual database edits.
- **Recommendation:** A. New catalog versions require evidence, diff, named approvals, checksum, release note, plan, and explicit apply. Normal apply creates missing codes and no-ops exact matches; any governed-field drift, inactive code, duplicate title, or missing parent stops the transaction. Updates require a separately approved mode and change record.
- **Evidence:** Constitution requires human approval, audit, and fail-safe behavior; B1 uses immutable codes/versioning but has no seed change workflow.
- **Benefits:** Traceable, deterministic change control.
- **Risks:** Operational overhead and no automatic repair.
- **Migration impact:** None unless execution metadata/provenance is approved as schema.
- **UX/reporting impact:** Admin manual edits may intentionally cause a seed conflict and require reconciliation.
- **Required approvers:** Product, Data, Architecture, Operations; Security consulted.
- **Fail-safe:** Plan-only documentation; no apply command.
- **Status:** Accepted.

## D10 — Environment execution policy

- **Options:** A) explicit plan/apply with production confirmation and approval evidence; B) migration/startup seed; C) unrestricted script.
- **Recommendation:** A. `python -m backend.reference_data_cli plan` is read-only. `apply --confirm --operator <name> --approval-reference <reference> --expected-checksum <checksum>` is transactional and forbidden by default in Production; Production additionally requires `--confirm-production`. No startup or migration execution. Output includes environment, catalog/source version, checksum, created/unchanged/conflict counts, and a secret-safe execution identifier. Apply evidence persistently records the bounded approval reference.
- **Evidence:** ADR-011/Constitution require explicit execution; repository operational CLI has environment guards; the legacy TransportMethod seed destructively deletes rows and is not a suitable precedent.
- **Benefits:** Safe reruns and controlled operations.
- **Risks:** Current B1 schema has no seed provenance or execution record. Existing OperationalAudit requires organization/actor context and is not a valid generic master-data seed ledger.
- **Migration impact:** A mandatory audit/provenance schema decision is required before compliant apply implementation.
- **UX/reporting impact:** No Seed button or bulk import in Admin UI.
- **Required approvers:** Product, Data, Architecture, Operations, Security.
- **Fail-safe before acceptance:** Do not implement an apply-capable CLI. This gate was resolved by the accepted bounded `ReferenceDataSeedRun`; Production execution remains separately unauthorized.
- **Status:** Accepted.

## Decision summary

| Decision | Status | Executable now |
| --- | --- | --- |
| D01 Code convention | Accepted | Yes, within bounded authorization |
| D02 CargoType catalog | Accepted with reviewed rows | Yes, Accepted rows only |
| D03 ServiceType catalog | Accepted with reviewed rows | Yes, Accepted rows only |
| D04 UOM catalog | Accepted | Yes |
| D05 Other/Unclassified | Accepted | Yes, with policy enforcement |
| D06 Dangerous/perishable | Accepted | No values; attributes deferred |
| D07 Seed ownership | Accepted | Yes |
| D08 Translation ownership | Accepted | Yes |
| D09 Change workflow | Accepted | Yes |
| D10 Environment execution | Accepted | Yes, excluding Production execution |

## Approval action requested

Engineering may implement only the bounded accepted scope and required verification. Production execution remains a separate explicit authorization gate.
