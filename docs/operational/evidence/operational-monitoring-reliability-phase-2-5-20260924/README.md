# Operational Monitoring Reliability Phase 2.5 — LPAF v2.7 requalification

- Date: 2026-09-24
- LPAF baseline: v2.7 — `ACTIVE / FROZEN / CANONICAL`
- Ancestry case: `CASE B`
- Branch: `codex/phase2-5-v27-integration-requalification`
- Canonical governance parent: `9b4298c0e89fb2b444bf159ba8e7a744d0eb88e4`
- Original qualified Product HEAD: `de94df0413fb68c5a542e1887476477da3295f24`
- Requalified Product HEAD: `1aea4bebdde7e240a903baea1b7b678993f3c505`
- Alembic head: `20260929_operational_monitoring_reliability` (one head)
- Environment: owned disposable local/UAT PostgreSQL 18 with synthetic data
- Browser: Google Chrome via Playwright

## Verdict

`PASS — PHASE 2.5 REQUALIFIED ON THE LPAF v2.7 CANDIDATE`

The current canonical line advanced from the Phase 2.5 base only through the
Forwarder `AGENTS.md` synchronization to LPAF v2.7. The five bounded Phase 2.5
Product commits were replayed linearly without merge or squash. The earlier
evidence commit was not replayed. This evidence was regenerated against the
full Product SHA `1aea4bebdde7e240a903baea1b7b678993f3c505`.

A direct comparison between the original and rebased Product candidates found
changes only in `AGENTS.md`, ADR-055 governance authority, and the Phase 2.5
mission contract. There is no backend, frontend, runtime, migration, script,
contract, or public-asset difference between the two Product candidates.

## Qualification results

| Gate | Result |
| --- | --- |
| Focused backend reliability/API/migration | PASS — 44/44 |
| Focused frontend freshness | PASS — 20/20 across 3 files |
| PostgreSQL concurrency/fencing | PASS — 14/14 |
| PostgreSQL clean upgrade | PASS |
| Downgrade to `20260928_operational_workspace_phase2` and re-upgrade | PASS |
| Browser Product qualification | PASS — 9/9 Chrome journeys |
| Full backend | PASS — 1373 passed, 107 skipped, 0 failed |
| Full frontend | PASS — 78 files, 383 tests, 0 failed |
| TypeScript | PASS |
| ESLint `--quiet` | PASS |
| Production frontend build | PASS |
| Python compileall | PASS |
| Repository structure | PASS |
| Architecture governance | PASS |
| One Alembic head | PASS |
| `git diff --check` | PASS |

The browser was closed before the CLI evaluation that created the current
Attention. Workspace and Control Tower consumed the same persisted freshness
truth. The browser qualification also reran Customer Account, Public Tracking,
Request/Shipment separation, tenant isolation, and Phase 1/2 regression paths.

## Product Authority and journey reconciliation

- `PRODUCT_AUTHORITY_RECONCILIATION=PASS` — all observable Phase 2.5 behavior is
  authorized or preserved; no PDA-07 violation or unknown remains.
- `JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY` — Transport Expert Workspace,
  Attention consumption, and Control Tower operational attention/freshness are
  existing journeys whose reliability/freshness behavior is affected.
- `SLICE_JOURNEY=PASS` on the exact Product SHA above.
- `INTEGRATED_PRODUCT_JOURNEYS=NOT_YET_RUN_PRE_RELEASE`.
- `HUMAN_PRODUCT_WALKTHROUGH=NOT_YET_RUN_PRE_RELEASE`.
- `PRODUCT_VALIDATION_EVIDENCE_FOR_THIS_SLICE=COMPLETE`.
- `GLOBAL_PRODUCT_VALIDATION=EVIDENCE_PENDING`.
- `RELEASE_READY=NO`.
- `REFERENCE_IMPACT=NONE` after the bounded v2.7 governance reconciliation.

Integrated whole-Product journeys and the authorized Human Product Walkthrough
are intentionally deferred to a separate pre-release Product Acceptance
mission. No human approval is inferred by this evidence.

## Safety boundary

Production was not accessed or mutated. No deployment, release artifact, Phase
3, AI, Finance, Carrier Portal, Driver Portal, business calendar, or new SLA
type was started.

## Artifacts

- `result.json`: machine-readable Product-SHA-bound result.
- Evaluation/status logs: browser-independent execution and freshness evidence.
- Phase 2.5 screenshots: current background-evaluated Attention and the shared
  Workspace/Control Tower stale state.
- Phase 1/2 screenshots: bounded browser regression evidence.
