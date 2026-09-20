# Optional Multi-Cargo Request — Governed Build Evidence

Date: 2026-09-20

Worktree: `D:\1-webapp\15-forwarder-golden-20260921`

Build branch: `codex/cargo-multi-item-build`

## A. LPAF Governance Gate

The Build was executed under the active LPAF v2.2 baseline with the v2.3 Product Integration / `REFERENCE_IMPACT` gate applied as the Forwarder project's strong default. Before implementation, the agent read the Entry Protocol, Architecture Framework, Product Integration governance, the approved implementation design, and the applicable Forwarder PDR/ADR/FDD/FDM/reconciliation records.

```text
MISSION = IDENTIFIED
OUTCOME = IDENTIFIED
CAPABILITY_OWNER = IDENTIFIED
SYSTEM_OF_RECORD = IDENTIFIED
ACTOR_ROLE_ENTITLEMENT = IDENTIFIED
TENANT_DATA_SCOPE = IDENTIFIED
USER_JOURNEY = IDENTIFIED
STATE_DATA_OWNER = IDENTIFIED
UPSTREAM_DOWNSTREAM = IDENTIFIED
MODULE_BOUNDARY = IDENTIFIED
API_IMPACT = IDENTIFIED
SCHEMA_IMPACT = IDENTIFIED
COMPATIBILITY_IMPACT = IDENTIFIED
ACCEPTANCE_CONTRACT = IDENTIFIED
NEGATIVE_AUTH_CONTRACT = IDENTIFIED

REFERENCE_IMPACT = NONE
```

No material conflict was found between the approved design, governing product truth, and runtime reality.

## B. Starting State

- Required starting branch: `codex/cargo-multi-item-implementation-design`
- Required and observed starting HEAD: `6c8ff371c9e43023d7367782b5b2be5c4e013f83`
- Required and observed design-commit parent: `31f3f503b5fc8d6e89bb9a60066a1ca3fa676a76`
- Required and observed database head: `20260923_notification_lifecycle`
- Alembic graph before Build: one base, one head, no pending migration
- Worktree before Build: clean
- Design commit scope: documentation only; no runtime delta
- Build branch created from the required starting HEAD: `codex/cargo-multi-item-build`
- Remote push: not performed

## C. Mission / Owner / SOR

Mission: implement the approved, bounded create/read capability through which a Customer Request can contain zero, one, or multiple optional cargo items.

- Capability owner: Commercial / Customer Request
- System of Record: `ShipmentRequest` plus its `RequestCargoItem` children
- State/data owner: existing Request creation and authorized Request read services
- Parent aggregate: `ShipmentRequest`
- Reference inputs: active governed `CargoType` and `UnitOfMeasure`
- Downstream boundary: commercial review only; no automatic operational handoff

## D. Schema / Migration

Exactly one fresh migration was added:

- Revision: `20260924_request_cargo_items`
- Previous head / down revision: `20260923_notification_lifecycle`
- Base: `20240917_initial_schema`
- New head: `20260924_request_cargo_items`
- Final graph: one base, one head
- Final database status: current equals head; pending migration is `no`

The additive `request_cargo_item` table has a server-generated opaque public identity, required parent Request, one-based stable position, optional governed Cargo Type, trimmed optional description, exact `NUMERIC(18,6)` quantity, optional governed UOM, timezone-aware creation timestamp, uniqueness constraints, structural checks, parent-position index, and `RESTRICT` foreign keys. No existing Request column was rewritten and the migration performs zero backfill.

Downgrade is reversible when the new table is empty and refuses to discard populated Customer evidence.

## E. Optional Cargo Contract

`cargo_items` is optional. Omission and `[]` both normalize to zero items. `null`, non-array input, non-object items, unknown fields, non-string decimal input, exponent notation, excessive precision/scale, non-positive quantity, inactive/missing governed references, incomplete quantity/UOM pairs, and voluntarily created empty rows produce indexed `422` validation errors.

A supplied item is meaningful when it contains at least one of:

- a valid active Cargo Type;
- a nonblank description; or
- a complete positive quantity/UOM pair.

No particular Cargo fact is mandatory for Request submission.

## F. Zero-Cargo Behavior

Zero Cargo was proven through service/API, persistence, component, and browser paths. Both omitted `cargo_items` and `cargo_items: []` create a valid Request, return `cargo_items: []`, persist no child rows, and reopen in the Customer journey with an explicit empty state.

The final browser zero-Cargo journey created and reopened Request ID `6` for the synthetic Customer context without adding Cargo.

## G. Multi-Cargo Behavior

One-item and multi-item Requests create atomically with their parent. Input order becomes stable one-based position; each row receives a server identity; responses and authorized reads retain identity and order. Exact decimal strings are never parsed through binary floating point.

PostgreSQL proved the boundary value `999999999999.123456`. The final browser journey created Request ID `7` with three ordered items and reopened it with preserved identities, order, and the displayed `3.25 kg` meaning.

## H. Historical Compatibility

- Existing nullable scalar cargo columns remain unchanged.
- Historical Cargo-less Requests remain valid.
- No scalar record is guessed or backfilled into `RequestCargoItem`.
- Structured cargo is not projected into legacy scalar fields.
- Legacy and structured representations can coexist independently.
- New Customer UI submissions no longer write legacy cargo scalars; Request-level special instructions and availability dates retain their existing meanings.
- Public tracking remains unchanged and does not expose structured cargo.

## I. API Contract

- `POST /api/shipment-request`: additively accepts optional `cargo_items` and returns ordered structured items.
- `GET /api/request-cargo-options`: returns deterministic, active, public-safe Cargo Type and UOM projections only.
- Customer workflow/detail: ordered `cargo_items` plus separately named legacy representation.
- Assigned Expert detail: retains legacy `cargo` and adds ordered `cargo_items`.
- Expert and authorized same-organization admin lists: lean `cargo_item_count` and `has_legacy_cargo` projections.
- Authorized admin detail: ordered items and legacy representation.
- No standalone child read, update, delete, or enumeration endpoint was introduced.

The client/API types preserve decimal quantities as strings and represent absent nested optional facts consistently as `null` in responses.

## J. Customer Journey

The existing Customer Request form now contains an optional, initially empty Cargo section. A Customer can add, remove, reorder, and edit voluntary rows; choose active governed references; enter exact decimal text; review the ordered summary; submit; and reopen the Request. Invalid voluntary rows remain in place with field-level feedback and no submission occurs. The confirmation and success states both show the resulting ordered cargo or the explicit zero-Cargo state. Persian and English copy was added.

No post-submission edit affordance was introduced.

## K. Authorization

Cargo has no independent authorization surface. Customer and Expert reads load cargo only through an already-authorized parent Request. Canonical parent-policy tests cover assigned Expert allow, same-organization unrelated Expert deny, foreign-tenant deny, inactive actor deny, legacy manager-label deny, Organization Admin without `request.read` deny, Organization Admin with `request.read` allow, and Platform Admin deny.

The legacy admin parent endpoint retains its pre-existing visibility contract, but the newly added cargo projection is separately gated by the canonical parent `request.read` decision. Explicit adversarial coverage proves that Platform Admin receives none of the new item, count, or legacy-cargo projection fields. No client-provided tenant identifier is trusted for authorization.

## L. Request vs Operational Cargo Boundary

`RequestCargoItem` records commercial Customer intent. `ShipmentCargoItem` remains an operational snapshot owned by `OperationalShipment`. This Build adds no operational Cargo writes, lineage column, copy, allocation, Shipment creation, Execution Unit, vehicle/container, Route Leg, Shipment-owner, expert-reassignment, quote, Notification, Control Tower, combined-transport, or dual-calendar behavior. Future Request-to-Shipment cargo handoff remains an explicit separately governed planning capability.

The tenant-ownership inventory was synchronized to record the child as parent-authorized and `LEGACY_AMBIGUOUS`, matching its required parent, which can be tenant-owned or retained legacy intake data.

## M. PostgreSQL Proof

An owned disposable PostgreSQL 18.0 instance on loopback port `55439`, database `forwarder_cargo_build`, was used. It was not a Production or shared database.

The hard-gate test passed and proved:

- reset of the owned database;
- upgrade from `20260923_notification_lifecycle` to `20260924_request_cargo_items`;
- byte-semantic preservation of a complete legacy Request row via `to_jsonb` comparison;
- zero synthetic child rows after migration;
- required types, timezone behavior, checks, uniqueness, index, and `RESTRICT` foreign keys;
- empty downgrade, historical-row preservation, and re-upgrade;
- zero/one/multi API persistence and exact maximum integer/fraction boundary;
- database rejection of invalid position, pair, empty item, duplicate position, and parent deletion;
- same-parent tenant join returning three rows for the correct tenant and zero for the foreign tenant;
- populated downgrade refusal with head and data intact.

Result: `1 passed, 8 warnings`.

Final migration CLI result:

```text
current=20260924_request_cargo_items
heads=20260924_request_cargo_items
pending=no
```

## N. Browser Evidence

Playwright exercised the real Vite application, real backend, and owned PostgreSQL database with one Chromium worker.

- Zero Cargo: submit and reopen — PASS
- Three Cargo Items: identity, order, exact quantity response, localized detail — PASS
- Invalid voluntary row: understandable error, draft retained, no POST — PASS
- Console/page/API network error audit — PASS

Result: `3 passed` in `47.4s`.

Ignored local screenshots:

- `test-results/request-cargo-optional-Req-dc22b-l-through-submit-and-reopen/zero-cargo-created.png`
- `test-results/request-cargo-optional-Req-a795c--order-precision-and-detail/multi-cargo-created.png`
- `test-results/request-cargo-optional-Req-a795c--order-precision-and-detail/multi-cargo-reopened.png`

## O. Regression Status

The exact final tree passed full frontend regression, production bundling, TypeScript, lint, focused authorization/contracts, migration hard gate, browser journeys, and release/source/package cohort. The full backend result is recorded in Section P after its isolated final run. Existing deprecation, chart-size, stale Browserslist, and large-bundle warnings remain non-blocking and were not introduced as functional failures by this slice.

No regression was found in legacy Request reads, quote flows, operational cargo, Control Tower, public tracking, notification lifecycle, migration graph, release identity, package policy, or tenant architecture contracts.

## P. Tests

| Qualification | Final result |
|---|---|
| Full backend, explicitly isolated test database | `1,281 passed, 98 skipped, 1 xfailed` |
| Full frontend | `70 files / 326 tests passed` |
| Focused Request Cargo + admin authorization | `31 passed, 7 skipped` |
| PostgreSQL hard gate | `1 passed, 8 warnings` |
| Browser journeys | `3 passed` |
| Release/source/package cohort | `54 passed, 1 skipped, 1 xfailed` |
| TypeScript | PASS |
| ESLint | PASS, zero errors; 13 pre-existing warnings in full output |
| Production frontend build | PASS, 2,546 modules transformed |
| Alembic static graph/current/check | PASS, one base, one head, no pending migration |
| Diff whitespace check | PASS |

Skipped and expected-failure tests retain their pre-existing environment/decision semantics; the PostgreSQL feature gate was run explicitly rather than inferred from the isolated full-suite skips.

## Q. Reference Re-check

Immediately before Freeze, the applicable LPAF v2.2/v2.3 governance, PDR-019, PDR-013, ADR-002, ADR-022, ADR-047, FDD-001, FDM-001, the 2026-09-20 reference reconciliation, and the approved Cargo implementation design were re-read against the final code and tests.

The Build still implements optional `0..N` commercial Request Cargo, leaves Operational Shipment Cargo independent, preserves historical truth, uses additive migration, derives new reads from the parent policy, and creates no unapproved downstream capability.

```text
REFERENCE_IMPACT_FINAL=NONE
```

## R. Scope Integrity

```text
REQUEST_CARGO_REQUIRED_FOR_SUBMISSION=NO
REQUEST_CARGO_MIN_ITEMS=0
MULTI_CARGO_REQUEST_ENABLED=YES
MANDATORY_CARGO_POLICY=DEFERRED

REQUEST_CARGO_OWNER=COMMERCIAL_REQUEST
OPERATIONAL_CARGO_OWNER=OPERATIONAL_SHIPMENT

CUSTOMER_CREATES_OPERATIONAL_SHIPMENT=NO
CUSTOMER_ALLOCATES_EXECUTION_UNITS=NO
CUSTOMER_DEFINES_ROUTE_LEGS=NO

EXPERT_REASSIGNMENT_WORKFLOW_ADDED=NO
NOTIFICATION_ACTIVATION_CHANGED=NO
CONTROL_TOWER_BEHAVIOR_CHANGED=NO
COMBINED_TRANSPORT_IMPLEMENTED=NO
DUAL_CALENDAR_IMPLEMENTED=NO
QUOTE_COMMUNICATION_IMPLEMENTED=NO

PRODUCTION_ACCESSED=NO
PRODUCTION_CHANGED=NO
SECRETS_ACCESSED=NO
```

Changed surfaces are bounded to the Request Cargo model and migration; Request create/reference/read services and routes; parent-derived admin projection gating; Customer/Expert/admin Request UI and types; bilingual copy; tenant inventory synchronization; migration-head expectations; focused, regression, PostgreSQL, and browser tests; and this evidence record. No Production system, deployment configuration, remote branch, generic LPAF source, or operational aggregate was changed.

## S. Remaining Risks

- Post-submission cargo edit/remove/reorder is intentionally unavailable; adding it needs lifecycle, audit, concurrency, authorization, quote-impact, and downstream decisions.
- Operational handoff/allocation is intentionally absent; a later capability must define explicit lineage and snapshot rules.
- Historical scalar cargo remains separately visible where already authorized and is not deduplicated against structured items.
- Existing non-failing dependency/deprecation, browser-data age, chart-layout test-environment, and bundle-size warnings remain project maintenance items outside this bounded slice.
- Browser screenshots are ignored local evidence artifacts under project convention; the durable evidence is the committed test and this report.

## T. Verdict

PASS — OPTIONAL MULTI-CARGO REQUEST COMPLETE
