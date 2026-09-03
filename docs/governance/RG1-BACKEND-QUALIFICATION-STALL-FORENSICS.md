# RG.1 — Backend Qualification Stall Forensics

## Scope and identity

This is Development-only release-qualification forensics. No production access,
artifact creation, deployment, push, merge, or application change occurred.

- Application candidate: `a2576690364fcaf58ca7ddc6c57143c3084bbb00`
- Release-engineering start: `4c2db33c4c5d87181c87780117f94a868479d15b`
- Branch: `release-gate/s7-forwarder-candidate`
- Application candidate invalidated: **NO**

## Reconstruction and classification

The release builder creates a temporary venv and invokes:

```text
<temporary-venv>\\Scripts\\python.exe -m pytest
```

Its qualification output previously did not identify the currently executing
test or provide bounded traceback diagnostics. A progress-visible equivalent
using the declared local Development environment completed continuously:

```text
D:\\Projects\\webapp\\15-forwarder\\.venv\\Scripts\\python.exe -u -m pytest -vv --durations=25
```

It completed in `327.67s` with `860 passed`, `92 skipped`, `1 xfailed`, and no
failure. Collection found 953 items; the difference is exactly the 92 skipped
and 1 xfailed items, not a baseline discrepancy.

The slowest completed test was `test_seed_is_complete_tenant_scoped_and_idempotent`
at `2.44s`; no individual test approached the diagnostic threshold. PostgreSQL
tests skipped under their explicit disposable-environment guards. During and
after the run, no test-owned listener on 5000, 5100, or 5101 and no orphaned
Python process remained.

**Primary classification: `OUTPUT_CAPTURE_FALSE_STALL`.** The prior record did
not retain enough progress evidence to distinguish quiet/buffered qualification
output from active execution. No application deadlock, database lock, process
leak, or application defect was reproduced.

## Correction and regression memory

The release builder now uses unbuffered, verbose pytest output, the 25 slowest
test report, and pytest's built-in `faulthandler_timeout=120`. This is limited
to release-engineering diagnostics; it neither skips tests nor changes product
behavior.

- `RGATE-R09`: Full backend release qualification must expose test progress and
  bounded stall diagnostics.
- `RGATE-R10`: Test-owned processes, listeners, and disposable DB resources
  must terminate before qualification is accepted.
- `RGATE-R11`: Qualification output capture must not make an active backend
  suite indistinguishable from a stall.

## Gate decision

Post-correction qualification used:

```text
D:\\Projects\\webapp\\15-forwarder\\.venv\\Scripts\\python.exe -u -m pytest -vv --durations=25 -o faulthandler_timeout=120
```

It completed with exit code `0` in `330.53s`: `861 passed`, `92 skipped`, and
`1 xfailed`. The one-pass increase over the pre-correction `860` result is the
new release-builder regression test. No test-owned Python process or listener
on 5000, 5100, or 5101 remained afterwards.

`BACKEND_RELEASE_QUALIFICATION = PASS` for the verified full backend suite.
`APPLICATION_CANDIDATE_INVALIDATED = NO`.
`RELEASE_GATE_MAY_RESUME = YES`, subject to Architecture / Business Owner
authorization; this record does not authorize packaging, deployment, or
production access.
