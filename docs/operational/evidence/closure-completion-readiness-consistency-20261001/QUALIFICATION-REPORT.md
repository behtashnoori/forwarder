# Closure completion/readiness consistency — qualification report

Date: 2026-10-01 (Asia/Tehran)

Implementation candidate: `c22bbb0aeec434481b3e3fca21b6b75c74502318`

## Result

`PARTIAL PASS — CLOSURE LIFECYCLE CONTRACT DECISION REQUIRED`

The lifecycle contract itself is proven and internally coherent. There is no standalone Complete Shipment command. Real departure/arrival occurrences project every active, non-cancelled route leg to complete and then project the Shipment to `completed`. Closing is a separate explicit `completed -> closed` command. Closure policy criteria, Final Delivery, and 5/5 Organization Shipment stages do not replace the route-execution predecessor.

The code defect is corrected: Closure now distinguishes zero policy blockers from the incomplete lifecycle prerequisite; Summary, Task, Attention, and Next Action derive completion from route-leg occurrences; optional cargo/allocation/delivery/ETA warnings cannot outrank the route prerequisite; and the legacy occurrence endpoint accepts the public milestone identity already emitted by the UI.

The remaining decision is authorization provisioning, not lifecycle design. The preserved owning expert, walkthrough admin, and platform admin do not have the route-occurrence permission required by the existing UI/API. This mission did not infer an implicit owner grant, remap capabilities, or mutate memberships. Product/authorization authority must designate a governed actor/capability assignment before the preserved walkthrough can perform the next business transition.

## Required contract fields

`SHIPMENT_CURRENT_LIFECYCLE_STATE=planned`

`COMPLETION_TRANSITION_EXISTS=YES — derived projection, not a standalone command`

`COMPLETION_PRECONDITIONS=active route plan; every active non-cancelled leg has valid actual departure and arrival occurrences; chronology/order invariants pass`

`COMPLETION_ACTION_AVAILABLE_NOW=NO — the current preserved personas lack milestone_event.create`

`CLOSURE_TRANSITION_EXISTS=YES — explicit immutable completed -> closed command`

`CLOSURE_PRECONDITIONS=lifecycle completed; normal policy readiness plus owning-expert authority for normal close, or the existing organization-admin exceptional path; exceptional close does not waive the completed predecessor`

`ZERO_BLOCKERS_MEANS_COMPLETABLE=NO — zero closure-policy blockers does not prove route execution complete`

`ZERO_BLOCKERS_MEANS_CLOSABLE=NO — lifecycle completed remains mandatory`

`CURRENT_EXPECTED_NEXT_ACTION=No action may be advertised to the current preserved persona; once the exact existing occurrence capability is provisioned by the proper authority, the next business action is ثبت حرکت`

`SUMMARY_CLOSURE_CONSISTENCY=PASS — both surfaces identify route execution as the lifecycle prerequisite and keep all three current warnings non-blocking`

## Root cause

1. The Closure checklist displayed policy progress (`10/10`, zero policy blockers) without naming the independent `completed` lifecycle predecessor, so the correct close denial appeared contradictory.
2. The shared operational projection treated the existence of any `RouteStageExecution` row as completed transport execution. The authoritative occurrence projection instead requires every active route leg to reach `completed` through actual departure/arrival facts.
3. The Next Action ranking could allow optional enrichment warnings to appear ahead of that missing predecessor.
4. The route UI sent a public milestone UUID to an endpoint constrained to an integer path, making the otherwise-authorized occurrence action fail routing.
5. The preserved walkthrough memberships have no route-occurrence capability. Changing that authority is not permitted by this corrective mission.

## Qualification summary

The eight required states pass in the owned qualification model; see `QUALIFICATION-MATRIX.md`.

`STATE_CASE_COUNT=8`

`STATE_CASE_PASS_COUNT=8`

The exact clean product candidate passed the complete browser path on disposable PostgreSQL 18 at schema head `20261015_org_shipment_stages`. The journey recorded route departure and arrival, observed projected `completed`, enabled and submitted explicit close with three warnings still present, verified append-only Unified History at desktop and 390px mobile widths, and verified foreign-tenant denial.

## Preserved walkthrough proof

Read-only pre-change and post-qualification normalized PostgreSQL data-only SHA-256 values are identical:

`88D053B79E4B192004A6D6BC3A44F826A365446DCFB38760E7CB2AEB50021933`

The post-qualification read confirms the two Delivery revisions remain present, with revision 2 current/final and quantity `95`; no transition was executed. The preserved facts remain 5/5 completed stages, explicit Final Delivery, 10/10 criteria, zero policy blockers, three warnings, Actual Cargo unknown, Planned/Actual Allocation `100/95`, and Delivered `95`.

`WALKTHROUGH_DATABASE_PRESERVED=YES`

`WALKTHROUGH_BUSINESS_ACTIONS_PERFORMED=0`

## Boundary receipt

`PRODUCTION_ACCESSED=NO`

`PRODUCTION_MUTATED=NO`

`DEPLOYMENT_PERFORMED=NO`

`RELEASE_CREATED=NO`

`HUMAN_PRODUCT_WALKTHROUGH=IN_PROGRESS`

`RELEASE_READY=NO`

## Publication fields

`PRODUCT_SHA=c22bbb0aeec434481b3e3fca21b6b75c74502318`

`EVIDENCE_SHA=THIS_EVIDENCE_COMMIT`

`FINAL_CANONICAL_SHA=PENDING_CONTROLLED_INTEGRATION`

`AHEAD_BEHIND=PENDING_POST_PUSH_FETCH_VERIFICATION`
