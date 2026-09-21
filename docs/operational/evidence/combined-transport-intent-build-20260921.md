# Combined Transport Request Intent — Governed Build Evidence

Date: 2026-09-21

Worktree: `D:\1-webapp\15-forwarder-golden-20260921`

Build branch: `codex/combined-transport-intent`

## A. LPAF Governance Gate

The Build used LPAF v2.2 as the normative baseline and applied the v2.3 Product Integration / `REFERENCE_IMPACT` gate as the Forwarder strong default. The mission, outcome, scope, owner, SOR, actors, tenant boundary, journey, state/data ownership, dependencies, module and public-contract boundaries, API/catalog/compatibility/authorization impacts, negative authorization, browser acceptance, and regression contract were identified before implementation.

```text
MISSION = IDENTIFIED
OUTCOME = IDENTIFIED
CAPABILITY_OWNER = IDENTIFIED
SYSTEM_OF_RECORD = IDENTIFIED
ACTOR_ROLE_ENTITLEMENT = IDENTIFIED
TENANT_DATA_SCOPE = IDENTIFIED
USER_JOURNEY = IDENTIFIED
STATE_DATA_OWNER = IDENTIFIED
UPSTREAM_DOWNSTREAM = IDENTIFIED
MODULE_BOUNDARY = IDENTIFIED
API_IMPACT = IDENTIFIED
SCHEMA_IMPACT = IDENTIFIED
CATALOG_IMPACT = IDENTIFIED
COMPATIBILITY_IMPACT = IDENTIFIED
AUTHORIZATION_IMPACT = IDENTIFIED
ACCEPTANCE_CONTRACT = IDENTIFIED
NEGATIVE_AUTH_CONTRACT = IDENTIFIED
BROWSER_CONTRACT = IDENTIFIED
REGRESSION_CONTRACT = IDENTIFIED

REFERENCE_IMPACT = NONE
```

## B. Starting State

- Canonical branch: `integration/golden-controlled`
- Required and observed starting SHA: `65557559d7562dec937afe23f03d81e4d57dbf7c`
- Expected remote: `github/integration/golden-controlled`
- Initial local/remote ahead-behind: `0/0`
- Initial worktree: clean
- Build branch created exactly from the canonical SHA: `codex/combined-transport-intent`
- Existing ancestry included Optional Multi-Cargo, Documents, Dual Calendar, and the post-D2/LPAF reconciliation.
- Existing repository Alembic head: `20260924_request_cargo_items`; head count: one.

## C. Existing Transport Architecture

The existing authoritative Request fact remains the scalar transport field selected by shipping scope on `ShipmentRequest`: `domestic_transport_method` for domestic Requests and `international_transport_method` for international Requests, with `transport_method` retained as the legacy compatibility field. `TransportMethod` remains the existing selector catalog. B3 presentation continues to project the Request scalar separately from ordered `RouteLeg.transport_mode` facts.

No second transport-intent model, ordered Request transport array, route builder, or alternate endpoint was introduced.

## D. Product Contract

`Combined Transport` means one Customer-authored Request-level preference. It does not state the number, order, or identity of operational legs. Actual execution remains an ordered Route Plan made from concrete Route Leg modes. Customer submission creates neither a Route Plan nor a modal permutation.

## E. Canonical Transport Value

- Canonical machine/catalog value: `Combined Transport`
- Persian label: `حمل ترکیبی`
- English label: `Combined Transport`
- Compatibility aliases added: none

The value is defined once in the bounded Request transport catalog contract and localized through the existing `transportLabel` seam. Customer and Expert surfaces do not expose a raw machine-only value.

## F. Schema / Catalog Decision

The existing nullable string fields safely store the new catalog value. No schema change or migration is required or authorized. The transport seed utility is now dry-run by default and applies only missing canonical rows with `--apply`; it never deletes historical rows. On the owned qualification database, initial apply inserted the seven missing canonical catalog rows and the second dry run reported `missing=[]`, `inserted=0`, and `historical_rows_deleted=0`.

The public catalog response is deterministic and de-duplicates same-name rows, including the historical duplicate Rail shape, without mutating stored history.

## G. Historical Compatibility

Historical Road, Rail, Sea, Air, and existing catalog spellings are still accepted/read unchanged. No Request row was rewritten or backfilled. Combined is not inferred from an operational route, and a historical non-Combined Request remains non-Combined even when its route later contains several concrete modes.

## H. Customer Journey

The existing Request selector exposes Combined as a normal option. The same form, validation, confirmation, submit endpoint, success state, Customer dashboard, and detail/reopen path are used. The confirmation now renders the selected localized scalar even when the form supplies the raw selected value rather than a separately populated display-name field.

No first/second mode, sequence, leg count, vehicle, container, or operational planning input was added.

## I. Expert Presentation

The existing Expert list and detail projections receive the persisted Request scalar and render `حمل ترکیبی` through the established B3 localization path. Browser qualification located each newly created Request by its unique tracking code, proved the label in its list card, opened the normal detail page, and proved the same label there.

## J. Request Intent vs Actual Route

Focused operational tests prove:

- Combined with no route remains Combined and requires no Route Plan.
- Combined with Road → Rail → Road remains Combined while the ordered route remains unchanged.
- Replacing an operational leg later does not mutate Request intent.
- A Road Request with a multimodal route remains Road and is not inferred as Combined.
- `Combined Transport` is rejected as a concrete Route Leg mode.

## K. Control Tower

Control Tower population, authorization, attention rules, pagination/windowing, 100-Shipment fail-closed ceiling, and Shipment Detail navigation were not changed. Its existing B3 projection continues to distinguish Request intent from actual route modes. Focused Control Tower regression and the full backend/frontend inventories passed.

## L. Authorization

No role, entitlement, tenant policy, owner, assignee, or cross-tenant read was added. Customer selection uses the existing public Request submission boundary. Customer/Expert/Admin reads remain parent-authorized through their existing contracts. Negative authorization coverage remained in the full suite; the disposable Expert browser identity received only the normal baseline `operational_shipment.read` membership needed by the existing detail page's background lookup.

## M. Cargo Regression

Combined and Cargo remain independent:

```text
REQUEST_CARGO_REQUIRED_FOR_SUBMISSION=NO
REQUEST_CARGO_MIN_ITEMS=0
MULTI_CARGO_REQUEST_ENABLED=YES
MANDATORY_CARGO_POLICY=DEFERRED
```

Service/API and browser journeys proved Combined with zero Cargo and Combined with two ordered Cargo Items. Both facts round-tripped independently.

## N. Quote Regression

No Quote model, API, lifecycle, currency, authorization, or UI file was changed. Existing Quote and EUR contracts remained green in the full regression inventory. `Needs discussion` / Simple Quote Communication was not implemented.

## O. Documents / Dual Calendar Regression

No Documents or temporal persistence behavior changed. Multi-file append, targeted replacement/history, known-failure Retry, unknown no-blind-Retry, owning-Expert management, and Gregorian (Jalali) presentation remain governed by their existing implementations and passed the full inventories. No date/time, timezone, `occurred_at`, or `recorded_at` contract was altered.

## P. Browser Evidence

Playwright exercised the real Vite application, real backend, and an owned PostgreSQL database with one Chromium worker:

- Journey A — Combined + zero Cargo: submit, exact create response, Customer reopen, explicit zero-Cargo state — PASS.
- Journey B — Combined + two Cargo Items: submit and reopen with exact intent, item order, and descriptions — PASS.
- Journey C — Expert list/detail: unique tracking-code cards and detail both display `حمل ترکیبی` — PASS.
- Journey D — responsive RTL: 390×844 detail, `dir=rtl`, visible Persian label, no API/page/request/console errors — PASS.

Result: `3 passed` in `30.8s`.

A separate app-browser visual inspection confirmed Combined is a normal domestic selector option and carries the governed explanation that the actual sequence is determined by the operational Route Plan.

## Q. Test Results

| Qualification | Final result |
|---|---|
| Focused Request/B3/operational/Cargo/Customer/Control Tower backend | `74 passed` |
| Full backend with explicitly isolated SQLite test database | `1,301 passed, 98 skipped, 1 xfailed` |
| Runtime migration-safety cohort under its intended environment | `22 passed` |
| Focused Quote/EUR/Documents/date regression | `68 passed` |
| Full frontend | `71 files / 351 tests passed` |
| Browser journeys | `3 passed` |
| Release/source/package/architecture cohort | `42 passed, 1 xfailed` |
| TypeScript | PASS, zero diagnostics |
| ESLint | PASS, zero errors; 13 existing warnings |
| Production frontend build | PASS, 2,547 modules transformed |
| Python compilation | PASS |
| Repository secret scan | PASS, `findings=0`, redaction enabled |
| Diff whitespace check | PASS |

Warnings are the repository's existing deprecation, stale Browserslist, Fast Refresh/hook, and large-bundle warnings; none is a new functional failure.

## R. Database Contract

An owned disposable PostgreSQL 18 cluster bound to loopback port `55439` and database `forwarder_combined_transport_qa` was used. It was not shared or Production.

```text
COMBINED_TRANSPORT_SCHEMA_CHANGE_REQUIRED=NO
MIGRATION_ADDED=NO
MIGRATION_MODIFIED=NO
ALEMBIC_HEAD_COUNT=1
DATABASE_HEAD=20260924_request_cargo_items
DATABASE_PENDING_MIGRATION=NO
```

Migration `current` and `check` both returned `current=20260924_request_cargo_items`, `heads=20260924_request_cargo_items`, `pending=no`. The catalog contained exactly one active `Combined Transport` row. Browser-created Requests persisted the exact scalar value.

## S. Reference Re-check

Immediately before Freeze, LPAF v2.2, the v2.3 Product Integration gate, PDR-019, FDD-001, FDM-001, the Canonical Business Object Catalog, architecture baseline, B3 evidence, and S6 Golden Business Journeys were re-read against the final runtime and tests.

The implementation still matches the approved scalar Request intent, existing catalog boundary, preserved historical values, and separately owned ordered Route Legs. Runtime, tests, and reference truth agree.

```text
REFERENCE_IMPACT_FINAL=NONE
```

## T. Scope Integrity

```text
COMBINED_TRANSPORT_REQUEST_INTENT_ENABLED=YES

COMBINED_TRANSPORT_IS_REQUEST_INTENT=YES
COMBINED_TRANSPORT_IS_ROUTE_LEG_MODE=NO

CUSTOMER_DEFINES_MODAL_SEQUENCE=NO

ACTUAL_ROUTE_REMAINS_ROUTE_LEGS=YES

REQUEST_TRANSPORT_INTENT_INFERRED_FROM_ROUTE=NO
ACTUAL_ROUTE_INFERRED_FROM_REQUEST_INTENT=NO

COMBINED_TRANSPORT_SCHEMA_CHANGE_REQUIRED=NO
MIGRATION_ADDED=NO
MIGRATION_MODIFIED=NO

CARGO_OPTIONALITY_CHANGED=NO
DOCUMENTS_BEHAVIOR_CHANGED=NO
DUAL_CALENDAR_BEHAVIOR_CHANGED=NO
QUOTE_LIFECYCLE_CHANGED=NO
CONTROL_TOWER_SEMANTICS_CHANGED=NO
NOTIFICATION_ACTIVATION_CHANGED=NO
EXPERT_OWNERSHIP_CHANGED=NO

PRODUCTION_ACCESSED=NO
PRODUCTION_CHANGED=NO
SECRETS_ACCESSED=NO
```

No Production, deployment, Notification activation, Quote Communication, Control Tower scaling, modularization, Route Plan, Route Leg, Execution Unit, allocation, tracking, geography, or logistics-point change occurred.

## U. Remaining Risks

- Existing lint, browser-data age, Python deprecation, and bundle-size warnings remain visible and independently governed.
- Catalog reconciliation must be run explicitly with `--apply` in each authorized environment; this stage does not deploy or mutate any shared environment.
- Control Tower scale beyond its existing fail-closed ceiling remains a separately governed future stage.

No remaining risk blocks this bounded capability.

## V. Verdict

PASS — COMBINED TRANSPORT INTENT COMPLETE
