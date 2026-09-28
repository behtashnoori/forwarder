# Human Walkthrough Expert Request Commercial Hardening — Mission Authority

- Date: 2026-09-28 (Asia/Tehran)
- Governing baseline: `LPAF v2.7 — ACTIVE / FROZEN / CANONICAL`
- Mission type: governed post-final-candidate Human Walkthrough hardening
- Rigor / capability route: `Level B / Sol`
- Product Owner authority: the attached mission titled
  `Forwarder — HUMAN WALKTHROUGH EXPERT REQUEST COMMERCIAL HARDENING`
- Verified canonical entry:
  `integration/golden-controlled@9f28c42110b2c0ccc626cc238f7063ed855c7393`
- Historical Product SHA before this hardening:
  `521380b37d4c09a695cd87984f783ef5670cb127`
- Required schema identity: one Alembic head,
  `20261012_phase3_cargo_eta`; `MIGRATION_REQUIRED=NO`

This record authorizes only the Product Owner-observed Expert Request defects.
It grants no Release, deployment, Production, migration, AI, agent or GPS
authority and cannot grant the Human Product Walkthrough PASS.

## Entry evidence

### FACT

- Local canonical and `github/integration/golden-controlled` resolve to the
  entry SHA above, ahead/behind is `0/0`, and canonical is clean.
- The requested isolated branch and worktree start from that exact SHA.
- Alembic reports one head: `20261012_phase3_cargo_eta`.
- `ShipmentRequest.status` is the commercial lifecycle SOR. Quote response is
  an independent immutable fact on the exact `ExpertQuote`.
- A new Quote currently moves the Request to `waiting_for_customer`; Customer
  response persists on the Quote without changing Request status.
- `CRMCustomerLinkAudit` and `ExpertConsoleLog` already preserve link/relink
  history. `ShipmentRequest.customer_id` is independent from the
  Admin-managed `CustomerEntitlement` DN10 SOR.
- Existing accepted-Quote Shipment creation is explicit, idempotent and
  requires an accepted Quote, a Request CRM Customer, owning-Expert scope and
  operational create authority. It does not run on Quote acceptance.
- Current Expert primary navigation has no Request entry or selected-route
  semantics; the direct-creation CTA is always visually primary.
- Current Request timeline exposes raw action codes and technical notes.
- Current Cargo presentation emits raw UOM symbols and has no neutral fallback
  when both description and type are unavailable.
- The current quote-currency contract labels `IRR` as `تومان (IRR)`.

### ASSUMPTION

- Component boundaries, endpoint spelling, additive DTO fields, deterministic
  read projections, Persian copy and test/evidence structure are delegated
  technical choices when the approved behavior below remains unchanged.

### UNKNOWN TO CLOSE DURING VERIFY

- Exact final Product/evidence SHAs and isolated qualification runtime IDs.
- Final full-suite and browser-journey results on the frozen candidate.
- Read-only preserved walkthrough-runtime identity after canonical integration.

## Product Authority Record

| Required field | Record |
| --- | --- |
| `AUTHORIZED_PRODUCT_CHANGES` | Add primary «درخواست‌ها و قیمت‌ها» navigation and route-aware selected state; make the owning Expert's Request-parented selection/link of an existing active same-organization CRM Customer available without CRM administration; preserve audited relink semantics already present; separate Request commercial state, latest Quote response and derived next action; make `waiting_for_customer` valid only when the current latest Quote has no response; reconcile list buckets/counts; narrate Request history in simple Persian without raw codes; fix Cargo title/UOM/number presentation; correct IRR/USD labels and grouped Quote amounts; expose the existing explicit Request-to-Shipment action only when its existing prerequisites are satisfied. |
| `DELEGATED_TECHNICAL_CHOICES` | Request-parented API shape, server-side tenant/owner predicates, additive read-model fields, derived bucket query, presentation helper/component structure, safe timeline adapter, copy details, fixtures and evidence organization. |
| `PROTECTED_OUT_OF_SCOPE_BEHAVIOR` | No CRM Customer creation by Expert; no Portal Account entitlement grant/revoke/inference; no identity merge; no Customer/Request/Quote/history rewrite; no automatic Shipment; no new Shipment creation path or Phase 3 operational semantics; no Control Tower or Workspace Shipment-count reinterpretation; no schema/migration; no AI/agent/GPS; no Production, deploy or Release; no self-granted Human Walkthrough PASS. |
| `DECISIONS_NEEDED` | `NONE` at entry. Stop for `ARCHITECTURE_REVIEW_REQUIRED` if a schema/migration becomes necessary or current history cannot support bounded relink safely. |
| `APPROVING_OWNER_OR_AUTHORITY` | Product Owner issuing the explicit Expert Request Commercial Hardening mission; LPAF v2.7 for governance. |
| `APPROVAL_REFERENCE` | Attached request `Pasted text.txt`, dated 2026-09-28, sections 1–56 and exact final flag contract. |

## Authority and SOR boundaries

- `ShipmentRequest.status` remains the commercial lifecycle SOR. No new status
  or workflow engine is introduced.
- `ExpertQuote.customer_response` remains the latest-response SOR. Derived next
  action and work bucket are read projections and are never persisted.
- `ShipmentRequest.customer_id` remains the Request-to-CRM relationship. The
  owning Expert may select an existing active same-tenant Customer through the
  authorized Request only. Organization Admin remains the normal CRM Customer
  creator.
- `CustomerEntitlement` remains the sole DN10 Portal Account-to-CRM Customer
  authorization SOR. Request linking creates no entitlement side effect.
- `OperationalShipment` remains a separate aggregate. Quote acceptance never
  creates it. The existing explicit accepted-Quote command remains the only
  Request commercial-flow creation path.

## Journey and reference impact

```text
JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY
DIRECTLY_AFFECTED_JOURNEYS=FWD-J02,FWD-J03,FWD-J04,FWD-J08,FWD-IPJ-01,FWD-IPJ-03
ADJACENT_REGRESSION=FWD-J01,FWD-J05,FWD-J06,FWD-J07,FWD-J09,FWD-IPJ-02,FWD-IPJ-04
REQUIRED_SLICE_RERUN=expert-request-commercial-hardening focused backend/frontend/browser set
REQUIRED_INTEGRATED_RERUN=FWD-J01..FWD-J09,FWD-IPJ-01..FWD-IPJ-04
HUMAN_WALKTHROUGH_RERUN=PRODUCT_OWNER_CONTINUES; RESULT_IN_PROGRESS
LPAF_REFERENCE_IMPACT=NONE
PROJECT_REFERENCE_IMPACT=UPDATE_REQUIRED
```

Project reference updates include ADR-071, API/read-model contracts, tests,
candidate/evidence manifests and integration receipts. Historical evidence and
Human Walkthrough records are preserved rather than rewritten.

## Entry disposition

```text
LPAF_BASELINE=2.7
GOVERNANCE_LEVEL=B
CAPABILITY_ROUTE=SOL
PRODUCT_AUTHORITY_RECONCILIATION=PASS_AT_ENTRY
JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY
MIGRATION_REQUIRED=NO
ALEMBIC_HEAD=20261012_phase3_cargo_eta
HUMAN_PRODUCT_WALKTHROUGH=IN_PROGRESS
RELEASE_READY=NO
PRODUCTION_UNTOUCHED=YES
```

