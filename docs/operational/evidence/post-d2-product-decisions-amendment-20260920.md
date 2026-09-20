# Post-D2 Product Decisions Amendment — Cargo and Expert Ownership — 2026-09-20

Scope: evidence-only product decision amendment and remaining-work planning. This report changes no runtime product file, test, migration, database, authorization behavior, release artifact, Production system, or canonical branch.

Baseline verification before this amendment passed: `integration/golden-controlled` was clean at `d4268e9854f4d31234a98a94c04c37c874a751b5`, fresh local/`github/integration/golden-controlled` ahead/behind was `0/0`, and Alembic exposed exactly one head, `20260923_notification_lifecycle`. A disposable in-memory schema comparison reported that head current and no pending upgrade operation. The amendment branch is `codex/product-decisions-amendment-cargo-expert`, created directly from that commit and not pushed.

## A. Purpose

This report amends `post-d2-product-gap-review-20260920.md`. It does not rewrite or delete that evidence record. Where the two records differ, this amendment is authoritative for the Cargo decision, Shipment ownership model, authorization-gate vocabulary, backlog classification, and remaining implementation order. All unaffected evidence and decisions in the original review remain in force.

## B. Superseded Cargo Decision

**OLD:** Mandatory Cargo = `DEFERRED`

The original review classified mandatory Cargo as `DEFERRED_BY_PRODUCT_DECISION` and treated the current optional scalar Cargo fields as sufficient for the release path.

**NEW:** Minimal Mandatory Cargo = `APPROVED / REQUIRED PRODUCT GAP`

Every Customer Request must contain at least one Cargo Item. This decision supersedes only the prior Cargo deferral; it does not activate Notification delivery or expand the other approved product slices.

## C. Final Cargo Contract

```text
REQUEST_MIN_CARGO_ITEMS = 1
CARGO_DESCRIPTION_REQUIRED = YES
CARGO_QUANTITY_REQUIRED = YES
CARGO_UNIT_REQUIRED = YES
OTHER_CARGO_FIELDS_REQUIRED = NO
```

A Request contains `1..N` Cargo Items. Each item requires only:

- description / cargo name;
- quantity;
- unit.

All other Cargo fields remain optional for the current release path, including approximate weight, volume, dimensions, packaging, declared/value information, brand/model, fragile status, refrigerated or temperature-sensitive information, dangerous-goods information, and additional notes. Existing optional fields must not become mandatory as a side effect of implementing the three-field minimum.

This is a request-completeness rule. It is not approval for catalog compulsion, detailed packing plans, containerization, route allocation, or a richer hazardous-goods workflow.

## D. Request / Shipment Boundary

The authoritative product boundary is:

```text
Customer Request
  -> one or more Cargo Items

Operational layer
  -> one or more Operational Shipments
  -> one or more Execution Units
```

A Request Cargo Item describes what the Customer asks to move. An Operational Shipment describes how operations organize that work. They are different product concepts and must not be collapsed into one record merely because the current operational schema already has shipment cargo lines.

During request intake the Customer does not decide:

- the number of Operational Shipments;
- how Request Cargo Items are split among Shipments;
- container count;
- vehicle count;
- Execution Unit allocation;
- route-leg allocation.

Those are later operational decisions. Future implementation must preserve traceability from Request Cargo Items into any later operational allocation without making the Customer author the operational plan.

## E. Responsible Expert Ownership Contract

```text
ONE_TRANSPORT_EXPERT_PER_SHIPMENT=YES
EXPERT_REASSIGNMENT_WORKFLOW_APPROVED=NO
```

Each company/organization has an Admin/Manager and may define any number of Transport Experts. Each Operational Shipment belongs to exactly one Transport Expert. There is no intended product workflow for changing, transferring, or replacing that Expert.

The authoritative visibility model is:

- an Admin/Manager of the same organization may see governed organization operations under existing tenant authorization;
- the Transport Expert who owns the Shipment may see it;
- another Transport Expert in the same organization does not gain access merely through organization membership;
- an actor from another organization/tenant does not gain access;
- an inactive or revoked actor does not gain access.

Historical Golden code or tests that transfer access when a Request assignment changes are evidence of historical behavior only. They do not approve an Expert reassignment feature and must not be used to introduce former-Expert state, transfer ownership, replacement-Expert flow, or a reassignment workflow into future product requirements.

## F. Other Approved Product Decisions

The following decisions from the Post-D2 review remain approved and unchanged.

### Dual Calendar

User-facing governed dates use `Gregorian date (Jalali date)`. Both render the same underlying date/time fact. There is no duplicate persisted date, and storage, sorting, filtering, comparison, instant-versus-local-date semantics, and occurred-versus-recorded semantics do not change.

### Combined Transport

Request-level transport may include `حمل ترکیبی` as a single multimodal Customer intent. Actual ordering remains the ordered Route Legs, for example `Road -> Rail -> Road` or `Road -> Sea -> Road -> Rail`. Request intake does not enumerate or persist every permutation.

### Quote Communication

The bounded two-way response model remains:

- Approve;
- Needs discussion plus one short message;
- Reject.

If discussion changes the price, the Expert may issue a new or revised official Quote through the governed quote journey. An endless counter-offer or bargaining engine is not approved.

### Documents

One logical document/requirement may contain multiple files. Users may append files and explicitly replace a selected file while preserving the previous version/history. Failed uploads retry at file level; successful sibling files remain successful. The approved scope is a simple version/history model, not an enterprise DMS.

### Notifications

Notification activation remains deferred. The approved C1/C2 foundation and lifecycle remain inactive. Event mapping, recipient policy, channel policy, provider selection, SMS/Email/Webhook, templates, quiet hours, and notification UI are not approved for implementation by this amendment.

## G. Backlog Impact

The original `PG-14` Cargo row is superseded as follows:

| Backlog item | Old status / priority | Amended status / priority | Amended phase |
| --- | --- | --- | --- |
| Minimal Mandatory Cargo + Multi-Cargo Request | `DEFERRED_BY_PRODUCT_DECISION` / `DEFERRED` | `REQUIRED_PRODUCT_GAP` / **P1** | First product implementation slice |

P1 follows the existing review rubric: P0 denotes release proof or safety gates, while P1 denotes approved product-completeness work that must close before the feature-complete candidate. Minimal Cargo is now essential to request completeness and supplies structured facts needed by pricing and later operations, so it must precede the remaining product slices. No evidence in this amendment establishes an immediate production safety failure that would reclassify it as P0.

The backlog count delta is:

```text
P0 = 6 (unchanged)
P1 = 6 (was 5)
P2 = 2 (unchanged)
DEFERRED = 1 (was 2; Notification activation remains deferred)
```

All other backlog items retain their prior status and priority except that `PG-01` authorization wording is replaced by Section H below. Cargo is no longer an allowable exception in A–L product acceptance or modularization entry criteria.

## H. Authorization Gate Amendment

The future Shipment Detail authorization verification must use this matrix:

| Actor | Expected result |
| --- | --- |
| Same-organization Admin/Manager with existing governed authority | Allowed according to existing tenant authorization |
| Owning Transport Expert | Allowed |
| Another Expert in the same organization | Denied unless another explicit existing authority independently permits access |
| Actor from another tenant | Denied |
| Inactive or revoked actor | Denied |

Future product requirements and acceptance gates must not be framed around former Expert, reassigned Expert, replacement Expert, transfer of ownership, or reassignment scenarios. The gate verifies fixed Shipment ownership plus existing Admin/Manager governance; it does not implement or imply a new authorization model.

No authorization code or test is changed by this amendment. Before product implementation proceeds, retain one narrow P0 evidence gate that characterizes Shipment Detail and Control Tower destination access against the matrix above. Any observed mismatch requires a separately scoped decision and implementation; it is not silently repaired here.

## I. Recommended Remaining Sequence

The proposed sequence is accepted with one explicit pre-slice verification retained from the original review:

0. **Shipment ownership authorization evidence gate** — verify the Section H matrix only; no reassignment scenarios and no planned runtime change.
1. **Minimal Mandatory Cargo + Multi-Cargo Request** — implement `1..N` Request Cargo Items with required description, quantity, and unit; preserve all other Cargo attributes as optional and keep the Request/Shipment boundary.
2. **Documents Completion** — deliver the already approved multi-file, append, explicit replacement, history, per-file retry, and metadata experience.
3. **Dual Calendar** — add the shared `Gregorian (Jalali)` presentation contract without persistence or sorting changes.
4. **Combined Transport** — add the scalar `حمل ترکیبی` Customer intent while keeping actual order in Route Legs.
5. **Quote Communication** — add Approve, Needs discussion plus short message, and Reject; use a new/revised official Quote for price changes.
6. **Control Tower Scaling** — remove the 100-Shipment ceiling, or formally retain the previously defined monitored launch constraint only if launch-volume evidence supports it.
7. **Modular Architecture Assessment** — freeze the completed product contracts and define module ownership and dependency rules.
8. **Staged Modularization** — perform behavior-neutral extractions in bounded stages with full regression evidence after each stage.
9. **Full UAT / RC / Release** — run owned-PostgreSQL migration qualification, role/mobile/RTL/two-timezone browser UAT, security/dependency and packaged-runtime gates, RC freeze, non-Production rehearsal, and only then separately authorized Production deployment.

Cargo moves ahead of Documents because it is now a mandatory intake invariant and a dependency for reliable pricing and operational planning. The remaining product-slice order is preserved: Documents reuses an existing schema; Dual Calendar is shared presentation; Combined Transport is a bounded catalog/intake change; Quote Communication carries a separate schema change. Architecture work remains after product contracts stabilize. The authorization evidence gate is numbered `0` because it is a small retained P0 verification, not a competing product implementation slice.

## J. Migration Forecast

```text
MINIMAL_CARGO_MIGRATION_EXPECTED=YES
MIGRATION_CREATED_BY_THIS_AMENDMENT=NO
```

Existing schema evidence makes an additive migration likely and currently expected:

- `ShipmentRequest` has only one nullable scalar set: `cargo_description`, `cargo_weight`, `cargo_volume`, and `cargo_value`;
- the Request schema has no Cargo quantity, Cargo unit, or `1..N` Request-to-Cargo-Item relation;
- the existing `ShipmentCargoItem` model has required quantity and unit but belongs to `OperationalShipment`, so reusing it for intake would violate the approved Request/Shipment boundary;
- the existing shipment cargo model also contains operational snapshots and execution-allocation relationships that are not Customer intake decisions.

The likely implementation therefore needs a fresh additive Request Cargo Item persistence model, linked to `ShipmentRequest`, plus an explicit compatibility and transition policy for historical Requests and current optional scalar fields. The exact table shape, constraint rollout, legacy backfill behavior, downgrade policy, and lineage from Request Cargo Items to later Shipment cargo lines require a separate controlled migration design. No migration is created, modified, or approved for execution by this report.

Any later migration must be a fresh direct descendant of the then-current Golden Alembic head, preserve exactly one head, avoid inventing values for historical Requests, and pass owned disposable PostgreSQL fresh-upgrade and prior-head-upgrade qualification before release.

## K. Verdict

PASS — PRODUCT DECISION AMENDMENT RECORDED
