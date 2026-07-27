# Phase 1B shipment-list deduplication remediation

## Final verification (2026-07-27)

P1B-UAT-001 is `CLOSED_VERIFIED` by the final full UAT. Browser/Mobile UAT is `YES`; persistent applied is `NO`. Earlier pending status below is historical.

Status: `PHASE_1B_SHIPMENT_LIST_DEDUPLICATION_REMEDIATION_PASS_WITH_NOTES`

Defect `P1B-UAT-001` was reproduced with one shipment, one active plan, three
route legs, and `per_page=1`: the list incorrectly reported `has_more=true`.
The backend query now selects distinct shipment rows before ordering and
pagination. Route-leg filters, active-plan selection, organization scope, and
permission enforcement remain in the SQL query.

## Verification

- Fresh disposable PostgreSQL 18/UTF8 migration: head
  `20260801_route_exception`, pending migrations zero.
- Official Phase 1B seed: 2 organizations, 8 users, 2 shipments, 2 plans,
  6 legs, 12 checkpoints, 12 dependencies, 36 milestones, and 2 work items.
- Direct PostgreSQL deduplication test: `1 passed`.
- Full backend: `393 passed, 13 skipped` (the added direct PostgreSQL test is
  skipped when its explicit disposable URL is absent).
- Frontend: `21 passed`.
- ESLint: 0 errors, 11 existing warnings.
- Build: PASS.
- Chromium 1440 x 900 and 390 x 844: one shipment link/card, correct disabled
  next page, no overflow, no off-viewport buttons, no duplicate-key warning,
  fatal console error, or backend 5xx.
- Note: existing React Router future-flag warnings remain non-fatal.

No migration, schema, seed, frontend product code, configuration, package,
persistent database, commit, push, or stage operation was performed.
Browser/Mobile UAT remains `NO`; persistent applied remains `NO`.

`TRACKED_DATABASE_ARTIFACT_REVIEW_DEFERRED_TO_PHASE1B_FINAL_REVIEW`
