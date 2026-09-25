# Phase 3 P3-02 — Cargo Lineage Qualification Evidence

- **Record date:** 2026-09-25
- **Governing baseline:** LPAF v2.7 — ACTIVE / FROZEN / CANONICAL
- **Rigor / route:** Level B / Astra
- **Qualified slice:** P3-02 only — per-Cargo Customer/Request lineage, semantic quantities, and progressive details
- **Mission:** [P3-02 Cargo Lineage Mission Contract](../../product/phase3/P3-02-CARGO-LINEAGE-MISSION-CONTRACT-FA.md)
- **Architecture:** [ADR-057](../adr/ADR-057-cargo-customer-request-lineage-and-quantity-semantics.md)
- **Product baseline:** `integration/golden-controlled@012d1fa1ae9afef902f0fada5ce4e5bf652edfad`
- **Candidate branch:** `codex/phase3-p3-02-cargo-lineage`
- **Phase 3 Product SHA:** `b38a4cb952f7ad74079399991511f35f63e4fd82`
- **Evidence SHA:** this document's evidence-only descendant, reported in the final delivery record

This record qualifies only P3-02. It does not claim completion of P3-03 or later slices, a full integrated Product journey, Human Product Walkthrough, global Product validation, release readiness, deployment, or Production access.

## Qualified Product boundary

One Operational Shipment can now retain Cargo lines for different active CRM Customers in the same tenant. Each new semantic Cargo line can be direct, with no fabricated Request, or can point to an authorized same-tenant Request and optional Request Cargo. The source Request's explicit Customer must match the Cargo Customer. Request Cargo quantity is copied only from the exact source fact when its governed UOM matches; conflicting quantities or UOMs are rejected and no conversion occurs.

Requested, planned, and actual quantities are distinct API/UI facts. The existing `quantity` column mirrors only an explicitly supplied planned quantity for compatibility. Historical rows and legacy commands with only `quantity` remain visibly `UNKNOWN`; migration performs no semantic inference or backfill.

Cargo Type, UOM, and Packaging Type must be active centrally and activated for the Shipment organization. HS, Packaging, weight, volume, destination, and actual quantity remain progressively completable. Missing HS is shown as incomplete and is never a blocker. The owning Transport Expert is the only Cargo mutator; Organization Admin and another Expert cannot edit. Customer Portal receives no new projection or permission.

Meaningful corrections use optimistic versioning and append bounded `OperationalAudit` history. Existing allocation, execution, tracking, route, document, lifecycle, and Customer Portal behavior remains outside this slice and unchanged.

## Product Authority result

| Material observable difference | Final classification | Evidence result |
| --- | --- | --- |
| Different Cargo Customers in one Shipment | `AUTHORIZED` | API, database, UI, reopen, and tenant tests PASS |
| Optional Request/Request Cargo lineage | `AUTHORIZED` | Exact source, Customer match, UOM match, and authorization tests PASS |
| Direct Cargo without Request | `AUTHORIZED` | API/UI persistence and no-fake-lineage checks PASS |
| Requested/planned/actual quantities stay distinct | `AUTHORIZED` | API/UI and PostgreSQL constraints PASS |
| Legacy quantity meaning | `PRESERVED_AS_UNKNOWN` | Zero-backfill migration and serializer/UI checks PASS |
| Progressive HS/Packaging/weight/volume/destination | `AUTHORIZED` | Create-incomplete, later correction, audit, and reopen PASS |
| Route/execution/allocation/lifecycle/portal changes | `PRESERVED_AS_OUT_OF_SCOPE` | Full regressions PASS; no new command or entitlement added |

No material difference was classified `UNKNOWN` or `VIOLATION` in P3-02.

## Migration and PostgreSQL 18 evidence

- Migration target: `20261001_phase3_cargo_lineage`.
- Parent: `20260930_phase3_reference_catalog`.
- Alembic head count: `1`.
- PostgreSQL server: `18.0` on an agent-owned loopback disposable cluster.
- Clean base-to-head upgrade, empty/no-seed verification, empty downgrade/re-upgrade, legacy-row preservation, runtime writes, database constraints, and populated downgrade refusal: `PASS`.
- Exact PostgreSQL qualification on the frozen Product SHA: `1 passed, 12 warnings in 6.31s`.
- No Customer, Request, quantity meaning, Packaging, HS, weight, volume, or destination was backfilled.

The populated downgrade guard deliberately refuses destructive loss; safe application rollback retains the expanded nullable schema until separately authorized reconciliation.

## Authorization, privacy, and history evidence

- Exact persisted owning Transport Expert mutation: `PASS`.
- Organization Admin and non-owning Expert mutation denial: `PASS`.
- Foreign Customer, foreign Request, and mismatched Request Customer denial without partial write: `PASS`.
- Inactive organization Packaging and wrong-dimension/UOM lineage denial: `PASS`.
- Optimistic version conflict, append-only create/update audit, and retained history: `PASS`.
- Customer Portal projection/entitlement added: `NO`.

## Automated evidence on the frozen Product SHA

| Evidence unit | Result |
| --- | --- |
| Focused backend Cargo lineage/migration/foundation | `22 passed` |
| Exact PostgreSQL 18 qualification | `1 passed, 12 warnings` |
| Full backend regression | `1382 passed, 109 skipped, 0 failed` |
| Focused frontend Cargo UI | `12 passed` |
| Full frontend regression | `81 files, 395 tests passed` |
| TypeScript check | `PASS` |
| Lint | `PASS` — 0 errors; 13 pre-existing warnings |
| Production build | `PASS` — advisory chunk-size/browser-data warnings only |
| Architecture governance check | `PASS` |
| Repository structure check | `PASS` |
| OpenAPI YAML/runtime route parity | `PASS` |
| Alembic single-head check | `PASS` — `20261001_phase3_cargo_lineage` |
| Diff whitespace check | `PASS` |

Runtime identity: Python `3.13.9`, Node `v24.11.0`, npm `11.6.1`, PostgreSQL `18.0`.

## Browser Product evidence

The dedicated real-browser P3-02 journey passed on the frozen Product SHA with runner cleanup passing. The successful disposable run identity was `4d7b013a31854cfb8484f9e7667c2c56`.

The scenario used normal navigation to the Shipment, created a Request-sourced Cargo for Customer A, created a direct Cargo for Customer B without Request lineage, displayed requested/planned/actual values side by side, showed incomplete fields, progressively completed actual quantity, HS, weight, volume, and destination, verified create/update history, navigated away, reopened the Shipment through the normal list, and verified persistence. RTL, horizontal overflow, API failures, page errors, failed requests, and console errors were checked. Result: `1 passed in 18.1s`; `RUNNER_EXECUTION=PASS`; `E2E_CLEANUP=PASS`.

| Evidence unit | Result |
| --- | --- |
| `P3-02-MULTI-CUSTOMER` | `PASS` |
| `P3-02-REQUEST-LINEAGE` | `PASS` |
| `P3-02-DIRECT-NO-FAKE-REQUEST` | `PASS` |
| `P3-02-THREE-QUANTITIES` | `PASS` |
| `P3-02-PROGRESSIVE-COMPLETION` | `PASS` |
| `P3-02-REFERENCES` | `PASS` |
| `P3-02-TENANT-AUTHORITY` | `PASS` |
| `P3-02-LEGACY-UNKNOWN` | `PASS` |
| Automated P3-02 Product slice | `PASS` |
| Human Product Walkthrough | `NOT_RUN` |

## Journey impact ledger

The statuses below are deliberately bounded. A P3-02 boundary PASS does not become an integrated-journey PASS.

| Journey | P3-02 evidence status | Broader journey status |
| --- | --- | --- |
| `FWD-J02` | `PARTIAL` — Request/Customer lineage regression covered; no Customer Account/end-to-end Quote walkthrough | `NO_INTEGRATED_EVIDENCE_YET` |
| `FWD-J03` | `PASS_FOR_P3_02_BOUNDARY` — authorized Request-to-operational Cargo handoff | `NO_INTEGRATED_EVIDENCE_YET` |
| `FWD-J04` | `PASS_FOR_P3_02_BOUNDARY` — owning Expert normal navigation, correction, persistence | `NO_INTEGRATED_EVIDENCE_YET` |
| `FWD-J08` | `PASS_FOR_P3_02_BOUNDARY` — tenant and role negatives | `NO_INTEGRATED_EVIDENCE_YET` |
| `FWD-J09` | `PASS_FOR_P3_02_BOUNDARY` — multi-Customer/multi-Cargo assembly only | `TARGET_PHASE3 / NOT_RUN_END_TO_END` |
| `FWD-IPJ-01` | `PASS_FOR_P3_02_BOUNDARY` | `NOT_RUN_AS_INTEGRATED_JOURNEY` |
| `FWD-IPJ-04` | `PASS_FOR_P3_02_BOUNDARY` | `NOT_RUN_AS_INTEGRATED_JOURNEY` |

## Reference reconciliation

LPAF v2.7, the Operational Shipment Product Contract, Product Acceptance Journey Pack v1.1, Phase 3 Implementation Plan, UX Blueprint v2.1, ADR-002/021/022/028/034/042/043/046/047/056/057, architecture baseline, FDM, FDD, decision indexes, tenant ownership inventory, and OpenAPI were reconciled against the frozen Product SHA. Historical planning text remains historical. No canonical LPAF change is required.

```text
REFERENCE_RECONCILIATION=PASS
LPAF_REFERENCE_IMPACT=NONE
PROJECT_REFERENCE_IMPACT=NONE_AFTER_RECONCILIATION
```

## Final status ledger

```text
LPAF_BASELINE=2.7
PHASE_3_IMPLEMENTATION_STARTED=YES
PHASE3_CURRENT_SLICE=P3-02
PHASE3_P3_01=PASS_ALREADY_IN_CANONICAL_BASE
PHASE3_P3_02=PASS
P3_02_ENGINEERING_COMPLETE=YES
P3_02_PRODUCT_COMPLETE=YES_BOUNDED_SLICE
CARGO_CUSTOMER_LINEAGE=PASS
REQUEST_LINEAGE=PASS
DIRECT_CARGO_WITHOUT_REQUEST=PASS
THREE_QUANTITY_SEMANTICS=PASS
PROGRESSIVE_CARGO_DETAILS=PASS
GOVERNED_REFERENCE_CONSUMPTION=PASS
OWNING_EXPERT_AUTHORITY=PASS
TENANT_ISOLATION=PASS
HISTORY_PRESERVATION=PASS
UNIT_CONVERSION_IMPLEMENTED=NO
HS_MANDATORY_RULE_IMPLEMENTED=NO
DN01_STATUS=OPEN
DN05_STATUS=OPEN
DN08_STATUS=PARTIAL_DECISION_NEEDED
DN10_STATUS=OPEN
JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY
AFFECTED_JOURNEYS=FWD-J02,FWD-J03,FWD-J04,FWD-J08,FWD-J09,FWD-IPJ-01,FWD-IPJ-04
SLICE_JOURNEYS=PASS
INTEGRATED_PRODUCT_JOURNEYS=NOT_RUN
BROWSER_PRODUCT_JOURNEY=PASS
FULL_BACKEND_REGRESSION=PASS
FULL_FRONTEND_REGRESSION=PASS
MIGRATION_REQUIRED=YES
ALEMBIC_HEAD=20261001_phase3_cargo_lineage
ALEMBIC_HEAD_COUNT=1
MIGRATION_QUALIFICATION=PASS
PRODUCT_AUTHORITY_RECONCILIATION=PASS
PRODUCT_VALIDATION_EVIDENCE_FOR_THIS_SLICE=COMPLETE
PHASE3_PRODUCT_HEAD=b38a4cb952f7ad74079399991511f35f63e4fd82
PHASE3_EVIDENCE_HEAD=EVIDENCE_ONLY_DESCENDANT_REPORTED_IN_FINAL_HANDOFF
REFERENCE_RECONCILIATION=PASS
REFERENCE_IMPACT=NONE
GLOBAL_PRODUCT_VALIDATION=EVIDENCE_PENDING
HUMAN_PRODUCT_WALKTHROUGH=NOT_RUN
RELEASE_READY=NO
P3_03_STARTED=NO
P3_04_STARTED=NO
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

- `DN01`, `DN05`, and `DN10` remain open; `DN08` remains partial. P3-02 does not consume those unresolved decisions.
- Global Product validation remains `EVIDENCE_PENDING`; only an authorized human can complete the Human Product Walkthrough.
- Release readiness remains `NO`; no deployment, release, or Production action occurred.
- The next permitted action is evidence-only commit, fast-forward integration and push of P3-02, verification of local/remote `0/0`, and only then creation of a fresh P3-03 worktree from the integrated canonical SHA.
