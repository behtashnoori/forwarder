# Release 1.7.0 Final RC Review

- **Review date:** 2026-08-03
- **Release:** 1.7.0 — Logistics Network Foundation
- **Decision:** **RELEASE 1.7.0 RC APPROVED FOR COMMIT**
- **Production baseline:** unchanged; no Production access, migration, Seed, deployment, packaging, tag, or push

## Authenticated UAT environment

UAT ran against candidate HEAD `bc46e3c` plus the bounded RC worktree on a uniquely named, loopback-only disposable PostgreSQL 18 database. The database was freshly migrated to the single head `20260810_logistics_network`; backend health returned HTTP 200 with `database=connected`; Vite served package version 1.7.0. The repository's supported `manage.py create-admin` path was verified; the disposable graph was created through the existing Logistics Network test-fixture model pattern and current bcrypt hash service so the organization memberships and representative graph were committed atomically to the disposable target. Credentials were generated locally, never written to tracked files or evidence, and deleted with the database after UAT.

The fixture contained two organizations, three users (Organization-A admin and expert; Organization-B outsider), two Projects, four initial active point types, five Organization-A points including one inactive point, five Organization-A associations including one inactive association, and foreign Organization-B Project/point data. Browser actions added one disposable type, two confirmed distinct points, and one Project association. Final introspection showed zero RoutePlan, OperationalCheckpoint, or OperationalEvent rows.

## Browser results

Authenticated Chromium exercised Admin Point Types, Admin Logistics Points, and the authorized Project Logistics Network. Type and point create/update/lifecycle operations passed; immutable codes were disabled in edit dialogs. Governed type/Country and optional Province/City fields were clear. Search passed. Exact duplicate creation returned an understandable rejection; probable duplicate creation exposed an explicit `Confirm distinct point` action and succeeded only after confirmation. Inactive master points were absent from Project selection.

Project selection, bounded role, positive sequence, optional label/notes, creation, lifecycle, and reactivation passed. No free-text master-point creation was present. Mixed-state reorder moved the first active row below the second, renumbered active rows 1–5, and preserved the inactive association separately. Canonical names remained visible.

| Viewport / language | Viewport | scrollWidth | clientWidth | Overflow | Console errors | Authentication | Workflow |
| --- | ---: | ---: | ---: | --- | ---: | --- | --- |
| Desktop Persian RTL | 1440×900 | 1434 | 1434 | No | 0 | Admin | Types, points, duplicates, Project network, reorder |
| Mobile Persian RTL | 390×844 | 385 | 385 | No | 0 | Admin | Project network and mixed-state result |
| Mobile Persian RTL | 412×915 | 406 | 406 | No | 0 | Admin | Admin points representative screen |
| Desktop English LTR | 1440×900 | 1440 | 1440 | No | 0 | Authenticated session | Supported bilingual representative shell |

All primary controls used visible or programmatic accessible names. Native selects, labeled inputs, buttons, dialogs, disabled immutable-code fields, and keyboard-focusable controls were present. No blocking accessibility observation was found.

Security observations passed: the Organization-A admin did not see the foreign point; direct navigation to the foreign Project produced only `Project not found`; the Organization-B non-admin was redirected from `/admin` to `/expert`. Focused API regression separately confirms non-disclosing 404 behavior for foreign point and association detail/mutations.

## Automated reconfirmation

| Gate | Result |
| --- | --- |
| Focused backend | 5 passed |
| Full backend | 546 passed, 20 skipped |
| Focused frontend | 3 passed |
| Full frontend | 18 files / 96 tests passed |
| ESLint | 0 errors; 12 existing warnings |
| Production build | Pass; existing size/browser-data warnings only |
| TypeScript | Pass; zero diagnostics |
| OpenAPI | Parsed; 18 operations; documented/runtime paths equal 12/12 |
| Migration | `20260810_logistics_network`; single head; pending=no |
| `git diff --check` | Pass (line-ending notices only) |
| Current-tree secret scan | Pass; findings=0 |

## Cleanup and decision

The browser session was closed, the UAT backend/frontend were stopped, the disposable PostgreSQL database was dropped, and temporary credential/runtime files were deleted. Five obsolete authentication-blocker screenshots were removed from the untracked evidence directory and replaced by authenticated evidence. Production remained unchanged.

Outcome **A. RELEASE 1.7.0 RC APPROVED FOR COMMIT**. Stage only the bounded source, tests, ADR/RC documents, and sanitized browser evidence; commit with `fix(logistics-network): close release 1.7.0 rc gaps`. Do not push, tag, package, deploy, migrate Production, or apply Production Seed.
