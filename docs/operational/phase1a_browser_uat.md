# Phase 1A browser UAT

## Final closure status

`PHASE_1A_OPERATIONAL_VERTICAL_SLICE_PASS_WITH_NOTES`

The accepted desktop run is `P1A-UAT-20260723125334`. It completed the real
login, accepted quote, create/double-click, list/filter/detail, report,
reporter/verifier separation, verify/correct, reconcile/queue/resolve,
permission/isolation, conflict, and empty-state scenarios. The two remaining
gates were closed by `P1A-MOBILE-CLOSURE-20260723132017`.

## Mobile viewport closure

The earlier in-app runner kept `window.innerWidth=1280`; this was a tooling
limitation rather than product CSS. The final run used temporary
`playwright-core 1.57.0` outside the repository with the cached local Chromium
binary. Each width used a fresh `browser.newContext` with
`deviceScaleFactor=1` and touch enabled.

| Viewport | inner | client | Media queries | PNG | Document overflow |
|---|---|---|---|---|---|
| 360x800 | 360x800 | 360x800 | 360/390/768 true | 360x800 | none |
| 390x844 | 390x844 | 390x844 | 360 false; 390/768 true | 390x844 | none |
| 768x1024 | 768x1024 | 768x1024 | 360/390 false; 768 true | 768x1024 | none |

Thirteen PASS screenshots were generated outside the repository. Interactions
covered filtering, create/open detail, timeline reporting/scrolling, correction
reason input and validation, back navigation, work-queue navigation, and tablet
resolve. RTL remained active and `scrollWidth == clientWidth` on every measured
page.

## UAT-20 resilience

The owned local backend PID `6552` was verified from port 8000 and stopped while
the frontend remained running. The operational list showed a bounded error and
visible Retry action, with no traceback or SQL disclosure. The backend was
restarted through the normal entry point as PID `14424`; ping, health, and
readiness returned 200. Clicking Retry restored shipment data without a full
browser reload.

## Cleanup and evidence

- Evidence directory: `P1A-MOBILE-CLOSURE-20260723132017` outside repository
- Browser contexts and Chromium: closed
- Backend/frontend/disposable PostgreSQL: stopped
- Cluster, logs, credential material, and temporary runner: removed
- `UAT_TEMP_RESOURCES_REMAINING=0`
- Production, deployment, merge, and Phase 1B: untouched

Notes are limited to twelve existing lint warnings and deferred Phase 1B
features.
