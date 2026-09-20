# PDR-019 — Post-D2 Product Reference Contract

- **Status:** ACCEPTED — reference phase only
- **Date:** 2026-09-20
- **Decision authority:** Product Owner direction recorded by the Post-D2 decision amendments
- **Rigor:** LPAF Level B
- **Implementation authority:** None. Runtime code, tests, migrations, catalog apply, deployment, and Production access require later bounded slices.
- **Related authority:** PDR-013, PDR-017, ADR-002, ADR-004, ADR-006, ADR-007, ADR-008, ADR-016, ADR-022, ADR-047, the Canonical Business Object Catalog, FDD-001, and FDM-001.

## 1. Supersession and scope

This record is a **NEW ACCEPTED DECISION** and a **SCOPE CHANGE** for the remaining Post-D2 product path. It preserves historical evidence rather than rewriting it.

It accepts the decisions in `post-d2-product-decisions-amendment-v2-20260920.md` and supersedes only the Minimal Mandatory Cargo decision in `post-d2-product-decisions-amendment-20260920.md`. It does not supersede PDR-013's Cargo master-data, `ShipmentCargoItem`, snapshot, search, or allocation decisions.

## 2. Optional multi-Cargo Request

```text
REQUEST_CARGO_REQUIRED_FOR_SUBMISSION=NO
REQUEST_CARGO_MIN_ITEMS=0
MANDATORY_CARGO_POLICY=DEFERRED
MULTI_CARGO_REQUEST_DIRECTION=APPROVED
```

A `ShipmentRequest` may contain `0..N RequestCargoItems`. `RequestCargoItem` is commercial/request information and is not `ShipmentCargoItem`. No Cargo field is required for Request submission, including type/name/description, quantity, unit, weight, volume, dimensions, packaging, value, brand/model, dangerous-goods data, refrigerated data, or another characteristic.

Omitting Request Cargo and submitting an empty Request Cargo collection are valid. Historical Requests with no Cargo remain valid. No scalar legacy Cargo value is silently promoted into a structured item, and no guessed item, unit, quantity, classification, or allocation is permitted. A later product decision may make selected fields mandatory, but that policy is currently deferred.

Operational planning owns Shipment creation, Shipment splitting, `ShipmentCargoItem` snapshots and allocation, Execution Units, vehicles/containers, and Route Legs. Customer intake owns none of those structures.

## 3. Dual-calendar presentation

Approved presentation is `Gregorian (Jalali)` for selected user-facing business dates. Both values render one authoritative stored date/time fact. Storage, ordering, filtering, comparison, Local Date versus Instant semantics, timezone ownership, `occurred_at` versus `recorded_at`, and API authority remain governed by ADR-016.

No duplicate Jalali persistence, parallel timestamp, date backfill, or calendar-derived sorting key is approved. Surface adoption must be explicit in a later slice and must preserve the underlying fact.

## 4. Combined Transport Request intent

A Request-level transport intent may include one scalar catalog choice displayed in Persian as `حمل ترکیبی`. It expresses Customer intent only.

```text
REQUEST_TRANSPORT_INTENT != ACTUAL_ROUTE_TRANSPORT
```

The Request does not enumerate mode permutations or author an ordered route. Actual execution sequence remains the ordered `RouteLeg.transport_mode` facts owned by an Operational Shipment's Route Plan. A combined Request may later be executed through any governed sequence, including repeated modes.

The later Build slice must reconcile the existing request `TransportMethod` catalog idempotently, preserve historical values and deterministic Rail presentation, and round-trip the combined scalar through existing Request summaries. It must not add ordered-intent JSON or reinterpret route-only values such as transfer/handling as Request intent.

## 5. Quote communication

`Quotation` owns the official commercial offer and lifecycle. The Customer response contract is:

- approve (`accepted` compatibility value);
- needs discussion with one short Customer message (`discussion` additive value);
- reject (`declined` compatibility value).

The discussion message is supporting communication/history attached to one official Quote. It is not a counter-offer, bargaining engine, price mutation, acceptance, rejection, or automatic Request-state transition. If terms change, an authorized Transport Expert issues a new/revised official Quote; older Quotes and their responses remain history. Only an accepted Quote is eligible for Operational Shipment creation.

A later API/state slice must preserve current replay, conflict, expiry, locking, tracking-code, tenant, authorization, unread, and audit contracts; require a bounded non-empty message for `discussion`; reject the message for `accepted`/`declined`; and expose bounded Quote history. Notification activation is not part of this flow.

## 6. Documents decision gate

The approved functional intent is preserved:

- multiple files;
- append without replacing successful siblings;
- targeted replacement with prior version/history preserved;
- retry only known failed files.

The actor/entitlement matrix is not approved. Implementation is:

```text
BLOCKED_PENDING_DOCUMENT_ACTOR_DECISION
```

The Product Owner must decide, per action, whether Customer, owning Transport Expert, and same-organization Admin/Manager may discover requirements, upload, append, replace, view history, retry failed files, and view/download versions. Until then PDR-008, PDR-009, ADR-020, FDD-001 document definitions, the document user journey, and API authorization remain unresolved for this product slice.

## 7. Control Tower and Notifications

D1/D2 Control Tower behavior remains implemented. Its 100-authorized-Shipment complete-population ceiling is a `PRE_RELEASE_SCALABILITY_GAP`, not a business limit. Before RC, either launch-tenant evidence must prove the ceiling retains acceptable headroom or a separately designed server-side search/windowing architecture must replace it. Partial client-side truncation is not acceptable.

C1/C2 Notification infrastructure remains approved and dormant. No current reference may imply business-event mapping, recipient/channel policy, provider, SMS, Email, Webhook, worker/scheduler, API, UI, or actual delivery activation.

## 8. Capability owner and System of Record map

| Capability | Business/architecture owner | System of Record | Required boundary |
| --- | --- | --- | --- |
| Requests / Request Cargo | Commercial/Request | `ShipmentRequest` plus future `RequestCargoItem` children | `0..N`; optional for submission; no operational allocation |
| Shipments / Operational Cargo | Operations | `OperationalShipment` plus `ShipmentCargoItem` snapshots/allocation | Created after commercial intent; Customer does not author execution structure |
| Documents | Document policy plus owning business scope | `DocumentDefinition`/requirements, immutable file versions, exact contextual associations | Actor/action entitlement unresolved; Build blocked |
| Quotes | Pricing/Commercial | `Quotation` (`ExpertQuote` compatibility model) and per-Quote response/history | Revised terms require a new official Quote |
| Tracking | Operations/Visibility | canonical execution event/history projections | Request intent and actual route remain distinct |
| Control Tower | Operations/Attention | governed read model over operational facts/work items | Projection is not Shipment truth; 100 ceiling is a scaling gap |
| Notifications | Notification boundary | dormant `NotificationAction`/`NotificationAttempt` lifecycle | No source-event activation or delivery policy |
| Calendar presentation | Presentation, constrained by Time Architecture | authoritative existing Local Date or Instant | Gregorian and Jalali are two renderings of one fact |

Physical modular extraction is not authorized by this map.

## 9. API, state, schema, and compatibility impact

| Decision | Target contract | Schema/migration forecast | Compatibility contract | Build gate |
| --- | --- | --- | --- | --- |
| Optional Request Cargo | Request create/update accepts absent or empty Cargo collection; no Cargo field blocks submission | Additive structured model may be needed; no migration required or authorized now | Historical Cargo-less Requests remain valid; no guessed backfill | Owner/SOR, API shape, lineage, PostgreSQL and journey acceptance before code |
| Dual Calendar | Presentation-only `Gregorian (Jalali)` | None | Same Local Date/Instant and ordering/filtering | Surface ledger, timezone tests, browser RTL before Freeze |
| Combined Transport | One scalar Request intent; actual Route Legs separate | No schema expected; controlled catalog reconciliation later | Historical Request values unchanged/readable | Catalog identity/apply plan and Request-summary round trip |
| Quote communication | `accepted | discussion | declined`; short message only for `discussion` | One later additive/constraint migration expected | Existing accepted/declined rows and official Quote history preserved | API/state/error/auth/concurrency and migration design before code |
| Documents | Functional behavior approved, actor/action authority unknown | No current schema migration expected for known behavior | Existing versions/history preserved | `BLOCKED_PENDING_DOCUMENT_ACTOR_DECISION` |
| Control Tower | Same governed read model; scale beyond current ceiling | No query-time schema assumed | Current fail-closed ceiling preserved until replacement/launch proof | `PRE_RELEASE_SCALABILITY_GAP` before RC |
| Notifications | Dormant lifecycle only | None for activation because activation is not approved | C1/C2 remains empty/dormant unless separately authorized | Activation deferred |

## 10. Reference impact

```text
REFERENCE_IMPACT=UPDATE_REQUIRED
REFERENCE_IMPACT_STATUS=CLOSED_FOR_REFERENCE_PHASE
```
The closure applies to the Forwarder project references changed by the Post-D2 reconciliation. It does not claim runtime implementation, test completion, migration readiness, catalog application, browser acceptance, Freeze, RC, deployment, or Production change.
