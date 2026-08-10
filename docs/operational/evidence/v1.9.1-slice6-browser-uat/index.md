# Forwarder v1.9.1 Slice 6 browser UAT

## Controlled environment

- Source branch/base HEAD: `codex/pr-4a-dms-gate-repair` / `56e4686b6bec4977092f70041a819abcbe93d7dc`
- Environment: disposable loopback-only UAT; Production untouched
- PostgreSQL: 18, private cluster on `127.0.0.1:55439`
- Database: uniquely named `forwarder_phase1b_uat_<run-id>`; created and dropped by the harness
- Migration current/head: `20260819_v191_acceptance_corrections`
- Frontend/backend: `http://127.0.0.1:5181` / `http://127.0.0.1:57069`
- Runtime: Python 3.13, Node 24.11.0, Playwright 1.57.0, Chromium 1200 bundle
- Document storage: isolated runtime default; runtime directory removed after completion

## Retained successful run

- Harness report: `P1B-UAT-20260810184838083707.json`
- Browser assertions: `P1B-UAT-20260810184838083707-artifacts/slice6-browser-result.json`
- Material screenshot: `P1B-UAT-20260810184838083707-artifacts/slice6-mobile-390.png`

The run passed authenticated source visibility for direct-only, explicit quote-only,
legacy quote, both, neither, and admin personas. It passed direct creation through
Chromium, no fabricated request/quote lineage, detail rendering, work-queue navigation,
real-HTTP quote creation/replay/stale conversion conflict/changed-payload conflict,
normal/support identity projections, visible `Forwarder 1.9.1`, zero unexpected console
errors, and horizontal-overflow checks at 360, 390, 412, 768, and 1440 pixels.

## Remaining acceptance gaps

This evidence does not close the complete requested matrix. The following still require
real-browser certification: accepted-quote creation through the UI and request deep-link;
all six domestic/international/Iran location scenarios and ineligible/duplicate master
data; Persian RTL plus English LTR; keyboard/focus/label/error associations; direct and
quote MDPM/economics/FX/OIP/lifecycle continuity; and a safely simulated transient
transport failure. Classification: `BROWSER ACCEPTANCE BLOCKER REMAINS`.

## Cleanup

The successful harness report records Vite/backend termination, database drop, and
private PostgreSQL shutdown as PASS. Port 55439 was unreachable after completion.
