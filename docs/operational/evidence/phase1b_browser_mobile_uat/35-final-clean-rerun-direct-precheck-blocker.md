# Final clean rerun direct-precheck blocker

Date: 2026-07-26

All values in this record are synthetic and sanitized. No password, token,
cookie, authorization header, DSN, or customer data is included.

## Environment

- PostgreSQL: 18.0, UTF8, bound only to `127.0.0.1`
- Databases: four fresh canonical `forwarder_phase1b_uat_<token>_*` databases
- Migration runner: `python -m backend.migration_cli upgrade --confirm`
- Migration head: `20260801_route_exception`
- Seed runner: `python -m backend.operational_cli seed-phase1b-uat --confirm`
- Seed: completed independently for all four databases

## Mandatory direct prechecks

| Test | Collected | Passed | Skipped | Failed | Result |
|---|---:|---:|---:|---:|---|
| Shipment deduplication | 1 | 1 | 0 | 0 | PASS |
| Reporter permission | 1 | 0 | 0 | 1 | BLOCKED |
| Correction authorization | 1 | 0 | 0 | 1 | BLOCKED |

Both failing runs used a fresh independently migrated and seeded database.
`test_reporter_permission_postgresql.py` expected the Reporter arrival report
to return HTTP 200, but the response was HTTP 409. The test stopped at that
assertion before the required correction authorization and zero-side-effect
assertions could run.

Per the final gate, Backend, Vite, and Chromium were not started. No viewport
or browser workflow is claimed as passed, no source/test/config/migration/seed
change was made, Browser/Mobile UAT remains `NO`, and persistent applied
remains `NO`.

Result: `PHASE_1B_BROWSER_MOBILE_UAT_BLOCKED`.
