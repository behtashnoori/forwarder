# Phase 3 P3-04 — Transport Execution Qualification Evidence

- **Record date:** 2026-09-25
- **Governing baseline:** LPAF v2.7 — ACTIVE / FROZEN / CANONICAL
- **Rigor / route:** Level B / Astra
- **Qualified slice:** P3-04 only — route-stage transport execution, Transport Means, ordered Transport Equipment/load units, Carrier context, progressive details, and immutable change history
- **Mission:** [P3-04 Transport Execution Mission Contract](../../product/phase3/P3-04-TRANSPORT-EXECUTION-MISSION-CONTRACT-FA.md)
- **Architecture:** [ADR-059](../adr/ADR-059-route-stage-transport-execution.md)
- **Canonical base:** `integration/golden-controlled@c69c0d3096c29d902a7fad2009d0b8ec2d4bdf68`
- **Candidate branch:** `codex/phase3-p3-04-transport-execution`
- **P3-04 Product SHA:** `af3d1c4a8406b0a8ae71f9e5b76b87dc38751981`
- **Evidence SHA:** this document's evidence-only descendant, reported in the final delivery record

This record qualifies only P3-04. It does not claim P3-05 Cargo allocation/split/transfer, permanent fleet registration, expanded driver management, a Human Product Walkthrough, global Product validation, release readiness, deployment, or Production access.

## Qualified Product boundary

The existing tenant-owned `ExecutionUnit` remains the source of truth. `RouteStageExecution` associates one such unit with an exact Shipment, RoutePlan revision, and RouteLeg; a stage may have zero, one, or many executions. No Shipment owner or access authority is derived from Carrier participation.

Each execution has append-only `ExecutionTransportRevision` records. Transport Means is required for creation. Carrier, means identifier, ordered Transport Equipment/load units, equipment identifiers/details, and lightweight driver context are progressive optional facts. Operational events pin the exact transport revision effective when the event was recorded, so a later change cannot rewrite prior event context.

Carrier reuses an existing same-tenant `Customer` carrying the `CARRIER` role. Means and Equipment reuse the governed P3-01 central definitions activated for the organization. Route context reuses the P3-03 Shipment/plan/leg graph. Rail `Train → Wagon → Container` is represented as Means `Train` with an ordered Equipment list `[Wagon, Container]`; this does not create a permanent fleet or deeper containment registry.

The Persian Forwarder UI renders the explicit chain `Carrier → Means → Equipment`, supports multiple executions for one stage, progressive completion, reopen, and immutable revision history. It does not expose Cargo allocation, split, or transfer.

## Product Authority result

| Material observable difference | Final classification | Evidence result |
| --- | --- | --- |
| Multiple executions for an exact route stage | `AUTHORIZED` | Database, API, service, UI, reopen, and browser tests PASS |
| Separate Means and ordered Equipment/load units | `AUTHORIZED` | Reference, schema, serializer, UI, road and rail tests PASS |
| Multiple same-tenant Carriers | `AUTHORIZED` | Role eligibility, tenant fence, UI and browser tests PASS |
| Progressive optional execution details | `AUTHORIZED` | Missing identifiers remain neutral; no fabricated exception or data PASS |
| Immutable revision and event-time history | `AUTHORIZED` | Event pinning, old/new snapshot rendering and inactive-history tests PASS |
| Existing fixed owning-Expert authority | `PRESERVED` | Owner PASS; Admin, Platform Admin, non-owner, guessed and cross-scope writes denied |
| Carrier as Shipment owner/access source | `FORBIDDEN` | `NO`; no ownership or entitlement is inferred from Carrier |
| P3-05 Cargo allocation/split/transfer | `PRESERVED_AS_OUT_OF_SCOPE` | No model, API, UI, or entitlement implemented |

No material P3-04 difference was classified `UNKNOWN` or `VIOLATION`.

## Migration and PostgreSQL 18 evidence

- Migration target: `20261003_phase3_transport_execution`.
- Parent: `20261002_phase3_branched_route`.
- Alembic head count: `1`.
- PostgreSQL server: `18.0`, 64-bit, agent-owned loopback disposable cluster.
- Clean parent-to-head upgrade, legacy-row preservation, no inferred backfill, safe empty downgrade/re-upgrade, populated downgrade refusal, composite tenant constraints, two distinct concurrent creates, same-key concurrent replay, and concurrent revision conflict: `PASS`.
- Exact PostgreSQL qualification on the frozen Product SHA: `1 passed, 15 warnings in 4.90s`.
- No route-stage execution, Means, Equipment, Carrier, driver, or Cargo relation was seeded or inferred for historical rows.

## Authorization, privacy, and history evidence

- Exact persisted owning Transport Expert mutation: `PASS`.
- Organization Admin, Platform Admin, non-owning Expert and guessed-execution mutation denial: `PASS`.
- Cross-tenant Shipment, RouteLeg, Carrier, Means, and Equipment denial without partial write: `PASS`.
- Active central reference intersected with active organization adoption for new selection: `PASS`.
- Historical inactive Means/Equipment snapshots remain readable but unselectable: `PASS`.
- Optimistic version conflict, idempotent replay, concurrent create/revision fencing: `PASS`.
- Internal timeline receives the pinned transport snapshot: `PASS`.
- Customer/public timeline excludes private transport context and internal note: `PASS`.
- Carrier-derived Shipment ownership or access: `NO`.

## Automated evidence on the frozen Product SHA

| Evidence unit | Result |
| --- | --- |
| Focused backend P3-04 service/migration | `7 passed, 151 warnings in 6.98s` |
| Exact PostgreSQL 18 qualification | `1 passed, 15 warnings in 4.90s` |
| Full backend regression | `1395 passed, 111 skipped, 0 failed in 675.82s` |
| Focused frontend P3-04/page integration | `2 files, 34 tests passed` |
| Full frontend regression | `83 files, 402 tests passed in 232.58s` |
| Focused P3-01/P3-02/P3-03 backend regression | `15 passed` |
| Focused P3-02/P3-03 frontend regression | `3 files, 32 tests passed` |
| TypeScript check | `PASS` |
| Lint | `PASS` — 0 errors; 13 pre-existing warnings |
| Production build | `PASS` — advisory chunk-size/browser-data warnings only |
| Architecture governance check | `PASS` |
| Repository structure check | `PASS` |
| Compile/import and OpenAPI YAML/path contract | `PASS` |
| Alembic single-head check | `PASS` — `20261003_phase3_transport_execution` |
| Diff whitespace check | `PASS` |

Runtime identity: Python `3.13.9`, Node `v24.11.0`, npm `11.6.1`, PostgreSQL `18.0`.

## Browser Product evidence

The dedicated Google Chrome journey passed on the frozen Product SHA. Disposable run identity: `75034ce2678944eb8914060af1ce3da3`. Result: `1 passed in 19.2s`; `RUNNER_EXECUTION=PASS`; `E2E_CLEANUP=PASS`.

The normal Expert navigation opened the Shipment, created two road executions on one stage with different Carriers, created a rail execution, reopened the Shipment, verified progressive missing identifiers as a neutral state, recorded an event under Truck A, revised to Truck B/Carrier B/Trailer B, and confirmed the old event still rendered Truck A revision 1. It also proved inactive historical references remain visible but absent from selectors, customer timeline privacy, and denial for foreign Carrier/Means/Equipment/leg/Shipment, Organization Admin, Platform Admin, non-owner, and guessed execution identities.

| Evidence unit | Result |
| --- | --- |
| Route-stage execution | `PASS` |
| Multiple executions per stage | `PASS` |
| Means/Equipment separation and rail chain | `PASS` |
| Multiple Carrier execution context | `PASS` |
| Progressive details and reopen | `PASS` |
| Event-time immutable transport history | `PASS` |
| Tenant/authority negative paths | `PASS` |
| Customer/public privacy | `PASS` |
| Automated P3-04 Product slice | `PASS` |
| Human Product Walkthrough | `NOT_RUN` |

## Journey impact ledger

| Journey | P3-04 evidence status | Broader journey status |
| --- | --- | --- |
| `FWD-J04` | `PASS_FOR_P3_04_BOUNDARY` — owning Expert stage execution workflow | `NO_FULL_PHASE3_INTEGRATED_EVIDENCE_YET` |
| `FWD-J07` | `PASS_FOR_P3_04_BOUNDARY` — execution history and event context | `NO_FULL_PHASE3_INTEGRATED_EVIDENCE_YET` |
| `FWD-J08` | `PASS_FOR_P3_04_BOUNDARY` — tenant, role, privacy and cross-scope negatives | `NO_FULL_PHASE3_INTEGRATED_EVIDENCE_YET` |
| `FWD-J09` | `PASS_FOR_P3_04_BOUNDARY` — route stages, multiple Carriers, Means and Equipment | `TARGET_PHASE3 / NOT_RUN_END_TO_END` |
| `FWD-IPJ-02` | `PASS_FOR_P3_04_BOUNDARY` | `NOT_RUN_AS_FULL_INTEGRATED_JOURNEY` |
| `FWD-IPJ-04` | `PASS_FOR_P3_04_BOUNDARY` | `NOT_RUN_AS_FULL_INTEGRATED_JOURNEY` |

## Reference reconciliation

LPAF v2.7, the Operational Shipment Product Contract, Product Acceptance Journey Pack v1.1, Phase 3 Implementation Plan, UX Blueprint v2.1, ADR-002/004/017/022/034/042/043/046/047/057/058/059, architecture baseline, FDM, FDD, decision indexes, tenant ownership inventory, and OpenAPI were reconciled against the frozen Product SHA. Historical planning text remains historical. No canonical LPAF change is required.

```text
REFERENCE_RECONCILIATION=PASS
LPAF_REFERENCE_IMPACT=NONE
PROJECT_REFERENCE_IMPACT=NONE_AFTER_RECONCILIATION
```

## Final status ledger

```text
LPAF_BASELINE=2.7
PHASE3_P3_01=PASS
PHASE3_P3_02=PASS
PHASE3_P3_03=PASS
PHASE3_P3_04=PASS
ROUTE_STAGE_EXECUTION=PASS
MULTIPLE_EXECUTIONS_PER_STAGE=PASS
TRANSPORT_MEANS_MODEL=PASS
TRANSPORT_EQUIPMENT_MODEL=PASS
MEANS_EQUIPMENT_SEPARATION=PASS
MULTI_CARRIER_EXECUTION=PASS
CARRIER_SHIPMENT_OWNER=NO
PROGRESSIVE_EXECUTION_DETAILS=PASS
EXECUTION_HISTORY=PASS
LEGACY_EXECUTION_COMPATIBILITY=PASS
PERMANENT_FLEET_REGISTRY=NO
DRIVER_MANAGEMENT_EXPANDED=NO
P3_05_CARGO_ALLOCATION_IMPLEMENTED=NO
TENANT_ISOLATION=PASS
AUTHORIZATION_NEGATIVE_TESTS=PASS
JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY
AFFECTED_JOURNEYS=FWD-J04,FWD-J07,FWD-J08,FWD-J09,FWD-IPJ-02,FWD-IPJ-04
BROWSER_PRODUCT_JOURNEY=PASS
POSTGRESQL_18_QUALIFICATION=PASS
FULL_BACKEND_REGRESSION=PASS
FULL_FRONTEND_REGRESSION=PASS
MIGRATION_REQUIRED=YES
ALEMBIC_HEAD=20261003_phase3_transport_execution
ALEMBIC_HEAD_COUNT=1
MIGRATION_QUALIFICATION=PASS
PHASE3_P3_04_PRODUCT_HEAD=af3d1c4a8406b0a8ae71f9e5b76b87dc38751981
PHASE3_P3_04_EVIDENCE_HEAD=EVIDENCE_ONLY_DESCENDANT_REPORTED_IN_FINAL_HANDOFF
PRODUCT_AUTHORITY_RECONCILIATION=PASS
PRODUCT_VALIDATION_EVIDENCE_FOR_THIS_SLICE=COMPLETE
REFERENCE_RECONCILIATION=PASS
REFERENCE_IMPACT=NONE
GLOBAL_PRODUCT_VALIDATION=EVIDENCE_PENDING
HUMAN_PRODUCT_WALKTHROUGH=NOT_RUN
RELEASE_READY=NO
P3_05_STARTED=NO
P3_06_STARTED=NO
PRODUCTION_ACCESSED=NO
PRODUCTION_MUTATED=NO
DEPLOYMENT_PERFORMED=NO
RELEASE_CREATED=NO
CANONICAL_INTEGRATION=NOT_PERFORMED_AT_EVIDENCE_CAPTURE
CANONICAL_PUSH=NOT_PERFORMED_AT_EVIDENCE_CAPTURE
```

## Residual gates and exact next action

- Global Product validation remains `EVIDENCE_PENDING`; only an authorized human can complete the Human Product Walkthrough.
- Release readiness remains `NO`; no deployment, release, or Production action occurred.
- P3-05 remains unopened and requires its own Product Authority and implementation gate.
- The next permitted action is an evidence-only commit, fast-forward integration and push of P3-04, verification of local/remote `0/0`, cleanup of disposable resources, and a hard stop before P3-05.
