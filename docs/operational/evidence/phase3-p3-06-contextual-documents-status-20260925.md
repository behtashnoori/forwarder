# Phase 3 P3-06 — contextual document candidate and blocked integration

- **Record date:** 2026-09-25
- **Governing baseline:** LPAF v2.7 — ACTIVE / FROZEN / CANONICAL
- **Rigor / route:** Level C / Astra
- **Canonical base:** `integration/golden-controlled@bd3610c4016cf643b6243fb0490260ac49a8b92d` (P3-05 integrated)
- **Candidate branch:** `codex/phase3-p3-06-contextual-documents`
- **P3-06 Product SHA:** `b1d973ada8122312cf0ad96db4f9623141cfb0c5`
- **Evidence SHA:** evidence-only descendant of the Product SHA, reported in the final delivery record
- **Candidate Alembic head:** `20261005_phase3_contextual_documents`, one head, exact P3-05 parent `20261004_phase3_cargo_allocation_trace`
- **Canonical Alembic head:** `20261004_phase3_cargo_allocation_trace`

## Scope and Product authority

The owning Expert can attach an exact `CaseDocumentFile` version to one typed Shipment, Cargo, RouteLeg or ExecutionUnit context. Context and visibility are independent. `INTERNAL` remains the safe default; `EXPLICIT_SHARED` addresses selected active portal accounts in the same tenant. `CARGO_OWNER` records policy intent for a Cargo context but grants no Customer access while DN10 has no governed Portal Account ↔ CRM Customer entitlement. Delivery is only an extension boundary; P3-08 has not started.

Replacement preserves previous file versions and starts the new exact version as internal, without inheriting Customer audience. Context and audience changes use an expected version and append a before/after event with actor and time. Legacy files receive no guessed context or visibility. Customer list and download authorize the active principal, tenant, exact active version and explicit audience before responding; Customer filenames are neutral. The existing Admin oversight read is preserved, with no Admin/Customer/Platform operational management grant and no Public file access.

## Qualification evidence and open gate

| Evidence unit | Result |
| --- | --- |
| Focused backend authorization and exact-version tests | `PASS` — explicit sharing, revocation, history, replacement, stale/guessed version and Admin boundary |
| PostgreSQL 18 migration | `PASS` — legacy row preserved, empty downgrade/re-upgrade, populated downgrade refused, one linear head |
| Normal Google Chrome P3-06 journey | `PASS` for typed upload/reopen, context and audience changes, explicit share, Customer A/B denial, exact version, Admin denial and multi-file partial retry |
| Adjacent Google Chrome journeys | P3-05, P3-04, P3-03, P3-02 and P3-01 `PASS` on the same Product runtime |
| Full frontend regression | `PASS` — 85 files, 406 tests |
| Full backend regression | `PASS` — 1,406 passed, 113 skipped on the frozen Product SHA |
| TypeScript, ESLint, production build | `PASS` — lint 0 errors/13 pre-existing warnings; build advisory warnings only |
| OpenAPI, architecture governance, structure, determinism, diff check | `PASS` |
| Positive Customer-own-Cargo entitlement journey | `BLOCKED` — canonical has no valid explicit Portal Account ↔ CRM Customer identity entitlement; the required authorized Customer A Cargo download cannot be demonstrated without inventing DN10 linkage |
| Human Product Walkthrough | `NOT_RUN` — separate Product gate |

The Chrome fixture uses synthetic accounts and owned PostgreSQL 18 databases. It proves that an explicitly shared Shipment document reaches only the selected portal account and that Cargo-owner documents currently deny all portal accounts. It does **not** satisfy the mission's positive Cargo-owner Customer journey. `P3_06_QUALIFICATION=BLOCKED`; this candidate is not integrated or pushed as canonical. P3-05 remains the final canonical baseline. There was no Production access, deployment or release.

The P3-01 browser regression needed evidence-only selector and fixture updates for the existing P3-02 Cargo form (required CRM owner, separate planned quantity). The P3-03 regression needed a heading-scoped assertion because the same stage label appears in the route and execution sections. These changes do not alter Product runtime behavior.

## Decisions, journeys and references

`DN02_DOCUMENT_VISIBILITY_STATUS=RESOLVED_FOR_P3_06` for the bounded document policy; `DN02_OWNER_TRANSFER_PORTION=OPEN_FOR_P3_13`; `DN09_STATUS=OPEN`; `DN10_STATUS=OPEN`. Resolving DN10 requires an independently approved identity/entitlement contract and a positive authorized Cargo-owner privacy journey. It is not inferred from Cargo ownership, Shipment membership, email, name, phone or Request source.

`ShipmentRequest` can separately reference a portal account and a CRM Customer, and the existing CRM workflow can manually link or relink the latter. That request-level pairing is mutable and is not an approved Portal Account ↔ CRM Customer identity entitlement for Cargo authorization.

`JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY`; affected journeys are `FWD-J02`, `FWD-J04`, `FWD-J08`, `FWD-J09`, `FWD-IPJ-03`, `FWD-IPJ-04`. Candidate-only browser evidence does not make integrated Product Journeys globally pass. `GLOBAL_PRODUCT_VALIDATION=EVIDENCE_PENDING`; `RELEASE_READY=NO`; `P3_07_STARTED=NO`; `P3_08_STARTED=NO`.

Current ADR-061, ADR-050 note, decision/architecture indexes, OpenAPI, tenant inventory, Product contract and Phase 3 status are reconciled on this candidate. Historical ADRs and prior slice evidence were not rewritten. The controlled fast-forward integration gate is intentionally closed until the positive Customer-own-Cargo requirement can be met under a governed entitlement.

`REFERENCE_RECONCILIATION=PASS`; `REFERENCE_IMPACT=NONE` within the candidate. This records candidate consistency, not canonical integration.

## Cleanup

The browser runner stopped its temporary backend/frontend processes. The owned loopback PostgreSQL 18 cluster was stopped after qualification (`pg_ctl` reports no server running). Automatic host approval rejected recursive deletion of its already-stopped temporary directory, so `C:\Users\pc\AppData\Local\Temp\forwarder-p305-owned-20d473edf6884a89adb93820f35d2342` remains. No unsafe alternative deletion was attempted. Both candidate and canonical Git worktrees are clean.
