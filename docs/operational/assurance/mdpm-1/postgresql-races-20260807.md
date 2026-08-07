# MDPM-1 PostgreSQL race validation — 2026-08-07

- Runner: `backend/tests/test_mdpm_races_postgresql.py`
- PostgreSQL: 18.0, real loopback cluster and transactions; no SQLite or in-memory substitute.
- Source database: `forwarder_phase1b_uat_mdpm_20260807_2215` on disposable cluster port `55449`.
- Isolation: each test cloned a uniquely named `forwarder_phase1b_uat_mdpm_race_*` database and dropped it after the test.
- Result: **13 passed** in 10.71 seconds.

Covered approval/transition, replacement/transition, rejection/transition, association/transition, conditional resolution/transition, override grant/transition, override revoke/transition, simultaneous transitions, simultaneous assessments, stale requirement version, stale milestone version plus organization isolation, same-key/same-payload replay, and same-key/different-payload rejection.

The suite proves serialized readiness and transition mutation, deterministic stale-writer failure, single override consumption, replacement invalidation of stale approval, one state-changing transition event, idempotent replay, payload-conflict rejection, and cross-organization non-disclosure.
