# Phase 3 P3-05 — Cargo allocation and trace qualification evidence

- **Record date:** 2026-09-25
- **Governing baseline:** LPAF v2.7 — ACTIVE / FROZEN / CANONICAL
- **Rigor / route:** Level C / Astra
- **Qualified slice:** P3-05 only — stage-scoped planned and actual distribution, split, correction, explicit transfer/handoff and end-to-end Cargo trace
- **Mission:** [P3-05 Cargo Allocation Mission Contract](../../product/phase3/P3-05-CARGO-ALLOCATION-MISSION-CONTRACT-FA.md)
- **Architecture:** [ADR-060](../adr/ADR-060-stage-scoped-cargo-allocation-and-trace.md)
- **Canonical base:** `integration/golden-controlled@3d4564bad7df7a2ec5aade24132c74d9c1ad0015`
- **Candidate branch:** `codex/phase3-p3-05-cargo-allocation-trace`
- **P3-05 Product SHA:** `630c31ad8e3ca845a8eec2e7c7faf8489f0096ca`
- **Evidence SHA:** evidence-only descendant of the Product SHA, reported in the final delivery record
- **Alembic head:** `20261004_phase3_cargo_allocation_trace`, one head, exact P3-04 parent `20261003_phase3_transport_execution`

This record qualifies P3-05 only. P3-06 does not start until this candidate is integrated into canonical, pushed to `github`, fetched again and confirmed `0/0`. No P3-07+, deployment, release or Production action is authorized. `GLOBAL_PRODUCT_VALIDATION=EVIDENCE_PENDING`; `RELEASE_READY=NO`.

## Product Authority and persisted behavior

The explicit Product Owner mission authorizes incomplete and excess planned allocation and actual reports as **non-blocking warnings**. No allocation lifecycle/status, automatic Exception, Attention, SLA or Shipment status change was introduced. `ShipmentCargoItem` remains the physical Cargo and requested/planned/known-actual quantity SOR. Each `RouteStageExecution` distribution has separate `PLANNED` and `ACTUAL` current rows. The same Cargo may appear in successive route stages without summing into a larger physical quantity.

The owning Transport Expert can revise a stage plan, correct stage actuals, release a current allocation with history, transfer between executions in the same stage, or hand off downstream. The command validates Shipment, Cargo, Cargo owner tenant, exact plan/leg branch, source/target execution unit, effective execution revision, Expert authority and UOM continuity. A Cargo row lock serializes its mutations, current allocation locks have deterministic primary-key order, expected versions fence stale commands and idempotency keys handle exact replay. One transaction records source/target effects and immutable revision/transfer facts. Downstream handoff preserves prior-stage actual history. Legacy rows retain unknown stage/dimension and receive no fabricated backfill.

The Persian Expert UI shows requested, planned and known actual Cargo quantities, stage planned/actual totals, remaining/unrecorded amounts, means/equipment, non-blocking warnings, revision history and explicit transfer. It loads through normal Shipment navigation and persists across reopen. History stays secondary and accessible.

## Evidence on the frozen Product SHA

| Evidence unit | Result |
| --- | --- |
| Focused P3-05 backend/API, migration, legacy adapter and authorization | `PASS` — stage plan/actual, split, warnings, Decimal, correction, branch denial, replay, transfer and preserved release history |
| PostgreSQL 18 owned loopback qualification | `PASS` — parent upgrade with a real legacy allocation, null meaning preserved, no invented revision, downgrade/re-upgrade, populated downgrade refusal, concurrent version conflicts and atomic transfer |
| Normal Google Chrome P3-05 Product journey | `PASS` — planned 60+40, under/over warnings, actual variation, correction history, same-stage transfer, next-stage continuity, Cargo plan/actual correction, reopen, negative tenant/non-owner/guessed IDs and no automatic Exception |
| Full backend regression | `PASS` — 1,403 passed, 112 skipped; no failures |
| Full frontend regression | `PASS` — 84 files, 404 tests |
| Focused frontend P3-05 | `PASS` — totals, remainder, warnings, history and versioned plan revision |
| TypeScript, ESLint, production build | `PASS` — lint has 0 errors and 13 pre-existing warnings; build has advisory chunk/browser-data warnings |
| OpenAPI, architecture governance, structure, backend determinism, diff check | `PASS` |
| Adjacent P3-04/P3-02 Chrome regressions | `PASS` — both normal Chrome journeys on the unchanged Product runtime; the P3-02 test assertion was scoped to the rendered source field and its API URL made runner-aware, with no runtime Product change |
| Human Product Walkthrough | `NOT_RUN` — separate Product gate |

The browser and PostgreSQL work used synthetic data in locally owned disposable PostgreSQL 18 databases. Neither qualification accessed Production.

## Journey and reference status

`JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY`. `FWD-J04`, `FWD-J08`, `FWD-J09` and `FWD-IPJ-04` have P3-05-boundary evidence only; no full integrated Phase 3 journey is claimed. The Product Acceptance Journey Pack remains `EVIDENCE_PENDING` globally.

`REFERENCE_RECONCILIATION=PASS`; `REFERENCE_IMPACT=NONE` after updating ADR-060 and its indexes, the allocation contract, OpenAPI, tenant inventory, domain map and this current Phase 3 status. Historical proposals and earlier slice evidence are not rewritten. The P3-05 rule is `QUANTITY_MISMATCH=NON_BLOCKING_WARNING`.

`PRODUCT_AUTHORITY=PASS`; no material Product difference remains `UNKNOWN` or `VIOLATION`. The next controlled gate checks clean candidate, exact Product SHA/evidence ancestry, one migration head, current references, fast-forward-only canonical integration, push/fetch and local/remote `0/0` before P3-06 work begins.
