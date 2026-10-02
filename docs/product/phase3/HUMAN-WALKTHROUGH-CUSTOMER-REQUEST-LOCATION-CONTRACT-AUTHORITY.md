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

Status: `DIAGNOSED — IMPLEMENTATION PENDING`.
