# Route Reference canonical location search — qualification evidence

Date: 2026-09-29

## Candidate and authority

- Product commit: `951ddac030654303b699b63223d89114323ff11f`
- Controlled branch: `integration/golden-controlled`
- Governing entry baseline: LPAF v2.6, Level B, Sol capability route
- Product authority: the Product Owner's supplied
  `FORWARDER — ROUTE REFERENCE CANONICAL LOCATION SEARCH BLOCKER`
- Scope: Organization Admin Route Reference endpoint search only

The task body also described LPAF v2.7. The repository-specific instruction
supplied above the task names the frozen v2.6 normative documents, so v2.6 was
applied and the mismatch was not used to expand scope or authority.

## Proven root cause and correction

The defect had two independent filters in the same picker flow:

1. the frontend required `Province.country_id` to equal Iran, but preserved
   domestic Province rows legitimately predate that relationship and carry
   `NULL`; therefore canonical Isfahan Province was removed before rendering;
2. the frontend requested only domestic city/port/customs projections and the
   Route Reference service rejected every Iranian `InternationalCity`, so the
   governed `IRBND` Bandar Abbas identity was never offered.

The correction is bounded to explicit Iran context. Nullable legacy Province
ancestry is accepted only when the caller supplies the active IR Country. The
Iran endpoint now returns only country-bound, active `InternationalCity` rows
with an `IR` UN/LOCODE. Unbound legacy rows stay excluded. The picker requests
that source type and exposes loading, empty, actionable error, and selected
states. Search text remains presentation-only; save resolution still produces
the existing `CanonicalLocation` foreign key.

## Canonical/runtime evidence

The preserved PostgreSQL 18 runtime contains:

| Name | CanonicalLocation | Source | Type | State |
| --- | --- | --- | --- | --- |
| اصفهان | internal `32`, public `425115cf-b686-4f8b-9f73-dd21b8f1764b` | `province:2` (`ISF`) | `province` | verified |
| بندرعباس | internal `33`, public `d75527cb-b8df-4ae5-83ca-2d204721ae83` | `international_city:59` (`IRBND`) | `city` | verified |

No geography row or Route Reference was created. Live API evidence returned
exactly `international_city:59` for Persian `بندرعباس`; the unbound legacy
InternationalCity search for `اصفهان` returned zero. The Province catalog
returned active `province:2`, and the live browser rendered:

- origin, Iran + `اصفهان`: `استان — اصفهان`;
- destination, Iran + `بندرعباس`: `بندر — بندرعباس`.

Both selectors remained on `انتخاب مکان معتبر`; the form was not submitted and
was left open for Product Owner selection.

Before runtime restart, a PostgreSQL custom-format backup was captured at
`D:\1-webapp\forwarder-human-walkthrough-runtime\pre-route-location-search-fix-20260929.dump`
(1,287,273 bytes, SHA-256
`82FF5A96C6C3862CC081944B319E95AD93809373B7D208C9594E4739931A4756`).
After restart, health/readiness/frontend were `200/200/200`; Alembic remained
`20261013_structured_route_progress_eta` with one head.

Read-only post-update assertions retained zero Route References, zero
structured-progress rows, and zero ETA v2 snapshots. Requested/planned/actual
Cargo remained `100/100/unknown`, PLANNED/ACTUAL allocation remained `100/95`,
one RoutePlan, one RouteLeg and one Execution remained, and the location report
remained `نزدیک مرز`.

## Qualification

- focused backend: `28 passed`;
- focused frontend: `9 passed`;
- affected Route/ETA/Admin/reference regressions: `33 passed, 1 skipped`;
- PostgreSQL 18 Route Reference upgrade/history/tenant/concurrency/rollback:
  `1 passed`;
- Alembic-version contract: `8 passed`;
- frontend full regression: `99 files, 477 tests passed`;
- frontend build: passed (existing chunk-size warning only);
- frontend lint: passed with 0 errors and 16 existing warnings;
- structure check: passed;
- architecture governance: passed;
- full backend regression: `1638 passed, 124 skipped`.

No migration was added. No Production access, mutation, deployment, or release
occurred. The Human Product Walkthrough remains `IN_PROGRESS`, and release
readiness remains `NO`.
