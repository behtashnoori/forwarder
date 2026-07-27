# Backend one-shot launch recovery

Date: 2026-07-26

All evidence is synthetic and sanitized. No password, token, cookie,
authorization header, DSN, customer data, or disposable identifier is present.

## Entry-point decision

| Candidate | Repository-supported | Inline code | UAT-compatible | Selected |
|---|---|---|---|---|
| `python -m backend.run` | Yes | No | No: writes `.backend-port` | No |
| `backend.wsgi:app` through Waitress | Yes | No | Yes: non-mutating readiness gate and loopback bind | Yes |
| Flask development CLI | Yes | No | Possible, but weaker than the versioned Waitress contract | No |
| Temporary launcher | Fallback | No | Not required | No |

The selected command used the mandated Python interpreter and the
repository-supported Waitress package to serve `backend.wsgi:app` on a
token-specific IPv4-loopback port. No `python -c`, inline Python, command
string evaluation, temporary launcher, source edit, or external `.env` was
used.

## Runtime results

- Fresh PostgreSQL 18.0/UTF8 cluster: PASS; loopback-only
- Official migration runner: `20260801_route_exception`; pending zero
- Official Phase 1B seed: PASS; exactly once
- Backend start attempts: 1
- Backend initialization: PASS
- Backend health: HTTP 200
- Backend listener: IPv4 loopback only
- Database target: current disposable PostgreSQL database
- SQLite/public PostgreSQL/persistent/production target use: zero
- Port 5001 use: zero
- `.backend-port`: unchanged at `57065`

## Remaining environment blocker

After backend readiness, three attempts to request a Windows-safe Vite process
launch were rejected by the execution policy before process creation. Vite
start attempts therefore remained zero. An in-process configuration override
was not substituted because it would not prove the required
`VITE_BACKEND_URL` `explicit_env` process contract. Chromium login/list/detail
was consequently not run.

The original backend inline-argument quoting defect is recovered, but this
targeted runtime gate cannot be marked PASS because its Vite and Chromium
requirements were not reached. This is an environment/tooling restriction,
not a product defect. Full Browser/Mobile UAT remains `NO`.

## Cleanup

- Browser tabs: finalized
- Backend process/listener: zero
- Vite process/listener: zero
- Disposable database: dropped
- Disposable PostgreSQL: stopped with direct `pg_ctl`
- Token process/listener/temp directory: zero
- Public PostgreSQL 5432 and production port 5001: untouched
- Tracked databases: untouched
- Persistent applied: `NO`
- Commit/stage/push: none

Result: `PHASE_1B_BACKEND_ONE_SHOT_LAUNCH_RECOVERY_ENVIRONMENT_BLOCKED`
