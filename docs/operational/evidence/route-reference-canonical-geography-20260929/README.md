# Route Reference canonical geography hardening — partial qualification

Date: 2026-09-29. LPAF v2.7, rigor C. Product:
`b0b22d4144d1fc78a02b8508d83b29aa5fdce558`.

## Qualified Product result

The Route Reference create flow now reads the shared Admin `Country` projection,
requires Country before a canonical location, persists CanonicalLocation and
optional same-tenant LogisticsPoint identity, rejects mismatched or country-only
keys, derives labels as display snapshots, localizes geography types, and excludes
Iranian `InternationalCity` records from new selection while preserving historical
reads. There is no schema change. `planned_distance_km`, immutable versions and
pins, and ETA_RULESET_V2 are unchanged.

Finding `HW_ADMIN_ROUTE_REFERENCE_001 — CANONICAL REFERENCE INTEGRATION GAP` and
all five subfindings are recorded in the Product authority record. The source
implementation is qualified:

- focused backend: 60 passed, then 50 passed after the UAT-only correction;
- focused frontend: 45 passed;
- exact-Product full backend: 1,633 passed, 124 environment-gated skipped;
- exact-Product full frontend: 99 files / 474 tests passed;
- PostgreSQL 18: fresh base-to-head migration PASS, 17/17 Phase 3 tests PASS,
  Public Tracking PASS, owned cluster stopped;
- real Chrome on exact Product: P310 Route Reference, P311 ETA, P312-P315,
  MT3, IPJ01, IPJ02/IPJ03, monitoring, commercial continuity and IPJ04 PASS;
- P301 Reference Catalog/Admin foundations also passed on the immediately prior
  candidate; the only subsequent delta was the IPJ04 UAT helper corrected and
  then proven by exact-Product IPJ04;
- TypeScript, build, lint (0 errors, 16 existing warnings), architecture,
  structure, backend determinism, diff and one-head checks PASS.

Alembic head is `20261013_structured_route_progress_eta`; head count is one.

## Preserved walkthrough runtime

The integrated Product bytes were started in the preserved local runtime without
resetting PostgreSQL. Backend health/readiness and frontend returned 200. Before
and after row counts and complete-row hashes were identical for Request, Quote,
Shipment, Cargo, RoutePlan, RouteLeg, ExecutionUnit, allocation, event, report
context, structured progress, Route Reference/version/pin, and ETA snapshot
tables. The significant counts remain: 1 Request, 2 Quotes, 1 Shipment, 1 Cargo,
1 plan/leg/execution unit, two current allocations, one event/report context,
zero structured progress, zero Route References, zero basis pins and zero
ETA_RULESET_V2 snapshots. Requested/planned Cargo are 100, actual is unknown;
PLANNED allocation is 100 and ACTUAL allocation is 95. Three older
ETA_RULESET_V1 snapshots remain byte-identical.

No Isfahan-to-Bandar Abbas Route Reference was created.

## Runtime catalog stop condition

The preserved database has only 12 active Country rows. A read-only plan against
the approved FWD-02 catalog (`sha256:b3e71f12f7c9cc8a9c5061a9df0ed67f085636bc84bd7120400694adab2d48ca`)
proved 249 source countries, 237 missing countries and 51 same-country unbound
legacy location-name conflicts. The existing governed reconciler correctly
refuses every write when such location identity conflicts exist. Apply was not
invoked; no Country or InternationalCity row was changed.

This is the mission's legacy-reconciliation stop condition. Bypassing the atomic
reconciler, adding rows with manual SQL, or assigning UN/LOCODE by name would
silently redefine the frozen geography contract.

## Exact Product decision required

Recommended decision: authorize a new governed `COUNTRY_ONLY` reconciliation
mode for this approved FWD-02 checksum. It may insert only the 237 missing exact
ISO alpha-2 Country identities, update/delete/reactivate nothing, leave every
InternationalCity untouched, record an audited plan/apply receipt, and keep the
51 unbound legacy InternationalCity records readable but unavailable for new
Route Reference selection until a separately reviewed mapping package exists.

Alternative: supply an adjudicated mapping package for all 51 conflicts and run
the existing all-or-nothing catalog apply. No heuristic mapping is acceptable.

Until one option is approved, the source implementation is qualified but the
preserved walkthrough cannot truthfully claim a complete canonical Country list.
Verdict: `PARTIAL PASS — LEGACY LOCATION RECONCILIATION DECISION REQUIRED`.

Production was not accessed or mutated. No deployment or release occurred.
Human Product Walkthrough remains `IN_PROGRESS`; Release Ready remains `NO`.
