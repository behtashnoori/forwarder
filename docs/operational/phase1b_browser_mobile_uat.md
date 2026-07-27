# Phase 1B Browser/Mobile UAT readiness

## Final status (2026-07-27)

Browser/Mobile UAT is `YES`. Targeted route-contract run `P1B-UAT-20260727044111047492` and full run `P1B-UAT-20260727044204801260` passed. All five viewports and all 22 workflows passed; console errors, unexpected 5xx responses, CORS violations, forbidden-port violations, and production requests were zero. P1B-UAT-001 through P1B-UAT-006 are `CLOSED_VERIFIED`. Persistent applied is `NO`; production/public PostgreSQL was untouched; `.backend-port` remains `57065`; no commit or push was performed.

Everything below this point is historical chronology retained for audit context and does not state current status.

## Historical chronology

Status on 2026-07-25: `UAT_READINESS_PASS`; full Browser/Mobile UAT remains
`PENDING` and must be rerun from the beginning on a new disposable database.

## Readiness delivered

- Deterministic, guarded, idempotent Phase 1B UAT seed.
- Explicit `localhost` to `127.0.0.1` resolution without widening explicit
  loopback binds; explicit `0.0.0.0` remains explicit.
- Shipment summary, active plan/revision, three-leg route, checkpoint and
  milestone details, planned/projected/actual/effective timeline with sources,
  timeline reconciliation, replan/revision history, exception reconciliation,
  manual exception resolution, work items, event history, and audit history.
- Permission-based actions using the backend permission contract.
- Optimistic versions, scoped idempotency keys, duplicate-submit prevention,
  required reasons, no-op feedback, sanitized errors, loading/empty states, and
  mobile-safe cards/scroll containers.

## Limited local smoke

The smoke used a freshly migrated and seeded disposable PostgreSQL 18 database,
a backend bound to `127.0.0.1`, and a frontend bound to `127.0.0.1`.

Passed controls:

- health and database connectivity;
- synthetic admin login;
- direct shipment-detail load and refresh;
- three route legs and six checkpoints;
- timeline/effective-source section;
- route-exception/work-item section;
- role actions for timeline reconciliation, replan, and exception reconciliation;
- reported/verified milestone event history;
- zero fatal console errors in the final clean tab;
- zero production-host requests.

At widths 1440, 768, 390, and 360, the page had zero page-level horizontal
overflow, zero off-viewport buttons, and retained all three legs, timeline, and
exception sections. This component/local smoke is not the final Browser/Mobile
UAT matrix and produced no screenshots.

## Pending gate

The next gate must create a new disposable database and execute the complete
desktop/tablet/mobile workflow, authorization/isolation, mutation, console,
network, accessibility, and evidence matrix. Browser/Mobile UAT remains `NO`.
Persistent migration application remains `NO`.

## Final local backend/frontend smoke gate (2026-07-25)

`PHASE_1B_LOCAL_BACKEND_FRONTEND_SMOKE_PASS_WITH_NOTES`

- Fresh token-scoped PostgreSQL 18.0/UTF8 migration and official Phase 1B UAT seed passed at the single head `20260801_route_exception`; pending migrations were zero.
- The real backend and Vite frontend listened only on `127.0.0.1` on distinct non-production ports. No external `.env`, SQLite database, public PostgreSQL service, production endpoint, or persistent target was used.
- Chromium at 1280 x 720 passed login, direct shipment-detail navigation, three route legs, six checkpoints, active revision, planned/projected/actual/effective timeline, reconciliation and replan controls, exception/manual-resolution UI, actionable work items, refresh, and direct URL reload.
- Fatal console errors, unhandled promises, React crashes, error-boundary activation, unexpected 5xx responses, CORS failures, failed essential assets, production requests, and credential/token exposure were zero. Non-fatal React Router future-flag warnings were observed.
- Alembic revision and the 57-table schema count were unchanged across backend startup. Tracked database artifacts were not used or changed. Browser, application, PostgreSQL, listener, log, and token-directory cleanup completed with zero current-token resources remaining.

This gate records `UAT readiness = YES`. Full `Browser/Mobile UAT = NO` and
`Persistent applied = NO` remain unchanged.

The local SQLite storage remediation does not constitute Browser/Mobile UAT.
The legacy local runtime file was relocated to the platform user-data
directory outside the repository after size, SHA-256, and restricted-ACL
verification. No database content was inspected and no persistent migration
was applied.

## Full Browser/Mobile UAT final gate (2026-07-25)

`PHASE_1B_BROWSER_MOBILE_UAT_BLOCKED`

The validation-only gate used a new disposable PostgreSQL 18.0 UTF8 cluster,
fresh migration to the single head `20260801_route_exception`, the official
Phase 1B seed, a real loopback-only backend and frontend, and Chromium. The
seed contained one Organization A shipment with three route legs.

The first core shipment-list workflow exposed the same shipment three times
at both 1440 x 900 and 390 x 844. DOM measurement found three links to
`/operations/shipments/1`; the page also emitted new React duplicate-key
console errors for key `1`. This conflicts with the single seeded shipment and
makes list counts and pagination unreliable. Defect `P1B-UAT-001` is `HIGH`
and open, so the remaining workflow/viewports were not represented as PASS.
No product source, test, migration, API, frontend, config, seed, or package
file was changed in this validation gate.

Browser/Mobile UAT remains `NO`. Persistent applied remains `NO`.

## P1B-UAT-001 remediation gate (2026-07-26)

`PHASE_1B_SHIPMENT_LIST_DEDUPLICATION_REMEDIATION_PASS_WITH_NOTES`

The list query now applies SQL `DISTINCT` to `OperationalShipment` rows after
the active-plan/leg joins and filters, but before ordering, offset, and limit.
This preserves organization scope and route-leg filter semantics while making
pagination operate on shipments instead of joined legs. No client-side
deduplication, React-key masking, migration, schema, seed, or configuration
change was used.

A fresh disposable PostgreSQL 18/UTF8 database migrated to the single head
`20260801_route_exception`, reported zero pending migrations, and accepted the
official Phase 1B seed. Direct PostgreSQL/API evidence passed one item for the
three-leg Organization A shipment, `has_more=false` at `per_page=1`, preserved
origin/destination filtering, and no Organization A leakage to Organization B.

The real loopback-only backend/frontend targeted browser retest passed at
1440 x 900 and 390 x 844. Each viewport had exactly one link to shipment `#1`,
zero page-level horizontal overflow, zero off-viewport buttons, and no React
duplicate-key warning, fatal console error, or unexpected backend 5xx. The
known non-fatal React Router future-flag warnings remain notes.

This remediation gate is not the full UAT. Browser/Mobile UAT remains `NO`
until the complete matrix is rerun from the beginning. Persistent applied
remains `NO`.

## Clean full rerun after P1B-UAT-001 remediation (2026-07-26)

`PHASE_1B_BROWSER_MOBILE_UAT_BLOCKED`

Pre-browser regression gates passed: backend `393 passed, 13 skipped`,
frontend `21 passed`, ESLint `0 errors, 11 warnings`, production build passed,
and the current-tree secret scan reported `findings=0`. A new disposable
PostgreSQL 18.0 cluster was initialized as UTF8 and bound only to loopback.
Fresh migration reached the single head `20260801_route_exception` with zero
pending revisions.

The official Phase 1B seed then failed closed with `UAT_DATABASE_REJECTED`.
Defect `P1B-UAT-002` records that the rerun-mandated database prefix
`forwarder_phase1a_test_phase1b_uat_` is rejected by the seed allow-list,
which accepts only `forwarder_phase1b_uat` or `phase1b_uat`. The direct
PostgreSQL deduplication test also requires `forwarder_phase1b_uat_`, so it
cannot validate the mandated database without changing the contract. No
source, test, migration, API, frontend, config, or seed fix was made.

Per the gate, Chromium and all five viewports were not started. P1B-UAT-001
remains `FIXED_PENDING_FULL_UAT`; it is not closed by the earlier targeted
retest. The disposable database and role were dropped, the cluster was
stopped, its listener was closed, and the token directory was removed.
Browser/Mobile UAT remains `NO`; persistent applied remains `NO`.

## P1B-UAT-002 database-name contract recovery (2026-07-26)

`PHASE_1B_UAT_DATABASE_NAME_CONTRACT_RECOVERY_PASS_WITH_NOTES`

Read-only source inspection proved the shared canonical database name is
`forwarder_phase1b_uat_<token>`: the seed accepts the
`forwarder_phase1b_uat` family and the direct deduplication test requires the
stricter `forwarder_phase1b_uat_` prefix. The rejected
`forwarder_phase1a_test_phase1b_uat_<token>` name belonged only to the prior
UAT harness. Neither the seed guard nor any source, test, migration, API,
frontend, or configuration file changed.

A new loopback-only PostgreSQL 18.0/UTF8 cluster migrated the canonical
database to the single head `20260801_route_exception` with zero pending
revisions. The official seed passed with 2 organizations, 8 users, 8
memberships, 2 shipments, 2 route plans, 2 active route plans, 6 route legs,
12 checkpoints, 12 dependencies, 36 milestones, and 2 open work items.
`UAT_DATABASE_REJECTED` occurrences were zero. The direct PostgreSQL shipment
deduplication test passed with `1 passed, 0 skipped, 0 failed`, proving the
seeded multi-leg shipment remains unique through filtering, pagination, and
tenant scope.

P1B-UAT-002 is therefore a non-product harness mismatch with status
`RESOLVED_HARNESS_ALIGNMENT_PENDING_FULL_UAT`. P1B-UAT-001 remains
`FIXED_PENDING_FULL_UAT`. This recovery gate did not start a browser or claim
any viewport/workflow as passed. Browser/Mobile UAT remains `NO`; persistent
applied remains `NO`.

## Final clean full browser/mobile rerun (2026-07-26)

`PHASE_1B_BROWSER_MOBILE_UAT_BLOCKED`

A fresh canonical `forwarder_phase1b_uat_<token>` PostgreSQL 18.0/UTF8
database reached the single Alembic head `20260801_route_exception`. The
official seed produced the expected graph, and the mandatory direct shipment
deduplication test passed with `1 passed, 0 skipped`.

Shipment deduplication passed at all five required viewports. Refresh, direct
URL, and location filtering rendered shipment 1 exactly once. Page overflow
and off-viewport buttons were zero. Timeline/exception reconciliation, manual
resolve/reopen, replan revision 1 to 2, source-plan exception resolution,
read-only UI, and Organization B direct-ID isolation were exercised before the
blocker was reached.

New HIGH defect `P1B-UAT-003` blocks the permission matrix: the seeded Reporter
has shipment-read and checkpoint-report permissions, but shipment detail
renders only `You do not have permission to perform this action.` No report
control is reachable, so the reporter/independent-verifier lifecycle and the
remaining full matrix cannot complete. No product or harness fix was made.

P1B-UAT-001 remains `FIXED_PENDING_FULL_UAT`; P1B-UAT-002 remains
`RESOLVED_HARNESS_ALIGNMENT_PENDING_FULL_UAT`. Browser/Mobile UAT remains
`NO`; persistent applied remains `NO`.

## P1B-UAT-003 targeted remediation (2026-07-26)

`PHASE_1B_REPORTER_PERMISSION_REMEDIATION_PASS_WITH_NOTES`

The root cause was missing read-only seed permissions (`route_plan.read` and
`route_exception.read`) for Reporter and Verifier. The page's nested plan,
timeline, and exception requests returned 403 and the concurrent loader
collapsed the complete detail page. The endpoint guards and frontend action
guards were correct and did not change.

The seed now grants only the two required read permissions. Reporter still
lacks verify, replan, timeline-reconcile, exception-manage, and manual-resolve
permissions. A fresh PostgreSQL 18/UTF8 database passed idempotent reseeding,
direct Reporter/Verifier API coverage, shipment deduplication, the full backend
suite, frontend tests, lint, build, and targeted desktop/mobile browser tests.
P1B-UAT-003 is `FIXED_PENDING_FULL_UAT`; Browser/Mobile UAT remains `NO` and
persistent applied remains `NO` until the full clean rerun.
## P1B-UAT-004 runtime closure probe (2026-07-26)

The narrow 1280 x 720 Chromium closure probe passed login, operational shipment
list, shipment detail, active route-plan display, refresh, and logout against a
fresh token PostgreSQL/backend/Vite environment. Fatal console errors,
unhandled promises, unexpected 5xx responses, CORS failures, blank pages, auth
loops, and credential exposure were zero. This probe does not constitute the
five-viewport Browser/Mobile UAT: Browser/Mobile UAT remains `NO`, persistent
applied remains `NO`, and P1B-UAT-004 is `FIXED_PENDING_FULL_UAT`.

## Final full Browser/Mobile UAT rerun (2026-07-26)

`PHASE_1B_BROWSER_MOBILE_UAT_BLOCKED`

A fresh canonical PostgreSQL 18.0/UTF8 database migrated through the official
runner to the single head `20260801_route_exception`, with pending migrations
zero and 57 public tables. The official seed produced the expected
2/8/8/2/2/2/6/12/12/36/2 baseline. Backend and Vite each started once on
token-specific loopback ports. Vite selected `explicit_env`; `.backend-port`
remained 57065.

Runtime-target login/list/detail/refresh passed. Shipment deduplication and
responsive measurements passed at 1440 x 900, 1280 x 720, 768 x 1024,
390 x 844, and 360 x 800: one shipment link, no page-level horizontal
overflow, no off-viewport buttons, and no blank page.

The Reporter permission workflow then exposed a new HIGH defect,
`P1B-UAT-005`. The confirmed Reporter session rendered six `Correct` controls
despite lacking `milestone.correct`. A synthetic correction succeeded,
committing one `corrected` milestone event and one
`checkpoint.milestone_corrected` audit row for the Reporter actor. The gate
stopped immediately; remaining workflows are not claimed as PASS.

Console errors, duplicate-key warnings, and unhandled promises were zero.
React Router future warnings were notes. No source, test, migration, API,
frontend, configuration, or seed fix was made. Browser/Mobile UAT remains
`NO`; persistent applied remains `NO`.

## P1B-UAT-005 targeted authorization remediation (2026-07-26)

`PHASE_1B_MILESTONE_CORRECTION_AUTHORIZATION_REMEDIATION_PASS_WITH_NOTES`

The canonical correction permission is `milestone.correct`. The checkpoint
correction service and all shipment-detail correction controls now use that
permission; `checkpoint.report` remains sufficient only for reporting.
Reporter correction returns HTTP 403 before idempotency, event, audit, outbox,
version, state, actual, or projected mutation. A correction-capable seeded user
still completes the reason-validated append-only correction flow.

A fresh disposable PostgreSQL 18/UTF8 database migrated through the official
runner and seed. Direct PostgreSQL authorization/dedup tests, the full backend
suite, frontend behavioral tests, lint, build, and targeted 1440 x 900 and
390 x 844 browser checks passed. This narrow retest is not the full UAT:
Browser/Mobile UAT remains `NO`, persistent applied remains `NO`, and
P1B-UAT-005 is `FIXED_PENDING_FULL_UAT`.

## Final clean rerun after P1B-UAT-001 through P1B-UAT-005 (2026-07-26)

`PHASE_1B_BROWSER_MOBILE_UAT_BLOCKED`

Four fresh canonical PostgreSQL 18.0/UTF8 databases migrated through the
official runner to `20260801_route_exception` and accepted the official seed.
The independent shipment-deduplication precheck passed with `1 passed, 0
skipped, 0 failed`.

The independent Reporter and correction-authorization prechecks each failed
at the same prerequisite: a fixed-row Reporter arrival selection returned HTTP 409
instead of the contractually required HTTP 200. Each run collected one test,
with zero skips and one failure. The correction assertions were therefore not
reached.

The mandatory three-precheck gate did not pass, so Backend, Vite, Chromium, and
all five viewports were not started. P1B-UAT-001 through P1B-UAT-005 remain in
their pending-full-UAT states and are not closed. No source, test, config,
migration, schema, seed, or permission assignment was changed. Browser/Mobile
UAT remains `NO`; persistent applied remains `NO`.

## Final clean rerun after P1B-UAT-006 (2026-07-26)

`PHASE_1B_BROWSER_MOBILE_UAT_ENVIRONMENT_BLOCKED`

Four fresh canonical PostgreSQL 18.0/UTF8 databases migrated through the
official runner to `20260801_route_exception`, reported zero pending
migrations, and accepted one official seed each with the expected counts. The
three independent mandatory direct prechecks each collected and passed one
test with zero skips and failures.

The one permitted backend start attempt then failed before application
initialization because Windows process argument parsing split the inline
Python launcher. The backend was not restarted; Vite and Chromium were not
started, and no viewport or browser workflow is claimed as passed. This is an
environment/UAT-harness launch failure rather than a product defect.

P1B-UAT-001 through P1B-UAT-006 retain their pending-full-UAT statuses.
Browser/Mobile UAT remains `NO`; persistent applied remains `NO`. All four
databases were dropped, the disposable cluster was stopped, and current-token
processes, listeners, and temporary resources were reduced to zero.

## Backend one-shot launch recovery probe (2026-07-26)

The original inline-argument blocker was recovered with the versioned
Waitress/WSGI entrypoint: one backend start completed initialization and health
returned HTTP 200 against a fresh seeded PostgreSQL database. The execution
environment then rejected Vite process creation before start, so the required
`explicit_env` and Chromium login/list/detail controls were not reached.

This targeted probe is `ENVIRONMENT_BLOCKED`; it is not Full UAT. Browser/Mobile
UAT remains `NO`, P1B-UAT-001 through P1B-UAT-006 retain their pending-full-UAT
states, persistent applied remains `NO`, and cleanup left zero token resources.
