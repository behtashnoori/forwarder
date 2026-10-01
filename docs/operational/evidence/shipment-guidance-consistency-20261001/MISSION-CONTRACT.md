# Shipment Guidance Consistency — Mission Contract and Product Authority Record

Date: 2026-10-01  
Capability route: Level B / Sol  
Status: authorized candidate work; Product qualification pending  
JOURNEY_IMPACT: `AFFECTS_EXISTING_JOURNEY`

## Mission

Make Current State, Operational Progress, Case Readiness, Tasks, Attention,
Closure Readiness and Next Action tell one coherent story without changing any
domain command, closure criterion, permission boundary or Shipment fact.

## Product Authority Record

| Field | Record |
| --- | --- |
| `AUTHORITY` | Product Owner mission “Shipment Guidance Consistency Audit and Correction”, supplied 2026-10-01 |
| `AUTHORIZED_PRODUCT_CHANGES` | One shared guidance classification; explicit semantic precedence; visible BLOCKER / NEEDS ACTION / WARNING / INFORMATIONAL categories; unambiguous Operational Progress versus Case Readiness labels; action-oriented primary CTA copy; the current preserved state must recommend `ثبت تحویل نهایی` while retaining Actual Cargo unknown, allocation mismatch and ETA absence as warnings. |
| `DELEGATED_TECHNICAL_CHOICES` | Internal projection refactor, backward-compatible response fields, tests, evidence organization and presentation implementation inside the existing Guided Operational Workspace. |
| `PROTECTED_PRODUCT_BEHAVIOR` | Closure policy criteria and mandatory flags; stage, route, execution, cargo, allocation, delivery, document and tracking semantics; command authorization; tenant/owner boundaries; lifecycle transitions; preserved walkthrough data; Production. |
| `DECISIONS_NEEDED` | None inside the authorized scope. Stop if implementation requires a new domain rule or changes warning/blocker meaning. |
| `PDA_07_RECONCILIATION` | Guidance classification/presentation differences are `AUTHORIZED`; all domain facts, commands and permissions are `PRESERVED`; a warning presented as a blocker or ranked before required work is a `VIOLATION`; any unclassified material behavior is `UNKNOWN` and stops integration. |

## Semantic precedence

The projection uses named lifecycle precedence, in this order:

1. `BLOCKING_PRECONDITION` — prerequisite absent or invalid, so meaningful continuation cannot start.
2. `CURRENT_REQUIRED_WORK` — required work is already in progress and must be completed.
3. `NEXT_REQUIRED_LIFECYCLE` — the next required lifecycle action is available.
4. `CLOSURE_BLOCKER` — an authoritative mandatory closure criterion is unsatisfied.
5. `OPTIONAL_IMPROVEMENT` — warning-only data quality or enrichment.
6. `INFORMATIONAL` — no action or blocking consequence.

Stable numbers may serialize/sort these named categories, but numbers are not
Product authority. A warning-only condition cannot outrank a required lifecycle
action or closure blocker.

## Affected journeys and required reruns

- Slice: `FWD-J04`, `FWD-J05`, `FWD-J07`, `FWD-J08`, `FWD-J09`.
- Integrated: `FWD-IPJ-02`, `FWD-IPJ-04`.
- Exact-candidate automated state matrix and invariant tests are mandatory.
- Representative browser journeys must use disposable PostgreSQL 18.
- The complete critical automated Product pack required by the controlled
  integration mission must be rerun on the exact candidate.
- Human Product Walkthrough remains `IN_PROGRESS`; an agent cannot grant its PASS.

## Data boundary

The preserved database `forwarder_human_walkthrough` is read-only for this
mission. No Final Delivery, Actual Cargo, allocation, document, tracking,
closure or other Product business action may be recorded. Candidate browser
qualification uses only disposable PostgreSQL 18 data.
