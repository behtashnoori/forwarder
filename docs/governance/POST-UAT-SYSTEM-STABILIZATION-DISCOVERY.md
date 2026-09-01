# Post-UAT System Stabilization Discovery

**Status:** discovery only — no runtime, migration, seed, configuration, or Production change.

**Evidence boundary.** This report distinguishes observed UAT evidence from code-derived behavior and test-proven behavior. It was produced on `stabilization/post-uat-system-review` from `9a362739eb64f2fd10b6bac4bb7d729984ce12c9`; no Production system, credentials, or data were accessed. The local assurance commit `8a14a75` is a separate descendant and was not merged or altered.

## A. Executive summary

The five UAT reports reveal gaps in the verification model more than a single common implementation cause. Existing tests are strong at tenant fencing, permission denial, bounded service behavior, and model invariants. They are weaker at *configured operational data*, *cross-role propagation over time*, and *the exact user-facing error contract*. A green focused suite is therefore not evidence that a staffed organization with a realistic reference-data catalog can complete a journey.

The primary stabilization order is: (S1) establish reference-data readiness contracts, (S2) make document-policy timing/snapshot behavior explicit and testable, (S3) expose and test catalog validation contracts, then (S4) reproduce and harden reporting with accumulated operational data. Cross-role golden journeys become the release gate, rather than a final manual click-through.

## B. Baseline and execution evidence

| Item | Evidence |
| --- | --- |
| Repository | `D:\Projects\webapp\15-forwarder\forwarder` |
| Canonical baseline | `9a362739eb64f2fd10b6bac4bb7d729984ce12c9` (`codex/pr-4a-dms-gate-repair`) |
| Discovery branch | `stabilization/post-uat-system-review`, created directly from the baseline |
| Starting worktree | clean |
| Separate assurance work | `8a14a756…` descends from the baseline by one test-only commit; preserved separately |
| Local focused discovery suite | `35 passed` — country/port/customs, organization document policy, cargo foundation, global-point adoption, logistics network, reporting fail-closed |

No claim in this report represents a Production observation beyond the five supplied UAT observations.

## C/D. UAT finding trace and root-cause status

### D1 — country/city reference data

* **Observed:** UAT reports a selectable country (for example Turkmenistan) with no available cities.
* **Reproduced:** **NEEDS VERIFICATION.** The UAT dataset was not accessed or copied locally.
* **Code-derived behavior:** `GET /api/locations/countries` returns every active `Country`; `GET /api/locations/international-cities?country_id=` independently returns active `InternationalCity` rows and returns `[]` when none exist (`backend/routes/locations.py`). There is no API contract that an active country must have an active city.
* **Root-cause status:** **PROVEN RISK; UAT instance root cause not proven.** `seed_international_data.py` is a legacy one-shot, all-or-nothing seed and its checked-in list contains China only. `Country` and `InternationalCity` are separate platform-scoped tables (`backend/models.py`). The governed global logistics-point catalog has Turkmenistan candidates, but its ADR explicitly says `InternationalCity` coverage is incomplete and is optional for global points (`docs/operational/adr/ADR-041-...`). That catalog cannot prove the UAT international-city rows exist.
* **Coverage gap:** `test_country_port_customs_domain.py` proves Country/Port/Customs domain constraints, not cardinality of active country → usable downstream locality, nor the form behavior for `[]`.
* **Similar-risk areas:** country with no city; active city with no usable transport/location type; active global point not adopted by an organization; active CargoType or UOM absent from a tenant’s UI options; country/city/port/customs conflation. Free-form international locality is **not proven** by this review; request fields and global-point `city_name` do not establish a public-form rule.

### D2 — management/admin dashboard statistics

* **Observed:** management/admin dashboard errors while statistics are retrieved.
* **Reproduced:** **NO — missing the UAT data/state and request/error record.**
* **Path:** `src/pages/AdminPanel.tsx` calls `fetchAdminDashboard`; `/api/admin/dashboard` requires `require_reporting_export_oversight`; `backend/services/admin_dashboard_service.py` queries `ShipmentRequest`, aggregates transport/status, UTC 24-hour/7-day windows, unassigned `new`/`pending`, and inner-joins origin `Province` for top provinces. The route catches every exception, logs it, and returns only a generic Persian 500 message.
* **Root-cause status:** **UNKNOWN.** The broad exception mask prevents the UI from distinguishing authorization, query/schema, unexpected null/type, or aggregate failure. Empty groups normally serialize as empty mappings/lists; that alone does not prove the observed 500. Tenant scoping is applied when `g.organization_context` exists; the route’s permission/context behavior must be reproduced with the actual management persona and accumulated records.
* **Coverage gap:** `test_adr043_reporting_fail_closed.py` proves fail-closed reporting authority, not realistic date/status/transport/province aggregation under an accumulated operational history or the frontend error classification.
* **Similar-risk areas:** assignment summary, overview, XLSX export, CRM dashboard and any `func.count`/grouped report paths. Classify them **SUSPECTED RISK**, not defects, until a fixture or stack trace reproduces them.

### D3 — document requirement configuration propagation

* **Observed:** an admin disables a document but an expert still sees it as active/optional/incomplete.
* **Reproduced:** **code-derived reproduction of the timing rule; UAT screen/state not reproduced.**
* **Root cause:** **PROVEN DESIGN/EXPECTATION MISMATCH for existing snapshots.** `OrganizationDocumentRequirement` accepts `DISABLED`; `effective_definitions` excludes disabled/inactive policies for future resolution (`backend/services/organization_document_policy_service.py`). `CaseDocumentRequirement` is explicitly immutable, and `initialize_requirements` does not revise an existing snapshot (`backend/services/case_document_service.py`). Operational shipment readiness separately materializes `OperationalDocumentRequirement` on command (`backend/services/document_readiness_service.py`). The policy documentation says edits affect later snapshot creation only (`docs/architecture/organization-document-policy.md`).
* **Meaning:** “disabled” means excluded from effective future policy, not retroactive deletion/hiding of case or shipment requirements. “optional” is a requirement level; “incomplete”/readiness belongs to the materialized runtime requirement and assessment/artifact state. Whether UAT intended a dynamic change is a product decision, not a defect conclusion.
* **Coverage gap:** existing policy tests intentionally certify immutable snapshots. They do not assert the admin-to-expert UX explanation, an existing-record policy-change scenario, or a transition/migration decision for previously materialized requirements.
* **Similar-risk areas:** project document overrides; global document-definition activation; global-point adoption then materialization; organization logistics points used by projects; catalog activation versus immutable shipment snapshots. These are **PROVEN RISKS** wherever a configuration is changed after a consumer snapshot exists.

### D4 — cargo/goods catalog creation validation

* **Observed:** creating a catalog item produces “invalid information”.
* **Reproduced:** **NO — exact UAT payload, role, and active master data are unavailable.**
* **Path:** `CargoCatalogAdminTab` submits all form strings and maps every rejected creation to the single generic message. `/api/internal/cargo-catalog` requires organization-admin context. `create_catalog` requires nonblank `immutable_code` (max 64), `fa_name` (max 160), and an active referenced CargoType; default UOM is optional but, if present, must be active (`backend/services/cargo_service.py`). Duplicate/constraint errors map to conflict; organization identity is server-derived.
* **Root-cause status:** **PROVEN observability/contract gap; input-specific root cause UNKNOWN.** The UI exposes `cargo_type_public_id` and `default_uom_public_id` as free-text inputs instead of controlled option selection, and hides the backend reason. This makes a missing/invalid/inactive reference indistinguishable from malformed code/name, duplicate, or version issue to UAT.
* **Smallest code-derived valid input:** an organization admin, an active CargoType public ID, a unique nonblank immutable code, and a nonblank Persian name; UOM omitted or an active UOM public ID. Exact runtime success remains **NEEDS VERIFICATION** against a local app fixture.
* **Coverage gap:** cargo tests prove service snapshots, tenant fencing, and invalid references with mocked/model fixtures. Frontend tests use successful mocked API responses; neither test asserts backend error-code-to-field feedback nor a create form with real active option data.
* **Similar-risk areas:** shipment cargo-line creation, aliases, logistics-point create/edit, document definitions, reference-data admin forms. **PROVEN RISK**: generic error masking; **SUSPECTED RISK**: further frontend/backend validation drift.

### D5 — Global Network versus Logistics Network

* **Proven meaning:** Global Network is the platform-owned catalog of reviewed real-world `GlobalLogisticsPoint` identities. Platform administration owns its lifecycle/verification. An organization can adopt an active, verified global point through `OrganizationGlobalLogisticsPointAdoption`; adoption is tenant-scoped metadata and is explicitly **not** an operational point, project, or tracking event.
* **Difference from Logistics Network:** Logistics Network is tenant-owned `LogisticsPoint` master data used operationally and may be manually created or materialized from one active adoption. Materialization creates the organization operational point; project associations then use those tenant points. The UI itself states this separation in `OrganizationGlobalNetworkTab.tsx`; `logistics_network_service.py` exposes `global_source` provenance.
* **Evidence:** `backend/global_logistics_point_models.py`, `backend/logistics_network_models.py`, `backend/services/global_logistics_point_adoption_service.py`, `backend/services/logistics_network_service.py`, `/api/admin/global-logistics-points*`, and `/api/admin/logistics-points*`.
* **UX/domain observation:** the underlying distinction is necessary and well bounded, but “Global Network” alone does not communicate “platform reference catalog requiring organizational adoption and optional materialization.” This is a **PROVEN UX comprehension risk**, not a request to rename in this mission.

## E. Why previous verification missed this

The prior suite proved isolated fixtures and authorization boundaries. It did not define release input contracts for the supplied organization’s reference catalog; did not execute an admin change followed by an expert view of both fresh and historical records; did not preserve a realistic reporting history; and used mocked successful frontend API flows where D4 needs contract/error assertions. The previous end-to-end UAT document also records transaction-scoped factories and no permanent reference seed data, so it cannot certify a populated organization’s master-data readiness.

## F. Business journeys and cross-role dependencies

| Journey | Actors and flow | Key dependencies | Current evidence / missing evidence |
| --- | --- | --- | --- |
| Customer request → expert | customer request → hostname/tenant resolution → referral/assignment → expert visibility | Country/city selections, tenant ownership, membership, referral rules | tenant/referral suites strong; country-with-zero-city and real selected master data missing |
| Expert → operations | expert reviews request → project/operational shipment → cargo → logistics point → events/documents | active cargo type/UOM/catalog; tenant point; lifecycle permission | operational/cargo/logistics tests strong; combined real-data journey missing |
| Admin configuration → operation | org admin policy/adoption/configuration → effective resolution/materialization → expert UI | policy precedence, snapshot timing, active status | policy isolation/snapshot tests strong; cross-role fresh-vs-existing UI journey missing |
| Operations → intelligence | request/shipment state and timestamps → aggregates → admin dashboard/report | reporting authority, status values, province, UTC clock, tenant context | authorization proven; accumulated-data aggregation journey missing |
| Platform reference → org use | platform global point → verified/active → org adoption → materialized logistics point → project use | platform authority, adoption lifecycle, tenant ownership | adoption/materialization tests strong; UAT terminology and end-to-end selection missing |

### Role × capability model

| Role/context | Capability | Downstream consumer |
| --- | --- | --- |
| Customer/public | submit transport request | tenant resolver, referral, assigned expert |
| Expert / business expert | review assigned work; operational shipment/cargo/document work | lifecycle, tracking, readiness, management aggregates |
| Organization admin | organization document policy, cargo catalog, tenant logistics points, global-point adoption | expert and project workflows |
| Reporting oversight/admin | dashboard and report retrieval | management decision-making |
| Platform admin | document vocabulary, global logistics catalog and point types | organization admin adoption/policy |

Critical dependency chains are: admin policy → future snapshot/materialization → expert readiness; platform global point → tenant adoption → tenant logistics point → project; customer request → tenant/referral → expert; expert operational state → dashboard aggregate.

## G/I. Configuration propagation map

| Configuration | Owner/scope | Effective timing | Consumer | Gap/risk |
| --- | --- | --- | --- | --- |
| Organization document requirement | organization admin / tenant | dynamic for future resolution; runtime records are immutable snapshots | case/shipment readiness, expert UI | timing is technically defined but not explained/proven across roles |
| Project document override | organization/project | overrides effective policy before snapshot/materialization | project/shipment readiness | same snapshot-versus-current-policy risk |
| Document definition active/default | platform | compatibility fallback or explicit tenant policy | org policy and future snapshots | platform and tenant modes need golden journey |
| Global-point adoption | organization / tenant | active adoption is prerequisite to materialization | tenant logistics network | adoption is not operational availability until materialized |
| Logistics point active state | organization / tenant | current master data, project association | expert/project operations | stale point/project selection needs coverage |
| Cargo catalog active state | organization / tenant | current selection; shipment line is snapshot | expert shipment work | reference availability and snapshot behavior need end-to-end coverage |

No in-process caching was found in the reviewed policy/adoption services. Browser state/cache behavior was not proven and remains **NEEDS VERIFICATION**.

## H/J. Reference/master-data map

| Dataset | Authority/scope | Downstream dependency | Integrity condition missing from current release proof |
| --- | --- | --- | --- |
| Country / InternationalCity | platform shared | international request location | active country must be assessed for usable localities, not merely existence |
| Province/County/City, IranPort, Customs | governed shared | domestic/entry location | hierarchy/port constraints are tested; operational completeness is not |
| Global logistics points/types | platform catalog | organization adoption/materialization | active/verified point vs organization usable point |
| Tenant LogisticsPoint | organization | project and operations | point’s active state and association timing |
| CargoType / UOM | governed master | cargo catalog and shipment lines | active entries available to UI and valid public IDs |
| Document definitions | platform vocabulary | org policy and snapshots | policy mode and snapshot timing |

The principal orphan pattern is selectable parent/reference A with zero usable child/consumer B. D1 demonstrates this class.

## K. Major state/lifecycle map

* Requests use at least `new` and `pending` in dashboard logic; their full transition contract was not re-derived here.
* Global points: `DRAFT → ACTIVE → DEPRECATED`; verification includes `UNVERIFIED`, `REVIEWED`, `VERIFIED`.
* Adoptions: `ACTIVE`/`INACTIVE`; only active verified global points can be adopted and active adoption can materialize.
* Organization document levels: `REQUIRED`, `OPTIONAL`, `CONDITIONAL`, `DISABLED`; runtime requirements/readiness are separate snapshots.
* Cargo catalog items: active/inactive; shipment cargo is immutable snapshot data.

The common propagation risk is changing a master/configuration lifecycle after a downstream object has captured a snapshot.

## L/M/N. Coverage assessment and similar-risk register

**Existing strengths:** authorization and tenant fencing, explicit platform/organization authority, model constraints, catalog/adoption lifecycle, immutable traceability, and focused service tests.

**Missing coverage:** release-level data readiness; real frontend→API validation/error contract; role A mutation→role B observation at both fresh and historical state; dashboard/report aggregation on representative histories; empty/partial reference-data UI behavior.

| Classification | Finding |
| --- | --- |
| Proven defect | None beyond supplied UAT observations can be declared without their data/request evidence. |
| Proven risk | active country can return zero active international cities; policy changes do not rewrite snapshots; generic cargo create UI error hides backend cause; global adoption and logistics operational point are distinct stages. |
| Suspected risk | dashboard/report aggregate endpoints share broad generic 500 handling; other admin forms may have validation drift; inactive/adopted/materialized reference states may be confused in UI. |
| Unknown | exact D2 stack trace and exact D4 payload/master-data failure; whether D1 is missing data, inactive rows, or a UI filter in the UAT organization. |

## O/P. Prioritized stabilization backlog

1. **S1 — Reference-data readiness contract.** Define usable-location completeness by supported journey, inventory active country→city/location cardinality, decide the zero-city UX, and add non-production catalog certification. DoD: release evidence lists supported countries and usable downstream choices; UI/API behavior for empty state is intentional and tested.
2. **S2 — Configuration propagation and snapshot UX.** Decide the product contract for disabled requirements on new versus existing cases/shipments; make timing visible to admin and expert; add an admin-change→expert fresh/historical golden journey. DoD: no ambiguity between disabled, optional, readiness, and immutable historical requirement.
3. **S3 — Cargo contract and field-level validation.** Capture the UAT request/response locally, make active CargoType/UOM selectable rather than opaque identifiers where applicable, preserve structured backend error codes, and test minimal valid/invalid/duplicate/inactive cases. DoD: every rejection maps to a usable field/action and a real API integration test.
4. **S4 — Reporting integrity.** Reproduce D2 with a tenant-scoped accumulated-history fixture; trace authorization/context and add structured safe diagnostics; cover null/empty/time-bound/status/province/transport aggregates and frontend recovery. DoD: dashboard, overview, assignment summary, and XLSX share a tested reporting contract.
5. **S5 — Cross-role golden journeys.** Implement a reusable role × capability × data/configuration/lifecycle fixture matrix. DoD: release run contains customer→expert, admin→expert, expert→dashboard, and platform reference→organization use paths.
6. **S6 — Release evidence gate.** Require manifest-backed reference-data certification, golden-journey results, schema/migration status, and expected-error checks before controlled release. DoD: no release PASS based solely on unit/API counts.

**Recommended first fix slice:** **S1**, because downstream valid input and operational selection cannot be reliably tested while reference-data usability is undefined. It must be a decision-and-certification slice first, not an unreviewed data import.

## Q. Proposed future release gate

Every release must execute a compact, versioned matrix across **role × capability × data state × configuration state × lifecycle × tenant × expected error**. At minimum:

1. Customer request with supported locations → exact tenant → referral/assignment → same-tenant expert visibility; include missing/empty reference state.
2. Organization admin changes document policy → new and existing expert-visible records → correct explanation/readiness behavior.
3. Organization admin creates catalog item using active references → expert creates shipment cargo → snapshot remains traceable after catalog change.
4. Expert creates/changes operational records across representative statuses and UTC boundaries → authorized management dashboard, overview, and XLSX agree.
5. Platform creates/activates a verified global point → organization adopts → materializes tenant point → project operationally uses it; inactive/deprecated transitions fail safely.

The gate must retain the actual fixture/catalog versions and request/response evidence. A test that only proves a mocked happy path does not satisfy a cross-role release journey.

## R. Production changes

**NONE.**

