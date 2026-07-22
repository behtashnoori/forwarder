# Phase 0.2 PostgreSQL test matrix

| Area | Scenario | Expected | Observed |
|---|---|---|---|
| Graph | heads/branches/history | one valid head | PASS |
| Fresh DB | current/check before upgrade | base/exit 2 | PASS |
| CLI guard | upgrade without confirm | exit 2, no write | PASS |
| Fresh DB | explicit upgrade | head/exit 0 | PASS |
| Version table | revision storage | one head row | PASS |
| Reversibility | head to previous to head | executable, same schema | PASS WITH IRREVERSIBLE MIGRATION NOTE |
| Existing data | synthetic sentinel before head | preserved | PASS |
| Constraints | port/province entry FKs | one each | PASS |
| Metadata | Alembic autogenerate check | no drift preferred | NOTE: historical drift found |
| Startup | app factory and skip startup | no schema write | PASS |
| CLI failure | invalid/unavailable URL | masked exit 1 | covered by regression tests |
| Probes | ping/health/ready at head | 200/200/200 | PASS |
| Probes | empty/behind/unavailable | readiness 503 | covered by targeted tests |
| Repetition | upgrade/check/probes repeated | no extra DDL/data | PASS |
| Concurrency | parallel revision checks | consistent read-only status | PASS |
| Concurrency | two upgrades from previous | no silent double migration | PASS WITH NOTE: explicit 1/0 |
| Security | current-tree scanner | zero findings | PASS |
| Backend | targeted migration/runtime tests | pass | 33 passed |
| Backend | full pytest suite | pass | 310 passed, 6 skipped |
| Frontend | lint/build | pass | PASS; lint has 10 existing warnings |

PostgreSQL-only automated checks are in `backend/tests/test_phase0_2_postgresql_gate.py`. They are skipped unless `FORWARDER_PHASE02_POSTGRES_URL` points to a loopback database whose name begins with `forwarder_phase02_test_`.

The PostgreSQL-only tests were executed against the isolated Phase 0.2 cluster and passed as part of the 33-test targeted run. The six full-suite skips are pre-existing tests that require separate explicit feature-specific PostgreSQL URLs; they are not counted as executed PostgreSQL checks.

Cleanup was completed and verified: temporary DB/cluster-owned role removed, cluster stopped, temporary data/state/log files absent, and zero PostgreSQL processes remained for the disposable data directory.
