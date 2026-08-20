# Forwarder End-to-End Operational Gap Register

- Review baseline: `aefb7271d8d38affe90fbf1113a4558020608897`
- Review date: 2026-08-20
- Scope: authenticated expert flow from transport request through shipment execution, cargo, tracking, documents, and certified external references
- Production access / production database / deployment: **none**

## Reference scenario

An automotive customer requests transport of `Gearbox / گیربکس` from Tehran to an international destination. One project contains two operational shipments: an air shipment with an AWB and a road continuation with CMR references. Each shipment carries a distinct gearbox quantity/UOM snapshot, has independent document readiness, and may have execution units/events. The operational question is whether an expert can identify every gearbox shipment, quantity/UOM, lifecycle, latest known location/event, document state, and applicable external reference without memorizing internal IDs.

## Actual operational map

| Step | Domain object | User screen | API | Authority / tenant source | Input → output / next step | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Intake | `ShipmentRequest` | public request form | `POST /api/shipment-request` | request creation policy; organization resolution | transport/cargo intent → tracking code | legacy commercial intake |
| Request detail | `ShipmentRequest` | `/expert/requests/:id` | `/api/expert/requests/<int:id>` | authenticated tenant membership plus admin/assignee | request, quote, CRM context, request documents, legacy tracking → create shipment | legacy numeric expert route; canonical request identity not integrated |
| Customer | internal `Customer` link | request CRM section | `/api/crm/shipment-requests/<int:id>/customer-link` | tenant membership and role | link/create bounded customer context | operationally usable; CRM otherwise on hold |
| Project | `Project` | shipment source card; project configuration/unit page | selectors and `/api/v2/projects/<public_id>/...` | membership-derived organization | optional project selection → project configuration/units | canonical but poorly linked |
| Shipment | `OperationalShipment` | list/new/detail | `/api/operational-shipments...` | `operational_shipment.*`, membership-derived organization | accepted quote/direct command → opaque shipment detail | canonical |
| Cargo | `CargoCatalogItem` → `ShipmentCargoItem` | admin cargo catalog; shipment detail | `/api/internal/cargo-catalog...`, shipment cargo endpoints | tenant-scoped catalog and authorized shipment parent | catalog/manual snapshot → quantity/UOM and reverse usage | canonical |
| Execution | `ExecutionUnit` | project unit page; shipment execution section | `/api/v2/projects/.../execution-units`, shipment execution endpoints | tenant project/shipment parent and execution permissions | unit/event/milestone commands → timeline/progress | canonical, fragmented navigation |
| Tracking | `ShipmentTransportUnit/Update` and `OperationalEvent` | request tracking tab and project/shipment execution views | expert tracking API and v2 event APIs | tenant request/project parents | location/update → two independent histories | overlapping legacy/canonical paths |
| Location | `LogisticsPoint` bridge plus free text/checkpoint snapshots | request tracking selector; cargo usage/current checkpoints | tracking selector and execution projections | tenant organization; legacy bridge per ADR-035 | governed point or explicit free text → display snapshot | usable locally; no single shipment authority |
| Documents | request-owned `CaseDocumentFile`; shipment-owned readiness | request documents tab; shipment readiness section | case documents and v2 readiness APIs | authorized request/shipment parent; exact file version | upload → associate/assess/readiness | canonical, independent per shipment |
| External references | governed types and owner-specific value tables | none at baseline | internal shipment/unit list/create/transition/search | authorized owner and membership-derived organization | B/L, AWB, CMR → history/evidence/search | backend-only at baseline |
| Overview | projections across shipment detail, cargo usage and execution pages | shipment detail | multiple APIs | per-domain read permissions | fragmented operational answer | incomplete |

## Findings

### E2E-001 — Request lineage ends before existing operational shipments

- **AREA:** Request → Project → Shipment
- **USER SCENARIO:** From the gearbox request, find all operational shipments already created from it.
- **CURRENT BEHAVIOR:** Request detail can create a shipment from an accepted quote but does not list or link existing shipments or their project/status.
- **EXPECTED OPERATIONAL BEHAVIOR:** Existing tenant-fenced shipments are visible and enterable from request context.
- **EVIDENCE:** `src/pages/RequestDetail.tsx` has only the creation link; `GET /api/operational-shipments` already supports tenant-scoped `request_id` filtering.
- **ROOT CAUSE:** Existing list projection is not consumed by request detail.
- **SEVERITY:** P1
- **ARCHITECTURE IMPACT:** None; read-only projection over ADR-002/017/034 lineage.
- **SECURITY/TENANT IMPACT:** Existing shipment endpoint derives organization from membership.
- **PROPOSED ACTION:** Add a request-context shipment list/link using the existing filtered API.
- **IMPLEMENT NOW?:** YES
- **REQUIRES ADR?:** NO
- **TEST STRATEGY:** Frontend behavior test verifies filtered call and opaque shipment links.

### E2E-002 — Shipment external references have no expert UI

- **AREA:** External Operational References
- **USER SCENARIO:** View, add, supersede, cancel, and understand B/L, AWB, or CMR history on a shipment.
- **CURRENT BEHAVIOR:** ADR-039 APIs and tenant/adversarial tests exist, but `src` contains no external-reference API client or operational screen.
- **EXPECTED OPERATIONAL BEHAVIOR:** Authorized users can perform the certified V1 workflow in shipment context and see lifecycle/history/evidence.
- **EVIDENCE:** `backend/routes/operations.py` exposes list/create/transition/search; frontend search finds no consumer.
- **ROOT CAUSE:** Backend slice was not integrated into the frontend.
- **SEVERITY:** P1
- **ARCHITECTURE IMPACT:** None; exact ADR-039 V1 owner/types/lifecycle.
- **SECURITY/TENANT IMPACT:** Backend remains authoritative and non-enumerating; UI sends no organization identifier.
- **PROPOSED ACTION:** Add shipment external-reference client/component for the three certified types, optional exact request-file evidence, and lifecycle actions.
- **IMPLEMENT NOW?:** YES
- **REQUIRES ADR?:** NO
- **TEST STRATEGY:** Component behavior tests plus existing backend adversarial suite.

### E2E-003 — Cargo reverse traceability is not navigable

- **AREA:** Cargo
- **USER SCENARIO:** From `گیربکس` catalog usage, open each matching shipment.
- **CURRENT BEHAVIOR:** Shipment count, quantity/UOM, status, location and latest event are shown, but usage cards are not links.
- **EXPECTED OPERATIONAL BEHAVIOR:** Each result opens its opaque shipment route.
- **EVIDENCE:** `CargoCatalogAdminTab.tsx` renders `operational_shipment_public_id` data without `Link`.
- **ROOT CAUSE:** Missing bounded navigation binding.
- **SEVERITY:** P1
- **ARCHITECTURE IMPACT:** None.
- **SECURITY/TENANT IMPACT:** Destination shipment endpoint rechecks tenant authority.
- **PROPOSED ACTION:** Add opaque shipment link.
- **IMPLEMENT NOW?:** YES
- **REQUIRES ADR?:** NO
- **TEST STRATEGY:** Frontend cargo behavior assertion.

### E2E-004 — Project execution units are disconnected from shipment detail

- **AREA:** Execution / Tracking
- **USER SCENARIO:** From an operational shipment, inspect its project execution units/events.
- **CURRENT BEHAVIOR:** Shipment detail prints project opaque ID; project units live on a separate route with no link.
- **EXPECTED OPERATIONAL BEHAVIOR:** Project-backed shipments provide a clear navigation action.
- **EVIDENCE:** `OperationalShipmentDetail.tsx` renders plain `project_public_id`; `App.tsx` exposes `/operations/projects/:projectId/units`.
- **ROOT CAUSE:** Missing navigation link.
- **SEVERITY:** P1
- **ARCHITECTURE IMPACT:** None; no cargo allocation inference.
- **SECURITY/TENANT IMPACT:** Project/unit endpoints recheck tenant authority.
- **PROPOSED ACTION:** Link to the existing project execution-unit page.
- **IMPLEMENT NOW?:** YES
- **REQUIRES ADR?:** NO
- **TEST STRATEGY:** Shipment-detail behavior test.

### E2E-005 — Empty eligible-document state is a dead end

- **AREA:** Shipment Documents
- **USER SCENARIO:** A shipment requirement is missing and no eligible request file exists.
- **CURRENT BEHAVIOR:** Text says to upload in request documents, but provides no navigation.
- **EXPECTED OPERATIONAL BEHAVIOR:** A direct action opens the source request document tab/context.
- **EVIDENCE:** `DocumentReadinessSection.tsx` empty state is plain text; shipment graph already exposes source request ID.
- **ROOT CAUSE:** Missing source-context link.
- **SEVERITY:** P1
- **ARCHITECTURE IMPACT:** None; file ownership remains request-scoped.
- **SECURITY/TENANT IMPACT:** Request endpoint reauthorizes access.
- **PROPOSED ACTION:** Pass source request identity and render a request-document link.
- **IMPLEMENT NOW?:** YES, using the current compatible route; opaque-route cutover remains E2E-006.
- **REQUIRES ADR?:** NO
- **TEST STRATEGY:** Document component empty-state link test.

### E2E-006 — Opaque ShipmentRequest identity is not integrated into expert navigation

- **STATUS:** RESOLVED — authenticated expert, tracking, document, operational-shipment request filtering, and frontend navigation now prefer `ShipmentRequest.public_id`; authorized numeric aliases remain controlled compatibility paths.

- **AREA:** Identity / Request UX
- **USER SCENARIO:** Navigate to a request without exposing or substituting sequential IDs.
- **CURRENT BEHAVIOR:** UUIDv4 storage/resolution is integrated into expert detail, tracking, document, request-filtered shipment and frontend navigation. Legacy numeric expert/document aliases and existing-role CRM/admin routes remain documented compatibility debt.
- **EXPECTED OPERATIONAL BEHAVIOR:** Opaque identities are the authenticated public resource identity with a controlled compatibility period.
- **EVIDENCE:** ADR-038; `backend/routes/expert_console.py`; `backend/services/expert_request_detail_service.py`; `src/App.tsx`.
- **ROOT CAUSE:** Migration/model foundation was completed without route/client rollout.
- **SEVERITY:** P1
- **ARCHITECTURE IMPACT:** Existing Accepted ADR authorizes it, but the change spans many request-parented surfaces.
- **SECURITY/TENANT IMPACT:** Numeric enumeration risk is mitigated by tenant/assignee checks but conflicts with the opaque boundary.
- **PROPOSED ACTION:** Controlled additive opaque-route rollout across expert, document, tracking and bounded CRM request context, then retire numeric navigation after compatibility evidence.
- **IMPLEMENT NOW?:** COMPLETE
- **REQUIRES ADR?:** NO (ADR-038 already accepted)
- **TEST STRATEGY:** malformed/foreign/numeric substitution, inactive membership, route parity and frontend navigation tests.

### E2E-007 — No authoritative one-screen current location across tracking paths

- **DECISION STATUS:** RESOLVED FOR ADR-040 PHASES 1–2 — deterministic canonical unit/shipment reads, provenance, cache health, and Cargo traceability adoption are implemented. Public and legacy transition remains governed later-phase work.

- **AREA:** Current Status / Tracking
- **USER SCENARIO:** On shipment detail, answer “where is this shipment now?”
- **CURRENT BEHAVIOR:** Internal Cargo reverse usage consumes the canonical event-derived shipment projection with `UNAVAILABLE/SINGLE/COMMON/MULTIPLE`; legacy expert/public request tracking remains compatibility behavior pending later ADR-040 cohorts.
- **EXPECTED OPERATIONAL BEHAVIOR:** Clearly labeled latest known location and timestamp with named source/authority.
- **EVIDENCE:** ADR-040; `tracking_projection_service.py`; `cargo_service.py`; `test_tracking_projection.py`; `test_cargo_traceability.py`.
- **ROOT CAUSE:** Closed for the authorized internal/Cargo read slice. Certified lineage/cohort gates intentionally remain before public or legacy transition.
- **SEVERITY:** P1
- **ARCHITECTURE IMPACT:** DECISION COMPLETE under ADR-040; bounded implementation required.
- **SECURITY/TENANT IMPACT:** No breach found; risk is operational inconsistency.
- **PROPOSED ACTION:** Execute later ADR-040 phases only through controlled lineage, cohort, privacy, write-authority, and retirement gates.
- **IMPLEMENT NOW?:** COMPLETE FOR PHASES 1–2; LATER PHASES DEFERRED
- **REQUIRES ADR?:** SATISFIED — ADR-040 ACCEPTED
- **TEST STRATEGY:** conflicting legacy/canonical timestamps/locations, no-data, tenant and timezone cases.

### E2E-008 — First-use terminology remains mixed and exposes opaque/internal values

- **AREA:** Terminology / First Use
- **USER SCENARIO:** A Persian-speaking expert filters shipments and understands operational status/history.
- **CURRENT BEHAVIOR:** Filter labels are raw English property names; several detail cards use English sentences/status codes; project/request identifiers are printed without human labels; RTL/LTR treatment is inconsistent.
- **EXPECTED OPERATIONAL BEHAVIOR:** Previously governed terms are used consistently with codes/identities secondary and direction-safe.
- **EVIDENCE:** `OperationalShipments.tsx`, `OperationalShipmentDetail.tsx`, `ExecutionUnits.tsx`, cargo forms.
- **ROOT CAUSE:** Incremental domain slices retained engineering-facing labels.
- **SEVERITY:** P2
- **ARCHITECTURE IMPACT:** None.
- **SECURITY/TENANT IMPACT:** None beyond avoidable identity exposure.
- **PROPOSED ACTION:** Bounded localization/first-use pass after P1 navigation and identity work.
- **IMPLEMENT NOW?:** NO
- **REQUIRES ADR?:** NO
- **TEST STRATEGY:** terminology component tests and RTL viewport UAT.

## Counts at implementation gate

| Severity | Count |
| --- | ---: |
| P0 | 0 |
| P1 | 7 |
| P2 | 1 |
| P3 | 0 |
| **Total** | **8** |

No finding changes aggregate ownership, tenant authority, cargo/document ownership, assignment semantics, CRM authority, or canonical hierarchy. E2E-007 is explicitly stopped at the architecture gate. CRM remains **ON HOLD — NO EXPANSION**. Cotage, Warehouse Receipt, Registration Order, and Barfarabaran remain **DEFERRED / NOT IMPLEMENTED**.

## Pre-publish polish update (2026-08-21)

E2E-008 is resolved for the bounded release-polish scope. Shipment filters, core Cargo Catalog and Logistics Network controls, first-use explanations, ADR-040 location-state wording, identifier direction isolation, and external-reference guidance were localized or clarified. The evidence and reviewed-screen matrix are recorded in `FORWARDER-PRE-PUBLISH-UX-POLISH.md`.

No E2E item was reopened. No P0/P1 was discovered. Deep route/economics terminology and remaining bilingual compatibility controls are non-blocking P3 items in the following post-publish backlog.

## POST-PUBLISH BACKLOG

- ADR-040 later phases under the accepted controlled transition gates.
- CRM expansion/remediation; remains on hold.
- Cotage, Warehouse Receipt, Registration Order, and Barfarabaran.
- Numeric compatibility contraction after consumer/tenant evidence.
- Full deep-screen localization, advanced analytics, and optional UI enhancements.
