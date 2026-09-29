# Structured route progress and ETA foundation — qualification evidence

Verdict: `PASS — STRUCTURED ROUTE PROGRESS AND ETA FOUNDATION QUALIFIED`

Qualification date: 2026-09-29

Canonical entry SHA: `95af46867c2900c9e832018e3e53ee8bb5d862ab`

Product SHA: `f8f65e5b8dd83095e111b8b0448295adce075068`

LPAF baseline: v2.7, rigor C
Product review: PASS — no blocking authority, correctness, privacy, migration,
or journey finding remained after review.

## Contract proved

| Field | Qualified value |
| --- | --- |
| ROUTE_BASELINE_MODEL | Optional positive Decimal `planned_distance_km` on immutable `OrganizationRouteTimeVersion`; exact version pinned by `RouteLegTimeBasis`. |
| ROUTE_PROGRESS_MODEL | One append-only `DISTANCE_REMAINING_KM` fact, one-to-one with a P3-07 reported event. |
| HUMAN_LOCATION_ROLE | Supplemental description only; never parsed, converted, or used as quantitative ETA progress. |
| ETA_INPUT_CONTRACT | Exact active RoutePlan/RouteLeg/RouteStageExecution/ExecutionUnit, matching selected basis and whole-Cargo ACTUAL allocation participation. |
| ETA_CALCULATION_CONTRACT | ETA_RULESET_V2; Decimal remaining/planned fraction; active-leg movement only; ceil each bound to seconds; later movement/stops remain whole. |
| ROUTE_REVISION_BINDING | Progress and ETA evidence pin the exact active plan revision, leg and selected reference version; later versions and replans do not rewrite history. |
| EXECUTION_BINDING | Composite database constraints bind the progress event to the same report context, Shipment, stage and execution unit. |
| CARGO_BINDING | Existing exact whole-unit ACTUAL allocation proof remains mandatory and fails closed on split or ambiguous participation. |
| CUSTOMER_VISIBILITY_BOUNDARY | Customer receives only safe calculated ETA and labels; no exact progress, planned distance, free text, internal identifiers or provenance is exposed. |
| MIGRATION_REQUIRED | YES — one additive migration; no row creation or historical backfill. Populated downgrade refuses evidence loss. |

Missing progress remains distinct from missing route baseline:
`PROGRESS_UNDEFINED` does not become `ROUTE_BASELINE_UNDEFINED`, and free-text-only
reports never qualify ETA. Existing ETA v1 snapshots remain immutable; new
materializations use v2.

## Exact Product SHA qualification

| Layer | Result |
| --- | --- |
| Focused route/progress/ETA/migration/ownership tests | PASS — 74 passed, 1 expected PostgreSQL-only skip |
| PostgreSQL 18 base-to-head migration chain | PASS — current/head `20261013_structured_route_progress_eta`, pending=no |
| Phase 3 PostgreSQL 18 suite | PASS — 17 passed |
| Public Tracking PostgreSQL regression | PASS — 1 passed |
| Full backend | PASS — 1,632 passed, 124 skipped |
| Frontend unit/component tests | PASS — 99 files, 473 tests |
| Production build | PASS |
| Lint | PASS — 0 errors, 16 existing warnings |
| Architecture governance | PASS |
| P3-11 Chrome | PASS — 4 tests, including structured progress entry and ETA v2 |
| Consolidated Chrome journeys | PASS — P3-01 through P3-15, MT3, IPJ01, IPJ02/IPJ03 continuations, HW-COMMERCIAL and IPJ04 |

The consolidated qualification used disposable, loopback-only PostgreSQL 18
databases and local Chrome runtimes. Source was clean and fixed at the Product
SHA throughout. Raw execution logs are retained outside the repository at
`D:\\1-webapp\\forwarder-dev\\structured-route-progress-final-f8f65e5`.

## Safety and completion state

- `ALEMBIC_HEAD=20261013_structured_route_progress_eta`
- `ALEMBIC_HEAD_COUNT=1`
- `PRODUCTION_ACCESSED=NO`
- `PRODUCTION_MUTATED=NO`
- `DEPLOYMENT_PERFORMED=NO`
- `RELEASE_CREATED=NO`
- `HUMAN_PRODUCT_WALKTHROUGH=IN_PROGRESS`
- `RELEASE_READY=NO`

The automated Human Walkthrough regression passed, but it does not replace or
close the Product Owner's preserved human walkthrough.
