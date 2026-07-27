# Phase 1B deterministic operator-run full UAT

## Final status note (2026-07-27)

The operator-run full UAT completed with `22/22 PASS` across five viewports under token `P1B-UAT-20260727044204801260`. Browser/Mobile UAT is `YES`; persistent applied is `NO`. For read-only head metadata use `python -m alembic -c backend/migrations/alembic.ini heads`. Upgrade and downgrade operations remain restricted to `backend.migration_cli`; raw Alembic upgrade is not allowed.

## Safety boundary

Run this harness only from a normal local Windows terminal. The restricted
automation executor must use only `--validate-only`, `--dry-run`, and the unit
tests. Real execution is deliberately double-gated by `--run --confirm`.

The harness never uses PowerShell process creation, `cmd /c`, npm/npx, a shell
wrapper, command strings, or `shell=True`. Every child is started from a Python
argument list with a deliberately small process environment.

Production repository `C:\1-webapp\1-forwarder`, production port `5001`, public
PostgreSQL port `5432`, `.backend-port`, repository SQLite files, and persistent
services are outside scope.

## Prerequisites

- Checkout must remain on
  `feature/forwarder-multileg-route-orchestration-phase1b` at
  `268d329060acd7f0516ddf90a2a0c54846d8e396`.
- Python 3.13, PostgreSQL 18, Node, and the repository Vite CLI must exist at
  the paths documented by the project.
- Supply an existing local Node browser runner with `--browser-runner`. It must
  consume `PHASE1B_UAT_BASE_URL`, `PHASE1B_UAT_API_URL`,
  `PHASE1B_UAT_PASSWORD`, and `PHASE1B_UAT_EVIDENCE_DIR`, return zero only when
  the complete browser/mobile matrix passes, and sanitize its own output.
- The browser runner and Chromium dependency remain operator-owned and outside
  this repository. This gate installs nothing.
- Chosen ports must be free, loopback-only, distinct, and must not be 5001 or
  5432.

## Safe inspection

```powershell
& 'C:\Users\pc\AppData\Local\Programs\Python\Python313\python.exe' `
  scripts\uat\phase1b_full_uat_runner.py --validate-only
```

The browser-runner check may show `FAIL` when none is supplied; it is
informational in safe modes. To validate the complete operator configuration:

```powershell
& 'C:\Users\pc\AppData\Local\Programs\Python\Python313\python.exe' `
  scripts\uat\phase1b_full_uat_runner.py --validate-only `
  --browser-runner 'C:\absolute\operator-owned\phase1b-browser-runner.mjs'
```

Preview the sanitized command and environment plan:

```powershell
& 'C:\Users\pc\AppData\Local\Programs\Python\Python313\python.exe' `
  scripts\uat\phase1b_full_uat_runner.py --dry-run `
  --browser-runner 'C:\absolute\operator-owned\phase1b-browser-runner.mjs'
```

No PostgreSQL, backend, Vite, or Chromium process is started in either mode.
Reports default to `%TEMP%\forwarder-phase1b-uat-reports`; use `--output-dir`
to select another non-production location.

## Operator execution

After reviewing the dry run, use a normal local terminal:

```powershell
& 'C:\Users\pc\AppData\Local\Programs\Python\Python313\python.exe' `
  scripts\uat\phase1b_full_uat_runner.py --run --confirm `
  --browser-runner 'C:\absolute\operator-owned\phase1b-browser-runner.mjs'
```

The deterministic order is: initialize disposable PostgreSQL, start it on
loopback, create the canonical database, run the official migration, run the
official seed, start Waitress, start Vite, wait for both readiness probes, and
run the browser runner. Cleanup stops application children, drops the
disposable database, and stops PostgreSQL after success, failure, timeout, or
Ctrl+C. The token-scoped runtime directory is then removed.

## Interpreting results

The final console line is sanitized JSON. Each run also emits sanitized JSON
and Markdown reports containing checks, durations, and the redacted command
plan. Child logs and screenshots exist only inside the temporary runtime and
are removed during cleanup; the browser runner should copy only sanitized
evidence needed by the operator before it exits if durable evidence is
required.

A failed readiness probe, non-zero child exit, timeout, or interruption makes
the run fail. Inspect operator-local child logs before the final cleanup only
when actively debugging; never paste secrets, DSNs, cookies, or authorization
headers into repository evidence.
