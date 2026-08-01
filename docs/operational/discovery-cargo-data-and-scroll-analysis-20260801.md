# Discovery and Domain Analysis Report

> **Governed evidence provenance:** Originally reviewed on 2026-08-01 and produced outside the Forwarder repository. It was admitted to the repository on 2026-08-01 as governed discovery evidence. Admission preserves the report's substantive findings and labels; it creates no implementation authority and does not accept any recommendation, PDR, or ADR.

Scope: repository state inspected read-only on 2026-08-01. No source, documentation, database, migration, release package, or Git state was modified. The immutable `release-v1.3.0-20260801` directory was not inspected as an implementation source or changed.

Labels used:

- **CONFIRMED** — directly supported by repository evidence.
- **INFERENCE** — recommended interpretation based on current architecture.
- **PRODUCT DECISION REQUIRED** — behavior cannot be selected safely from current evidence.
- **EVIDENCE MISSING** — no corresponding current implementation was found.

## 1. Executive Summary

**CONFIRMED:** The platform has no current cargo-item domain. Cargo is stored as four optional scalar fields on `ShipmentRequest`: description, weight, volume, and value. Cargo quantity, UOM, part number, HS Code, catalog identity, and execution-unit allocations do not exist. [ShipmentRequest model](D:/1-webapp/15-forwarder/backend/models.py:328)

**CONFIRMED:** Transport terminology is fragmented:

- `ShipmentRequest` contains legacy, domestic, and international string fields.
- An admin-managed `TransportMethod` table exists, but requests store strings rather than its identifier.
- `RouteLeg.transport_mode` is another required string.
- There is no `ServiceType`.

Evidence: [request transport fields](D:/1-webapp/15-forwarder/backend/models.py:389), [TransportMethod](D:/1-webapp/15-forwarder/backend/models.py:964), [RouteLeg](D:/1-webapp/15-forwarder/backend/operational_models.py:277).

**CONFIRMED:** The mobile scroll defect has a strong likely root cause: the application uses `BrowserRouter` without centralized route scroll handling. No application use of `window.scrollTo`, `history.scrollRestoration`, or a location-aware scroll component was found. Browser/React Router history behavior can therefore retain the previous document scroll offset during client-side navigation. [router root](D:/1-webapp/15-forwarder/src/App.tsx:83)

**INFERENCE:** A second contributor is focus-driven scrolling from Radix dialogs/selects and late content expansion. The repository does not contain runtime browser evidence tying one particular control to the defect, so this remains secondary rather than confirmed.

**RECOMMENDATION:** Use three runtime releases:

1. PATCH: centralized scroll restoration.
2. MINOR: governed master-data and cargo/allocation foundation.
3. MINOR: authenticated cross-project customer item search.

This separates a low-risk UI correction from schema/domain changes and customer-facing disclosure risk.

**READINESS VERDICT:** Ready to draft governance decisions; not ready to implement cargo standardization, allocation, or item search. The scroll fix is close to implementation-ready after a short browser reproduction matrix.

---

## 2. Confirmed Current-State Findings

### Existing aggregate boundaries

**CONFIRMED:**

- `Project` is a coordination boundary and contains customer and organization identity. [Project](D:/1-webapp/15-forwarder/backend/operational_models.py:55)
- `ShipmentRequest` remains commercial/request truth and can reference a Project. [ShipmentRequest.project_id](D:/1-webapp/15-forwarder/backend/models.py:417)
- `OperationalShipment` references one request, accepted quote, organization, and optionally Project. [OperationalShipment](D:/1-webapp/15-forwarder/backend/operational_models.py:220)
- `ExecutionUnit` belongs to a Project and may reference an OperationalShipment. [ExecutionUnit](D:/1-webapp/15-forwarder/backend/operational_models.py:111)
- `OperationalEvent` is append-only, unit-scoped, and explicitly separates `internal` and `customer` visibility. [OperationalEvent](D:/1-webapp/15-forwarder/backend/operational_models.py:152)

These boundaries are consistent with the canonical architecture and must not be collapsed into one cargo/search record.

### Existing reference-data patterns

**CONFIRMED:**

- `TransportMethod` has bilingual names, active state, description, and creation time, but no immutable code, validity interval, revision, update metadata, or audit fields. [TransportMethod](D:/1-webapp/15-forwarder/backend/models.py:964)
- `TrackingLocationReference` has an immutable-looking internal key, bilingual names, aliases, active state, status, ordering, and timestamps. It is an internal UI helper rather than a general EAV framework. [TrackingLocationReference](D:/1-webapp/15-forwarder/backend/models.py:526)
- `DocumentDefinition` is the strongest governance pattern: immutable code, revision, activation, applicability, audit actors, and policy snapshots on transactions. [DocumentDefinition](D:/1-webapp/15-forwarder/backend/models.py:1349)
- Shipment document requirements preserve historical policy snapshots. [CaseDocumentRequirement](D:/1-webapp/15-forwarder/backend/models.py:1380)

**INFERENCE:** The document-definition/snapshot pattern is the best precedent for cargo-related master-data governance.

### Current customer timeline

**CONFIRMED:** Customer visibility already has a domain boundary: `OperationalEvent.visibility`, `customer_message`, and public timeline endpoints/components. Internal notes are stored separately. [event visibility](D:/1-webapp/15-forwarder/backend/operational_models.py:159), [ProjectTracking page](D:/1-webapp/15-forwarder/src/pages/ProjectTracking.tsx), [public tracking routes](D:/1-webapp/15-forwarder/backend/routes/public_tracking.py).

---

## 3. Mobile Scroll Root-Cause Analysis

### Root cause

**CONFIRMED:** `BrowserRouter` wraps one document-level route tree with no route-change scroll controller. [App router](D:/1-webapp/15-forwarder/src/App.tsx:83)

**CONFIRMED:** Navigation is predominantly client-side via `Link` and `navigate()`, including dashboard-to-detail, list-to-detail, form-to-result, and authentication replacement navigation. Examples:

- [customer request navigation](D:/1-webapp/15-forwarder/src/pages/CustomerDashboard.tsx:347)
- [expert request navigation](D:/1-webapp/15-forwarder/src/pages/ExpertConsole.tsx:566)
- [operational shipment navigation](D:/1-webapp/15-forwarder/src/pages/OperationalShipments.tsx:11)
- [history-based back navigation](D:/1-webapp/15-forwarder/src/components/PageNav.tsx:24)

**LIKELY ROOT CAUSE:** On push/replace SPA navigation, React Router replaces the rendered route without inherently resetting the document scroll offset. The incoming page consequently appears at the outgoing page’s prior vertical offset.

### Navigation classification

| Navigation | Expected current behavior | Assessment |
|---|---|---|
| Push via `Link`/`navigate(path)` | Existing document offset can carry forward | **LIKELY AFFECTED** |
| Replace navigation | Same document; offset can carry forward | **LIKELY AFFECTED** |
| Back/Forward | Browser may restore prior history-entry offset | **EXPECTED TO PRESERVE** |
| Full reload/direct URL | Browser-controlled; usually top unless history/hash restoration applies | **CONDITIONAL** |
| Hash navigation | Should navigate to target rather than force top | **EVIDENCE MISSING** for application hash routes |

### Affected routes

Because the missing behavior is at the router root, all client-side route transitions are potentially affected. Highest-risk routes have long or asynchronously populated pages:

- `/customer/:customerId`
- `/request/:requestId`
- `/expert`
- `/expert/requests/:id`
- `/admin`
- `/operations/shipments`
- `/operations/shipments/:id`
- `/operations/projects/:projectId/units`
- `/customer/track/:requestId`
- `/project/track/:trackingCode`

Route inventory: [App.tsx](D:/1-webapp/15-forwarder/src/App.tsx:87).

### Secondary contributors

- **INFERENCE:** Dialog/select focus restoration can scroll a trigger into view after close.
- **INFERENCE:** Async loading and expandable timelines can shift layout after an initial top scroll.
- **CONFIRMED:** A sticky header exists and could obscure hash/focus targets. [Header](D:/1-webapp/15-forwarder/src/components/Header.tsx:20)
- **EVIDENCE MISSING:** No confirmed problematic `autoFocus` usage or production hash-fragment route was found.

### Recommended centralized solution

Add one router-level `ScrollRestorationController` that:

1. Distinguishes `PUSH`, `REPLACE`, and `POP`.
2. Scrolls to `{top: 0, left: 0, behavior: "auto"}` on ordinary push/replace.
3. Preserves browser restoration on `POP`.
4. Honors a valid hash target, with sticky-header offset support.
5. Allows explicit route state such as `preserveScroll`.
6. Runs after location change using a layout-safe effect.
7. Does not move keyboard focus to `<body>`; page focus behavior should be handled separately.

Consider setting `history.scrollRestoration = "manual"` only if the controller also stores/restores POP positions. Otherwise retain browser POP restoration.

### Preservation exceptions

- Back/Forward to lists with filters and pagination.
- Same-route query changes used only for filtering/pagination.
- Modal/background-route navigation.
- In-page hash anchors.
- Explicit “return to previous position” workflows.
- Infinite-scroll/list-to-detail-to-list journeys.

### Accessibility

Resetting visual scroll without focus can leave screen-reader and keyboard users conceptually on the previous control. New-page navigation should optionally focus a page heading or main-region sentinel with `tabIndex={-1}` and announce the route title. Reduced-motion preference must be respected; do not use smooth scrolling by default.

### Test plan

- Mobile widths: 360, 390, 412; desktop control at 1280/1440.
- Long page → short page for Link, push, and replace.
- List → detail → browser Back restores list position.
- Same-route query update preserves position.
- Hash target remains visible below sticky header.
- Dialog close does not unexpectedly jump.
- Async page loading remains top unless the user scrolls meanwhile.
- Keyboard focus and screen-reader announcement.
- iOS Safari and Android Chrome real-device/manual coverage.
- Automated router unit tests plus Playwright/Cypress scroll assertions.

**Version:** PATCH candidate under the repository’s SemVer policy: bug fixes are PATCH. [release governance](D:/1-webapp/28-AI-Rules/06-Version-Release-Deployment-Governance.md)

---

## 4. Current Field Inventory

“No current field” means no domain persistence/UI implementation was found; an OpenAPI-only property does not establish runtime storage.

| Field | Business Meaning | Current Storage / UI | Type | Reused In | Reporting Risk | Recommended Classification | Evidence |
|---|---|---|---|---|---|---|---|
| Cargo type | High-level cargo taxonomy | No runtime field; OpenAPI mentions `cargo_type` | Contract-only | None confirmed | Critical contract drift | Hierarchical Taxonomy | [OpenAPI](D:/1-webapp/15-forwarder/docs/openapi/openapi.yaml:140) |
| Cargo description | Customer’s narrative of goods | `ShipmentRequest.cargo_description`; optional textarea/form | Free text | Expert detail, tracking context, reports/XLSX | High: synonyms and mixed granularity | Free Text | [model](D:/1-webapp/15-forwarder/backend/models.py:395), [form payload](D:/1-webapp/15-forwarder/src/components/LocationForm.tsx:1235) |
| Commodity/goods | Commodity identity | No distinct field | Missing | — | Critical | CargoCatalogItem or Free Text, depending use | **EVIDENCE MISSING** |
| Service type | Commercial/operational service supplied | No field/model/UI | Missing | — | Critical | Admin-managed Master Data | **EVIDENCE MISSING** |
| Transport method | Customer-requested method | Three request strings; options loaded from `TransportMethod` with hard-coded fallback | String + table disconnected | Forms, assignment, admin reports | High: duplicate columns and labels | Admin-managed Master Data; legacy columns deprecated | [model](D:/1-webapp/15-forwarder/backend/models.py:389), [fallback](D:/1-webapp/15-forwarder/src/components/LocationForm.tsx:492) |
| Transport mode | Actual route-leg movement mode | `RouteLeg.transport_mode` required string | Code-like string | Operational route planning | Medium/high: no FK governance | Fixed enum initially or master-data FK | [RouteLeg](D:/1-webapp/15-forwarder/backend/operational_models.py:295) |
| Vehicle/unit type | Execution carrier/container class | `ExecutionUnit.unit_type`; legacy `ShipmentTransportUnit.unit_type` | String | Unit tracking | High | Admin-managed Master Data or governed enum | [ExecutionUnit](D:/1-webapp/15-forwarder/backend/operational_models.py:134), [legacy unit](D:/1-webapp/15-forwarder/backend/models.py:503) |
| Cargo category | Secondary classification | No field | Missing | — | Critical | Hierarchical Taxonomy; avoid duplicate of CargoType | **EVIDENCE MISSING** |
| Package type | Packaging form | No cargo field | Missing | — | Critical | Admin-managed Master Data | **EVIDENCE MISSING** |
| UOM | Quantity measurement | Not stored; context service explicitly records missing weight/volume units | Missing | — | Critical: quantities ambiguous | Admin-managed Master Data with compatibility rules | [shipment context](D:/1-webapp/15-forwarder/backend/services/shipment_context_service.py:107) |
| Cargo quantity | Requested/shipped quantity | No field | Missing | — | Critical | Transactional Entity field | **EVIDENCE MISSING** |
| Weight | Cargo weight | Optional float, no stored UOM | Numeric scalar | Forms, expert detail, reports/XLSX | Critical unit ambiguity | Transactional field + UOM | [model](D:/1-webapp/15-forwarder/backend/models.py:396) |
| Volume | Cargo volume | Optional float, no stored UOM | Numeric scalar | Forms, expert detail, reports/XLSX | Critical unit ambiguity | Transactional field + UOM | [model](D:/1-webapp/15-forwarder/backend/models.py:397) |
| Declared value | Cargo/commercial value | `cargo_value` optional float; no currency | Numeric scalar | Expert detail, reports; omitted from safe context | Critical currency/meaning ambiguity | Transactional confidential value + currency | [model](D:/1-webapp/15-forwarder/backend/models.py:398), [sensitivity](D:/1-webapp/15-forwarder/backend/services/shipment_context_service.py:88) |
| HS Code | Customs commodity classification | No field | Missing | — | Critical | Governed code/reference plus transactional snapshot | **EVIDENCE MISSING** |
| Part number | Manufacturer/customer product identity | No field | Missing | — | Critical | Catalog attribute and transactional snapshot | **EVIDENCE MISSING** |
| Brand/model | Product attributes | No cargo fields; `vehicle_reference` is unrelated | Missing | — | High | Catalog attributes + transactional snapshots | **EVIDENCE MISSING** |
| Delay reason | Reason for delayed execution | Boolean `delayed`, but no reason code | Boolean only | Unit status/event | High | Admin-managed Master Data | [ExecutionUnit](D:/1-webapp/15-forwarder/backend/operational_models.py:140), [event](D:/1-webapp/15-forwarder/backend/operational_models.py:175) |
| Exception type | Operational exception classification | Work-item type/string behavior, not a governed reference concept | String/domain behavior | Route reconciliation | High | Fixed Domain Enum or explicit domain table | [OperationalWorkItem](D:/1-webapp/15-forwarder/backend/operational_models.py:409) |
| Document type | Required document policy | `DocumentDefinition.code/title`, snapshotted to request | Explicit table | Admin document definitions, case files | Low/medium; bilingual gap | Admin-managed Master Data/domain policy | [DocumentDefinition](D:/1-webapp/15-forwarder/backend/models.py:1349) |
| Customer industry | CRM segmentation | `Customer.industry` free string | Free text | CRM | High | Admin-managed Master Data | [Customer](D:/1-webapp/15-forwarder/backend/models.py:802) |
| Project type | Project classification | No field | Missing | — | Critical if reported | Admin-managed Master Data only after business definition | **EVIDENCE MISSING** |
| Request source/channel | Acquisition/submission source | `Customer.source`; no canonical ShipmentRequest source | Free text | CRM only | High and semantically misplaced for request reporting | Admin-managed channel + transactional request source | [Customer.source](D:/1-webapp/15-forwarder/backend/models.py:806) |

---

## 5. Master Data Classification Matrix

Shared conventions should include immutable code, bilingual labels where user-facing, activation rather than deletion, audit, optional validity, and historical label snapshots.

| Concept | Owner / Scope | Hierarchy / bilingual | Governance behavior | Other policy | Phase 1? |
|---|---|---|---|---|---|
| CargoType | Product/Data; global with org extensions later | Hierarchical; FA+EN | Immutable code; deactivate; no hard delete after use; audited; validity/remap desirable; preserve historical snapshot | Explicit `OTHER` plus required description; `UNCLASSIFIED` system state separate | Yes |
| ServiceType | Product/Commercial; global | Usually flat; FA+EN | Immutable code; deactivate; historical snapshot; audited | `OTHER` only with governed review | Yes |
| TransportMode | Operations; global | Flat; FA+EN | Stable code; code-owned compatibility rules; admin labels/activation | Avoid unrestricted Other in route execution | Yes, reconcile current fields |
| VehicleType | Operations; global, possibly org extension | Optional hierarchy; FA+EN | Deactivate, never delete used values; audited | Allowed with free-text detail and review | Later unless allocation UI needs it |
| UnitOfMeasure | Data/Domain; global | Dimensions/conversion groups, not display hierarchy; bilingual symbols/names | Immutable code; code-governed dimensional compatibility and conversion; no delete | No generic Other | Yes |
| PackagingType | Operations/Data; global | Optional hierarchy; FA+EN | Immutable code; deactivate/remap; historical snapshot | Controlled Other | Cargo phase |
| DelayReason | Operations/Product; global/org-specific | Optional parent groups; FA+EN | Audited activation; effective dates useful; preserve event snapshot | Controlled Other with required note | Later PDR |
| ExceptionType | Operations/Architecture; global | Usually flat | Core behavior code-governed; admin labels/severity only | Unknown fallback, not business Other | Later PDR |
| DocumentType | Compliance/Operations; global/org-specific | Flat; FA+EN required | Existing definition revision/snapshot model; deactivate; no deletion in use | Miscellaneous document already separate | Existing/further refinement |
| CustomerIndustry | CRM/Product; global | Optional hierarchy; FA+EN | Deactivate/remap; audited | Controlled Other | Later |

### Framework choice

**Recommendation: B — explicit domain tables sharing common governance conventions.**

Use reusable infrastructure for:

- admin CRUD patterns,
- code/name/activation/audit columns,
- validity validation,
- localization,
- references-in-use checks,
- remap workflows.

Do not create one unbounded `ReferenceValue(type, key, value, metadata)` store. Cargo types, UOMs, service types, exception types, and document definitions have materially different invariants and relationships. A generic EAV design would hide foreign-key integrity and move domain rules into runtime metadata.

A narrow shared base/mixin and shared admin components are appropriate; shared storage is not.

---

## 6. ServiceType Cardinality Analysis

**CONFIRMED:** Current request forms capture shipping type (`domestic`/`international`) and a preferred transport method. They do not capture customs clearance, warehousing, loading, packing, or a service package. [ShipmentRequest](D:/1-webapp/15-forwarder/backend/models.py:338), [request form transport selection](D:/1-webapp/15-forwarder/src/components/LocationForm.tsx:2391)

**CONFIRMED:** `OperationalShipment` contains no service field. [OperationalShipment](D:/1-webapp/15-forwarder/backend/operational_models.py:220)

**INFERENCE:** Transport mode and service are different axes:

- Road/rail/sea/air are execution modes.
- Customs clearance, warehousing, loading, and packing are services.
- “International road transport” is likely a service offering parameterized by international scope and road mode, not a single universal enum value.
- Multimodal is an execution composition, not necessarily a service type.

### Recommended ownership

Introduce a transactional `ProjectService`/`ShipmentService` selection:

- A Project may contain multiple requested/contracted services.
- One service may be primary; others supporting.
- OperationalShipment may link to the services it fulfills.
- Transport legs retain their actual `TransportMode`.
- ShipmentRequest captures requested services before acceptance.
- Project holds the accepted/coordinated service package.

**PRODUCT DECISION REQUIRED:**

- Whether one primary service is mandatory.
- Whether supporting services can be added after request acceptance.
- Whether prices/quotes are per service.
- Whether service fulfillment belongs to Project, OperationalShipment, or a separate work package.

A single `service_type_id` on Project or ShipmentRequest is not sufficiently expressive for the stated examples.

---

## 7. Proposed Cargo Item Domain Model

| Object | Definition and owner | Identity/scope | Lifecycle and integrity | Visibility/search |
|---|---|---|---|---|
| `CargoType` | Governed high-level taxonomy; owned by Master Data | Immutable code; global, with organization extension only if approved | Versioned label/hierarchy; deactivate, remap, no destructive delete | Customer-safe labels may be public |
| `CargoCatalogItem` | Reusable standardized item definition, not shipment quantity | UUID/public-safe ID; organization-scoped by default; optional customer owner; canonical code | Mutable descriptive metadata with audit; immutable code; deactivation; historical transaction snapshots | Authenticated only by default; indexed names, aliases, part/customer codes |
| `ShipmentCargoItem` | Transactional cargo line belonging to one OperationalShipment | UUID/public ID and shipment-local line number | Quantity/UOM and shipment facts; snapshots catalog/type/name/codes; corrections audited; never silently rewritten from catalog | Customer-visible projection per Project authorization |
| `ExecutionUnitCargoAllocation` | Quantity of one ShipmentCargoItem assigned to one ExecutionUnit | Allocation ID plus item/unit relationship | Versioned/concurrency-controlled; reallocation audit; additive correction history | Expose approved quantity/UOM/status only |
| `CargoItemAlias` | Alternative search terminology for a catalog item | Alias ID; item plus organization/customer scope | Normalized value, language, type, activation, audit | Search only within authorized scope |

### Suggested fields

`CargoCatalogItem`:

- Required: organization/customer scope, canonical code, Persian or English primary name, CargoType, active state.
- Optional: second-language name, aliases, part number, customer item code, HS Code, brand, model, default UOM, description, origin, dangerous/perishable indicators.
- Avoid default declared value, weight, or quantity unless explicitly defined as reference metadata.

`ShipmentCargoItem`:

- Required: OperationalShipment, line number, display-name snapshot, quantity, UOM snapshot/code.
- Optional: catalog item, CargoType snapshot, part/customer codes, HS Code snapshot, description, weight and UOM, volume and UOM, declared value and currency, origin, hazard/perishable flags.
- Created/updated actor/time and optimistic version.

`ExecutionUnitCargoAllocation`:

- ShipmentCargoItem, ExecutionUnit, allocated quantity, UOM, state, version, created/updated actor/time, correction/supersession reference.

### Aggregate boundaries

- `ShipmentCargoItem` belongs to `OperationalShipment`.
- Allocation changes are coordinated against the shipment item and unit, with transactional invariant enforcement.
- Catalog edits must never rewrite transaction snapshots.
- Project search is a read model across child shipments/units; Project does not own cargo quantities.

### Current-model compatibility

Existing `ShipmentRequest.cargo_description/weight/volume/value` remain request-level legacy facts. They cannot be losslessly promoted to shipment lines because quantity, UOM, item boundaries, currency, and allocation are absent.

---

## 8. Allocation Integrity Rules

### Suitable for the first implementation

- Allocation quantity must be positive.
- Sum of active allocations cannot exceed shipment-item quantity.
- Allocation and item UOM must match exactly in phase one.
- Unallocated quantity is derived as `item quantity - active allocation sum`.
- ExecutionUnit must belong to the same Project and normally the same OperationalShipment.
- New allocation to an inactive/cancelled unit is rejected.
- Every create/update/reallocation records actor, time, reason, previous value, and idempotency key.
- Optimistic version checking or row locking prevents concurrent over-allocation.
- Cancellation releases outstanding allocation only through an explicit audited command.
- Delivered quantities cannot be silently reduced or reassigned.

For 300 gearboxes, allocations of 100 + 120 + 80 are valid and yield zero unallocated.

### Later PDR decisions

**PRODUCT DECISION REQUIRED:**

- Whether over-allocation/back-ordering is ever permitted.
- UOM conversion and rounding.
- Meaning of allocated vs loaded vs dispatched vs delivered.
- Partial delivery and returned/damaged quantity.
- Unit split/merge lineage.
- Cancellation after physical movement.
- Corrections to delivered quantities.
- Whether one cargo line can span multiple OperationalShipments.
- Whether inactive units retain historical allocation in operational totals.
- Negative adjustment versus superseding correction semantics.

Until approved, phase one should use exact-UOM allocation and prohibit over-allocation.

---

## 9. Customer Search Model

### Access model

**Recommendation:** Global cross-project item search must require authenticated customer access. Public tracking codes should expose only the single Project/request explicitly authorized by that opaque code.

No anonymous endpoint should accept an item query and search across Projects.

### Scope

Every search query must be constrained first by authorized customer organization/stakeholder scope, then matched against items. Authorization cannot be applied after an unscoped search.

Selected-stakeholder access requires an explicit Project membership/visibility rule; mere possession of a customer identifier is insufficient.

### Match fields

Rank in this order:

1. Exact normalized part number.
2. Exact customer item code.
3. Exact canonical code or HS Code.
4. Exact normalized FA/EN name.
5. Exact alias.
6. Prefix/fuzzy name or alias.

Normalize Persian text using Unicode NFC plus controlled folding of Arabic/Persian `ي/ی` and `ك/ک`, removal/standardization of ZWNJ and spacing for a separate search key, Arabic digit normalization, trimming, and case-folding. Preserve original display text.

### Result structure

```text
Item
└─ Project
   └─ OperationalShipment
      └─ ExecutionUnit
```

Summary:

- Project count
- OperationalShipment count
- ExecutionUnit count
- total, allocated, and unallocated quantity
- allocation quantity grouped by unit status
- latest customer-visible event
- last update

Row:

- Project code/public-safe identifier
- OperationalShipment public-safe identifier
- ExecutionUnit code
- item name and part number
- allocated quantity and UOM
- current lifecycle status
- delay/attention indicator
- latest customer-visible event
- updated time
- timeline link

### UX behavior

- Cursor pagination, default 25 item groups.
- Filters: Project, status, CargoType, date range, allocated/unallocated.
- Sorting: relevance first; optional latest update, item name, Project.
- Mobile: item summary card, expandable Project → shipment → unit sections; avoid wide tables.
- Empty state distinguishes no match from inaccessible data without disclosing which.
- Export deferred.
- Public tracking: permit search/filter only within the already-authorized Project if needed later.

---

## 10. Search Technology Recommendation

### First stage

Use normalized PostgreSQL tables and indexes:

- Exact B-tree indexes for normalized part number, customer item code, canonical code, and HS Code.
- Alias table with normalized alias and scope indexes.
- `pg_trgm` GIN/GiST indexes for Persian/English names and aliases.
- Explicit organization/customer predicates in every query.
- Stable ranking in SQL.
- Keyset/cursor pagination.

PostgreSQL full-text search is optional, not the initial foundation: item names and identifiers are short, and Persian configuration/normalization requires careful validation. Trigram matching is simpler for name variants and limited typo tolerance.

A dedicated search projection becomes useful when aggregation joins become slow or stale-event ranking becomes expensive. It must remain organization-scoped and rebuildable from canonical tables.

### External engine threshold

Consider OpenSearch/Elasticsearch only when one or more are demonstrated:

- Multi-million item/allocation rows with unacceptable indexed PostgreSQL latency.
- Advanced typo tolerance, synonyms, phonetics, or faceting.
- Cross-language ranking requirements exceed SQL maintainability.
- Search load materially competes with transactions.
- A governed CDC/index reconciliation process is funded.

At 500 Projects and roughly 50,000 items, normalized PostgreSQL plus trigram indexes is sufficient.

---

## 11. Security and Privacy Model

### Mandatory controls

- Organization/customer scope must be embedded in query construction.
- Public IDs/opaque tracking codes only; never expose sequential internal IDs.
- Parent Project authorization must be verified for every shipment, unit, item, event, and timeline request.
- Latest event must filter `visibility = 'customer'`; internal notes must never enter the projection. [OperationalEvent visibility](D:/1-webapp/15-forwarder/backend/operational_models.py:159)
- Declared values, internal descriptions, supplier data, and customer-specific codes require separate field permissions.
- HS Code visibility requires Product/Compliance approval.
- Counts must be calculated after authorization scope.
- Empty/no-result responses and timing should not reveal another tenant’s existence.
- Rate-limit queries and bound minimum query length for fuzzy name search.
- Audit sensitive search and export activity.

### Permission families

- `cargo_catalog.create/edit/deactivate/classify`
- `shipment_cargo.create/edit/view`
- `cargo_allocation.create/reallocate/correct/view`
- `cargo_search.customer`
- `cargo_search.internal`
- `cargo_sensitive_value.view`
- `cargo_hs_code.view`
- `cargo_alias.manage`

Catalog deactivation and classification do not imply permission to alter transactions. Allocation rights do not imply catalog administration.

### Current precedent

Project and execution objects already carry organization/project linkage, public identifiers, and customer-visible events. [Project organization/customer](D:/1-webapp/15-forwarder/backend/operational_models.py:82), [ExecutionUnit project](D:/1-webapp/15-forwarder/backend/operational_models.py:130), [OperationalShipment same-organization constraint](D:/1-webapp/15-forwarder/backend/operational_models.py:225).

---

## 12. Legacy Data Strategy

1. Add structured fields/tables as nullable and additive.
2. Continue rendering the legacy description, weight, volume, and value.
3. Mark records without structured cargo lines as `Unclassified` in internal reporting/search.
4. Do not manufacture `CargoCatalogItem` records from descriptions.
5. Provide an authorized manual classification workflow with before/after audit.
6. Store mapping provenance and reviewer identity.
7. Preserve legacy values alongside structured values during compatibility.
8. Defer bulk import until its matching, conflicts, rollback, and approval process is governed.

### Adoption cohorts

- New requests: permit/require structured cargo entry after catalog/UOM readiness; retain optional description.
- Existing open Projects: manually classify high-value/current work; never block existing execution solely because classification is absent.
- Historical closed Projects: read-only legacy by default; classify only for an approved reporting/search need.

No destructive backfill is justified by current evidence.

---

## 13. Reporting-Readiness Data Model

### Reliable after standardization

Dimensions:

- CargoType
- CargoCatalogItem
- ServiceType
- TransportMode
- UnitOfMeasure
- PackagingType
- Customer
- Project
- OperationalShipment
- ExecutionUnit lifecycle status
- customer-visible event type/time

Facts:

- requested/shipment quantity
- allocated quantity
- unallocated quantity
- delivered quantity after policy approval
- shipment count
- unit count
- event timestamps
- weight/volume only when paired with governed UOM
- declared value only when paired with currency and access policy

### Still unsafe

- Existing cargo description as commodity/category.
- Existing weight and volume without UOM.
- Existing cargo value without currency and semantic definition.
- Current coalesced transport-method reporting across three strings.
- Service reporting, because no ServiceType exists.
- Delay-reason or exception-type reporting without governed codes.
- Customer industry and source/channel while free text.
- Delivered quantity until delivery semantics are approved.
- Catalog-level cross-customer statistics without confidentiality approval.

Current reports already coalesce the three request transport strings and export cargo scalars, confirming present reporting ambiguity. [report coalescing](D:/1-webapp/15-forwarder/backend/services/admin_report_overview_service.py:402), [XLSX cargo fields](D:/1-webapp/15-forwarder/backend/services/admin_report_xlsx_service.py:150).

---

## 14. Capability Mapping

| Requirement | Capability | Change class |
|---|---|---|
| Central scroll restoration | CAP-007 Customer Portal plus shared frontend shell | PATCH |
| Master-data governance | CAP-013 Master Data, CAP-009 Administration | MINOR |
| CargoType/ServiceType administration | CAP-013, CAP-009 | MINOR |
| CargoCatalogItem/ShipmentCargoItem | CAP-002 Shipment Management, CAP-013 | MINOR |
| ExecutionUnit allocation | CAP-003 Execution Management, CAP-002 | MINOR |
| Cross-project authenticated customer search | CAP-007, CAP-001 Project Management, CAP-002, CAP-003 | Later MINOR |

The capability registry identifies capabilities as governed scopes rather than permission to merge aggregate ownership. [Capability Registry](D:/1-webapp/15-forwarder/docs/operational/capability_registry.md), [Capability Map](D:/1-webapp/15-forwarder/docs/operational/platform_capability_map_v1.md).

---

## 15. Required Governance Decisions

Before implementation, create—not in this analysis:

- **PDR:** master-data scope and ownership.
- **PDR:** ServiceType cardinality and service package behavior.
- **PDR:** catalog scope: global, organization, or customer.
- **PDR:** aliases and customer terminology ownership.
- **PDR:** allocation, delivery, cancellation, correction, split/merge rules.
- **PDR:** customer item/field visibility and authenticated search.
- **PDR:** legacy classification policy and cohorts.
- **RFC:** cargo standardization, allocation, and customer-search capability proposal.
- **ADR:** explicit master-data tables and shared governance convention.
- **ADR:** cargo aggregate boundaries and transaction snapshots.
- **ADR:** allocation concurrency/integrity mechanism.
- **ADR:** PostgreSQL normalization/search and tenant-scoping architecture.
- **Epic:** Cargo Data Foundation.
- **Epic or follow-on Epic:** Customer Cross-Project Cargo Search.
- **Slices:** separately authorized implementation slices below.

The scroll PATCH needs a bounded defect record/slice and test evidence; it does not require a new domain RFC unless repository governance explicitly classifies all router infrastructure changes that way.

---

## 16. Recommended Release/Slice Plan

### Release 1 — PATCH: SLICE-A Central Scroll Restoration

- Goal: deterministic top-on-new-route with history preservation.
- Capability: shared frontend/CAP-007.
- Dependencies: browser reproduction matrix.
- Scope: router controller, hash/history/focus behavior, tests.
- Out: page redesign.
- Schema/API/migration/security: none.
- UI: centralized navigation behavior.
- Compatibility: preserve POP and explicit exceptions.
- Tests: router unit + real mobile browser matrix.
- Rollback: remove/disable controller.
- Acceptance: push/replace open top; Back restores; anchors and focus work.
- Proposed version: next PATCH after 1.3.0.
- Blocker: exact preservation exceptions.

### Release 2 — MINOR: SLICE-B Master Data Governance Foundation

- Goal: shared conventions without generic EAV.
- Capability: CAP-013/CAP-009.
- Dependencies: master-data PDR/ADR.
- Scope: audit, code, bilingual names, activation, historical-reference conventions.
- Out: cargo catalog/search.
- Schema/API/UI: explicit base conventions and admin infrastructure.
- Security: master-data role separation.
- Migration: additive.
- Compatibility: current references remain usable.
- Tests: lifecycle, duplicate code, referenced deactivation, audit.
- Rollback: feature flag/admin disable; preserve records.
- Acceptance: governed create/edit/deactivate with no hard-delete history loss.
- Version: MINOR.
- Blocker: ownership and scope.

### SLICE-C CargoType and ServiceType Administration

- Goal: first governed concepts.
- Capability: CAP-013/CAP-009.
- Dependencies: B; ServiceType decision.
- Scope: CargoType hierarchy, ServiceType definitions, transport reconciliation plan.
- Out: transactional cargo.
- Schema/API/UI: explicit tables and admin pages.
- Security/migration: admin-only, additive.
- Compatibility: legacy transport strings retained.
- Tests: hierarchy cycles, code immutability, bilingual validation, inactive historical display.
- Rollback: disable selection/admin writes.
- Acceptance: active values selectable; inactive retained historically.
- Version: same MINOR vertical release if independently flaggable.
- Blocker: service ownership/cardinality.

### SLICE-D Cargo Catalog and ShipmentCargoItem

- Goal: structured reusable identity plus transactional lines.
- Capability: CAP-002/CAP-013.
- Dependencies: B/C, UOM governance.
- Scope: catalog, aliases, shipment line snapshots, legacy coexistence.
- Out: unit allocations/search.
- Schema/API/UI: additive tables/endpoints/forms.
- Security: catalog/customer scope and confidential fields.
- Migration: no guessed backfill.
- Compatibility: legacy descriptions remain readable.
- Tests: scope isolation, snapshots, nullable catalog link, Unicode normalization.
- Rollback: disable structured entry; preserve data and legacy rendering.
- Acceptance: new shipment lines can be created without altering legacy records.
- Version: MINOR.
- Blockers: catalog scope, aliases, required fields.

### SLICE-E ExecutionUnitCargoAllocation

- Goal: trace item quantities to execution units.
- Capability: CAP-003/CAP-002.
- Dependencies: D and allocation PDR.
- Scope: allocation, unallocated calculation, audit, concurrency.
- Out: advanced conversion/split/merge unless approved.
- Schema/API/UI: allocation entity and unit/item views.
- Security: separate allocate/reallocate/correct permissions.
- Migration: additive, none guessed.
- Compatibility: units without allocations remain supported.
- Tests: over-allocation race, inactive units, cancellation, audit, IDOR.
- Rollback: disable writes/views while retaining evidence.
- Acceptance: 300 = 100 + 120 + 80; concurrent excess rejected.
- Version: MINOR release 2, if D is stable.
- Blockers: delivery/correction/UOM rules.

### Release 3 — MINOR: SLICE-F Customer Cross-Project Item Search

- Goal: authenticated item-to-Project/shipment/unit traceability.
- Capability: CAP-007/CAP-001/CAP-002/CAP-003.
- Dependencies: D/E, stable customer event projection.
- Scope: PostgreSQL search, aggregation, mobile results, timeline links.
- Out: anonymous cross-project search and export.
- API/UI: customer-scoped cursor endpoint and hierarchical mobile UI.
- Security: tenant-first predicates, non-enumeration, field projection.
- Migration: indexes/search keys only; rebuildable.
- Compatibility: public tracking unchanged.
- Tests: cross-tenant negative tests, Persian normalization, ranking, pagination, leakage, performance.
- Rollback: feature flag; retain canonical data.
- Acceptance: exact and bilingual queries return only authorized Projects and correct totals/events.
- Version: later MINOR.
- Blockers: authenticated access, selected stakeholders, visible fields, result semantics.

---

## 17. Files and Components Likely Affected

No files were changed. Likely future touchpoints:

### Scroll

- [App.tsx](D:/1-webapp/15-forwarder/src/App.tsx)
- [PageNav.tsx](D:/1-webapp/15-forwarder/src/components/PageNav.tsx)
- [Header.tsx](D:/1-webapp/15-forwarder/src/components/Header.tsx)
- Route/page tests under [src/tests](D:/1-webapp/15-forwarder/src/tests)

### Domain and persistence

- [models.py](D:/1-webapp/15-forwarder/backend/models.py)
- [operational_models.py](D:/1-webapp/15-forwarder/backend/operational_models.py)
- Additive Alembic migrations under [backend/migrations/versions](D:/1-webapp/15-forwarder/backend/migrations/versions)
- OpenAPI source: [openapi.yaml](D:/1-webapp/15-forwarder/docs/openapi/openapi.yaml)

### APIs/services

- [shipment_request.py](D:/1-webapp/15-forwarder/backend/routes/shipment_request.py)
- [operations.py](D:/1-webapp/15-forwarder/backend/routes/operations.py)
- [execution_units.py](D:/1-webapp/15-forwarder/backend/routes/execution_units.py)
- [public_tracking.py](D:/1-webapp/15-forwarder/backend/routes/public_tracking.py)
- [shipment_service.py](D:/1-webapp/15-forwarder/backend/services/shipment_service.py)
- [execution_unit_service.py](D:/1-webapp/15-forwarder/backend/services/execution_unit_service.py)

### UI/admin/customer

- [LocationForm.tsx](D:/1-webapp/15-forwarder/src/components/LocationForm.tsx)
- [AdminPanel.tsx](D:/1-webapp/15-forwarder/src/pages/AdminPanel.tsx)
- [OperationalShipmentDetail.tsx](D:/1-webapp/15-forwarder/src/pages/OperationalShipmentDetail.tsx)
- [ExecutionUnits.tsx](D:/1-webapp/15-forwarder/src/pages/ExecutionUnits.tsx)
- [ProjectTracking.tsx](D:/1-webapp/15-forwarder/src/pages/ProjectTracking.tsx)
- [CustomerDashboard.tsx](D:/1-webapp/15-forwarder/src/pages/CustomerDashboard.tsx)
- [api.ts](D:/1-webapp/15-forwarder/src/lib/api.ts)
- [i18n.tsx](D:/1-webapp/15-forwarder/src/i18n.tsx)

---

## 18. Risks and Open Questions

### Highest risks

- Treating transport mode as service type.
- Creating catalog records by guessing from descriptions.
- Missing quantity/UOM/currency semantics.
- Cross-customer count or timing leakage.
- Catalog edits changing historical shipment meaning.
- Concurrent over-allocation.
- Delivering search before classification coverage is useful.
- A generic reference EAV becoming the de facto domain model.
- Adding customer visibility without distinguishing internal events/notes.
- Incorrect Unicode normalization causing false merges.

### Open Product questions

- Is catalog identity global, organization-owned, or customer-owned?
- Can two customers use the same part number for different items?
- Is HS Code customer-visible?
- Is one primary service required?
- Can a shipment line use different allocation UOMs?
- What exactly constitutes delivered quantity?
- How are damaged/returned goods represented?
- Can a unit carry items from multiple shipments?
- Should open Projects be mandatory classification candidates?
- Are selected stakeholders entitled to catalog/item search or only Project tracking?

---

## 19. Readiness Verdict

### Scroll restoration

**CONDITIONALLY READY.** Architecture evidence is sufficient for a centralized solution, but a browser reproduction matrix should confirm push/replace/POP behavior and identify focus/hash exceptions before implementation.

### Master data and cargo foundation

**NOT IMPLEMENTATION-READY.** The architecture direction is clear, but Product decisions on ServiceType, catalog scope, UOM rules, aliases, visibility, and legacy classification are blocking.

### Allocation

**NOT IMPLEMENTATION-READY.** Basic invariants are recommendable, but delivery, cancellation, correction, split/merge, and unit/shipment ownership require PDR closure.

### Customer search

**NOT IMPLEMENTATION-READY.** It depends on structured cargo, allocations, authenticated customer scope, and approved field visibility. PostgreSQL is technically sufficient once those foundations exist.

---

## 20. Exact Recommended Next Codex Prompt

> Perform a read-only governance-preparation pass for Forwarder’s Cargo Data Foundation. Do not modify source code, documentation, migrations, databases, release packages, or Git state. Using the existing Platform Constitution, Architecture Baseline, Canonical Business Object Catalog, Capability Map/Registry, accepted ADRs/PDRs, RFC-001, EPIC-001, and the current domain implementation, prepare decision-ready option matrices—but do not create the artifacts—for:
>
> 1. CargoCatalogItem scope: global vs organization vs customer.
> 2. ServiceType cardinality and ownership across ShipmentRequest, Project, and OperationalShipment.
> 3. CargoType hierarchy and “Other/Unclassified” policy.
> 4. UnitOfMeasure dimensions, compatibility, and conversion policy.
> 5. ShipmentCargoItem quantity, delivery, cancellation, correction, and split/merge behavior.
> 6. ExecutionUnitCargoAllocation concurrency and audit rules.
> 7. Customer aliases and part-number collision policy.
> 8. Authenticated customer search visibility, selected-stakeholder access, and sensitive fields.
> 9. Legacy classification cohorts for new, open, and historical records.
>
> For every decision provide: options, recommendation, benefits, risks, backward-compatibility impact, security impact, migration impact, fail-safe behavior, required approver, blocking slice, and repository evidence. Clearly label CONFIRMED, INFERENCE, PRODUCT DECISION REQUIRED, and EVIDENCE MISSING. End with the minimum PDR/RFC/ADR/Epic/Slice artifact set and the order in which Product, Architecture, Security, Data, and Operations should approve them. Do not implement anything.
