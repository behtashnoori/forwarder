# Dashboard local UAT report

**Date:** 2026-09-07  
**Scope:** local-only investigation and UAT evidence. No application source, routes, UI, backend, migration, environment, database, commit, push, or deployment was changed.

## PRECHECK

| Item | Evidence |
| --- | --- |
| Repository | `C:\frdiag\shipment-summary-presentation-polish` |
| Branch | `feature/shipment-summary-presentation-polish` |
| HEAD at start | `fef9bf5` (`fix(release): avoid duplicate fixture companion entries`) |
| Frozen application RC reference | `e5a54ac7808763e72da0242032b5019ac442746e` |
| Worktree at start | No tracked changes. One pre-existing untracked release-candidate directory: `release-candidates/UAT-Shipment-Summary-RC1-4c96ea4/`. It was not changed. |
| Frontend startup command | `npm run dev` (Vite, configured port `8080`) |
| Backend startup command | `npm run backend` (configured port `5001`) |
| Health endpoint | `http://localhost:5001/api/health` |
| Browser/E2E tooling | No Playwright, Chromium test configuration, or E2E test files found. The repository has Vitest component/route tests. |
| UAT user source | A synthetic Personal Analytics UAT seeder exists, but this local checkout has no `.env`, `backend/.env`, `DATABASE_URL`, or documented local credentials. It was not configured or seeded. |

## Startup and live-browser result

- `http://127.0.0.1:8080/` returned HTTP 200, but the listener is an `httpd` process rather than a verified Vite application process; it was therefore not accepted as proof of the repository UI being live.
- `http://127.0.0.1:5001/api/health` was refused: no backend listener was running.
- The canonical backend launcher reports that `DATABASE_URL` is required. Creating configuration, choosing a database, or loading UAT fixtures would exceed the local-only, no-change scope.
- Consequently, authenticated Chromium/Playwright interaction, normal-navigation clicks, dashboard creation, and real saved-view snapshotting are **NOT EXECUTED**, not passed.

## Product-surface and navigation findings

### What a normal operational user can discover

`OperationsNav` exposes these operational links after permissions load:

1. Shipments: `/operations/shipments`
2. Operations Control Tower: `/operations/control-tower`
3. Control-Tower work queue: `/operations/work-queue`

The Control Tower runtime has an **"ایجاد نسخه شخصی" (Create personal copy)** action. Its successful path navigates to `/dashboards/:public_id`, so a user can create and immediately open a personal dashboard from that one entry point.

### What is missing

- There is no `/dashboards` collection/index route.
- There is no navigation item to list, reopen, or manage existing personal dashboards.
- The only persisted-dashboard routes are `/dashboards/:public_id` and `/dashboards/:public_id/edit`; both require an already-known `public_id`.
- The global public header contains only marketing links and login; it does not surface a Dashboard entry.

This is a material discoverability/re-entry failure: after leaving a personal dashboard, an ordinary user has no normal in-product route to find it again. The route, API, builder, and persistence code exist, but the capability is not integrated as a complete navigable product surface.

## Saved Views and dashboard snapshot findings

- `SavedViewControls` is embedded on the normal Shipments page, so Saved Views are discoverable from `/operations/shipments`.
- The control supports save, apply, update, archive, and—only for a selected compatible Saved View—selecting a personal dashboard then using **"افزودن به داشبورد" (Add to dashboard)**.
- The dashboard selector is populated by the personal-dashboard list API. When no dashboard exists it explicitly displays that no personal dashboard is available to select.
- The source wiring preserves the expected dashboard version and passes the selected Saved View title as the widget title to the snapshot endpoint.
- Live execution was blocked by the unavailable backend and authentication/database configuration, so no real snapshot persistence or post-refresh verification can be claimed.

## Automated verification

| Area | Command class | Result |
| --- | --- | --- |
| Backend dashboard persistence, snapshot, analytics authorization, saved-view alignment, project/shipment propagation | focused pytest | **14 passed** |
| Frontend dashboard builder, persisted-dashboard route, Control Tower, widgets, Saved View controls and adapter | focused Vitest | **20 passed** across 6 files |

The frontend run emitted chart-size warnings from the zero-dimension DOM test environment. All tests passed; the warnings do not establish live-browser chart usability.

## Defects and blockers

1. **P0 product-surface defect — personal dashboards have no index/list/re-entry navigation.** Existing personal dashboards are addressable only by a private `public_id` URL. This blocks normal discoverability and routine return to the product surface.
2. **Local UAT environment blocker — backend cannot start.** `DATABASE_URL` and local credentials are absent, and the configured health endpoint is not listening. This prevented authenticated browser UAT; it was not repaired because doing so would alter local configuration/data.
3. **Evidence limitation — no browser automation framework is configured.** The repository’s frontend evidence is component/route testing rather than a real browser journey.

## Required verdict

`DASHBOARD_PRODUCT_SURFACE = FAIL`

**Root cause:** UX / navigation integration incomplete. The governed dashboard implementation is present and tested, and creation is reachable through Operations Control Tower, but users cannot normally discover or reopen existing personal dashboards. The missing local backend configuration independently blocks live UAT and must not be confused with a passing browser result.
