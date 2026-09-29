# Governed Cargo Continuity Repair — Qualification Evidence

## Identity and verdict

- LPAF baseline: `2.7`
- Product SHA: `101872b3c297d9ac3ab3310b6790504324ef9435`
- Schema/head: `20261012_phase3_cargo_eta` / one head
- Automated capability verdict: `PASS`
- Walkthrough verdict: `REFUSED_UNCHANGED`
- Final mission verdict: `PARTIAL PASS — REPAIR CAPABILITY QUALIFIED — EXISTING RECORD REMAINS UNCHANGED`
- External evidence root: `D:\1-webapp\forwarder-dev\cargo-continuity-repair-final-product-101872b`

## Capability qualification

- Focused repair suite: `30 passed`.
- PostgreSQL 18 migrated-head concurrency/CLI suite: `1 passed`; concurrent results were one `CHANGED` and one `UNCHANGED` with singleton mapping/audit/outbox/idempotency records.
- Full backend regression: `1607 passed, 123 skipped`.
- Full frontend regression: `99 files / 472 tests passed`.
- Python compile, TypeScript, ESLint (zero errors), production build, OpenAPI parse, architecture governance, structure, backend determinism, secret scan and diff checks: `PASS`.
- No migration was added; migration head remained unchanged.
- Independent final implementation review found no remaining code, ORM, locking, replay, CLI or PostgreSQL-test blocker.

The exact Product SHA passed the final owned qualification runner. Its
`result.json` records PASS for the PostgreSQL 18 base-to-head chain, Phase 3
PostgreSQL matrix, Public Tracking, P301–P314, MT3, P315-CORE,
HW-COMMERCIAL, IPJ01, IPJ02/IPJ03 (including Phase 2 and monitoring), and
IPJ04. The receipt records `production_accessed=false`,
`production_mutated=false`, `deployment_performed=false` and
`release_created=false`.

## Controlled integration

Product SHA `101872b3c297d9ac3ab3310b6790504324ef9435` was fast-forwarded to
`integration/golden-controlled`, pushed to `github`, fetched, and verified at
`ahead/behind=0/0` before the walkthrough runtime update.

## Preserved walkthrough PLAN

The existing PostgreSQL 18 runtime was restarted on the integrated Product SHA
with the same database. Backend health/readiness and frontend returned HTTP
200. The governed read-only PLAN was invoked for Shipment
`c66be7ef-ee20-4d39-a985-a3db5bd611db` with the exact reviewed Cargo,
source-Cargo, RoutePlan and terminal-leg bindings.

PLAN refused before domain eligibility with
`MAINTENANCE_AUTHORITY_REQUIRED`: the preserved `walkthrough_admin` is an
`ORGANIZATION_ADMIN`, while this bounded command requires an active
`PLATFORM_ADMIN`. No authority was changed. Independently, the mission-provided
Request tracking code uses digit `0`, while the stored linked Request uses
letter `O` in two positions. That mismatch was not normalized.

Read-only ORM verification after PLAN showed one Request, two Quotes, one
Shipment, one Cargo, the same active RoutePlan revision 1 and RouteLeg, one
existing RouteStageExecution/ExecutionUnit, zero allocation, zero
RouteCargoDestination and zero repair audit. Cargo lineage and requested
quantity remain NULL. APPLY was not invoked.

Consequently the existing database/history and Execution are preserved, but
Allocation UI discovery and removal of the walkthrough-specific false ETA
route-incomplete reason are not claimed. Human Product Walkthrough remains
`IN_PROGRESS`; Release Ready remains `NO`.

## Exact next step

The Product Owner must resolve both preconditions without guessing: confirm or
correct the exact `O/0` Request identity and designate an already-governed active
`PLATFORM_ADMIN` maintenance actor for this preserved tenant. Then rerun PLAN.
Only an all-PASS plan may be applied; after that, verify Allocation UI read-only,
re-evaluate ETA read-only, and let the Product Owner manually test planned 100
then actual 95 allocation.
