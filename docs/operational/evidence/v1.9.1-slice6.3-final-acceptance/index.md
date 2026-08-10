# Forwarder v1.9.1 Slice 6.3 final acceptance

## Classification

`SLICE 6.3 CLOSED — GO FOR SLICE 7`

Final controlled run: `P1B-UAT-20260810201934797790` at accepted base HEAD
`4868c7be50f3e1c0108dd73caa33e3e9d81cad32` plus the changes recorded by this closure.

## Mandatory Chromium matrix

| Scenario | Result |
|---|---|
| Deep-link normal navigation | PASS |
| Deep-link refresh | PASS |
| Deep-link back/forward history | PASS |
| Deep-link invalid identity | PASS |
| Deep-link stale/deleted target | PASS |
| Non-Iran origin | PASS |
| Iran origin | PASS |
| Non-Iran destination | PASS |
| Iran destination | PASS |
| Iran destination city | PASS |
| Iran destination port | PASS |
| Iran destination customs | PASS |
| Duplicate-location disambiguation | PASS |
| Non-Iran international scenario | PASS |
| Persian RTL operations closure | PASS |
| Keyboard traversal | PASS |
| Keyboard interaction | PASS |
| Direct economics | PASS |
| Direct FX | PASS |
| Direct OIP | PASS |
| Accepted-quote Documents / MDPM | PASS |
| Accepted-quote economics | PASS |
| Accepted-quote FX | PASS |
| Accepted-quote OIP | PASS |
| Browser dropped-request recovery | PASS |
| Idempotent retry without duplicate business operation | PASS |
| Stale quote two independent actors | PASS |
| Release identity MATCH | PASS |
| Release identity MISMATCH | PASS |
| Release identity BACKEND_UNAVAILABLE | PASS |
| Release identity IDENTITY_UNAVAILABLE | PASS |

The retained `slice6-browser-result.json` contains the individual assertions,
canonical location payloads, actor conflict proof, transient recovery proof,
Chromium/Playwright identities, viewport checks, and zero unexpected console errors.
Direct and quote OIP independently rendered the governed `STALE` state with
`SOURCE_AHEAD_OF_PROJECTION`, the expected truthful state after creating new
authoritative shipment facts without fabricating a projection reconciliation.

## Automated validation

| Check | Result |
|---|---|
| Final disposable PostgreSQL 18 migration/seed/backend/Vite/Chromium run | PASS |
| Alembic sole head `20260819_v191_acceptance_corrections` | PASS |
| Relevant backend tests (28) | PASS |
| Frontend tests (125) | PASS |
| TypeScript | PASS |
| ESLint | PASS (12 pre-existing warnings, 0 errors) |
| Ruff for touched Python harness files | PASS |
| Python compile | PASS |
| Production build | PASS |
| `git diff --check` | PASS |

## Isolation and cleanup

- Final PostgreSQL/backend/frontend ports: `55501` / `57141` / `5245`, loopback only.
- The harness stopped Chromium, backend, and Vite; dropped its disposable database;
  and stopped its private PostgreSQL cluster.
- Production was not accessed or changed. No deployment, tag, package, publish,
  push, or production operation occurred.
