# Post-D2 Product Decisions Amendment V2 — Optional Cargo — 2026-09-20

Scope: product-decision evidence only. This record changes no runtime product code, test, migration, database, authorization behavior, release artifact, Production system, or LPAF framework file.

The verified starting point was the clean branch `codex/product-decisions-amendment-cargo-expert` at `e919cd5bd07544627feaa656377167e205f1d899`, whose parent is `d4268e9854f4d31234a98a94c04c37c874a751b5`. Alembic exposed exactly one head: `20260923_notification_lifecycle`.

```text
SUPERSEDES_CARGO_DECISION_FROM =
post-d2-product-decisions-amendment-20260920.md
```

This record does not make the entire older amendment obsolete. It supersedes only that amendment's Minimal Mandatory Cargo decision. Its Responsible Expert ownership contract and all other unaffected approved product decisions remain in force.

## A. Superseded Cargo Decision

**OLD:** minimal mandatory Cargo. A Customer Request required at least one Cargo Item, with description/name, quantity, and unit mandatory.

**NEW:** Cargo is optional for Request submission. The structural multi-Cargo direction is retained: a Customer Request may contain zero or more Request Cargo Items.

No Cargo characteristic is mandatory for submission at this time. In particular, submission must not be blocked because any of the following is absent: cargo type, name or description; quantity; unit; weight; volume; dimensions; packaging; value; brand or model; dangerous-goods information; refrigerated information; or any other Cargo characteristic.

No new required Cargo validation is approved by this decision. The design must remain capable of supporting a future product decision that makes selected Cargo information mandatory, but no such mandatory policy exists now.

## B. Current Cargo Contract

```text
REQUEST_CARGO_REQUIRED_FOR_SUBMISSION=NO
REQUEST_CARGO_MIN_ITEMS=0
MULTI_CARGO_REQUEST_DIRECTION=APPROVED
MANDATORY_CARGO_POLICY=DEFERRED
```

A Request may structurally contain `0..N RequestCargoItems`. Historical and future Requests without Cargo remain valid for submission under the current product contract.

## C. Request / Operational Boundary

`RequestCargoItem` belongs to the Request/commercial context and is not an Operational Shipment or an operational cargo allocation.

```text
Customer Request
  -> zero or more Request Cargo Items

Operational planning
  -> Operational Shipment creation
  -> shipment splitting
  -> Shipment Cargo snapshots/allocation
  -> Execution Units
  -> vehicles/containers
  -> Route Legs
```

When Request Cargo Items are present, they describe commercial/request information. Operations later owns Operational Shipment creation, the number of Shipments, Cargo snapshots and allocation, Execution Units, vehicles or containers, and Route Legs. The Customer does not determine those operational structures during Request intake.

Future implementation must preserve the conceptual distinction between `RequestCargoItem` and `ShipmentCargoItem` and must not invalidate historical Requests that contain no Cargo.

## D. Responsible Expert Ownership Contract

The previously approved ownership decision is preserved unchanged:

```text
ONE_TRANSPORT_EXPERT_PER_SHIPMENT=YES
EXPERT_REASSIGNMENT_WORKFLOW_APPROVED=NO
```

The organization model consists of one Admin/Manager and any required number of Transport Experts. Each Shipment belongs to one Transport Expert. The owning Expert may access that Shipment. Another Expert in the same organization does not gain access merely through organization membership. An actor from another tenant is denied, and an inactive or revoked actor is denied.

No former-Expert state, reassigned-Expert state, replacement-Expert state, ownership-transfer workflow, or Expert reassignment workflow is an approved target product state.

## E. Other Approved Product Decisions

The following decisions remain approved and are not superseded by this Cargo-only change:

- **Dual Calendar:** user-facing governed dates use `Gregorian (Jalali)` for one underlying authoritative date/time fact; no duplicate persisted dates are introduced.
- **Combined Transport:** Request-level intent may include `حمل ترکیبی`; the actual transport sequence remains owned by Route Legs.
- **Quote Communication:** the Customer may approve, request discussion with a short message, or reject; when commercial terms change, the Expert may issue a new or revised official Quote.
- **Documents:** multi-file, append, explicit replacement with preserved history, and retry of failed files remain the approved functional direction.
- **Notifications:** the approved C1/C2 foundation and lifecycle remain preserved and dormant; activation is deferred.
- **Control Tower:** D1/D2 remain preserved. The 100-Shipment ceiling remains a known scalability gap, not a newly approved business limit.

## F. LPAF Reference Impact

This evidence records the current product decision but does not itself satisfy authoritative Forwarder reference reconciliation. The affected project PDRs, ADRs, Decision Index, FDD, FDM, canonical catalogs, API/state contracts, migration and compatibility contracts, authorization contracts, acceptance references, and user journeys still require the separately governed LPAF reference-impact phase.

The historical amendment remains evidence of the decision sequence. Reference reconciliation must preserve that history and express the Cargo change as a scoped supersession rather than silently rewriting the earlier decision.

```text
REFERENCE_IMPACT=UPDATE_REQUIRED
REFERENCE_IMPACT_STATUS=OPEN_PENDING_FORWARDER_REFERENCE_RECONCILIATION
```

## G. Verdict

PASS — SUPERSEDING CARGO PRODUCT DECISION RECORDED
