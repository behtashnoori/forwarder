# Phase 1B Vite backend target precedence remediation

## Final verification (2026-07-27)

P1B-UAT-004 is `CLOSED_VERIFIED` by the final full UAT. Browser/Mobile UAT is `YES`; `.backend-port` remains `57065`; persistent applied is `NO`. Earlier pending status below is historical.

## Runtime closure gate (2026-07-26)

P1B-UAT-004 is `FIXED_PENDING_FULL_UAT`. The resolver verification remains
8/8 passed, the frontend suite remains 30/30 passed, and the production build
remains PASS. The closure run added an ESLint PASS with zero errors and the
existing 11-warning baseline; no warning concerned the resolver.

A fresh PostgreSQL 18/UTF8 environment was migrated to
`20260801_route_exception` with pending zero and received the official Phase
1B seed. Backend and Vite each had exactly one start attempt. Before Vite was
created, `VITE_BACKEND_URL` selected the current token backend as an explicit
origin. `.backend-port` remained unchanged at 57065 and port 5001 was unused.

A fresh non-persistent Chromium context at 1280 x 720 passed login, operational
shipment list, shipment detail, active route-plan display, refresh, and logout.
Browser API calls were same-origin `/api` requests and returned data that existed
only in the current token database. Requests to 57065, 5001, production, and
cross-origin API origins were zero. Unexpected 5xx, CORS failures, fatal console
errors, unhandled promises, blank pages, auth loops, and credential exposure
were zero. Only non-fatal React Router future-flag warnings were observed.

Cleanup closed Chromium and removed every current-token Vite, backend,
PostgreSQL process, listener, database artifact, role artifact, and temporary
directory. `PHASE1B_VITE_PRECEDENCE_CURRENT_TOKEN_RESOURCES_REMAINING=0`.
Browser/Mobile UAT remains `NO` and persistent applied remains `NO`.

Result: `PHASE_1B_VITE_BACKEND_TARGET_PRECEDENCE_RUNTIME_CLOSURE_PASS_WITH_NOTES`.
The note is limited to non-fatal React Router warnings and full UAT/persistent
application remaining pending.

## Backend one-shot launch recovery probe (2026-07-26)

The repository-supported Waitress contract successfully served
`backend.wsgi:app` without inline Python. A fresh PostgreSQL 18/UTF8 database
reached `20260801_route_exception`, was seeded exactly once, and the backend
started exactly once on IPv4 loopback. Initialization completed and
`/api/health` returned HTTP 200. `.backend-port` remained `57065`; SQLite,
public/persistent PostgreSQL, production, and port 5001 were unused.

The environment rejected each requested Vite process launch before process
creation. Vite start attempts remained zero, so `explicit_env` and the narrow
Chromium login/list/detail probe were not claimed. Cleanup completed with zero
current-token resources. Result:
`PHASE_1B_BACKEND_ONE_SHOT_LAUNCH_RECOVERY_ENVIRONMENT_BLOCKED`.
