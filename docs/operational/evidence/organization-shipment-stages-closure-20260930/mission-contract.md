# Organization Shipment Stages and Exact Closure Foundation — Mission Contract

Status: `QUALIFIED / WALKTHROUGH RUNTIME CONFIGURED`

Baseline: `LPAF v2.7 — ACTIVE / FROZEN / CANONICAL`

Starting Product SHA: `c27b15ee6a0b16b8c84f6fa072f3c56f70c5b8c7`

Rigor / routing: `Level B / Sol`

Mission owner and approving authority: Product Owner
Approval reference: the 2026-09-30 mission titled “FORWARDER — ORGANIZATION SHIPMENT STAGES + EXACT CLOSURE CRITERIA”

## Mission and evidence boundary

Outcome: a projectless Operational Shipment can use a governed Organization-owned stage sequence, Experts can append explicit start/completion facts, and normal closure evaluates the exact authorized blockers while retaining non-blocking warnings.

In scope: Organization stage configuration/versioning, Shipment stage execution/events, explicit final-delivery semantics, exact closure blockers/warnings, Organization Admin and Expert UI/API boundaries, unified history, one additive migration, tests, PostgreSQL 18 qualification, affected frontend checks, and affected Product journeys.

Out of scope: broad UI redesign, Project Milestone redefinition, inferred stage progress, inferred final delivery, quantity reconciliation, Production, release, closing the preserved Shipment, or performing Product Owner walkthrough actions.

Known current facts and recoverable evidence:

- `backend/services/operational_execution_service.py` obtains operational milestone definitions through `ProjectMilestoneDefinition.project_id`; a Shipment with `project_id=NULL` cannot obtain that chain.
- `backend/closure_models.py` has no `FINAL_DELIVERY_EXISTS` or `REQUIRED_OPERATIONAL_STAGES_COMPLETE` criterion.
- `backend/services/closure_service.py::_facts` derives delivery completion from Actual Cargo and delivered quantity and returns `UNKNOWN` for required-document readiness when no requirements exist.
- `backend/delivery_models.py::CargoDelivery` cannot distinguish final from partial delivery.
- `backend/services/unified_shipment_history.py` has no Organization Shipment Stage event source and no explicit closure decision branch.
- Preserved runtime facts supplied by the Product Owner were re-verified before and after controlled runtime configuration. Recoverable PostgreSQL 18, browser, test, backup, and runtime receipts now qualify this foundation; the manual Human Product Walkthrough itself remains `IN_PROGRESS`.

Assumptions: existing fixed Shipment ownership remains the Expert command boundary; the existing completed-to-closed predecessor remains separate from checklist criteria; current append-only correction conventions remain applicable.

Unknowns to close with evidence: exact disposable PostgreSQL 18 command/environment, preserved runtime Organization identity and authorized Organization Admin credentials, and exact affected browser journey runner inputs.

Stop conditions: any Production target; destructive or non-additive migration; cross-tenant ambiguity; missing authority for a product-visible deviation; inability to preserve stage/closure history; or a request to perform the Product Owner’s manual stage/closure actions.

Definition of Done: the focused qualification list passes on the exact candidate; `ALEMBIC_HEAD_COUNT=1`; preserved runtime configuration contains five active required ROAD stages and one active exact closure policy; preserved Shipment facts remain unchanged with zero stage-progress and closure-action facts; no Production/release/deployment action occurs.

## Product Authority Record

`AUTHORIZED_PRODUCT_CHANGES`

- Organization-scoped Shipment Operational Stage definitions with stable identity/code, Persian display name, order, activation, and required-for-completion semantics.
- Organization Admin publishes/activates stage configuration; the fixed responsible Expert records explicit started/completed events.
- Shipment stage execution is independent of Project Milestones and supports `project_id=NULL`.
- Delivery explicitly distinguishes a final Shipment Delivery fact from partial delivery; final is never inferred from quantity equality.
- Closure blockers are exactly `FINAL_DELIVERY_EXISTS`, `REQUIRED_OPERATIONAL_STAGES_COMPLETE`, `NO_BLOCKING_OPERATIONAL_ISSUE`, and `REQUIRED_DOCUMENTS_READY`.
- Closure warnings are exactly `ACTUAL_CARGO_UNKNOWN`, `ACTUAL_ALLOCATION_DIFFERS_FROM_PLANNED`, `DELIVERED_DIFFERS_FROM_PLANNED`, `OPTIONAL_DOCUMENTS_ABSENT`, `ETA_UNAVAILABLE`, and `NON_BLOCKING_OPERATIONAL_WARNINGS`.
- Zero required documents makes `REQUIRED_DOCUMENTS_READY` pass.
- Stage and closure facts join Unified Shipment History with understandable Persian labels.

`DELEGATED_TECHNICAL_CHOICES`

- Additive relational schema, immutable configuration versions, Shipment instance pinning, append-only events, API shape, component boundaries, indexes, idempotency, and proportional tests.
- Retain legacy closure criterion codes only to read historical policy/decision evidence; new policy publication is limited to the authorized V1 code set and fixed blocker/warning classification.

`PROTECTED_OUT_OF_SCOPE_BEHAVIOR`

- `ProjectMilestoneDefinition` remains distinct and unchanged in meaning.
- Existing Shipments remain readable; migration creates no historical Shipment stage instance/event.
- Delivery, allocation, tracking, ETA, and route position do not create stage completion.
- Actual Cargo remains unknown unless explicitly recorded; Actual Allocation never becomes Actual Cargo.
- Optional documents remain optional; warnings never block closure.
- Fixed Shipment ownership, tenant isolation, closed-Shipment guards, route workspace, and “تکمیل و بستن” placement remain intact.
- Preserved Shipment receives no stage event, final-delivery mutation, closure decision, document, quantity, route, or allocation change from the agent.

`DECISIONS_NEEDED`: none before Build; runtime application stops if Organization/admin identity cannot be proven without guessing.

`APPROVING_OWNER_OR_AUTHORITY`: Product Owner.

`APPROVAL_REFERENCE`: exact mission brief supplied in this task, sections 2–20.

## Journey impact and verification

`JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY`

Affected critical journeys: `FWD-J04`, `FWD-J05`, `FWD-J06`, `FWD-J08`, `FWD-J09`, `FWD-IPJ-02`, `FWD-IPJ-03`, and `FWD-IPJ-04`. The new normal Shipment-stage flow is an authorized extension inside `FWD-J09/FWD-IPJ-04`, not a silently invented critical-journey ID.

Required evidence: focused backend and PostgreSQL 18 tests; migration head proof; frontend component tests, type-check/build/lint; Organization Admin normal-navigation stage/policy configuration; Expert normal-navigation projectless stage start/complete and closure refusal/success; cross-tenant and non-admin definition denial; partial/final delivery distinction; unified-history Persian labels; preservation before/after facts. Human walkthrough remains `IN_PROGRESS` and cannot be marked PASS by the agent.

Reference impact: LPAF `NONE` (the mission applies v2.7 without changing it); Forwarder architecture `UPDATE_REQUIRED` through ADR-075 and this mission record; Product Journey Pack `UPDATE_REQUIRED` before freeze with exact-candidate rerun evidence.

