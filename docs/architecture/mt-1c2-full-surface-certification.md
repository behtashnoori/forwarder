# MT-1C.2 full-surface certification

Date: 2026-08-12. Candidate start HEAD: `da4f85114f9d61cc645e748ea1d4c35d62a2ddaf`.

## Certification results

- PostgreSQL 18.0, loopback-only disposable databases: 10 passed, 0 skipped, 0 xfailed, 0 failed.
- Matrix: 15/15 PASS across detail, list, search, selector, report, aggregation/count, export, pagination/batching, reconciliation/job, assignment/notification, outbox/side effect, document metadata, guarded download/storage, descendant/composite, and public tracking containment.
- Six states: CLEAR behaves normally; QUARANTINED, CONFLICT, UNRESOLVED, INVALID_LINEAGE, and missing certification metadata fail closed.
- Transaction/concurrency: pinned N, serialized N+1 publication, held-instance validation, no mixed census result, rollback atomicity, logical report/export/page census, and cache version/token checks passed.
- Broad backend regression: 698 passed, 75 explicit integration skips, 1 expected xfail, 0 failed. The xfail is the unresolved MT-3 numeric public-tracking characterization.
- Focused triage: 7 passed. Related migration/security/user-management/quarantine/auth suites: 83 passed.

## Seven-failure triage

| Test | Group | Expected | Actual before fix | Root cause | Classification | Fix | Rerun |
|---|---|---|---|---|---|---|---|
| `test_readiness_endpoint_returns_503_for_unversioned_schema` | migration safety | 503 pending | census queried absent schema | health probe incorrectly fenced | REAL_MT1C2_REGRESSION | exact health endpoint exemption | PASS |
| `test_readiness_endpoint_returns_revisions_when_ready` | migration safety | 200 with revisions | census preempted mocked readiness | health probe incorrectly fenced | REAL_MT1C2_REGRESSION | exact health endpoint exemption | PASS |
| `test_health_is_db_only_and_masks_failures` | migration safety | masked 503 | census hook reached mocked DB first | health probe incorrectly fenced | REAL_MT1C2_REGRESSION | exact health endpoint exemption | PASS |
| `test_ping_never_touches_database` | migration safety | DB-free 200 | census hook touched DB | liveness probe incorrectly fenced | REAL_MT1C2_REGRESSION | exact health endpoint exemption | PASS |
| `test_crm_customers_requires_authentication` | security config | 401 | missing census table | isolated test omitted schema setup | TEST_ENVIRONMENT_DEFECT | test-local `db.create_all()` | PASS |
| `test_user_delete_cleanup_and_hard_delete_contract` | user deletion | atomic 200 cleanup | protected bulk DML rejected | legacy cleanup bypassed mapped validation | REAL_MT1C2_REGRESSION | mapped protected-row cleanup | PASS |
| `test_user_without_dependencies_is_permanently_deleted` | user deletion | atomic 200 deletion | zero-row protected bulk DML rejected | same unconditional bulk path | REAL_MT1C2_REGRESSION | mapped protected-row cleanup | PASS |

Health exemptions name only the three registered health endpoints; no business or public resource endpoint is exempt. User deletion selects census-visible protected instances and uses ORM flush validation, retains one terminal commit, and rolls back on failure. Authentication, CORS, secrets, tenant isolation, and quarantine defaults were not relaxed.

## Static and operational integrity

- Python compilation: PASS.
- Ruff on the three triage-touched Python files: PASS. A wider dirty-worktree scan reported pre-existing style debt and was not used as a repository-wide blocker.
- `git diff --check`: PASS.
- Alembic sole head: `20260822_mt1c1_census_fence`.
- Secret/security policy tests: 24 passed.
- Migrations remain explicit; startup does not auto-upgrade or seed Production.
- Production was untouched. No deployment, push, tag movement, Legacy Census, MT-1, MT-2, or MT-3 redesign occurred.

## Independent security review and closure

The fresh read-only adversarial review returned `MT-1C.2 SECURITY REVIEW — PASS`.
It found no weakened migration, authentication, tenant, quarantine, deletion,
storage, tracking, cache, raw SQL/Core, or concurrency boundary. The exact
health endpoint exemptions expose no certified resource data, and mapped user
cleanup retains census visibility, flush validation, one commit, and rollback.

`QUARANTINE_RUNTIME_CERTIFIED=true`

`MT1C_FULL_SURFACE_CERTIFIED=true`

Final classification: `MT-1C.2 CLOSED — QUARANTINE RUNTIME CERTIFIED — READY FOR LEGACY DATA CENSUS`.
