# Release 1.7.0 Publication Review

- Release: 1.7.0 — Logistics Network Foundation
- Previous release: 1.6.1
- Change type: MINOR
- Deployment type: backend-frontend-migration
- Migration: `20260809_cargo_catalog_items` → `20260810_logistics_network`
- Rollback application: `release-v1.6.1-20260802`
- Production deployment: not performed
- Production Seed: not executed; separate authorization required

Independent review covered commits `2e5e126`, `6866ab0`, `bc46e3c`, and
`93deda8`. The cumulative release contains the DA-1.0 documentation baseline,
governed LogisticsPointType/LogisticsPoint/ProjectLogisticsPoint foundation,
tenant isolation, immutable codes, duplicate handling, active/inactive
lifecycle, bounded roles and ordering, OpenAPI completion, IDOR tests,
responsive acceptance tests, mixed-state reorder correction, and authenticated
UAT evidence. It introduces no GIS/map/coordinates, public point search,
allocation, route optimization, reporting engine, automatic operational graph,
inventory relationship, split/merge, generic EAV, or generic workflow engine.

Final gates: backend 546 passed/20 skipped; frontend 96 passed; TypeScript and
compileall clean; ESLint zero errors/12 existing warnings; Ruff clean for the
seven Logistics Network Python files; production build passed with only stale
Browserslist and large-chunk warnings; OpenAPI parsed to 18 operations with
12/12 runtime path parity; one Alembic head; changed-document links valid;
current-tree secret scan zero findings; `git diff --check` passed.

Disposable PostgreSQL 18 passed fresh head, previous-head upgrade,
head-to-parent-to-head, required table/index/unique/composite-FK inspection,
partial active-sequence uniqueness, zero automatic LogisticsPointType rows,
and cleanup. Production was not contacted.

Known limitation: version 1.7.0 is embedded in the frontend bundle through
`VITE_APP_VERSION` but is not visibly rendered. This publication does not add a
version API or UI redesign.
