# Test matrix

## Final matrix status (2026-07-27)

| Gate | Final result |
|---|---|
| Targeted route-contract | PASS (`P1B-UAT-20260727044111047492`) |
| Full Browser/Mobile UAT | PASS (`P1B-UAT-20260727044204801260`) |
| Five viewports | PASS |
| Workflows | 22/22 PASS |
| Backend full | 396 passed, 14 conditional skipped (reused) |
| Frontend full | 31 passed (reused) |
| Reporter/Milestone frontend | 18 passed (reused) |
| Direct PostgreSQL | PASS (reused) |
| Harness tests | 12 passed (reused) |
| ESLint | 0 errors, 11 baseline warnings (reused) |
| Build | PASS (reused) |
| Browser/Mobile UAT | YES |
| Local database cutover | PASS — [final closure report](phase1b_local_backup_restore_migration_result.md) |
| Local active database/head | `forwarder_db` / `20260801_route_exception` |
| Retained legacy database | `forwarder_db_legacy_20260727_222328` |
| Server/Production | `NOT_STARTED` / `UNTOUCHED` |

P1B-UAT-001 through P1B-UAT-006 are `CLOSED_VERIFIED`. The remaining content is historical chronology and its earlier pending statuses are superseded.

## Historical chronology

P1B-UAT-006 now selects a semantically reportable, event-free milestone.
Fresh PostgreSQL tests cover same-key replay, distinct duplicate 409,
stale-version 409, Reporter correction 403 with zero side effects, and
authorized correction success. Full UAT remains pending.

Current evidence from 2026-07-25:

- Validation used system Python 3.13.9 with process-local UTF-8; `.venv` was not changed.
- One localhost-only disposable PostgreSQL 18.0 UTF8 cluster hosted two independent guard-compatible databases: `forwarder_phase1a_test_<token>` and `forwarder_phase1a_test_phase1b_<token>`.
- Alembic reported one head, `20260801_route_exception`; fresh official-runner upgrades of both databases reached that revision, including the Iranian reference seed and follow-up exception transition state.
- Targeted route-orchestration service/API, delay, and exception tests: 39 passed.
- Disposable PostgreSQL 18 Phase 1A compatibility: 1 passed.
- Disposable PostgreSQL 18 Phase 1B integrity/idempotency: 1 passed.
- Direct Phase 1B HTTP contract tests: 4 passed (included in the targeted and full-suite counts).
- Direct exception race evidence: 2 passed. Manual/automatic reconciliation covered four scenarios with 10 independent iterations each; replan/reconciliation covered 10 independent iterations.
- Direct safe-downgrade guard tests: 2 passed on PostgreSQL 18, covering stored replay responses and scoped idempotency with pre/post schema, data, revision, and transaction assertions.
- Full backend suite: 357 passed, 12 skipped. The four additions over the original baseline are two explicit-DSN race tests and two explicit-DSN safe-downgrade tests; all four passed separately on PostgreSQL.
- Frontend behavior: 10 passed.
- ESLint: 0 errors, 12 warnings.
- Frontend production build: passed.
- Current-tree secret scan: findings=0.
- Empty stepwise downgrade: head → `20260730_multileg_route` → `20260729_operational_vertical_slice` passed; Phase 1A schema was equivalent except harmless whitespace formatting in one restored function body; re-upgrade to head passed.
- Populated Phase 1B downgrade: rejected by `SAFE_DOWNGRADE_GUARD` before destructive DDL; revision, schema, data, triggers, functions, constraints, and connection usability remained intact.
- Disposable databases, role, cluster process, data directory, and log were removed after validation.
- Resource ownership audit: the running `postgresql-x64-18` service and its process tree were identified at the public data directory and excluded without stop, restart, configuration change, or test connection. Two allowed-prefix old directories were classified as non-PostgreSQL temp and preserved; no orphan deletion was authorized.

PostgreSQL coverage directly rejects cross-plan checkpoint insert/update, foreign predecessor/successor dependencies, foreign checkpoint milestones, and invalid exception scope. It also verifies rollback after integrity failure.

Atomic idempotency coverage uses two independent connections/threads. Same scope/key/payload returns the winner result to both callers with one event, idempotency row, audit row, and outbox row. Same scope/key with different payload produces one winner and one stable `IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_PAYLOAD` conflict without raw `IntegrityError`.

Direct HTTP coverage verifies stable cross-plan `409`, tenant-scoped direct-ID `404`, same-key/different-payload `409`, same-key/different-resource independence, inactive-membership fail-closed behavior, the standard error envelope, and no traceback/constraint leakage.

Checkpoint lifecycle coverage verifies report/verify/correct/re-verify, reporter/verifier separation, stale-actual invalidation, corrected-actual derivation, HTTP replay, immutable history, PostgreSQL UPDATE/DELETE rejection, and concurrent same-key report/verify/correction without duplicate event, audit, or outbox rows.

Atomic replan coverage includes full graph/provenance mapping, event non-duplication, old-plan work-item supersession, ten injected rollback points, stale/inactive contracts, same-key replay, different-key winner/loser concurrency, unique revision allocation, and exactly one active plan. These scenarios passed on PostgreSQL 18 using a fresh supported-runner migration. The populated downgrade guard remained fail-closed and the disposable cluster was removed.

Delay coverage verifies baseline preservation, shuffled topological chain propagation, fan-in, actual precedence, checkpoint/milestone/leg synchronization, cycle-before-mutation, idempotent replay, and exactly one reconciliation audit/outbox. Real PostgreSQL coverage also verifies projection synchronization and that reconciliation does not mutate the milestone-event ledger.

Timeline failure injection passes after the first checkpoint update, mid-chain, after milestone synchronization, after route-leg synchronization, before audit, before outbox, and before commit. Every rollback preserves prior projected and actual values and leaves event, audit, and outbox counts unchanged.

Exception coverage verifies overdue and dependency detection, automatic resolution, manual resolution, controlled reopen, scoped idempotent replay/conflict, active-plan isolation, superseded history, one actionable item, audit/outbox atomicity, database open uniqueness, and simultaneous reconciliation. Two PostgreSQL threads produced one opener and one unchanged result with no duplicate exception, audit, or outbox.

Final direct race evidence used independent application transactions and `threading.Barrier`, not fixed sleeps. Condition-cleared, condition-persisting, stale-manual, and same-key retry scenarios each passed 10 iterations. The replan/reconcile race passed 10 iterations with one active plan, unique revisions, source history preserved and non-actionable, no target exception clone, no mixed-revision mutation, no partial graph, and zero raw database errors, deadlocks, timeouts, or invalid outcomes.

Still deferred: browser/mobile UAT and any persistent migration application.

## UAT readiness remediation evidence (2026-07-25)

- Seed and loopback-binding focused tests: 20 passed.
- Integrated readiness/operational targeted backend tests: 85 passed.
- Full backend suite after the final adapter edit: 377 passed, 12 skipped.
  The 20-test increase over the 357 baseline is the new seed and binding
  coverage; the skip count did not increase.
- Frontend behavioral suite: 21 passed across four files, including 11 focused
  Phase 1B detail/reconcile/permission/error/responsive tests.
- ESLint: 0 errors, 11 warnings. The previous detail-page hook warning was
  removed; remaining warnings are pre-existing.
- Frontend production build: passed.
- Disposable PostgreSQL UAT seed: fresh migration passed; two identical seed
  summaries; direct count and integrity checks passed.
- Direct PostgreSQL Phase 1A: 1 passed.
- Direct PostgreSQL Phase 1B plus exception races: 3 passed.
- Direct safe downgrade: 2 passed.
- Limited loopback-only local browser smoke: passed at 1440, 768, 390, and 360.
- Full Browser/Mobile UAT: pending.
- Persistent database application: `NO`.

## Local SQLite runtime remediation evidence (2026-07-25)

- Focused config, host-binding, application-factory/startup-safety, and UAT
  seed selection: 67 passed, 0 skipped, 0 failed.
- Phase 1B UAT seed focused run: 6 passed, 0 skipped, 0 failed.
- Full backend suite: 392 passed, 12 known skips, 0 failed. The skip count did
  not increase.
- Explicit PostgreSQL URL wins over local SQLite configuration.
- An explicit absolute external local path wins over the user-data default.
- Relative and repository-local paths, including `instance`, are rejected.
- Windows LocalAppData, Linux XDG/fallback, macOS Application Support,
  Unicode, spaces, and Windows drive-path behavior are covered.
- Test collection does not resolve or create the user-local database.
- Config import and database URI resolution create neither a directory nor a
  database file.
- Production without `DATABASE_URL` and UAT without an explicit PostgreSQL
  `DATABASE_URL` fail closed; UAT rejects SQLite.
- Local runtime relocation passed source-lock, size, SHA-256, ACL, post-ACL
  hash, destination-exists, and source-removed controls.
- No database content was inspected; no migration was run; persistent applied
  remains `NO`.
- Current-tree secret scan remained at zero findings.

## Direct PostgreSQL regression replay (2026-07-25)

The current working-tree snapshot was replayed on a new loopback-only,
token-scoped PostgreSQL 18.0 UTF8 cluster using system Python 3.13.9 and
process-local UTF-8. Each suite used its own guard-compatible database; safe
downgrade used separate head and Phase 1B databases.

| Suite | Passed | Skipped | Failed | Duration | Result |
|---|---:|---:|---:|---:|---|
| Phase 1A PostgreSQL | 1 | 0 | 0 | 3.002 s | PASS |
| Phase 1B PostgreSQL | 1 | 0 | 0 | 3.677 s | PASS |
| Exception reconciliation races | 2 | 0 | 0 | 12.713 s | PASS |
| Phase 1B safe downgrade | 2 | 0 | 0 | 3.144 s | PASS |

Alembic exposed one head, `20260801_route_exception`, with the expected parent
chain. The exception tests retained all ten iterations and thread barriers and
completed with zero deadlocks, timeouts, raw database errors, or invalid
outcomes. Safe-downgrade guards rejected populated destructive downgrades
before partial DDL and preserved revision, schema, data, and connection
usability. Cluster startup took 9.496 seconds and final cleanup took 2.149
seconds; current-token resources remaining were zero.

## Local backend/frontend smoke gate (2026-07-25)

- PostgreSQL startup: PASS (fresh PostgreSQL 18.0/UTF8, loopback only).
- Fresh migration: PASS in 3.20 s; head `20260801_route_exception`, pending zero.
- Official Phase 1B seed: PASS in 3.65 s; 2 organizations, 8 users, 2 shipments, 2 route plans, 6 legs, 12 checkpoints, 12 dependencies, 36 milestones, and 2 open work items.
- Backend startup: PASS in 2.09 s, loopback only; frontend startup: PASS in 1.30 s, loopback only.
- Sanitized API smoke: PASS in 0.46 s for health, login, shipment list/detail, active route plan, three-leg/six-checkpoint graph, timeline, two exceptions, and two work items.
- Chromium smoke at 1280 x 720: PASS in 22.12 s for login, shipment summary, active revision, role-visible controls, refresh, and direct URL reload.
- Browser quality: zero fatal console errors, unhandled promises, unexpected 5xx, CORS failures, failed essential assets, production requests, credential/token exposure, or error-boundary activation. Non-fatal React Router future-flag warnings were recorded.
- Startup schema side effect: zero; revision stayed at head and the 57-table count was unchanged.
- SQLite use: zero. Tracked database artifacts were unchanged. Cleanup removed every current-token process, listener, database cluster, and temporary artifact.
- Current-tree secret scan: `findings=0`.

Result: `PHASE_1B_LOCAL_BACKEND_FRONTEND_SMOKE_PASS_WITH_NOTES` and
`UAT readiness = YES`. Full Browser/Mobile UAT remains `NO`; persistent applied
remains `NO`.

## UAT database-name contract recovery (2026-07-26)

| Consumer | Accepted prefix | Canonical database accepted | Result |
|---|---|---|---|
| Seed CLI | `forwarder_phase1b_uat` or `phase1b_uat` | `forwarder_phase1b_uat_<token>` | PASS |
| Direct dedup test | `forwarder_phase1b_uat_` | `forwarder_phase1b_uat_<token>` | PASS |
| Recovery harness | Contract intersection | `forwarder_phase1b_uat_<token>` | PASS |

- PostgreSQL 18.0/UTF8, loopback-only, unique token directory and port: PASS.
- Fresh migration: single head `20260801_route_exception`, pending zero.
- Official seed: PASS with 2 organizations, 8 users, 8 memberships, 2
  shipments, 2 route plans, 2 active plans, 6 legs, 12 checkpoints, 12
  dependencies, 36 milestones, and 2 open work items.
- Direct `test_shipment_list_deduplication_postgresql.py`: 1 passed, 0
  skipped, 0 failed.
- Full-suite status for that explicit-DSN test: skipped when the disposable
  environment variable is absent; direct PostgreSQL status: passed;
  acceptable: YES.
- Seed guard, source, test, migration, API, frontend, and config changes: none.
- Full backend, frontend tests, lint, build, and browser were intentionally not
  rerun in this narrow recovery gate.
- P1B-UAT-002: `RESOLVED_HARNESS_ALIGNMENT_PENDING_FULL_UAT`.
- P1B-UAT-001: `FIXED_PENDING_FULL_UAT`.
- Browser/Mobile UAT: `NO`; persistent applied: `NO`.

## P1B-UAT-003 reporter permission remediation (2026-07-26)

| Control | Result |
|---|---|
| Seed permission/idempotency tests | 8 passed |
| Direct PostgreSQL reporter boundary | 1 passed, 0 skipped |
| Direct PostgreSQL shipment dedup | 1 passed, 0 skipped |
| Backend full | 395 passed, 14 skipped; the new explicit-DSN test passed directly |
| Frontend behavioral | 22 passed |
| ESLint | 0 errors, 11 warnings |
| Production build | PASS |
| Reporter desktop/mobile detail and report | PASS |
| Reporter self-verify and privileged actions | DENIED as required |
| Verifier independent verify | PASS |
| Read-only / no-permission / inactive | PASS |
| Full Browser/Mobile UAT | PENDING (`NO`) |
## P1B-UAT-004 runtime closure gate (2026-07-26)

| Control | Result |
|---|---|
| Resolver tests | 8/8 passed |
| Frontend suite | 30/30 passed |
| ESLint | PASS; 0 errors, 11 baseline warnings, 0 resolver warnings |
| Production build | PASS |
| Explicit Vite target | Current token backend selected |
| Stale port 57065 / port 5001 requests | 0 / 0 |
| Chromium login / list / detail / refresh / logout | PASS / PASS / PASS / PASS / PASS |
| Unexpected 5xx / CORS / fatal console / unhandled promise | 0 / 0 / 0 / 0 |
| Current-token cleanup | 0 processes, listeners, or temp artifacts remaining |
| P1B-UAT-004 | `FIXED_PENDING_FULL_UAT` |
| Browser/Mobile UAT / persistent applied | `NO` / `NO` |

## Final clean full-UAT admission prechecks (2026-07-26)

| Test | Collected | Passed | Skipped | Failed | Result |
|---|---:|---:|---:|---:|---|
| Shipment deduplication | 1 | 1 | 0 | 0 | PASS |
| Reporter permission | 1 | 0 | 0 | 1 | BLOCKED: report returned 409 |
| Correction authorization | 1 | 0 | 0 | 1 | BLOCKED: report returned 409 before correction assertions |

Browser/Vite/backend runtime and all five viewports were not started.
Browser/Mobile UAT remains `NO`; persistent applied remains `NO`.

## P1B-UAT-005 milestone correction authorization (2026-07-26)

| Control | Result |
|---|---|
| Targeted backend correction authorization | 2 passed; 0 skipped; 0 failed |
| Seeded PostgreSQL Reporter boundary + shipment dedup | 2 passed; 0 skipped; 0 failed |
| Backend full | 396 passed; 14 existing conditional skips; 0 failed |
| Frontend behavioral | 31 passed; 0 failed |
| ESLint | PASS; 0 errors; 11 existing unrelated warnings |
| Production build | PASS |
| Reporter desktop/mobile Correct controls | 0 / 0 |
| Reporter report / direct correction | PASS / 403 |
| Reporter event/audit/outbox/version/timeline deltas | all 0 |
| Correct-capable desktop/mobile | visible and usable |
| Missing reason / valid correction | denied / PASS |
| Fatal console / unexpected 5xx | 0 / 0 |
| P1B-UAT-005 | `FIXED_PENDING_FULL_UAT` |
| Browser/Mobile UAT / persistent applied | `NO` / `NO` |
