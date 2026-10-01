# Closure completion/readiness qualification matrix

Date: 2026-10-01

## Qualified lifecycle contract

- There is no standalone `Complete Shipment` command.
- Actual departure and arrival occurrences complete every active, non-cancelled route leg. The occurrence projection then derives the shipment's `completed` lifecycle state.
- `completed -> closed` is a separate explicit close command. It requires the normal closure policy to pass, or the already-defined exceptional organization-admin path, and it always requires the `completed` predecessor.
- Organization Shipment stages and closure-policy criteria are separate facts. Completing 5/5 stages and reaching zero policy blockers does not complete the route or the shipment.
- Warnings remain visible and do not block an authorized route occurrence or close command.

## Required cases

| Case | Qualified state | Expected result | Evidence | Result |
|---|---|---|---|---|
| 1 | A mandatory closure blocker exists | No complete/close action; the blocker outranks warnings | `test_guided_operational_projection.py` matrix cases J-M; browser journey before Final Delivery | PASS |
| 2 | Zero policy blockers plus warnings; route incomplete | Next existing route occurrence is recommended only to a user with `milestone_event.create`; close remains unavailable | PostgreSQL 18 browser journey after 5/5 stages and Final Delivery | PASS |
| 3 | Actual Cargo unknown | `ACTUAL_CARGO_UNKNOWN` remains a non-blocking warning and cannot outrank route execution or close | Projection matrix H/I; browser closure count shows three warnings | PASS |
| 4 | Actual Allocation differs from Planned | `ACTUAL_ALLOCATION_DIFFERS_FROM_PLANNED` remains a non-blocking warning | Projection matrix H/I; browser closure count shows three warnings | PASS |
| 5 | Delivered differs from Planned | `DELIVERED_DIFFERS_FROM_PLANNED` remains a non-blocking warning | Projection matrix H/I; browser closure count shows three warnings | PASS |
| 6 | Before and after projected completion | Before: departure/arrival occurrence action. After all active legs complete: explicit `Review and close` action, with warnings still non-blocking | PostgreSQL 18 browser records departure and arrival, observes normal-ready, and closes explicitly | PASS |
| 7 | Shipment closed | No lifecycle action is offered; closure decision and occurrences remain in Unified History | Projection matrix O; browser Unified History desktop/mobile proof | PASS |
| 8 | Unauthorized actor | No inaccessible occurrence or close action is advertised; cross-tenant access is denied | Permission-aware projection/UI tests; browser foreign-tenant denial | PASS |

`STATE_CASE_COUNT=8`

`STATE_CASE_PASS_COUNT=8`

## Cross-surface consistency

- Closure: distinguishes policy blockers from the route/lifecycle prerequisite and keeps the three warnings non-blocking.
- Summary / Next Action: derives execution readiness from active route-leg status, not the presence of a transport-execution row. It selects departure or arrival ahead of optional enrichment when authorized.
- Task List / Attention: show execution as the blocking prerequisite. If the actor lacks the exact occurrence permission, the blocker remains visible but no unavailable action or lower-priority warning action is recommended.
- Unified History: shows the two occurrence facts, organization-stage facts, Final Delivery, and the explicit close decision as distinct append-only records.

## Preserved walkthrough authority finding

The owning preserved walkthrough expert can manage the shipment and close it once completed, but its membership lacks `milestone_event.create`. The walkthrough admin also lacks that capability. The current real shipment therefore has no authorized persona that can record the required route occurrences. Ownership cannot be treated as an implicit permission, and this mission did not mutate memberships or grant capabilities.

The Product/authorization authority must decide which existing route-occurrence capability is assigned to the walkthrough operator (or provide another already-governed authorized actor). Until that decision is implemented through the proper provisioning authority, the current preserved shipment is not human-walkthrough ready even though the lifecycle contract and code behavior are qualified.
