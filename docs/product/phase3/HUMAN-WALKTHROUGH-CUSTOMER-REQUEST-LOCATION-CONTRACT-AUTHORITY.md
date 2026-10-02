# Customer Request location contract — mission authority

Finding: `HW_GEO_009`  
Entry candidate: `8f4b4c47f142ce7293588e48b1108b59ec2fdfc4`  
Date: 2026-10-02

## Product Authority Record

| Field | Authorized value |
| --- | --- |
| `AUTHORIZED_PRODUCT_CHANGES` | Customer Request international endpoints may use an active canonical Country plus either a known canonical City, a separately typed active airport/port reference, or a required customer-declared place description. The declared option must remain visibly unresolved through Customer, Expert, Quote/request context and accepted-request handoff. |
| `DELEGATED_TECHNICAL_CHOICES` | Reuse the existing Country, Admin1, City, InternationalCity and ShipmentRequest storage; extend safe public reference reads; use the existing city and international text/id columns with explicit API typing; preserve N-1 payload reads; add focused API, PostgreSQL, frontend, browser and architecture guards. |
| `PROTECTED_OUT_OF_SCOPE_BEHAVIOR` | Domestic Request semantics; Organization Logistics Network; Direct Operation; Route Reference; Delivery; precise operational endpoint, route, Route Basis and ETA requirements; Request/Quote/Shipment separation; tenant and role boundaries; all historical rows and snapshots; the preserved walkthrough database and draft. No canonical or Organization Location is created from a customer declaration. |
| `DECISIONS_NEEDED` | None. The approved input contract and existing fields are sufficient; no migration is authorized or required. |
| `APPROVING_OWNER_OR_AUTHORITY` | Product Owner issuing the HW_GEO_009 mission. |
| `APPROVAL_REFERENCE` | Supplied “FORWARDER — CUSTOMER REQUEST LOCATION CONTRACT”, finding HW_GEO_009, §§1–15. |

`JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY`: `FWD-J01`, `FWD-J02`, `FWD-J03`
and the entry/handoff boundary of `FWD-J04`; focused integrated impact is
`FWD-IPJ-01`. Anonymous intake, authenticated Customer Request, Customer detail,
Expert list/detail, Quote context and accepted-request creation require
re-qualification. Direct Operation, Route Reference, Delivery and Organization
Location are regression surfaces only.

LPAF reference impact is `NONE`: the frozen v2.7 framework is unchanged. Project
reference impact is `UPDATE_REQUIRED`: the finding register, API contract,
consumer inventory and qualification evidence must bind to the final candidate.

The mission is Level B under LPAF capability routing. The Product Owner supplies
the required product authority; implementation and verification remain within
the Sol route. Human Product Walkthrough remains `IN_PROGRESS` and
`RELEASE_READY=NO`.

## Initial diagnosis

Both `/` anonymous intake and `/customer/requests/new` authenticated intake use
`LocationForm`. Country eligibility was corrected in HW_GEO_008, but each
international endpoint still bound its only required place control to paginated
`/api/international-cities`. That collection contains typed physical references
and legacy city-like rows; it is not the canonical City source used by the
qualified geography consumers. A country with no `InternationalCity` row could
therefore be selected but could not satisfy Request validation.

The current `ShipmentRequest` fields are sufficient without a schema change:
`*_country_id` stores the canonical Country; `*_city_id` stores a selected
canonical City; `*_international_city_id` stores a typed physical reference;
and `*_city_international` stores the immutable display/declaration snapshot.
Exactly one endpoint mode is accepted on new writes. Historical combinations
remain readable and are not rewritten.

The pre-fix reproducer is retained by the consumer coverage guard: the old
`LocationForm` would fail because its only selectable place source was
`InternationalLocationSelector`/`/api/international-cities`. The corrected form
must contain the explicit three-kind request payload and canonical city reader,
and must not recreate the legacy numeric `*_international_city_id` write.

## Consumer inventory

| Route / role | Component and reader | Accepted identity and precision | Persistence / downstream |
| --- | --- | --- | --- |
| `/` / anonymous | `LocationForm`, `CustomerRequestLocationSelector`; public Country, canonical City and typed international-reference reads | Country plus canonical City, airport/port, or required declaration; both endpoints required for international Request | Explicit typed Request payload; confirmation before public submission |
| `/customer/requests/new` / Customer | Same shared Request form and readers | Same demand-level contract as anonymous intake | `ShipmentRequest`; Customer workspace detail |
| Domestic Request branches / anonymous or Customer | Existing province/county/city controls | Existing domestic precision and meaning | Existing Request columns and projections; unchanged |
| `/customer/requests/:public_id` / entitled Customer | `CustomerPortalRequestDetail`; customer Request API | Read-only canonical/physical/declaration classification | Shows selected reference or unresolved customer declaration |
| `/expert/requests` and `/expert/requests/:public_id` / assigned Expert | `ExpertConsole`, `RequestDetail`; scoped Expert Request APIs | Read-only demand identity and resolution state | Quote/request review; declaration remains unresolved |
| Quote and accepted-request handoff / Expert | Existing Request route projection and `NewOperation` | Demand context only; unresolved declaration is flagged | Exact operational endpoints remain required before Shipment creation |
| `/operations/new` / authorized operator | `CanonicalLocationPicker`; canonical geography and entitled organization points | Precise operational canonical/facility identity | Existing operational Shipment command; unchanged |
| Operational route authoring and actual / authorized operator | `RouteAuthoringSection`, `RouteActualSection` | Governed operational route endpoint identities | Existing Route Leg and actual traversal facts; unchanged |
| Route Reference / authorized operator | `RouteReferenceLocationPicker`, `CanonicalLocationPicker` | Precise canonical/organization location identity | Existing versioned Route Reference; unchanged |
| Structured Delivery / authorized operator | `DeliverySection`, `CanonicalLocationPicker` | Precise canonical/organization location identity | Existing Delivery fact; unchanged |
| Organization Location creation / authorized operator | `CanonicalLocationPicker` and logistics-network APIs | Canonical City plus governed LogisticsPoint type | Explicit tenant-owned LogisticsPoint creation only; never invoked by Request |
| Admin reference maintenance / platform admin | Existing Locations admin surface and privileged APIs | Governed reference administration | Privileged catalog writes; not exposed to public/Customer readers |

All in-scope consumers above were discovered and verified. Customer/public
reads expose only safe canonical names and typed public references; no private
organization configuration, membership, capability or provenance is added.

## Implemented request contract

New Customer Request writes use exactly one explicit endpoint kind:

- `canonical_city` stores a country-compatible active canonical `City` identity
  and its immutable display snapshot;
- `physical_reference` stores a country-compatible active airport or port
  identity, never a legacy city-like row;
- `declared` stores the trimmed, length-limited customer text with the canonical
  Country and no canonical, Organization Location or operational endpoint ID.

The server rejects missing declarations, cross-country IDs, unknown IDs and
wrong entity types. Country changes clear dependent form state. Read projections
retain historical legacy references without relabeling or rewriting them.
Customer review uses `محل اعلام‌شده مشتری؛ نیازمند بررسی کارشناس`; persisted
Customer/Expert views use
`محل اعلام‌شده مشتری؛ هنوز به مکان مرجع متصل نیست`. An accepted Quote carrying
an unresolved declaration is flagged and still fails the existing precise
operational-endpoint guard until an Expert supplies valid endpoints.

## Required state-case matrix

| Case | Qualification proof | Result |
| --- | --- | --- |
| 1. Authenticated international Request | Browser: canonical Beijing to Bandar Abbas submission, Customer detail and assigned Expert detail | PASS |
| 2. Anonymous intake | Browser: distinct public route loads all 249 countries and canonical city/declaration controls without private data | PASS |
| 3. China to Iran | Browser/API: origin and destination selected and persisted independently | PASS |
| 4. Iran city coverage | Component/service/PostgreSQL fixture: Isfahan, Tehran and Bandar Abbas come from canonical City | PASS |
| 5. Typed physical references | Browser/service: Imam Khomeini Airport remains an airport and never substitutes a City | PASS |
| 6. No deeper data | Browser/PostgreSQL: Brazil plus `Santos customer warehouse` submits and remains explicitly unresolved | PASS |
| 7. Place absent in supported country | Service/component declaration path stores text without a fake canonical identity | PASS |
| 8. Missing declaration | Component and server validation require text and return `DECLARED_PLACE_REQUIRED` | PASS |
| 9. Country change | Browser/component tests clear the incompatible city or physical reference before submission | PASS |
| 10. Three legacy records | PostgreSQL fixture keeps IRBND, IRTHR and IRIKA readable while canonical paging remains complete | PASS |
| 11. Search and paging | Independent PostgreSQL SOR comparison plus normalized exact-match/alias/offset tests | PASS |
| 12. Customer/Expert handoff | Browser covers canonical and declared requests across both details with exact labels | PASS |
| 13. Operational guards | Accepted-Quote selector flags resolution; creation without precise endpoints returns `LOCATION_MAPPING_REQUIRED` and creates no Shipment | PASS |
| 14. API validation | Direct cross-country, unknown and wrong-type writes are rejected server-side | PASS |
| 15. Operational regression | Full backend/frontend suites protect Direct Operation, Route Reference, Delivery and Organization Location consumers | PASS |
| 16. HW_GEO_008 preserved | Country contract tests prove 249-country completeness, separate depth metadata and consumer coverage | PASS |

## Qualification binding

`PRODUCT_SHA=b9f6e9951acb99b01e52c161632a5610425f593a`

The owned PostgreSQL 18 run used fresh loopback databases and passed the
Customer Request contract, independent HW_GEO_008 contract and operational
selector guards: 8 passed. The exact-candidate browser run used a fresh database
migrated from zero to `20261017_document_type_ownership`: 3 passed. The full
frontend run passed 107 files / 509 tests. The full backend run passed 1,688
tests with 129 environment-gated skips. Production build, TypeScript, lint,
structure, Python compilation and `git diff --check` passed.

The first full backend run retained an honest failure history: it exposed an
N-1 v1.9.1 payload using `{type, id}` in `origin_location`. The explicit contract
discriminator was narrowed to the new `kind` key, the failed legacy test plus
focused contract tests passed, and the complete backend suite then passed on the
corrected product SHA.

Status: `QUALIFIED — READY FOR CONTROLLED INTEGRATION`.
