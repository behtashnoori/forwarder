# External Operational Reference Domain Map

- Status: Architecture evidence supporting ADR-039
- Date: 2026-08-20
- Repository baseline: `a8ddf6b5011cc03b6fdd8cafec7501564ade95ce`
- Scope: discovery and architecture only; no runtime, migration, catalog population, or production authority

## 1. Boundary and evidence method

An external operational reference is a value assigned by a party or system outside Forwarder's canonical identity scheme and used to correlate a shipment or execution unit with a transport, customs, warehouse, or trade process. It is not a `DocumentDefinition`, uploaded file, requirement, tracking code, opaque `public_id`, or numeric database key.

Evidence labels are `VERIFIED_FROM_REPO`, `VERIFIED_FROM_OFFICIAL_DOMAIN_SOURCE`, `STRONG_DOMAIN_INFERENCE`, and `DOMAIN_CONFIRMATION_REQUIRED`. Inference is not promoted to fact. The primary international sources used were the [UN/CEFACT reference qualifier list](https://unece.org/fileadmin/DAM/trade/edifact/code/1153cl.htm), which distinguishes AWB, bill-of-lading, booking, and CMR reference numbers; the [CMR Convention](https://unece.org/fileadmin/DAM/trans/conventn/cmr_e.pdf); the [UNECE e-CMR guide](https://unece.org/trade/documents/2023/10/executive-guide-e-cmr); and the [e-CMR protocol](https://unece.org/DAM/trans/conventn/e-CMRe.pdf). No authoritative specification was found for Barfarabaran ownership/cardinality/lifecycle.

## 2. Repository census

| Concept | Current field/model | Owner/type | Required/unique/search | Exposure/tenant/document | State and usage |
| --- | --- | --- | --- | --- | --- |
| Authenticated request identity | `ShipmentRequest.public_id` | Forwarder opaque UUID identity | rollout nullable; globally unique; lookup index | authenticated; tenant-fenced; not document-linked | IMPLEMENTED (expand phase); API adoption bounded by ADR-038; not an external reference |
| Public request tracking | `ShipmentRequest.tracking_code` | public tracking capability/identity | nullable; globally unique; indexed | deliberately customer-facing; tenant authority still required for private data | IMPLEMENTED/LEGACY public API and UI; not an external reference |
| Project identity/code | `Project.public_id`, `project_code`, `tracking_code` | internal opaque/project-local/public identities | constrained per their ADRs | organization-owned | IMPLEMENTED; not external references |
| Shipment identity | `OperationalShipment.public_id` | internal opaque identity | required and globally unique | tenant-scoped API identity | IMPLEMENTED; not an external reference |
| Execution-unit identity/code | `ExecutionUnit.public_id`, `unit_code` | internal opaque and project-local identity | required; project-local code constraint | inherited tenant | IMPLEMENTED; not an external reference |
| Legacy unit reference | `ShipmentTransportUnit.unit_code`, `vehicle_reference` | request tracking unit, free text | unit code required per tracking aggregate | legacy tenant envelope; customer tracking UI/API | LEGACY/FREE_TEXT; not a governed external-reference model |
| Document number label | `DocumentDefinition.reference_number_label_fa/en` | platform document-type display metadata | optional; not a value; not searchable as operational data | tenant-neutral catalog metadata | PARTIAL metadata; admin UI/API; no reference values |
| Document artifact identity | `CaseDocumentFile.public_id` | immutable uploaded-file version metadata | unique opaque identity | request-owned and private | IMPLEMENTED; not an external reference |
| Operational document use | `OperationalDocumentRequirement`, `ArtifactAssociation` | shipment readiness/use of exact file version | governed by MDPM | tenant-scoped; document-linked | IMPLEMENTED; no external-number field |
| Cotage, B/L, AWB, CMR, warehouse receipt, registration order, Barfarabaran values | none | none | none | none | NOT_IMPLEMENTED; document definitions/candidates are not values |

Repository searches also found document catalog definitions/candidates for `BILL_OF_LADING`, `AIR_WAYBILL`, `CMR_CONSIGNMENT_NOTE`, `WAREHOUSE_RECEIPT`, `CUSTOMS_DECLARATION`, and `REGISTRATION_ORDER`. ADR-036 explicitly keeps their numbers outside `DocumentDefinition`. No canonical source field named `cotage`, `bl_number`, `awb`, `cmr`, `warehouse_receipt`, `registration_order`, `barfarabaran`, `external_reference`, `manifest_number`, `container_number`, `booking_number`, `seal_number`, or `invoice_number` stores an operational value.

## 3. Candidate classification, ownership, and lifecycle

| Type | Meaning and source/issuer | Natural owner and cardinality | Lifecycle/history | Search/index | Evidence | V1 decision |
| --- | --- | --- | --- | --- | --- | --- |
| `COTAGE_NUMBER` | Identifier associated with an Iranian customs declaration/registration context; exact issuing workflow and formal uniqueness were not established | Customs context is absent as an aggregate. OperationalShipment is the only bounded operational projection candidate; multiple must be allowed | correction/reissue and supersession must be retained; issuer/source metadata required | exact; normalized index | repository proves document boundary; meaning/issuer details `DOMAIN_CONFIRMATION_REQUIRED` | type may exist inactive; no value writes until Iranian customs owner confirms scope and format |
| `BILL_OF_LADING_NUMBER` | Reference number assigned to a bill of lading; UN/CEFACT qualifier `BM` | OperationalShipment; multiple allowed (master/house, split/reissue); optional exact file bridge | append new/supersede old; never overwrite; issued and effective metadata optional | exact and prefix; tenant/type/normalized-value index | `VERIFIED_FROM_OFFICIAL_DOMAIN_SOURCE`; ownership is `STRONG_DOMAIN_INFERENCE` | V1 active candidate after catalog provenance review |
| `AIR_WAYBILL_NUMBER` | Air waybill number; UN/CEFACT qualifier `AWB` | OperationalShipment; multiple allowed (master/house or reissue); optional file bridge | append/supersede; issuer/carrier/source metadata | exact and prefix | `VERIFIED_FROM_OFFICIAL_DOMAIN_SOURCE`; ownership is `STRONG_DOMAIN_INFERENCE` | V1 active candidate after catalog provenance review |
| `CMR_NUMBER` | Reference number assigned to a road consignment note; UN/CEFACT qualifier `CMR` | OperationalShipment by default; ExecutionUnit only when a separately evidenced note covers one independently managed road unit; multiple allowed | convention permits separate notes for vehicles/kinds/lots; amendments/replacements require history | exact and prefix | `VERIFIED_FROM_OFFICIAL_DOMAIN_SOURCE` | V1 active candidate, with owner applicability constrained in type metadata |
| `WAREHOUSE_RECEIPT_ID` | Identifier of a warehouse receipt, not the receipt definition/file | Shipment or warehouse-lot ExecutionUnit is plausible; repository provides no custody/warehouse aggregate proof | multiple, replacement and supersession allowed; issuer/warehouse metadata required | exact; prefix only if proven safe/useful | `DOMAIN_CONFIRMATION_REQUIRED` for owner/cardinality | inactive/deferred in V1 until warehouse-domain confirmation |
| `REGISTRATION_ORDER_NUMBER` | Structured identifier in the Iranian trade-registration/authorization domain, distinct from evidence artifact | Most plausibly commercial request or a future trade-authorization aggregate; neither is authorized as a V1 owner | amendments, validity/status and commodity coverage show key/value may be insufficient | exact when future domain is approved | ADR-036 boundary `VERIFIED_FROM_REPO`; semantics `DOMAIN_CONFIRMATION_REQUIRED` | excluded from V1; requires separate structured-domain decision |
| `BARFARABARAN_REFERENCE` | Unproven code/reference associated with the Barfarabaran system; non-authoritative public pages mention bill-of-lading registration and a transport tracking code | unknown: shipment, bill of lading, trip, or execution unit cannot be selected safely | generation, correction, replacement, and uniqueness unknown | unknown | `DOMAIN_CONFIRMATION_REQUIRED` | excluded from V1 and no catalog activation or implementation |

No candidate is assumed globally unique. V1 treats uniqueness as an explicit type policy selected from `NONE`, `OWNER`, `TENANT`, or `ISSUER`; a global rule requires authoritative proof. Normalized equality is for lookup/constraints while the original display value is retained.

## 4. Ownership matrix

| Candidate | Request | Shipment | Cargo item | Execution unit | Document file | Project | Decision |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Cotage | weak | plausible projection | no proof | plausible customs lot, unproven | optional evidence only | no | deferred type activation; shipment only if confirmed |
| B/L | commercial lineage only | primary V1 owner | no | no default | optional exact bridge | derived navigation | shipment |
| AWB | commercial lineage only | primary V1 owner | no | no default | optional exact bridge | derived navigation | shipment |
| CMR | no | primary owner | no | permitted only by type applicability/evidence | optional exact bridge | derived navigation | shipment or unit |
| Warehouse receipt | no | plausible | no | plausible warehouse lot | optional exact bridge | no | deferred |
| Registration order | plausible but structured | not primary | future commodity linkage | no | evidence only | no | outside V1 |
| Barfarabaran | unknown | unknown | no evidence | unknown | relationship unknown | no evidence | excluded |

Project and cargo are not V1 reference owners. Project results are reached through shipment lineage; cargo relationships require a later allocation/coverage model. `CaseDocumentFile` is a bridge/evidence association, not the owner of operational truth.

## 5. Product queries and exposure

V1 supports tenant-fenced exact lookup and an explicitly enabled prefix lookup over a normalized value. Results return reference type/label, original display value, lifecycle state, owning shipment or unit opaque identity, and project navigation derived from the owner. They may answer “which shipment uses this B/L?” and “does this tenant use this reference more than once?” without granting access from the value itself.

There is no global/public resolver. Customer/public tracking exposure defaults to none and requires a later allowlisted projection per type and use case. Logs omit raw values; metrics use result classes or approved keyed fingerprints. Prefix queries have minimum length, pagination, result caps, rate limits, and authorization before search. Masking is type policy and defaults to full value only for authorized internal users.

## 6. Barfarabaran questions for the domain owner

1. What legal authority and operator own the system, and what official specification/version governs the code?
2. What is the official field name: transport tracking code, bill-of-lading tracking number, trip code, endorsement reference, or something else?
3. Does one code identify a bill of lading, master/house bill, trip, shipment, vehicle, execution unit, or submission event?
4. Can one bill/shipment/unit have several codes, and can one code cover several bills/shipments/units?
5. At which submission/approval/endorsement step is it generated, and by which system?
6. Can users enter it, or must it be imported/verified from the authority?
7. What correction, cancellation, rejection, reissue, and supersession states exist?
8. What is the uniqueness scope and normalization/format rule, including mode-specific CAAB behavior if relevant?
9. Is it mandatory by mode, jurisdiction, date, customs office, or trade workflow?
10. Which roles may search/display it, and may customers or public tracking ever see it?
11. What durable evidence links it to the underlying bill of lading and any trade/customs records?

## 7. Exact authorized implementation boundary

A later controlled V1 may add the governed type model and two FK-strong value tables, one for `OperationalShipment` and one for `ExecutionUnit`; type applicability, tenant fencing, append/supersede lifecycle, optional exact `CaseDocumentFile` association, exact/prefix internal search, audit, and negative authorization tests. It may initially activate only B/L, AWB, and CMR after type provenance review. Cotage and warehouse receipt remain inactive until domain confirmation. Registration order and Barfarabaran are excluded. No request/project/cargo/document-owned value table, arbitrary owner type, public resolver, analytics, API/UI scope, seed, or migration execution is implicitly authorized.
