# Optional Multi-Cargo Request — LPAF-Governed Implementation Design

**Status:** Ready for a bounded Build phase

**Design date:** 2026-09-20

**Canonical parent:** `31f3f503b5fc8d6e89bb9a60066a1ca3fa676a76`

**Governing baseline:** LPAF v2.2, with the v2.3 Product Integration / `REFERENCE_IMPACT` gate applied as the project strong default

**Artifact class:** Level B combined Mission Contract and implementation design

**REFERENCE_IMPACT:** `NONE`

**CARGO_SCHEMA_DECISION:** `ADDITIVE_MIGRATION_REQUIRED`

**Expected migration:** Yes — design only in this artifact; no migration is created here

This document is the single Mission Contract and implementation-design artifact for this capability. LPAF v2.2 permits the Level B evidence to be combined, and the repository has no separate mandatory Mission Contract format. A second governance document would duplicate this contract.

## A. LPAF Mission Contract

### A.1 Mission and outcome

**Mission:** design the smallest safe implementation that lets a Customer submit a `ShipmentRequest` with zero, one, or multiple optional `RequestCargoItem` records without conflating commercial Request facts with operational Shipment cargo.

**Outcome:** a Build team can implement the accepted PDR-019 direction from this contract without making another product decision, weakening Request authorization, inventing historical cargo, changing operational allocation, or silently changing numeric meaning.

The resulting product contract is:

```text
REQUEST_CARGO_REQUIRED_FOR_SUBMISSION=NO
REQUEST_CARGO_MIN_ITEMS=0
MULTI_CARGO_REQUEST_DIRECTION=APPROVED
MANDATORY_CARGO_POLICY=DEFERRED
```

### A.2 Problem

The accepted product model permits `ShipmentRequest 1 -> 0..N RequestCargoItem`, but the current Request runtime persists only nullable single-value cargo scalars. Those scalars cannot preserve item identity, order, or a repeated quantity/UOM pairing. Operational `ShipmentCargoItem` and the organization cargo catalog exist, but neither is owned by the Commercial / Request capability and neither may be repurposed as Customer Request state.

### A.3 Scope

In scope for the later Build:

- additive Request-owned cargo-item persistence;
- create-time Customer Request payload and response behavior for 0/1/N items;
- ordered Request cargo read projections for authorized Customer, assigned Expert, and authorized same-organization administration;
- an optional cargo-item editor embedded in the existing Request form and read-only presentation in existing Request detail surfaces;
- governed Cargo Type and Unit of Measure selection, exact decimal handling, validation, tenant fencing, and historical compatibility;
- implementation tests, PostgreSQL migration proof, and browser journey evidence described by this contract.

Out of scope:

- making Cargo or any named Cargo field mandatory;
- a standalone Cargo-management application;
- Customer Request edit, item add/remove/reorder after submission, because no such Request edit lifecycle currently exists;
- operational Shipment creation, splitting, allocation, Execution Unit, vehicle/container, or Route Leg decisions;
- copying Request cargo into `ShipmentCargoItem`, allocation logic, or hidden synchronization;
- exposing the organization `CargoCatalogItem` master to public/customer APIs;
- backfilling or reinterpreting legacy scalar cargo;
- changing quote calculation, Control Tower behavior, operational cargo, tracking disclosure, or production data;
- physical module extraction or broad repository refactoring.

### A.4 Actors, roles, entitlements, and tenant/data scope

| Actor | Permitted capability | Governing scope |
|---|---|---|
| Customer | Create optional cargo as part of the existing public Request intake; read it only through an existing Request view that proves ownership/context | The parent Request; never a free-standing child lookup |
| Assigned Transport Expert | Read cargo for a Request the existing assignment policy authorizes | Active, exact membership; same tenant; assigned Request |
| Same-org Organization Admin | Read cargo only when the existing `request.read` capability and membership rules authorize the parent | Active, exact membership and same tenant |
| Same-org Manager label | No authority merely from the legacy label; access exists only if canonical capability/assignment policy independently grants it | Same parent Request policy as every other actor |
| Other Customer | No access | Must not enumerate or address cargo children |
| Other/unassigned Expert | No access merely from role or same organization | Existing parent Request denial applies |
| Other tenant | No access and no existence disclosure | Parent-derived tenant fence |
| Inactive/revoked/ambiguous actor | No access | Existing fail-closed membership policy |
| Platform Admin | No implicit tenant work access | Existing tenant-work boundary |

The child carries no independent authorization surface. Authorization is evaluated on `ShipmentRequest`; cargo is loaded only after the parent is authorized.

### A.5 Capability, state, and data ownership

- **Capability owner — Request Cargo:** Commercial / Request.
- **System of Record — Request Cargo:** `ShipmentRequest` plus the proposed `RequestCargoItem` child relation.
- **State owner:** the existing Request creation and Request read services; an item has no independent lifecycle in this slice.
- **Data owner — Request cargo facts:** Commercial / Request on behalf of the submitting Customer.
- **Capability owner — Operational Cargo:** Operations.
- **System of Record — Operational Cargo:** `OperationalShipment` plus `ShipmentCargoItem`.
- **Capability/data owner — Cargo Catalog:** the existing catalog/reference-data capability: global governed `CargoType` and `UnitOfMeasure`, and organization-scoped internal `CargoCatalogItem` master data.
- **Upstream:** public Customer Request intake, organization resolution, governed Cargo Type/UOM reference data.
- **Downstream:** commercial Request review, quote workflow, and later explicit operational planning. Downstream consumers do not acquire ownership of Request cargo.

### A.6 Module boundary and public contract

The implementation remains inside the existing Request route/service/model/UI boundary. It may reference Cargo Type and UOM by stable public identity, but it must not write operational Cargo state or expose the internal organization catalog. The public contract changes additively: `cargo_items` is optional on Request creation and appears only in authorized Request projections defined below. Existing keys retain their meanings.

### A.7 Constraints and quality attributes

- Optional means zero items is a first-class valid result.
- An existing item must be structurally meaningful, but no particular cargo field is required by name.
- Request and operational cargo remain separate aggregates and separate systems of record.
- Tenant isolation and non-enumerability take precedence over child-resource convenience.
- Quantity is exact decimal data, never binary floating-point in the new contract and never silently rounded.
- Historical evidence is preserved as recorded; no guessed migration is allowed.
- Create is atomic: either the Request and all supplied items persist, or none do.
- Ordered reads are deterministic and stable across reloads.
- The new surface is additive and backward compatible for existing clients.

### A.8 Facts, assumptions, unknowns, and human decisions

Verified facts at the canonical parent:

- the Golden worktree was clean and local/remote ahead-behind was `0/0` before branching;
- the canonical head was the reconciliation commit `31f3f503b5fc8d6e89bb9a60066a1ca3fa676a76`;
- Alembic had exactly one head, `20260923_notification_lifecycle`;
- the current Request write path has no customer edit/update route;
- the current Request has legacy nullable scalar cargo fields;
- operational shipment cargo already has a separate exact-decimal child model;
- Customer intake is public and organization-scoped by the existing hostname/context resolution;
- assigned-work authorization is enforced on parent Requests for expert/admin reads.

Implementation assumptions bounded by accepted references:

- a non-empty item can be established by any one meaningful fact: a Cargo Type, a nonblank description, or a complete quantity/UOM pair;
- Cargo Type and UOM are global governed reference data safe for a minimal active-reference Customer projection; organization `CargoCatalogItem` is not;
- input order is the Customer's intended presentation order.

There is no unresolved decision blocking the bounded Build. Customer editing after submission, organization-catalog selection, and operational handoff execution are explicitly deferred capabilities, not gaps in this create/read slice. Any request to add them reopens the relevant governance gates.

### A.9 Evidence and qualification standard

Qualification requires all of the following in the later Build:

- focused backend and frontend contract tests;
- authorization and negative-authorization tests using the parent Request policy;
- PostgreSQL N-to-N+1 migration, constraint, precision, downgrade-refusal, re-upgrade, data-preservation, and single-head proof;
- regression tests for legacy Request reads, quote, operational cargo, Control Tower, and tracking;
- browser evidence for the Customer 0/1/N create-and-return journey;
- a clean diff proving no unintended operational allocation or public tracking expansion.

### A.10 Definition of done

The capability is done only when the schema/API/UI behavior in this contract is implemented, all acceptance scenarios in section P pass, the browser journey in section M is evidenced, PostgreSQL proof passes, the migration graph remains single-head, and no stop condition in section R is present.

## B. Authoritative references

This design is derived from, and does not override:

- LPAF v2.2 and the Agent Entry Protocol;
- LPAF v2.3 Product Integration / `REFERENCE_IMPACT` gate as the project strong default;
- PDR-019 Post-D2 Product Reference Contract, including the accepted optional multi-cargo Request direction;
- PDR-013 Cargo Data Foundation, especially governed UOM, exact quantity, catalog/snapshot separation, public projection limits, and no guessed backfill;
- ADR-002 Request/Operation separation;
- ADR-022 Cargo catalog versus operational snapshot separation;
- ADR-047 only where it protects fixed Shipment ownership and prohibits Request assignment from mutating operational shipment state;
- the reconciled FDD Request Cargo entries, FDM `RequestCargoItem` concept, capability catalog/owner map, decision index, architecture baseline, and S6 optional multi-cargo journey;
- `docs/operational/evidence/lpaf-project-reference-reconciliation-20260920.md`.

The references agree on the requested direction. No conflict was found that would require a stop.

## C. Reference impact

```text
REFERENCE_IMPACT = NONE
```

Rationale: PDR-019 and its reconciled FDD/FDM/catalog/decision-index entries already establish optional `0..N RequestCargoItem`, Commercial / Request ownership, and separation from operational cargo. This document resolves the implementation shape inside that accepted truth. It does not alter user outcomes, authority, ownership, lifecycle policy, public product intent, or operational allocation. The document itself is implementation evidence, not a new governing product reference.

If Build discovers that a named Cargo field must be mandatory, that Customer catalog selection is required, that post-submit editing is required, or that Request cargo must drive Shipment allocation automatically, `REFERENCE_IMPACT` becomes `UPDATE_REQUIRED` and work must stop for reconciliation.

## D. Current Cargo implementation inventory

| Area | Canonical implementation at parent | Design consequence |
|---|---|---|
| `ShipmentRequest` persistence | Nullable scalar `cargo_description`, `cargo_weight`, `cargo_volume`, `cargo_value`, and `special_instructions` | Can represent at most one loose set of facts; retain for compatibility |
| Legacy DB checks | Nullable weight/volume must be positive when present; value must be nonnegative | Do not modify or reinterpret |
| Public Request create | `POST /api/shipment-request`; resolves organization context and atomically creates Request, logs, document requirements, and referral assignment | Extend this transaction; do not introduce a separate Cargo app |
| Current Cargo input | Optional top-level scalar values; tolerant float parsing can reduce invalid input to `None` | New items use strict decimal-string validation; legacy behavior remains isolated |
| Request update | No Customer Request cargo or general edit route exists | D/E update operations are not available in this slice |
| Customer Request read | Existing customer workflow resolves a Request in customer context; cargo items do not exist | Add ordered projection only after parent authorization |
| Expert Request read | Detail exposes a scalar `cargo` object; list/search uses scalar description/summary behavior | Preserve `cargo`; add `cargo_items` to detail and lean count flags to list |
| Admin Request read | Existing admin Request list/detail surfaces; no multi-item projection | Add only through authorized parent reads |
| Public tracking | Exposes legacy scalar cargo through its current lookup behavior | Do not add `cargo_items`; avoid unreviewed disclosure expansion |
| Quote workflow | Quote belongs to Request and does not copy cargo | No quote model or calculation change |
| Operational conversion | Accepted quote creates `OperationalShipment`; it does not create shipment cargo | No automatic cargo copy in this slice |
| `ShipmentCargoItem` | Operational child with stable identity, shipment line order, exact positive quantity, required governed UOM and Cargo Type, immutable snapshots, version/audit | Remains unchanged and cannot be reused for Request data |
| `CargoCatalogItem` | Organization-scoped internal master referencing governed types/default UOM | Not a transaction row and not exposed to Customer intake |
| `CargoType` / `UnitOfMeasure` | Governed, stable, active/versioned reference data; UOM includes measurement dimension and bilingual display data | Reference by public identity; reject free-text UOM |
| Numeric presentation | Operational cargo serializes exact decimals as strings; UI formatting trims display-only trailing zeros | Reuse the semantic convention without rounding stored/input values |

## E. Owner / SOR boundaries

```text
Customer input
    -> ShipmentRequest [Commercial / Request SOR]
        -> 0..N RequestCargoItem [Commercial / Request SOR]

Explicit future planner action (not this Build)
    -> OperationalShipment [Operations SOR]
        -> 0..N ShipmentCargoItem [Operations snapshot/allocation SOR]
```

`RequestCargoItem` records Customer-supplied commercial intent/evidence. `ShipmentCargoItem` records an operational snapshot suitable for planning and execution. The latter has stricter required facts because operational execution has different invariants. A Request item is never an allocation instruction and does not choose shipment count, shipment line, execution unit, vehicle/container, or route leg.

## F. RequestCargoItem domain model

### F.1 Aggregate rules

- A `ShipmentRequest` has zero or more items.
- Items are created atomically with the Request in this slice.
- Items are ordered by a server-assigned one-based `position` derived from payload order.
- Items have opaque public identities generated by the server; database IDs are never external contract identifiers.
- Item access and tenant scope are inherited exclusively through the parent Request.
- No field is mandatory for Request submission because the entire collection may be absent or empty.
- If an item object exists, it must contain at least one meaningful fact:
  - a valid Cargo Type; or
  - a nonblank description; or
  - a complete positive quantity plus governed UOM pair.
- Quantity and UOM are a pair: both absent or both supplied. This prevents an uninterpretable number or unit without quantity.
- Cargo Type and UOM must be active when the item is created. Later deactivation does not make historical items unreadable.

The any-of rule is a structural row invariant, not a new mandatory cargo field and not a mandatory-Cargo policy. `{}` or an object containing only whitespace/null values is rejected; omission or `[]` remains valid.

### F.2 Proposed persistence shape

Table: `request_cargo_item`

| Column | Type | Null | Contract |
|---|---|---:|---|
| `id` | `BIGINT` | no | Internal primary key |
| `public_id` | string UUID representation | no | Unique, opaque, server-generated external identity |
| `shipment_request_id` | `BIGINT` | no | FK to `shipment_request.id`, `ON DELETE RESTRICT` |
| `position` | integer | no | One-based deterministic order within parent |
| `cargo_type_id` | `BIGINT` | yes | FK to `cargo_type.id`, `ON DELETE RESTRICT` |
| `description` | text | yes | Trimmed; application maximum 2,000 characters |
| `quantity` | `NUMERIC(18,6)` | yes | Exact positive quantity; never float |
| `uom_id` | `BIGINT` | yes | FK to `unit_of_measure.id`, `ON DELETE RESTRICT` |
| `created_at` | timezone-aware timestamp | no | Server creation time |

Deliberately absent in this slice: organization ID, catalog-item FK, operational shipment FK, allocation fields, edit version, soft-delete state, and operational snapshots. Tenant scope is unambiguous through the required parent; adding an independently filterable organization column would create two possible authorities.

### F.3 Constraints and indexes

- unique `public_id`;
- unique `(shipment_request_id, position)`;
- check `position >= 1`;
- check description is null or nonblank after trimming;
- check quantity is null or greater than zero;
- check quantity/UOM pairing: both null or both nonnull;
- check structural meaning: Cargo Type is present, or description is present, or the quantity/UOM pair is present;
- index `shipment_request_id` for ordered parent loading;
- restrictive FKs for parent, Cargo Type, and UOM to preserve evidence.

The database enforces shape; application validation additionally enforces active references, length, input grammar, precision, and friendly indexed field errors.

### F.4 Quantity contract

- JSON input is a canonical non-exponent decimal string, not a JSON float. Its lexical form is `^(?:0|[1-9][0-9]*)(?:\.[0-9]{1,6})?$`; the positive-value rule then rejects zero.
- Maximum precision is 18 digits and maximum scale is 6.
- A value outside the precision/scale contract is rejected; it is not rounded or truncated.
- Positive values only; zero and negative values are invalid.
- Persistence uses `NUMERIC(18,6)`.
- JSON output is a decimal string preserving numeric significance within the stored scale contract.
- UI display may trim insignificant trailing zeros using the existing quantity formatter. That formatting never changes the transmitted or stored value.
- UOM is selected by opaque public identity from the governed catalog; free-text units and implicit conversions are forbidden.

## G. Request vs Shipment Cargo lineage

The current Build creates no operational lineage column and performs no copy. The future handoff contract is:

- an explicit authorized planning command, not Request submission or generic Shipment creation, chooses whether and how Request intent becomes operational cargo;
- one `RequestCargoItem` may source zero, one, or many `ShipmentCargoItem` snapshots, allowing operational splits;
- one `ShipmentCargoItem` may identify at most one source Request item; operational consolidation from several Request items requires an explicit future lineage design rather than a misleading single source;
- a future nullable `source_request_cargo_item_id` on `ShipmentCargoItem`, or a dedicated lineage relation if consolidation is approved, must be separately designed and migrated;
- the planner supplies any operationally required facts that were optional at Request time;
- copied values become operational snapshots. Later operational edits never mutate Request cargo, and Request data never silently resynchronizes an operational line;
- no bidirectional synchronization, inferred allocation, or guessed field completion is permitted.

## H. Schema decision

### Option A — existing schema represents 0..N safely

**Rejected.** Nullable Request scalars cannot represent repeated item identity/order, a per-item quantity/UOM pair, or deterministic lineage. Encoding an array into text/JSON or overloading scalar weight/volume/value would discard governed reference integrity and historical meaning.

### Option B — additive `RequestCargoItem`

**Selected.** A Request-owned child relation is the smallest persistence model aligned with PDR-019, the FDM, aggregate ownership, authorization through the parent, historical compatibility, and future one-to-many operational lineage.

### Option C — reuse another canonical relation

**Rejected.** `ShipmentCargoItem` belongs to Operations and carries operationally mandatory snapshot invariants. `CargoCatalogItem` is organization master data, not Customer transaction evidence. Reusing either would violate owner/SOR boundaries and could turn Customer input into operational allocation or internal catalog mutation.

```text
CARGO_SCHEMA_DECISION = ADDITIVE_MIGRATION_REQUIRED
```

## I. Historical compatibility

- All existing Requests with no cargo remain valid and readable.
- Existing nullable scalar columns remain in place and keep their current database checks and API meanings.
- Scalar fields become compatibility-only for existing clients and historical records; the new UI stops writing them except that `special_instructions` remains Request-level under its current meaning.
- No scalar record is backfilled into `RequestCargoItem`, even if it looks complete.
- No `RequestCargoItem` is projected back into scalar weight, volume, value, or description.
- If a legacy client supplies scalars and a new client payload supplies `cargo_items` in the same Request, both are stored independently and shown as separate representations. The system does not deduplicate, merge, or claim lineage between them.
- Authorized details expose `cargo_items` and the existing legacy `cargo`/`legacy_cargo` block separately. UI labels legacy data as such when it is present.
- Scalar search, report, export, public tracking, and operational behavior remain unchanged. Multi-item search/reporting is deferred unless separately scoped.
- Removing the scalar columns or translating legacy floats into exact quantities requires its own evidence-backed compatibility decision and is not part of this capability.

## J. API contract

### J.1 Create Request

Existing endpoint: `POST /api/shipment-request`.

The new optional key is additive:

```json
{
  "cargo_items": [
    {
      "description": "Medical devices",
      "cargo_type_public_id": "2a5e15ce-50f2-4b35-ae71-0f80cb554f80",
      "quantity": "12.500000",
      "uom_public_id": "ace39a51-4b84-48cb-a22c-38bb6da53a2d"
    }
  ]
}
```

Rules:

- omitted `cargo_items` and `"cargo_items": []` both mean zero items and are valid;
- `"cargo_items": null`, a non-array value, an empty object item, unknown item keys, and client-supplied `public_id` or `position` are invalid;
- each item accepts optional `description`, `cargo_type_public_id`, `quantity`, and `uom_public_id`, subject to the structural rule in F.1;
- description is Unicode text trimmed at the boundary; empty-after-trim becomes absent and cannot alone make a valid item;
- quantity is accepted only as a canonical decimal string; JSON numbers are rejected to prevent transport/runtime rounding ambiguity;
- referenced public IDs must exist and be active at create time;
- all items are validated before persistence; any error rolls back the entire Request create, while the UI retains every draft row locally;
- array order assigns `position` values `1..N`;
- the existing request-body and transaction protections remain in force; this slice does not invent a lower product-facing item cap that is absent from the approved `0..N` contract.

Zero-item example:

```json
{
  "cargo_items": []
}
```

Multiple-item example:

```json
{
  "cargo_items": [
    {"description": "Two boxed pumps"},
    {
      "cargo_type_public_id": "2a5e15ce-50f2-4b35-ae71-0f80cb554f80",
      "quantity": "3.25",
      "uom_public_id": "ace39a51-4b84-48cb-a22c-38bb6da53a2d"
    }
  ]
}
```

The existing success response retains `message`, Request `id`, and `tracking_code`, and adds the ordered `cargo_items` projection. The additive key does not change the success status or error envelope convention.

### J.2 Item projection

```json
{
  "public_id": "fb83cbf8-e745-4f87-b4d9-67e113b18b4b",
  "position": 1,
  "description": "Medical devices",
  "cargo_type": {
    "public_id": "2a5e15ce-50f2-4b35-ae71-0f80cb554f80",
    "code": "GENERAL_GOODS",
    "fa_name": "کالای عمومی",
    "en_name": "General goods"
  },
  "quantity": "12.500000",
  "uom": {
    "public_id": "ace39a51-4b84-48cb-a22c-38bb6da53a2d",
    "code": "KG",
    "fa_name": "کیلوگرم",
    "en_name": "Kilogram",
    "symbol": "kg",
    "measurement_dimension": "WEIGHT"
  }
}
```

Nullable nested objects are returned as `null`; missing optional values do not disappear inconsistently. Items are always ordered by `(position, id)` with the unique position constraint making `id` only a defensive tie-breaker.

### J.3 Reference options

Add a read-only public intake endpoint under the existing Request route boundary, proposed as `GET /api/request-cargo-options`. It returns only active Cargo Types and Units of Measure needed by the form, with the safe projection shown in J.2. It must not return `CargoCatalogItem`, aliases, internal database IDs, organization catalog state, audit fields, inactive entries, or operational cargo. Results are deterministically ordered. An empty reference list does not block a zero-item or description-only Request.

### J.4 Authorized reads

- Customer Request workflow/detail: add ordered `cargo_items`; keep scalar data in a separately named `legacy_cargo` representation where that endpoint does not already expose `cargo`.
- Expert Request detail: retain the current scalar `cargo` object and add ordered `cargo_items`.
- Expert/admin Request lists: add only `cargo_item_count` and `has_legacy_cargo`; avoid large child projections and do not expand multi-item search in this slice.
- Admin Request detail: add ordered `cargo_items` and retain legacy scalar representation.
- Public tracking: unchanged; it does not receive `cargo_items`.
- No `GET/PATCH/DELETE /request-cargo-item/{id}` endpoints are introduced.

### J.5 Update/remove behavior

- D — adding cargo to an existing Request: **not available**, because the current Request journey has no authorized Customer edit lifecycle.
- E — updating/removing/reordering a cargo item: **not available** for the same reason.

The UI must not imply that a submitted item is editable. A later edit capability requires explicit state eligibility, concurrency, audit, notification, quote-impact, authorization, and downstream-propagation decisions.

### J.6 Validation error

Use the current route's error envelope with a stable code and indexed field paths:

```json
{
  "message": "Request cargo is invalid.",
  "error": {
    "code": "REQUEST_CARGO_VALIDATION_FAILED",
    "message": "Request cargo is invalid.",
    "fields": [
      {
        "field": "cargo_items[1].quantity",
        "code": "DECIMAL_SCALE_EXCEEDED",
        "message": "Quantity may have at most 6 decimal places."
      }
    ]
  }
}
```

Return HTTP 422 for syntactically valid JSON that fails the cargo contract. Report all independently detectable cargo field errors in payload order. Stable field codes include `INVALID_TYPE`, `UNKNOWN_FIELD`, `ITEM_EMPTY`, `REFERENCE_NOT_FOUND`, `REFERENCE_INACTIVE`, `QUANTITY_UOM_PAIR_REQUIRED`, `DECIMAL_FORMAT_INVALID`, `DECIMAL_PRECISION_EXCEEDED`, `DECIMAL_SCALE_EXCEEDED`, `MUST_BE_POSITIVE`, and `MAX_LENGTH_EXCEEDED`.

## K. Authorization

Authorization is parent-first and fail-closed:

1. Resolve the Request through the existing organization/customer/assignment context.
2. Apply existing Request membership, tenant, capability, ownership, and assignment policy.
3. Only after authorization, load its cargo relation by parent ID.
4. Serialize opaque item identities; never accept internal IDs from a caller.

The public create endpoint preserves its existing hostname/organization boundary and permits only create-time nested items. The reference-options endpoint exposes a fixed allowlist of global active reference metadata and no tenant records. Expert/admin/customer reads do not query by child public ID. This removes a direct-object-reference path and makes Request authorization the single authority.

## L. Customer journey and reachability

| LPAF stage | Contract |
|---|---|
| ENTRY | Customer enters the existing Request intake; no separate Cargo application or prerequisite |
| DISCOVER | An optional Cargo section is visible in the existing Request form and clearly marked optional |
| USE | Customer may leave it empty, add one row, add more rows, reorder draft rows, or remove draft rows before submit |
| RESULT | One atomic submit persists the Request with 0/1/N ordered items and shows the same ordered representation in confirmation |
| LEAVE | Customer continues through the existing submission/confirmation and Request detail path |
| RETURN | Customer reopens the Request through the existing customer workflow/detail and sees the same immutable submitted representation |
| ERROR | Indexed errors remain adjacent to the affected draft row; unrelated valid draft rows and entered Request data remain in the browser |
| DENIAL | Existing Request ownership, assignment, membership, capability, and tenant rules deny access without child enumeration |
| DOWNSTREAM | Authorized commercial review can read Request cargo; quote and later operations remain separate and unchanged |

The optional section must be keyboard reachable, preserve logical focus when adding/removing rows, associate labels and errors to controls, announce validation summaries, support bilingual/RTL rendering already used by the Request form, and not hide zero-cargo submission behind a Cargo interaction.

## M. Browser acceptance journey

Browser UAT is specified here and must not be executed during Design.

For each of zero, one, and multiple item cases:

1. Start from the normal Customer Request entry route in the implementation candidate environment.
2. Reach the optional Cargo section through the existing form without a deep link.
3. For zero, leave Cargo untouched. For one, create one structurally valid item. For multiple, create at least three varied items and establish a recognizable order.
4. Submit the Request and assert the existing success/confirmation behavior.
5. Assert the confirmation representation: count, order, descriptions, reference labels, and exact displayed quantity meaning.
6. Leave the page through the normal Customer navigation.
7. Return through the existing Customer Request list/workflow and reopen the created Request.
8. Assert the same item identities/order/content as the create response and confirmation; assert zero remains an intentional empty state.
9. In a validation case, submit an empty row and an over-scale quantity; assert indexed errors, no Request creation, and preservation of the other draft rows.
10. In a denial case, attempt the parent Request from a different Customer/tenant context and assert the existing non-disclosing denial behavior.

Evidence must record role, tenant, environment, candidate commit, route, test data identifiers, assertions, and screenshots/log artifacts without exposing secrets or personal data.

## N. Migration design

The later Build creates one additive Alembic revision whose `down_revision` is the then-current canonical head; from this design baseline that is `20260923_notification_lifecycle`. The revision creates the table, FKs, checks, unique constraints, and parent index described in F. It does not alter, copy, or drop legacy scalar columns and inserts zero rows.

Upgrade behavior:

- create an empty `request_cargo_item` table and its constraints;
- preserve all existing Requests byte-for-byte in their existing columns;
- perform no synthetic backfill and no catalog inference;
- keep a single Alembic head.

Downgrade behavior:

- if the new table contains any row, fail closed with a clear operator message rather than discard Customer evidence;
- if it is empty, remove the new table and its objects;
- never translate new items into legacy scalars as a downgrade shortcut.

Mandatory PostgreSQL proof in Build:

- upgrade N to N+1 on a representative existing database;
- assert a single head and expected schema objects;
- prove zero-item historical Requests are unchanged;
- prove parent/order uniqueness, positive quantity, quantity/UOM pairing, structural-meaning checks, restrictive FKs, and exact precision/scale;
- prove empty-table downgrade succeeds;
- prove populated-table downgrade refuses without data loss;
- prove re-upgrade succeeds and legacy/request data is preserved.

## O. Negative authorization cases

Build tests must prove:

- another Customer cannot read items by guessing Request or item identity;
- an unassigned Expert in the same organization cannot obtain cargo through a list/detail shortcut;
- an actor in another tenant receives the existing non-disclosing parent denial;
- inactive, revoked, missing, or multiply ambiguous membership fails closed;
- a Manager role label alone does not grant Request access;
- Organization Admin without `request.read` is denied;
- Platform Admin receives no implicit tenant-work access;
- an item `public_id` cannot be used in a standalone route, query parameter, mutation, or cross-parent lookup;
- the public reference endpoint cannot enumerate organization cargo catalog or inactive/internal data;
- create cannot bind internal IDs, an item from another parent, an operational cargo row, or an organization catalog row;
- Customer input cannot set Shipment, allocation, execution-unit, vehicle/container, or route-leg fields.

## P. Acceptance and regression contract

### P.1 Required functional acceptance

1. Customer submits a Request with zero Cargo Items — **PASS**.
2. Customer submits a Request with one Cargo Item — **PASS**.
3. Customer submits a Request with multiple Cargo Items — **PASS**.
4. Server-generated item identity and input ordering round-trip deterministically — **PASS**.
5. Request reload preserves every item and exact quantity meaning — **PASS**.
6. Request summary/detail shows the designed count and ordered detail representation — **PASS**.
7. An assigned/authorized Expert sees allowed Request cargo — **PASS**.
8. Other tenant cannot read or enumerate child items — **PASS**.
9. No Customer-controlled Shipment or execution allocation is introduced — **PASS**.
10. Existing Requests without cargo and with legacy scalar cargo remain compatible — **PASS**.
11. Existing `ShipmentCargoItem` creation, invariants, serialization, and authorization remain intact — **PASS**.
12. Quote and Control Tower regressions remain intact — **PASS**.

### P.2 Additional contract cases

- omitted and empty collections are equivalent zero-item success cases;
- `null`, non-array, malformed, and meaningless empty rows fail with stable 422 errors;
- description-only, Cargo-Type-only, and complete quantity/UOM-only items are valid;
- quantity without UOM and UOM without quantity fail;
- decimal input never rounds, exponent notation is rejected, and output remains a string;
- inactive/unknown references fail create, while deactivated historical references remain readable;
- payload order remains contiguous after draft add/remove/reorder before submit;
- a mixed legacy-scalar plus `cargo_items` create preserves both independently;
- no legacy row is synthesized into an item and no item is synthesized into legacy scalars;
- public tracking response is unchanged;
- public reference options disclose no `CargoCatalogItem` or internal/audit fields;
- failed item validation persists neither the Request nor a partial item set;
- parent deletion behavior remains restrictive while child evidence exists.

## Q. Implementation file/scope plan

The later Build should remain a narrow vertical slice.

Backend:

- `backend/models.py`: add `RequestCargoItem` and the ordered `ShipmentRequest` relation near the Request aggregate; do not physically modularize now.
- `backend/services/shipment_service.py`: strict nested normalization/validation, reference resolution, atomic item creation, and ordered serialization while leaving legacy scalar handling intact.
- `backend/routes/shipment_request.py`: accept/return the additive field and expose the safe Request cargo reference-options projection.
- existing expert, customer workflow, and admin Request read services: add the projections/counts defined in J.4 after parent authorization.
- do not modify operational cargo models/services, quote semantics, allocation services, or public tracking for this capability.

Database:

- one new Alembic revision under `backend/migrations/versions/` implementing only section N; no backfill.

Frontend:

- `src/lib/api.ts`: typed optional input and ordered output contracts using decimal strings.
- `src/components/LocationForm.tsx` and its existing composition boundary: replace the new-customer scalar cargo editor with an optional repeatable item editor; keep Request-level special instructions.
- `src/components/RequestConfirmation.tsx` and existing Customer/Expert/Admin Request detail surfaces: render ordered structured items and clearly separated legacy data.
- reuse existing quantity display behavior and add only small Request-owned Cargo components where it prevents form/detail duplication.
- update established i18n resources for optional labels, row actions, empty state, and indexed errors.

Tests/evidence in Build:

- backend create/read/validation/authorization/regression contract tests;
- migration and PostgreSQL proof;
- frontend item-editor and rendering tests;
- the browser journey in M.

Shared hotspots are `backend/models.py`, Request services/routes, `src/lib/api.ts`, the Request form, Request confirmation/detail surfaces, and existing Cargo formatting/reference components. Changes in hotspots must stay owner-bounded; this design does not authorize broad refactoring.

## R. Stop conditions

Stop Build and return to governance if any of the following occurs:

- an authoritative reference conflicts with optional 0..N Request cargo or Commercial / Request ownership;
- implementation would require a named Cargo field or at least one Cargo item for submission;
- Customer post-submit edit/remove/reorder is required;
- the organization Cargo Catalog must become customer-visible or customer-editable;
- Request submission must create, allocate, merge, or split operational Shipment cargo;
- bidirectional Request/Shipment synchronization is proposed;
- parent Request authorization cannot fully fence child reads;
- exact quantity requires silent rounding, a float contract, or free-text UOM;
- historical scalar cargo must be inferred, backfilled, destroyed, or reinterpreted;
- migration cannot remain additive, single-head, zero-backfill, and loss-refusing on downgrade;
- public tracking or another public disclosure surface must expand;
- Build requires quote, Control Tower, operational ownership, or allocation changes outside the regression-only boundary.

Each condition requires an explicit decision/reference update or a newly governed mission before implementation continues.

## S. Verdict

READY — OPTIONAL MULTI-CARGO IMPLEMENTATION MAY BEGIN
