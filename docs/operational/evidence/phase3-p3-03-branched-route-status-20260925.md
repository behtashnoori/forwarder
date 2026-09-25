# Phase 3 P3-03 — Branched Route Qualification Evidence

- **Record date:** 2026-09-25
- **Governing baseline:** LPAF v2.7 — ACTIVE / FROZEN / CANONICAL
- **Rigor / route:** Level B / Astra
- **Qualified slice:** P3-03 only — progressive route drafts, shared/branched destinations, Cargo destination association, separate actual traversal, and replan history
- **Mission:** [P3-03 Branched Route Mission Contract](../../product/phase3/P3-03-BRANCHED-ROUTE-MISSION-CONTRACT-FA.md)
- **Architecture:** [ADR-058](../adr/ADR-058-branched-planned-route-and-actual-traversal.md)
- **Product baseline:** `integration/golden-controlled@629e6f5a544b7b2824670960d90eb5209d3c594b`
- **Candidate branch:** `codex/phase3-p3-03-route-planning`
- **Phase 3 Product SHA:** `d7ff7208fdc25caff7af86379fd8afc5b41b24aa`
- **Evidence SHA:** this document's evidence-only descendant, reported in the final delivery record

This record qualifies only P3-03. It does not claim completion of P3-04 or later slices, a full integrated Product journey, Human Product Walkthrough, global Product validation, release readiness, deployment, or Production access.

## Qualified Product boundary

The fixed owning Transport Expert can save an honestly incomplete route draft without a fabricated transport mode, planned time, stop, or Milestone. The existing `RoutePlan/RouteLeg` source of truth now supports a shared root and same-plan destination branches. Activation remains fail-closed: the graph must be complete, continuous, acyclic, chronologically valid, and each Cargo line in a multi-destination plan must point to a terminal branch.

`RouteCargoDestination` associates an existing Shipment Cargo line with a terminal RouteLeg in the same Shipment and plan revision. It does not create or duplicate Cargo, Shipment, allocation, or execution. Reassignment is versioned and audited. Replan preserves the source revision and clones planned topology and Cargo associations with remapped leg identities.

`RouteTraversalFact` records append-only actual movement separately from the plan. A fact can be compared with an optional same-plan leg, but it never overwrites the planned route. A deviation is explicit evidence and does not automatically create an `OperationalException`. Replan leaves actual facts on the source revision.

The Forwarder UI exposes separate Persian sections for planned route and actual route, progressive incomplete states, Cargo-to-destination mapping, deviation, version history, and replan. Carrier, vehicle, equipment, transport execution expansion, ETA, P3-07 reported-location taxonomy, Customer projection, delivery/closure, and ownership transfer are excluded.

## Product Authority result

| Material observable difference | Final classification | Evidence result |
| --- | --- | --- |
| Incomplete route draft without invented facts | `AUTHORIZED` | API, database, UI, reopen, and no-fake-Milestone tests PASS |
| Shared root and multiple destination branches | `AUTHORIZED` | Same-plan FK, graph/cycle, continuity, chronology, UI and browser tests PASS |
| Cargo destination association without duplication | `AUTHORIZED` | Composite scope, terminal-leaf, activation, version and history tests PASS |
| Planned route and actual traversal remain separate | `AUTHORIZED` | Append-only actual facts, serializer, UI and PostgreSQL constraints PASS |
| Deviation does not automatically create an exception | `AUTHORIZED` | Service, browser and persistence checks PASS |
| Replan retains source history | `AUTHORIZED` | Topology/Cargo clone and source actual-fact preservation PASS |
| Existing fixed owning-Expert authority | `PRESERVED` | Owning Expert PASS; Admin/non-owner/cross-scope writes denied |
| Carrier/vehicle/equipment, ETA and Customer projection | `PRESERVED_AS_OUT_OF_SCOPE` | No P3-04/P3-07/Customer command or entitlement added |

No material difference was classified `UNKNOWN` or `VIOLATION` in P3-03. The exact Product rule for later promotion of a route deviation into an Operational Exception remains unknown; this slice deliberately performs no automatic promotion.

## Migration and PostgreSQL 18 evidence

- Migration target: `20261002_phase3_branched_route`.
- Parent: `20261001_phase3_cargo_lineage`.
- Alembic head count: `1`.
- PostgreSQL server: `18.0` on an agent-owned loopback disposable cluster.
- Clean base-to-head upgrade, empty/no-seed verification, empty downgrade/re-upgrade, runtime writes, composite scope constraints, branch constraints, and populated downgrade refusal: `PASS`.
- Exact PostgreSQL qualification on the frozen Product SHA: `1 passed, 8 warnings in 3.87s`.
- No parent branch, label, planned time, Cargo destination, or actual traversal was backfilled.

The populated downgrade guard refuses destructive loss when P3-03 data or newly nullable legacy values cannot be safely represented. Safe application rollback may retain the additive schema until separately authorized reconciliation.

## Authorization, privacy, and history evidence

- Exact persisted owning Transport Expert mutation: `PASS`.
- Organization Admin and non-owning Expert mutation denial: `PASS`.
- Cross-tenant Shipment/Cargo and cross-plan leg/reference denial without partial write: `PASS`.
- Same-plan parent/child and Cargo/Shipment/plan database equivalence: `PASS`.
- Optimistic version conflict, append-only audit/outbox, route revision and replan provenance: `PASS`.
- Customer Portal projection/entitlement added: `NO`.

## Automated evidence on the frozen Product SHA

| Evidence unit | Result |
| --- | --- |
| Focused backend P3-03 service/migration | `6 passed, 45 warnings` |
| Existing multi-leg/facility regression | `56 passed, 616 warnings` |
| Combined focused backend route boundary | `62 passed` |
| Exact PostgreSQL 18 qualification | `1 passed, 8 warnings` |
| Full backend regression | `1388 passed, 110 skipped, 0 failed` |
| Focused frontend route UI/API | `4 files, 54 tests passed` |
| Full frontend regression | `82 files, 399 tests passed` |
| TypeScript check | `PASS` |
| Lint | `PASS` — 0 errors; 13 pre-existing warnings |
| Production build | `PASS` — advisory chunk-size/browser-data warnings only |
| Architecture governance check | `PASS` |
| Repository structure check | `PASS` |
| OpenAPI YAML/runtime route parity, including PUT | `PASS` |
| Tenant ownership composite-FK contract | `PASS` |
| Alembic single-head check | `PASS` — `20261002_phase3_branched_route` |
| Diff whitespace check | `PASS` |

Runtime identity: Python `3.13.9`, Node `v24.11.0`, npm `11.6.1`, PostgreSQL `18.0`.

## Browser Product evidence

The dedicated real-browser P3-03 journey passed on the frozen Product SHA with runner execution and cleanup passing. The successful disposable run identity was `b34a29958b5f4385ab34390a7b443dab`.

The scenario used normal navigation to the Shipment, saved an incomplete plan without fake defaults, progressively completed the shared root and two terminal destination branches, associated separate Cargo lines with their branches, activated the plan, recorded an actual traversal deviation without automatic exception creation, verified plan-versus-actual presentation and history, replanned, navigated away, reopened the Shipment, and verified retained source history and current revision. Result: `1 passed in 21.6s`; `RUNNER_EXECUTION=PASS`; `E2E_CLEANUP=PASS`.

| Evidence unit | Result |
| --- | --- |
| `P3-03-INCOMPLETE` | `PASS` |
| `P3-03-BRANCHES` | `PASS` |
| `P3-03-CARGO-DESTINATIONS` | `PASS` |
| `P3-03-PLAN-ACTUAL` | `PASS` |
| `P3-03-REPLAN-HISTORY` | `PASS` |
| `P3-03-DEVIATION-NO-EXCEPTION` | `PASS` |
| `P3-03-TENANT-AUTHORITY` | `PASS` |
| Automated P3-03 Product slice | `PASS` |
| Human Product Walkthrough | `NOT_RUN` |

## Journey impact ledger

The statuses below are deliberately bounded. A P3-03 boundary PASS does not become an integrated-journey PASS.

| Journey | P3-03 evidence status | Broader journey status |
| --- | --- | --- |
| `FWD-J03` | `PASS_FOR_P3_03_BOUNDARY` — authorized Cargo-to-route handoff and persistence | `NO_INTEGRATED_EVIDENCE_YET` |
| `FWD-J04` | `PASS_FOR_P3_03_BOUNDARY` — owning Expert plan/actual/replan workflow | `NO_INTEGRATED_EVIDENCE_YET` |
| `FWD-J08` | `PASS_FOR_P3_03_BOUNDARY` — tenant, role and cross-scope negatives | `NO_INTEGRATED_EVIDENCE_YET` |
| `FWD-J09` | `PASS_FOR_P3_03_BOUNDARY` — shared route, destination branches and Cargo mapping only | `TARGET_PHASE3 / NOT_RUN_END_TO_END` |
| `FWD-IPJ-01` | `PASS_FOR_P3_03_BOUNDARY` | `NOT_RUN_AS_INTEGRATED_JOURNEY` |
| `FWD-IPJ-04` | `PASS_FOR_P3_03_BOUNDARY` | `NOT_RUN_AS_INTEGRATED_JOURNEY` |

## Reference reconciliation

LPAF v2.7, the Operational Shipment Product Contract, Product Acceptance Journey Pack v1.1, Phase 3 Implementation Plan, UX Blueprint v2.1, ADR-002/004/017/022/034/042/043/046/047/057/058, architecture baseline, FDM, FDD, decision indexes, tenant ownership inventory, and OpenAPI were reconciled against the frozen Product SHA. Historical planning text remains historical. No canonical LPAF change is required.

```text
REFERENCE_RECONCILIATION=PASS
LPAF_REFERENCE_IMPACT=NONE
PROJECT_REFERENCE_IMPACT=NONE_AFTER_RECONCILIATION
```

## Final status ledger

```text
LPAF_BASELINE=2.7
PHASE_3_IMPLEMENTATION_STARTED=YES
PHASE3_CURRENT_SLICE=P3-03
PHASE3_P3_01=PASS_ALREADY_IN_CANONICAL_BASE
PHASE3_P3_02=PASS_ALREADY_IN_CANONICAL_BASE
PHASE3_P3_03=PASS
P3_03_ENGINEERING_COMPLETE=YES
P3_03_PRODUCT_COMPLETE=YES_BOUNDED_SLICE
INCOMPLETE_ROUTE_DRAFT=PASS
BRANCHED_ROUTE_GRAPH=PASS
CARGO_DESTINATION_ASSOCIATION=PASS
PLANNED_ACTUAL_SEPARATION=PASS
REPLAN_HISTORY_PRESERVATION=PASS
DEVIATION_AUTO_EXCEPTION=NO
OWNING_EXPERT_AUTHORITY=PASS
TENANT_ISOLATION=PASS
HISTORY_PRESERVATION=PASS
CARRIER_ASSIGNMENT_IMPLEMENTED=NO
VEHICLE_EQUIPMENT_IMPLEMENTED=NO
ETA_IMPLEMENTED=NO
CUSTOMER_ROUTE_PROJECTION_IMPLEMENTED=NO
DN01_STATUS=OPEN
DN05_STATUS=OPEN
DN08_STATUS=PARTIAL_DECISION_NEEDED
DN10_STATUS=OPEN
JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY
AFFECTED_JOURNEYS=FWD-J03,FWD-J04,FWD-J08,FWD-J09,FWD-IPJ-01,FWD-IPJ-04
SLICE_JOURNEYS=PASS
INTEGRATED_PRODUCT_JOURNEYS=NOT_RUN
BROWSER_PRODUCT_JOURNEY=PASS
FULL_BACKEND_REGRESSION=PASS
FULL_FRONTEND_REGRESSION=PASS
MIGRATION_REQUIRED=YES
ALEMBIC_HEAD=20261002_phase3_branched_route
ALEMBIC_HEAD_COUNT=1
MIGRATION_QUALIFICATION=PASS
PRODUCT_AUTHORITY_RECONCILIATION=PASS
PRODUCT_VALIDATION_EVIDENCE_FOR_THIS_SLICE=COMPLETE
PHASE3_PRODUCT_HEAD=d7ff7208fdc25caff7af86379fd8afc5b41b24aa
PHASE3_EVIDENCE_HEAD=EVIDENCE_ONLY_DESCENDANT_REPORTED_IN_FINAL_HANDOFF
REFERENCE_RECONCILIATION=PASS
REFERENCE_IMPACT=NONE
GLOBAL_PRODUCT_VALIDATION=EVIDENCE_PENDING
HUMAN_PRODUCT_WALKTHROUGH=NOT_RUN
RELEASE_READY=NO
P3_04_STARTED=NO
P3_05_STARTED=NO
AI_IMPLEMENTED=NO
GPS_IMPLEMENTED=NO
FINANCE_IMPLEMENTED=NO
CARRIER_PORTAL_IMPLEMENTED=NO
DRIVER_PORTAL_IMPLEMENTED=NO
PRODUCTION_ACCESSED=NO
PRODUCTION_MUTATED=NO
DEPLOYMENT_PERFORMED=NO
RELEASE_CREATED=NO
CANONICAL_INTEGRATION=NOT_PERFORMED_AT_EVIDENCE_CAPTURE
CANONICAL_PUSH=NOT_PERFORMED_AT_EVIDENCE_CAPTURE
```

## Residual gates and exact next action

- `DN01`, `DN05`, and `DN10` remain open; `DN08` remains partial. P3-03 does not consume those unresolved decisions.
- The later rule for promoting route deviation into an Operational Exception remains unapproved; P3-03 safely creates no automatic exception.
- Global Product validation remains `EVIDENCE_PENDING`; only an authorized human can complete the Human Product Walkthrough.
- Release readiness remains `NO`; no deployment, release, or Production action occurred.
- The next permitted action is evidence-only commit, fast-forward integration and push of P3-03, verification of local/remote `0/0`, cleanup of temporary resources, and then a hard stop before P3-04.
