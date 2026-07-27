# Phase 1B Browser Runner Exit-Code-1 Recovery

## Final status note (2026-07-27)

The recovered runner passed the targeted route contract and final full Browser/Mobile UAT. Browser/Mobile UAT is `YES`; five viewports and 22/22 workflows passed; P1B-UAT-001 through P1B-UAT-006 are `CLOSED_VERIFIED`; persistent applied is `NO`. Earlier blocked states below are historical chronology only.

## Prior run

- Run: `P1B-UAT-20260726185010908193`
- Browser exit: `1`
- Original browser stdout, stderr, result JSON, and screenshot: not preserved
- Classification of the original exit: `RC-F + RC-H` (output/evidence contract defect); the underlying browser assertion cannot be proven from the surviving report
- Product defect: `NO`

The harness deleted the disposable runtime in `finally`. Its surviving report contained PostgreSQL startup text as the browser failure tail and no browser stage or assertion. A blind full-UAT retry was therefore rejected.

## Recovery applied

- Browser failures now emit a machine-readable diagnostic with stage, mapped error code, sanitized message, viewport, workflow, last successful step, console/5xx counts, screenshot, launch/page state, and cleanup result.
- Exit mapping is `0=PASS`, `2=UAT assertion`, `3=environment/launch`, `4=runner contract/internal`, and `5=timeout`.
- The harness preserves browser stdout, stderr, result JSON, and last failure screenshot before deleting the runtime.
- A constrained `--targeted-smoke` harness mode sets `PHASE1B_UAT_MODE=targeted-smoke` only for the browser child.

## Single targeted reproduction

- Run: `P1B-UAT-20260727042941307917`
- Viewport: `1280x720`
- Exit: `5`
- Stage: `targeted-navigation`
- Last successful step: `route-plan-detail`
- Chromium launched: `YES`
- Page created: `YES`
- Console errors: `0`
- Unexpected 5xx: `0`
- Cleanup: `PASS`
- Failure: the operational-detail locator timed out after navigation redirected to the public landing page.
- Evidence: `C:\Users\pc\AppData\Local\Temp\forwarder-phase1b-uat-reports\P1B-UAT-20260727042941307917-artifacts`

The screenshot and source contract showed that `ProtectedRoute` requires both `expert_token` and `expert_user`; the runner injected only `expert_token`. Classification: `RC-E — SELECTOR_OR_ROUTE_CONTRACT_DEFECT`. The runner now injects both values and clears both during targeted logout.

No second targeted reproduction was run because this gate allowed exactly one. Full UAT was not run because the targeted reproduction did not pass.

## Gate result

- Browser/Mobile UAT: `NO`
- Persistent applied: `NO`
- Product source changed by this recovery: `NO`
- Full UAT: `NOT RUN`
- Final status: `PHASE_1B_BROWSER_RUNNER_CONTRACT_BLOCKED`
