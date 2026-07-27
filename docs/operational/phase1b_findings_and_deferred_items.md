# Findings and deferred items

## Final status (2026-07-27)

All Phase 1B UAT findings P1B-UAT-001 through P1B-UAT-006 are `CLOSED_VERIFIED`. Targeted route-contract and full Browser/Mobile UAT passed; five viewports and 22/22 workflows passed. Browser/Mobile UAT is `YES`. Persistent applied is `NO`, production/public PostgreSQL was untouched, `.backend-port` remains `57065`, and no commit or push was performed. Regression results are reused from unchanged UAT source.

The remainder is historical chronology; earlier open, pending, blocker, or UAT=NO statements are superseded and retained only as an audit trail.

## Historical chronology

Phase 1A read paths assumed one unordered leg; Phase 1B orders legs and retains the singular first-leg response for compatibility. Route optimization, GPS, notifications, full SLA processing, accounting, claims, documents, auto-dispatch, and Excel import remain deferred.

The database-integrity and atomic-idempotency gate passed on disposable PostgreSQL 18. Composite foreign keys now protect checkpoint/leg, dependency endpoints, milestone/checkpoint, and exception shipment/plan/checkpoint/organization scope. Application validation remains a complementary error-contract layer.

Idempotency is scoped by organization, operation, resource type, command resource ID, and key. A PostgreSQL transaction-scoped advisory lock serializes only the exact scope; the result row is inserted in the same transaction as domain, audit, and outbox mutations, so a durable reserved-without-result state is not created.

The checkpoint milestone lifecycle gate passed its targeted and PostgreSQL checks. Correction now invalidates a formerly verified actual immediately; independent re-verification derives the corrected actual from the append-only event ledger. PostgreSQL enforces ledger immutability, while service/API policy enforces actor separation, optimistic locking, scoped idempotency, audit, and outbox atomicity. No schema change was required.

The replan graph-atomicity gate now uses shipment-scoped row locking, allocates revision N+1 under the lock, constructs a non-active target, remaps the full structural graph, preserves source/event history, resolves only superseded-plan actionable items, and commits activation with audit/outbox/idempotency. PostgreSQL 18 same-key and competing-key tests proved deterministic replay/winner behavior, one active plan, unique revisions, and no duplicated event history. Ten failure-injection points proved complete rollback. No schema change was required.

Final PostgreSQL evidence used system Python 3.13.9 with process-local UTF-8 and two independent guard-compatible databases in a localhost-only disposable PostgreSQL 18.0 UTF8 cluster. Both fresh official-runner upgrades reached the single head `20260801_route_exception`; Phase 1A and Phase 1B PostgreSQL tests passed. The populated downgrade was rejected by `SAFE_DOWNGRADE_GUARD` before destructive DDL and remained at head. Backend finished with 357 passed and 10 known skips; the two new skips are explicit-DSN race tests outside the disposable run. Frontend finished with 10 passed, lint with 0 errors and 12 warnings, and production build passed. Cleanup removed all current-token exception-gate resources.

Delay propagation and projected timeline are complete: deterministic topological chain/fan-in processing, actual override, checkpoint/milestone/leg synchronization, active-revision isolation, versioned idempotent reconciliation, API effective-source fields, and real PostgreSQL evidence all pass.

Route-exception reconciliation is complete using the existing work-item-backed exception model. It provides deterministic overdue/dependency/replan-required detection, automatic resolve, idempotent manual resolve, controlled reopen, active-revision isolation, history preservation, optimistic locking, scoped idempotency, database-enforced open uniqueness, and atomic audit/outbox behavior. PostgreSQL 18 directly proved simultaneous reconciliation produces no duplicate exception, audit, or outbox.

The final ownership audit identified the public PostgreSQL 18 service and all of its child processes at the Program Files data directory, then excluded them completely. Two old allowed-prefix TEMP directories were non-PostgreSQL and were preserved. A unique-token cluster on a separate localhost port provided all database evidence. Barrier-based direct races ran 10 iterations for each manual/automatic scenario and 10 iterations for replan/reconcile with zero deadlocks, timeouts, raw integrity leakage, duplicate actionable items, mixed revisions, or partial target graphs.

The final safe-downgrade gate found two genuine fail-closed gaps: stored idempotency replay responses in `20260801_route_exception`, and non-default scoped-idempotency identity in `20260730_multileg_route`, could previously be dropped by a successful downgrade. Only downgrade predicates in the existing revisions were tightened; upgrade schema and domain behavior were not changed. The correction also guards projected/reconciliation fields, changed plan versions, Phase 1B milestone/work-item ownership, and replan provenance before any DDL. Empty stepwise downgrade, Phase 1A schema equivalence, re-upgrade, populated rejection, no-partial-DDL snapshots, and transaction recovery passed on PostgreSQL 18.

Still deferred: browser/mobile UAT and `.venv` repair. Persistent database application remains pending with every application-register target set to `NO`. No commit or push was performed; the Phase 1B working tree remains preserved.

The UAT readiness remediation gate closed the three prior readiness blockers
without a schema or migration change. A guarded deterministic seed now creates
the complete synthetic Phase 1B graph and role matrix; explicit loopback binds
are preserved; and the operational detail UI now exposes the established
timeline, checkpoint lifecycle, replan, exception, work-item, permission, and
history contracts. Smoke-driven fixes added checkpoint expected versions and
verification idempotency keys to the client adapter and included checkpoint
milestones in the compatibility shipment event-history read.

Final evidence is 377 backend tests passed with the same 12 skips, 21 frontend
tests passed, lint at 0 errors/11 warnings, build passed, all direct PostgreSQL
gates passed, and a clean loopback-only local smoke passed. The smoke is not the
full Browser/Mobile UAT. That gate, `.venv` repair, and every persistent
migration application remain deferred.

## Local SQLite runtime path remediation

Local database precedence is now explicit: test isolation first when testing;
otherwise an explicit `DATABASE_URL`; then, for local development only, an
absolute external `FORWARDER_LOCAL_DB_PATH`; finally the OS-specific user-data
default. Production fails closed without `DATABASE_URL`. UAT fails closed
without an explicit PostgreSQL `DATABASE_URL`, rejects SQLite, and does not
automatically load environment files.

Configuration import and URI resolution do not create the database or its
directory. The application creates a file-backed SQLite parent directory only
at startup. Relative paths and paths inside the repository, including
`instance`, are rejected.

After focused and full backend tests passed, the ignored legacy runtime
database was copied to the Windows user-data location outside the repository.
Source and destination size and SHA-256 matched, the destination directory and
file ACLs were restricted to the current user and SYSTEM, and the hash still
matched after the ACL change. Only then was the source removed. Database
content was not read or queried. Tracked database artifacts were preserved:
`forwarder_dev.db`, `backend/forwarder_dev.db`, `test_live.db`, and
`test_run.db`.

`TRACKED_DATABASE_ARTIFACT_REVIEW_DEFERRED_TO_PHASE1B_FINAL_REVIEW`

Browser/Mobile UAT remains pending, `.venv` remains unchanged, persistent
application remains `NO`, and no commit or push was performed.

## Final local backend/frontend smoke finding

The real local stack passed on a new disposable PostgreSQL 18.0/UTF8 cluster,
the real loopback-only backend and frontend, and Chromium at 1280 x 720. Login,
the primary shipment graph, three legs, six checkpoints, active revision,
timeline states and reconciliation, replan, exceptions, manual resolution,
actionable work items, refresh, and direct reload were present and usable.
Console fatal errors and unexpected 5xx/production requests were zero. The only
browser notes were non-fatal React Router future-flag warnings; the backend also
emitted a non-fatal SQLAlchemy warning while serializing work items with no
milestone ID. No mutation was needed for the smoke.

Startup did not change the Alembic revision or 57-table schema count. No SQLite,
external `.env`, public PostgreSQL, persistent environment, production endpoint,
or tracked database was used. Cleanup left zero current-token resources. This
closes local-smoke readiness as `YES`; full Browser/Mobile UAT, `.venv` repair,
Phase 1B Final Review, commit/push, target selection, backup/restore readiness,
persistent migration application, and post-migration verification remain
deferred.

## Browser/Mobile UAT blocking defect

| ID | Severity | Workflow | Viewport | Expected | Actual | Evidence | Status |
|---|---|---|---|---|---|---|---|
| P1B-UAT-001 | HIGH | Operational shipment list | 1440 x 900; 390 x 844 | One card for the one Organization A shipment | Shipment-level SQL deduplication now produces one API/UI item and correct pagination | `evidence/phase1b_browser_mobile_uat/03-desktop-shipment-list-dedup-remediation.png`; `04-mobile-390-shipment-list-dedup-remediation.png` | REMEDIATED; TARGETED RETEST PASS |
| P1B-UAT-003 | HIGH | Permission matrix / milestone lifecycle | 1440 x 900; 390 x 844 | Reporter can open shipment detail and report milestones while privileged actions remain denied | Reporter and Verifier now receive only `route_plan.read` and `route_exception.read`; Reporter report and independent verification pass | Before: `16-final-reporter-permission-blocker.png`; after: files `17` through `23` | FIXED_PENDING_FULL_UAT |
| P1B-UAT-004 | HIGH | Vite backend target selection | Runtime configuration | Explicit `VITE_BACKEND_URL` overrides the local port file; invalid explicit targets fail closed | Resolver now applies explicit environment > `.backend-port` > legacy default and rejects credential-bearing or malformed explicit targets | Eight focused resolver tests; one-shot proxy health probe to the token backend on `127.0.0.1:52054` while stale `.backend-port` remained `57065` and port 5001 had no listener | FIXED_PENDING_FULL_UAT |

The defect was found on a fresh disposable PostgreSQL 18/UAT seed and was
reproduced after reload in both tested viewports. No remediation was attempted
because this gate is validation-only. Browser/Mobile UAT remains `NO` and
persistent applied remains `NO`.

The targeted remediation used a fresh disposable PostgreSQL 18/UTF8 database,
the official seed, direct PostgreSQL/API coverage, full backend and frontend
regressions, and a real loopback-only browser retest. The query deduplicates
shipments before pagination without client-side masking. Full Browser/Mobile
UAT remains `NO` and must be rerun from the beginning.

## Clean full-rerun blocker after deduplication remediation

| ID | Severity | Workflow | Expected | Actual | Status |
|---|---|---|---|---|---|
| P1B-UAT-002 | HIGH | Fresh disposable environment / official Phase 1B seed | Harness uses the shared seed/test contract | Canonical `forwarder_phase1b_uat_<token>` migrated, seeded, and passed direct dedup with zero skips | RESOLVED_HARNESS_ALIGNMENT_PENDING_FULL_UAT |

The clean rerun passed backend, frontend, lint, build, secret-scan, PostgreSQL
18 initialization, and migration-to-head controls before this failure. No
validation workaround or source fix was applied. Browser workflows and the
five-viewport matrix were not started. Cleanup removed the disposable
database, role, cluster, listener, and token directory. P1B-UAT-001 remains
`FIXED_PENDING_FULL_UAT`; Browser/Mobile UAT remains `NO`; persistent applied
remains `NO`.

### P1B-UAT-002 recovery result

The prior rejection was caused solely by the harness selecting
`forwarder_phase1a_test_phase1b_uat_<token>`. Read-only source inspection
proved `forwarder_phase1b_uat_<token>` is accepted by both the official seed
and the direct PostgreSQL deduplication test. A fresh PostgreSQL 18.0/UTF8 run
then passed migration, every expected seed count, and the direct test with one
pass and zero skips. The security guard was neither bypassed nor changed.

Classification: `UAT_HARNESS_DATABASE_NAME_MISMATCH`; product defect: `NO`.
P1B-UAT-002 is resolved pending full UAT. P1B-UAT-001 remains
`FIXED_PENDING_FULL_UAT`; neither defect is `CLOSED_VERIFIED` until the clean
five-viewport Browser/Mobile UAT completes.

### P1B-UAT-004 recovery result

The Vite proxy target resolver now gives an explicitly present
`VITE_BACKEND_URL` precedence over `.backend-port`. The local port file remains
an unchanged convenience fallback, and `http://localhost:5001` remains the
last fallback only when neither prior source is usable. An invalid explicit
target is not silently replaced by either fallback; non-HTTP(S), malformed,
credential-bearing, path-bearing, query-bearing, and fragment-bearing values
fail closed during configuration.

Eight targeted resolver tests and the full 30-test frontend suite passed. A
single-start, loopback-only Vite runtime probe returned `status=ok` through
the proxy to the existing token backend on port 52054 while `.backend-port`
remained 57065. Port 5001 had no listener. The temporary probe Vite process
was stopped; the token backend was left running. Browser/Mobile UAT remains
`NO`, persistent applied remains `NO`, and P1B-UAT-004 is
`FIXED_PENDING_FULL_UAT`.

## Final clean-rerun direct-precheck blocker (2026-07-26)

| ID | Severity | Workflow | Expected | Actual | Evidence | Status |
|---|---|---|---|---|---|---|
| P1B-UAT-006 | HIGH | Direct PostgreSQL Reporter/correction precheck | Select an active, event-free, reportable arrival milestone | Fixed sequence-3 selection could target consumed state and correctly receive 409 `INVALID_CHECKPOINT_TRANSITION`; semantic selection passes fresh and pre-consumed databases | `phase1b_reporter_arrival_report_409_remediation.md` | RESOLVED_TEST_FIXTURE_ALIGNMENT_PENDING_FULL_UAT |

Shipment deduplication passed independently. The five-viewport browser matrix
was not started because the three-precheck admission gate failed. No fix was
attempted in this validation-only gate.
### P1B-UAT-004 runtime closure result (2026-07-26)

The previous stale-port backend was safely attributed and stopped, leaving zero
previous-runtime backend processes, children, or listeners. ESLint passed with
zero errors and the existing 11-warning baseline. A fresh PostgreSQL 18/UTF8
token environment reached `20260801_route_exception` with pending zero and the
official seed baseline. Backend and Vite each started once; Vite used the
explicit current-token backend while `.backend-port` remained 57065.

Fresh Chromium at 1280 x 720 passed login, operational shipment list, shipment
detail, active route-plan display, refresh, and logout. Requests to stale port
57065, port 5001, production, and cross-origin API origins were zero. Fatal
console errors, unhandled promises, unexpected 5xx, CORS failures, blank pages,
auth loops, and credential exposure were zero. Cleanup left zero current-token
processes, listeners, database/role artifacts, or temporary files.

P1B-UAT-004 is `FIXED_PENDING_FULL_UAT`. Browser/Mobile UAT remains `NO`,
persistent applied remains `NO`, and no defect is `CLOSED_VERIFIED` by this
narrow closure gate. Result:
`PHASE_1B_VITE_BACKEND_TARGET_PRECEDENCE_RUNTIME_CLOSURE_PASS_WITH_NOTES`.

## Final full UAT blocker: Reporter correction authorization

| ID | Severity | Workflow | Viewport | Expected | Actual | Evidence | Status |
|---|---|---|---|---|---|---|---|
| P1B-UAT-005 | HIGH | Reporter permission matrix / milestone lifecycle | 1440 x 900 | Reporter can report but cannot correct verified milestones | Reporter correction UI is guarded by `checkpoint.report`; one unauthorized correction and audit row committed | `evidence/phase1b_browser_mobile_uat/27-final-full-reporter-correct-permission-blocker.png`; `29-final-full-uat-blocked-reporter-correction.md` | OPEN; FULL UAT BLOCKER |

The final full rerun stopped immediately after this finding. Browser/Mobile UAT
remains `NO`, persistent applied remains `NO`, and no source fix was made.

### P1B-UAT-005 remediation result (2026-07-26)

Root-cause classification is RC-A plus RC-B/service-path enforcement. Both the
shipment-detail control and `correct_checkpoint_milestone` incorrectly used
`checkpoint.report`; the stored seed and permission matrix consistently define
`milestone.correct` as the canonical correction permission. There was no
contract conflict and no permission escalation.

The frontend and backend now enforce `milestone.correct`. Direct API and
PostgreSQL tests prove Reporter denial before every side effect, while the
seeded correction-capable user still succeeds. Desktop and 390 x 844 targeted
browser retests passed. P1B-UAT-005 is `FIXED_PENDING_FULL_UAT`; P1B-UAT-001
through P1B-UAT-004 retain their prior pending-full-UAT statuses. Full
Browser/Mobile UAT must restart from the beginning and remains `NO`; persistent
applied remains `NO`.
