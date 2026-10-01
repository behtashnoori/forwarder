# Shipment Next-Action Ranking — Qualification Report

`AUTHORITATIVE_LPAF_BASELINE=LPAF v2.7 — ACTIVE / FROZEN / CANONICAL`

`MISSION=HW_GUIDED_UX_001 — NEXT ACTION RANKING IGNORES INCOMPLETE REQUIRED STAGE`

`JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY`

`HW_GUIDED_UX_001=RESOLVED`

## Corrective model

The existing Shared Operational Projection remains the single ranking engine. It now derives the current actionable required stage from the authoritative Shipment Operational Stages projection and ranks actions by lifecycle phase:

1. complete the current required stage when it is `STARTED` and incomplete;
2. start the next available required stage when none is currently started;
3. allow later lifecycle actions such as explicit Final Delivery only after required stage work is satisfied;
4. preserve the existing closure action after explicit Final Delivery and closure readiness.

The stage CTA links to the exact stage row on the existing Operational Stages surface. No Shipment identity, stage name, or stage sequence is hard-coded.

`CURRENT_STAGE_NEXT_ACTION_CONSISTENCY=PASS`

`PRODUCT_BEHAVIOR_CHANGED=YES — only the authorized next-action priority and exact-stage CTA target`

`BUSINESS_SEMANTICS_CHANGED=NO`

## Required cases

`CASE_1_RESULT=PASS — Stage 1 NOT_STARTED produces start Stage 1`

`CASE_2_RESULT=PASS — Stage 1 STARTED/incomplete produces complete Stage 1`

`CASE_3_RESULT=PASS — completed Stage 1 makes available Stage 2 the start action`

`CASE_4_RESULT=PASS — a STARTED middle required stage outranks Final Delivery`

`CASE_5_RESULT=PASS — after all required stages complete, Final Delivery may become primary under existing rules`

`CASE_6_RESULT=PASS — explicit Final Delivery plus satisfied blockers preserves closure routing`

`CASE_7_RESULT=PASS — a closed Shipment exposes no operational primary action`

`CASE_8_RESULT=PASS — an unauthorized user receives no unauthorized action`

## Qualification gates

`FOCUSED_TESTS=PASS — 56 affected backend tests; 16 affected frontend tests; 1 dedicated Shipment stages Chrome journey`

`FRONTEND_TESTS=PASS — 102 files / 486 tests; production build PASS; lint 0 errors / 16 pre-existing advisory warnings`

`JOURNEY_RESULT=PASS — 11 Guided Workspace Chrome tests / 13 affected journey areas on owned disposable PostgreSQL 18 at exact head 20261015_org_shipment_stages; cleanup PASS`

`PRODUCT_SHA=5bf020f29cb1b331e2b5bbc78a2c426027759554`

`EVIDENCE_SHA=THIS_EVIDENCE_COMMIT`

`FINAL_CANONICAL_SHA=PENDING_CONTROLLED_INTEGRATION`

`AHEAD_BEHIND=PENDING_POST_PUSH_FETCH_VERIFICATION`

## Preserved walkthrough boundary before integration

The preservation snapshot was obtained through read-only PostgreSQL 18 operations. The target Shipment has exactly one operational-stage event: sequence 1, `آماده‌سازی / بارگیری`, `STARTED`. No Product action was automated against the preserved walkthrough.

`WALKTHROUGH_DATABASE_PRE_NORMALIZED_SHA256=35860D14CFEF91A70C063347A9AB97A1D77F932A9E931064C3F87DB5A6E371F4`

`WALKTHROUGH_STAGE1_STARTED_EVENT_PRE=YES`

`WALKTHROUGH_BUSINESS_ACTIONS_PERFORMED=0`

`PRODUCTION_ACCESSED=NO`

`PRODUCTION_MUTATED=NO`

`DEPLOYMENT_PERFORMED=NO`

`RELEASE_CREATED=NO`

## Qualification decision

`QUALIFIED_FOR_CONTROLLED_INTEGRATION=YES`

The first browser attempt was invalidated by a local dependency-junction/Vite filesystem-path collision. It did not access the preserved walkthrough or production. A clean candidate-local dependency installation removed that environmental condition; the exact candidate then passed both browser suites on fresh owned PostgreSQL 18 runtimes.
