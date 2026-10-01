# Human Walkthrough — Shipment next-action ranking correction authority

Date: 2026-10-01 (Asia/Tehran). Baseline: LPAF v2.7. Rigor and capability route:
Level B / Sol. Canonical entry SHA: `c6152de9564afb84c504d071c115f2b196d288cb`.
Human Product Walkthrough remains `IN_PROGRESS`; Release Ready remains `NO`.

## Mission contract

| Field | Governed value |
| --- | --- |
| Outcome | Resolve `HW_GUIDED_UX_001` by making the existing Shared Operational Projection rank the current required Shipment stage ahead of later lifecycle work. |
| Scope in | Existing deterministic next-action projection, state-derived Persian action label, direct stage deep link, focused regression, owned disposable PostgreSQL 18 browser qualification, controlled canonical integration, and preserved-runtime source refresh. |
| Scope out | Stage sequence or transition semantics, automatic stage progress, Delivery/final-Delivery meaning, closure rules, tasks, allocation, ETA, documents, history, permissions, ownership, lifecycle transitions, Production, deployment, or release. |
| Owner / authority | Product Owner through the attached mission `FORWARDER — FIX SHIPMENT NEXT-ACTION RANKING`. |
| Definition of Done | Cases 1–8 pass; current stage, process progress, task readiness, primary next action and attention are consistent; the exact stage is deep-linked; affected regression and browser journeys pass; preserved walkthrough data and Stage 1 STARTED event are unchanged; canonical and remote are 0/0. |
| Stop conditions | Any need to change stage, Delivery, closure, permission, ownership, lifecycle, schema/migration, preserved business data, Production, deployment, release, or Human Walkthrough result. |

## Product Authority Record

| Required field | Record |
| --- | --- |
| `AUTHORIZED_PRODUCT_CHANGES` | When a required stage is STARTED and incomplete, rank completion of that exact stage before later lifecycle actions; when no stage is started and the next required stage is available, recommend starting it; expose a direct deep link to the actionable stage; allow existing Delivery and closure actions only after required stage work is satisfied according to existing authoritative state. |
| `DELEGATED_TECHNICAL_CHOICES` | Small changes inside the existing ranking function, deterministic priority numbers, state-derived Persian copy, fragment identity, focused tests and evidence layout. |
| `PROTECTED_OUT_OF_SCOPE_BEHAVIOR` | All stage sequence/state/transition and lifecycle semantics; Delivery and closure rules; task status; allocation; ETA; documents; Unified History; permissions; ownership; all preserved walkthrough business facts; Production; deployment; release. |
| `DECISIONS_NEEDED` | `NONE` at entry. |
| `APPROVING_OWNER_OR_AUTHORITY` | Product Owner; LPAF v2.7 supplies governance only. |
| `APPROVAL_REFERENCE` | Attached mission dated 2026-10-01, sections 1–14. |

## Facts, assumptions, unknowns, and boundaries

FACT: `operational_projection_service` is the one existing Shared Operational
Projection and owns ranking only, not workflow truth. Its prior `_action` gave
the first mandatory closure-attention item rank 5, while stage work had rank 30.
Because `FINAL_DELIVERY_EXISTS` sorted before the stage closure criterion, Final
Delivery could become primary while the stage projection still reported a
STARTED required stage.

FACT: `shipment_stage_service.read` supplies the current stage, stage status,
configured display name, required flag, stable public identity and current
recording authority. `ShipmentOperationalStages` owns the actionable stage UI.

ASSUMPTION: priority values, helper boundaries, exact explanatory copy and the
fragment identifier are delegated technical choices as long as they implement
the authorized precedence without changing domain semantics.

UNKNOWN pending Verify: exact Product/evidence/final canonical SHAs, disposable
runtime identity, final test results and preserved database comparison.

## Journey and reference impact

`JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY`.

- Directly affected: `FWD-J04`, `FWD-J08`, `FWD-J09`, `FWD-IPJ-02`, `FWD-IPJ-04`.
- Required slice rerun: Shipment Summary, Operational Stages, stage deep link,
  closed and unauthorized states.
- Required integrated rerun: Guided Operational Workspace and the affected
  operational Shipment browser journeys on the exact candidate.
- Human result: Product Owner walkthrough continues; no agent-granted PASS.
- LPAF reference impact: `NONE`; v2.7 is applied, not changed.
- Project reference impact: `UPDATE_REQUIRED` for this authority and exact-candidate evidence only; Product Contract, Journey Pack, stage/Delivery/closure references remain unchanged.

## PDA-07 target reconciliation

The only authorized observable difference is the primary ranking label and
deep link for the current required stage. Stage state, Delivery, closure,
attention facts and every protected adjacent behavior must classify as
`PRESERVED`. Any other observable difference is `VIOLATION` or `UNKNOWN` and
blocks integration.
