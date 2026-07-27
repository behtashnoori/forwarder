# Full UAT rerun seed-guard evidence

- Date: 2026-07-26
- Workflow: fresh disposable environment / official Phase 1B seed
- Viewport: not reached
- Role: not reached
- Expected: the mandated database name
  `forwarder_phase1a_test_phase1b_uat_<token>` is accepted by the official
  `seed-phase1b-uat` command.
- Actual: migration reached the single head `20260801_route_exception` with
  pending migrations equal to zero, then the official seed failed closed with
  `UAT_DATABASE_REJECTED` before browser or application workflows began.
- Cause evidence: `backend/operational_cli.py` allows only database names
  beginning `forwarder_phase1b_uat` or `phase1b_uat`. The direct deduplication
  test independently requires `forwarder_phase1b_uat_`, which is also
  incompatible with the mandated rerun name.
- Before/after status: new defect; no remediation attempted in this
  validation-only gate.
- Sanitization: PASS. No password, token, cookie, authorization header, DSN,
  email address, or customer data is included.
- Cleanup: database and role dropped, cluster stopped, listener closed, and
  the current-token directory removed.

Result: `PHASE_1B_BROWSER_MOBILE_UAT_BLOCKED`.
