# Human Walkthrough Cargo Lineage, Route Allocation, and ETA Repair

## Mission contract

- **Governance baseline:** LPAF v2.7, as required by this repository's `AGENTS.md`.
- **Change class:** Level B coupled backend/frontend remediation with PostgreSQL and browser validation.
- **Journey impact:** `AFFECTS_EXISTING_JOURNEY`.
- **Product validation state:** `EVIDENCE_PENDING`; automated evidence cannot self-pass the Human Walkthrough.
- **Canonical baseline:** `integration/golden-controlled` at `43932edd9967d9d692ef8aac68c5e8d758d68cf8`, verified clean and synchronized with `github/integration/golden-controlled` before isolation.
- **Isolated implementation branch:** `codex/human-walkthrough-cargo-lineage-route-allocation`.
- **Authority boundaries:** no production mutation, no raw database repair, no history deletion or replacement, no release/deployment, and no Human Walkthrough completion claim.

## Product Authority Record

### Product truth

1. Request, Shipment, Cargo, Execution Unit, and route participation are separate identities.
2. Requested, planned, actual, and allocated quantities are separate facts; one must not silently overwrite another.
3. Request Cargo lineage is an explicit relationship. Catalog similarity, names, descriptions, and quantities are not lineage proof.
4. Shipment-level route existence does not establish Cargo participation. `RouteCargoDestination` is the authoritative Cargo-to-terminal-leg relationship for a route revision.
5. Execution allocation eligibility and ETA path resolution must consume that governed Cargo route relationship.
6. A Cargo may traverse multiple stages, but its Shipment quantity must not be counted once per stage.
7. Human Walkthrough remains `IN_PROGRESS` until a human accepts it.

### Observed facts

- The preserved walkthrough Shipment is rooted in one accepted quote and one Shipment Request.
- That Request has exactly one Request Cargo row: quantity `100`, UOM `UOM_PIECE`, cargo type `CARGO_AUTOMOTIVE_MECHANICAL_COMPONENTS`.
- The Shipment has exactly one Cargo row with planned quantity `100`, the same UOM and cargo type, but with null requested quantity and null Request lineage fields.
- The Shipment has one active route revision and one terminal leg, but no Cargo destination relationship.
- The Shipment has one route-stage execution and one Execution Unit, but no Cargo allocation.
- Immutable audits show Shipment creation followed immediately by Cargo creation; the Cargo audit records null lineage at creation.
- The creation UI currently performs Shipment creation and Cargo creation as separate commands. Its Cargo command omits Request Cargo lineage, and it never creates the Cargo route destination.
- Allocation and ETA services independently reject the Cargo path when the authoritative route destination is absent.

### Root-cause decision

The defect is at the Shipment creation boundary: accepted-quote creation does not carry an explicit Request Cargo selection into an atomic Shipment aggregate command, and initial Cargo creation does not establish its terminal route-leg destination. The downstream allocation and ETA behaviors are faithful consequences of the missing source-of-record relationships, not independent projection defects.

### Authorized remediation

- Include eligible Request Cargo identities and governed type/UOM/quantity facts in the accepted-quote selector.
- Require an explicit Request Cargo selection when an accepted-quote Shipment is created with Cargo.
- Create Shipment, route, Cargo lineage, and initial Cargo route destination atomically and idempotently.
- Preserve direct Shipment creation without fabricated Request lineage.
- Keep planned, requested, actual, and allocated quantities distinct; quantity mismatches remain warnings unless another invariant is violated.
- Present the governed Persian UOM name as the primary walkthrough label where available.

### Observable-difference reconciliation

| Difference | Decision | Authority |
|---|---|---|
| Accepted-quote Shipment creation can explicitly select Request Cargo and persist source lineage | `AUTHORIZED` | This mission, sections 6, 18, 19, 23, and 30 |
| Initial Shipment Cargo is assigned to the terminal leg of the route created by the same command | `AUTHORIZED` | This mission, sections 9, 18, 24, and 30 |
| Requested, planned, actual, and stage-allocation values remain separate | `PRESERVED` | P3-02/P3-05 and this mission, sections 7, 13, 26, and 27 |
| Direct Shipment Cargo may remain without Request lineage | `PRESERVED` | This mission, section 8 |
| Customer-requested destination may differ from the operational planned destination | `PRESERVED` | This mission, section 10; `HW_SHIPMENT_ROUTE_001` remains open |
| Allocation and ETA resolve the same Cargo-specific route path | `AUTHORIZED` | This mission, sections 14 and 15 |
| Existing active-plan route participation may be invented from similarity | `VIOLATION` | Explicitly prohibited by sections 16 and 17 |
| Human Product Walkthrough automated approval | `VIOLATION` | LPAF v2.7 and this mission, sections 34 and 39 |

### Journey impact

`JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY`.

The core creation boundary and shared Cargo path affect Request/Quote creation,
operational execution, allocation, customer-scoped read truth, ETA, final
runtime UX, closure/history, and integrated owner/entitlement behavior. The
exact Product candidate therefore requires the complete automated critical
pack: `FWD-J01` through `FWD-J09` and `FWD-IPJ-01` through `FWD-IPJ-04`, in
addition to P3-02, P3-03, P3-04, P3-05, P3-09, P3-11, P3-14, and P3-15.

### Existing-data repair gate

The preserved walkthrough database may be changed only through a pre-existing governed/domain command after the Product fix and qualification. Lineage repair and route participation must each have exact immutable evidence and an authorized command path. If either relationship lacks a safe pre-existing command, the runtime remains unchanged and the mission reports `EXISTING_WALKTHROUGH_CARGO_LINEAGE_REPAIR_DECISION_NEEDED`.

Diagnosis found an existing governed Cargo update command that could represent
the Request lineage. It did not find an existing command that may add the
missing Cargo destination to the preserved Shipment's already-active RoutePlan;
the P3-03 command correctly permits that mutation only while a plan is draft.
Creating a replacement route revision or partially repairing lineage would be
a new Product decision, not a technical inference. Therefore the preserved
record has not been mutated and its bounded stop code is
`EXISTING_WALKTHROUGH_CARGO_LINEAGE_REPAIR_DECISION_NEEDED`.

## Implemented boundary

- Accepted-quote and direct creation now accept bounded nested Cargo commands
  and include them in idempotency identity.
- Accepted-quote Cargo facts are server-derived from the selected Request Cargo;
  caller attempts to override source Request, owner, type, UOM, or requested
  quantity are rejected.
- Shipment, active RoutePlan, terminal RouteLeg, Cargo lineage, and
  `RouteCargoDestination` commit atomically; a rejected Cargo command leaves no
  partial Shipment aggregate.
- The creation UI no longer performs a second Cargo write after Shipment
  creation.
- Allocation and ETA share one strict root-to-terminal Cargo route resolver;
  ETA retains truthful unavailable reasons when progress or references are
  absent.
- Persian UOM names are used in the affected Cargo and allocation projections;
  numeric storage scale is trimmed for display.

## Pre-candidate verification

- Full backend: `1577 passed, 122 skipped`.
- Full frontend: `99` files and `472` tests passed.
- Focused backend: `64 passed`; focused frontend: `22 passed`.
- Targeted PostgreSQL 18 concurrency/persistence proof: `1 passed`.
- Owned PostgreSQL 18 + real Chrome continuity proof: PASS for Request Cargo
  `100 عدد`, planned Cargo/allocation `100`, actual allocation `95`,
  non-blocking mismatch warning, immutable allocation history, execution
  discovery, and ETA whose reason is not `ROUTE_UNDEFINED`.
- TypeScript production build, ESLint, OpenAPI YAML parse, Python compile,
  architecture governance, repository structure, backend determinism,
  current-tree secret scan, and `git diff --check`: PASS.

These checks established the candidate boundary before the frozen exact-SHA
qualification below.

## Exact-SHA final qualification

- **Product SHA:** `2ddb61aa06721b884f7b142997cd15659865d4fc`.
- **Source state:** clean before and after the run; the runner bound every gate
  to the exact Product SHA.
- **Environment:** owned disposable local/UAT PostgreSQL 18 and real Chrome;
  the preserved walkthrough database was not used.
- **Migration:** base-to-head chain PASS; one repository head,
  `20261012_phase3_cargo_eta`.
- **PostgreSQL:** all 16 Phase 3 persistence, authorization, concurrency,
  isolation, and scalability modules passed in `830.67s`; Public Tracking also
  passed.
- **Chrome:** P301 through P314, MT3, IPJ01, all three IPJ02/IPJ03 chapters,
  P315-CORE, HW-COMMERCIAL, and IPJ04 main/follow-up passed. P304 included the
  new exact Cargo-chain scenario.
- **Product journeys:** `FWD-J01..FWD-J09` and
  `FWD-IPJ-01..FWD-IPJ-04` PASS for automated qualification. This does not
  self-pass the Human Product Walkthrough.
- **Runner result:** all 25 recorded gates PASS; disposable PostgreSQL and
  application processes stopped cleanly.
- **Production boundary:** production accessed/mutated = false; production
  migration, deployment, and release = false.

The first exact-candidate attempt at
`ded5b066f55b9865272d06ccd0a887693022710f` stopped before integration at P302:
the UI deliberately rendered `هنوز ثبت نشده` for an absent actual quantity,
while the pre-existing browser assertion still expected `نامشخص`. The
assertion was aligned with the authorized wording, the Product SHA advanced,
and the complete qualification was rerun from the beginning. No failed-run
evidence was used for acceptance.

### External evidence identity

Evidence directory:

`D:\1-webapp\forwarder-dev\human-walkthrough-cargo-lineage-route-allocation-evidence-20260928-final-product-2ddb61a`

- `result.json` SHA-256:
  `fdc6b6eadbd8cde41d58beb50247a9277877d89a97d26847052d6318bf767a76`
- `postgresql-migration-chain.log` SHA-256:
  `2e42a993122c2c0d55bc846921bfe524b759bc0cf1d0b47dfbedb74dbf76b7f8`
- `postgresql-phase3.log` SHA-256:
  `ef8bb330c6c1f813b89a00327c02819a2c855d88111b82ff740d0232b80262da`

## Verification plan

- Focused backend tests for atomicity, lineage validation, route destination creation, authorization, idempotency, allocation visibility, and ETA continuity.
- Focused frontend tests for explicit Request Cargo selection, payload correctness, quantity/UOM presentation, and removal of the split write.
- PostgreSQL 18 qualification for affected persistence and concurrency behavior.
- Full backend and frontend regression suites.
- All P3 journeys and all FWD acceptance journeys impacted by the change.
- Chrome walkthrough against the preserved runtime after controlled integration only; services and historical data must remain intact.
