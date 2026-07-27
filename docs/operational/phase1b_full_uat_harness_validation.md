# Phase 1B full UAT harness validation

## Final status note (2026-07-27)

Targeted token `P1B-UAT-20260727044111047492` and full token `P1B-UAT-20260727044204801260` passed. Browser/Mobile UAT is `YES`; five viewports and 22/22 workflows passed; persistent applied is `NO`; production/public PostgreSQL was untouched. Earlier incomplete-run material below is historical.

Date: 2026-07-26

Classification: `AUTOMATED_EXECUTOR_CAPABILITY_LIMITATION`

## Scope and preflight

- Branch: `feature/forwarder-multileg-route-orchestration-phase1b`
- HEAD: `268d329060acd7f0516ddf90a2a0c54846d8e396`
- Repository secret scan: `findings=0`, redaction enabled
- Repository-local `.env`: zero
- `.backend-port`: unchanged at `57065`
- `git diff --check`: PASS
- Existing working tree: preserved
- Persistent applied: `NO`
- Real Full UAT: `NOT RUN IN THIS GATE`

The four tracked SQLite files were reviewed by filesystem metadata only. They
were not opened, queried, or modified:

| File | Size |
|---|---:|
| `forwarder_dev.db` | 32768 bytes |
| `backend/forwarder_dev.db` | 32768 bytes |
| `test_live.db` | 32768 bytes |
| `test_run.db` | 32768 bytes |

## Harness contract

`scripts/uat/phase1b_full_uat_runner.py` is the single operator entry point.
It uses only discrete `subprocess` argument lists with `shell=False`, supplies
limited child environments, enforces canonical disposable database naming and
loopback ports, starts Waitress using `backend.wsgi:app`, invokes the official
migration and seed CLIs, invokes Vite through Node directly, and delegates the
Chromium workflow to an explicit operator-owned browser runner.

Real execution is rejected unless both `--run` and `--confirm` are present.
`--validate-only` and `--dry-run` do not enter the execution function and
therefore cannot start long-running processes. JSON and Markdown reporting
redact secret variables, literal secret values, credential-bearing PostgreSQL
URLs, and common token/password forms.

Cleanup is in a `finally` boundary. Backend and Vite are terminated (then
killed after a bounded timeout), the disposable database is dropped, the
PostgreSQL cluster is stopped, and the token-scoped runtime directory is
removed for success, failure, timeout, and operator interruption.

## Gate validation

This gate is limited to:

- Python compile/static inspection
- focused Runner unit tests
- `--validate-only`
- `--dry-run`
- repository secret scan and diff checks

Observed result:

| Validation | Result |
|---|---|
| Python compile | PASS |
| Focused Runner unit tests | PASS (`9 passed`) |
| `--validate-only` | PASS; `processes_started=false` |
| `--dry-run` | PASS; `processes_started=false` |
| Sanitized report marker scan | PASS; `findings=0` |
| Gate-owned PostgreSQL/backend/Vite/browser processes after safe modes | zero |

It does not start PostgreSQL, Waitress, Vite, Chromium, or any persistent
application. Port 5001 and PostgreSQL 5432 remain untouched. No product,
frontend, API, migration, schema, seed, permission, package, Vite
configuration, `.backend-port`, or tracked SQLite file is changed.

Final real Browser/Mobile UAT remains an operator action under the companion
guide. This Gate validates the orchestration boundary; it does not claim a
Full UAT result.
