# Forwarder v1.9.1 Slice 6.1 browser acceptance closure

## Result

`BROWSER ACCEPTANCE BLOCKER REMAINS`

The retained run `P1B-UAT-20260810185354100526` reproduced the controlled
non-Production topology at authoritative HEAD
`ea9d9154807f800c264b848fc9a570baf7d36231`. PostgreSQL 18, the disposable
database, backend on loopback port 57079, frontend on loopback port 5191, and
Chromium/Playwright all started successfully. Migration and seed completed,
the existing Slice 6 browser runner passed, and the harness stopped both
applications, dropped the database, and stopped the private PostgreSQL
cluster.

## Certified by this run

- Source visibility for the direct-only, quote-only, legacy-quote, combined,
  no-create, and admin personas.
- Direct creation through Chromium and direct detail/work-queue continuity.
- Accepted-quote create/replay, stale conversion conflict, and changed-payload
  conflict over real HTTP (not creation through the browser form).
- Normal/support release-identity projections and visible `Forwarder 1.9.1`.
- Horizontal-overflow checks at 360, 390, 412, 768, and 1440 pixels.
- Zero unexpected browser console errors in the exercised paths.

## Mandatory items not certified

- Accepted-quote creation by completing and submitting the real browser form.
- Request Detail deep-link, refresh, stale-link, and history behavior.
- The full six-scenario browser location matrix, including real Iran city,
  port, and customs/border round trips and ancestry-negative cases.
- Full Persian RTL and English LTR creation flows at every required viewport.
- Keyboard traversal, focus return, and programmatic required/error semantics.
- Direct and quote Documents/MDPM, economics, FX, OIP, lifecycle, and work-queue
  continuity as a complete browser matrix.
- A browser submission with a real post-submit transport interruption and
  recovery using the unchanged idempotency key.
- The concurrent quote conflict initiated from a stale browser selection.
- Automated browser regression for all release-identity failure states.

These are acceptance-evidence gaps, not evidence of a backend contract or
architecture defect. Slice 7 remains NO-GO.

## Defects observed

1. `TEST/HARNESS DEFECT`: the full-UAT orchestrator was pinned to pre-Slice-6
   HEAD `56e4686`; corrected to the authoritative HEAD.
2. `TEST/HARNESS DEFECT`: the release-publication regression retained `1.9.0`
   identity assertions after the governed version sources moved to `1.9.1`;
   corrected in the test only.
3. `PRESENTATION DEFECT` (not fixed in this closure): canonical selectors and
   schedule inputs on New Operation are not consistently marked as required,
   and the creation page remains English-labelled when the application is in
   Persian RTL. These block the requested accessibility/localization matrix.

## Reports and cleanup

- Passing controlled run: `P1B-UAT-20260810185354100526.json` and `.md`.
- Browser assertions and screenshot: the matching `-artifacts` directory.
- The earlier `P1B-UAT-20260810185333778278` report is retained as evidence of
  the safe preflight rejection that exposed the stale HEAD pin; no process was
  started by that run.
- Production credentials, data, services, ports, deployment, packaging, tags,
  and pushes were not accessed or changed.
