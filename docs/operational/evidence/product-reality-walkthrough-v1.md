# Product Reality Walkthrough v1

**Environment:** disposable loopback-only UAT database, seeded Shared Transport qualification graph.  No Production access was used.

## Actor contract

| Actor | Capabilities / data scope | Landing | Product surfaces observed |
| --- | --- | --- | --- |
| ORGANIZATION_ADMIN | Tenant-scoped administration and the seeded operational graph | `/admin` | Admin, shipments, Control Tower, execution units |
| EXPERT (restricted) | Explicit ProjectAccess to Project A only; no Project B access | `/expert` | Expert console, direct authorized Project A execution-unit journey |
| PLATFORM_ADMIN | Not exercised: this fixture provides no independent product journey or tenant operational-data entitlement for this actor | n/a | n/a |

`PRODUCT_REALITY_ACTORS = PASS`  
`ACTOR_CONTRACT = PASS`

## Journeys and navigation observed

| Actor | Journey / surface | Result |
| --- | --- | --- |
| Organization Admin | Login → Admin | PASS; canonical admin landing was reached. |
| Organization Admin | Shipments | FAIL; the populated fixture displayed the empty state. |
| Organization Admin | Control Tower | BLOCKED; the business view rendered, but exposed technical coverage formulas and a raw warning enum. |
| Organization Admin | Work Queue | FAIL; visible navigation led to a technical authorization error. |
| Restricted Expert | Login → Expert console | PASS; expected Expert landing and legitimate empty request state. |
| Restricted Expert | Project A → Execution Units → Shared Transport | PASS for authorized access; Project A unit and eligible Project A cargo were visible. |
| Restricted Expert | Operations navigation | FAIL before correction; Control Tower and Work Queue were offered without their corresponding capabilities. |
| Restricted Expert | Project B data | PASS; no Project B data was displayed during the authorized Project A flow. |

`OPERATIONAL_STORY_CONTINUITY = BLOCKED` because the principal shipment list hides the populated operational lineage, preventing natural Request → Project → Shipment continuity.

## Defects

| ID | Severity | Class | Expected / actual | Disposition |
| --- | --- | --- | --- | --- |
| PR-001 | P1 | PRODUCT_STORY_DEFECT | The populated operational-shipment list should expose the fixture graph; it showed its normal empty state. | Corrected in the local-only UAT graph; browser re-walkthrough remains pending because the already-open UAT occupied the required local ports. |
| PR-002 | P2 | NAV_AUTH_MISMATCH + ERROR_HANDLING_DEFECT | Work Queue must not be visible to actors unable to use it; it rendered `You are not allowed to perform this operation.` | Fixed in `OperationsNav`: visibility now follows `oip.read`. |
| PR-003 | P2 | TECHNICAL_SEMANTIC_LEAKAGE + I18N_DEFECT | Normal Control Tower view must default to business meaning; it showed English technical coverage formulas and `PARTIAL_DIMENSION_COVERAGE`. | Fixed in `DashboardWidgets`: technical formulas and warning enums are replaced with business-language coverage text. |
| PR-004 | P1 | PRODUCT_DOMAIN_GAP | Carrier selection must contain carrier candidates only; it also listed cargo-owner customers. | Open architecture gap; `Customer` has only `customer_type`/`status`, neither is a canonical Carrier eligibility or multi-role model. |
| PR-005 | P2 | STATE_SEMANTICS_DEFECT | The operational shipment list’s empty state must distinguish a genuine zero from missing authorized data. | Open; coupled to PR-001. |
| PR-006 | P3 | TECHNICAL_SEMANTIC_LEAKAGE | Release/version/database migration information is visible in ordinary operational navigation. | Open; follow-on presentation decision rather than a safe local removal. |
| PR-007 | P2 | TEST_FIXTURE_DEFECT | Re-running the Shared Transport UAT seed should remain deterministic; it fails with `MultipleResultsFound` after its duplicate same-name Customer setup. | Open; fixture-only and outside Production source. |

## State, language, and error audit

- `TECHNICAL_SEMANTIC_LEAKAGE = FOUND` (PR-003, PR-006); PR-003 corrected and re-walkthrough required.
- `MIXED_LANGUAGE_DEFECTS = FOUND` (PR-003).
- `RAW_ENUM_LEAKAGE = FOUND` (PR-003).
- `AMBIGUOUS_ZERO_STATES = FOUND` (PR-005).
- `EMPTY_STATE_DEFECTS = FOUND` (PR-001).
- `ERROR_STATE_DEFECTS = FOUND` (PR-002).
- `NORMAL_JOURNEY_ERROR_AUDIT = FAIL before PR-002 correction`; the visible Work Queue made an unauthorized request and surfaced technical copy.

## Bounded corrections and validation

- Navigation now hides shipment/control-tower links unless `operational_shipment.read` is present, and hides Work Queue unless `oip.read` is present.
- Dashboard coverage and warning presentation no longer reveals internal definitions or raw warning codes in the normal product view.
- Focused frontend tests: `OperationalPages`, `ExecutionUnitPages`, and `control-tower` — **10 passed**.
- Frontend production build — **PASS**.
- `git diff --check` — **PASS**.

## Product Reality corrective slice

### PR-001 / PR-005 — Shipment list false-empty state

- **Actor:** ORGANIZATION_ADMIN (`shared_transport_e2e_operator`)
- **Surface:** `/operations/shipments`
- **Root cause:** the list API intentionally admits only the authorized route-envelope population. The Shared Transport UAT seed persisted accessible `OperationalShipment` rows without an active `RoutePlan`/`RouteLeg`, so `PR01_DATA_IN_DB = YES`, `PR01_API_ROWS = 0`, and `PR01_UI_ROWS = 0`.
- **Fix:** the local-only Shared Transport seed now creates a valid active route envelope for every seeded Shipment and asserts that invariant. The focused browser test checks both API membership and rendered list membership.
- **Validation:** Python compilation; 21 focused backend tests; 3 focused frontend tests; lint (warnings only); production build; `git diff --check` all pass. Browser retest is pending: the pre-existing local UAT occupied ports 5011/4174, causing the isolated runner to reach its stale service and reject its ephemeral credential. No existing process was stopped.

### PR-002 / PR-004 — Carrier candidate semantic contamination

- **Actor:** ORGANIZATION_ADMIN
- **Surface:** Shared Transport Carrier selector
- **Domain discovery:** `ExecutionUnit.carrier_customer_id` and cargo ownership both reference the CRM `Customer` entity. `Customer.customer_type` is a single CRM classification (`prospect`, `customer`, `partner`, `vendor`) and `status` is lifecycle only; there is no Carrier role, provider eligibility flag, or multi-role party model.
- **Decision:** `PR02_ARCHITECTURE_GAP = YES`. Existing selection and assignment deliberately use all active same-tenant Customers. Filtering out Cargo Owners would be a heuristic and could incorrectly remove a legitimate dual-role party.
- **Follow-on implementation:** `CustomerRoleAssignment` is an additive tenant-owned role record.  `CARRIER` is its first role, backed up deterministically only from existing `ExecutionUnit.carrier_customer_id` relationships.  Carrier candidates now require an active Customer and an active CARRIER assignment; Cargo Owner remains the contextual `ShipmentCargoItem.cargo_owner_customer_id` relationship.

## Decision

`FEATURE_ACCEPTANCE = PASS`  
`CATALOG_OPERATIONAL_CARGO_JOURNEY = PASS`  
`PRODUCT_REALITY = BLOCKED`

The block is Product Reality: PR-004 is an explicit Carrier eligibility architecture gap. PR-001/PR-005 has a bounded local-UAT correction, but its required isolated browser retest is pending until the existing UAT port owners are released. No previously qualified Shared Transport A-I acceptance is downgraded absent a direct regression proof.

`COMMIT = NO`  
`PUSH = NO`  
`DEPLOY = NO`  
`PRODUCTION_CHANGED = NO`

## Corrective browser retest — 2026-09-09

### Local-environment recovery

- Port ownership audit found only loopback ports `5011` and `4174` in use.  The
  listeners were a `python -m backend.run` backend and Vite frontend launched
  at 20:31 from this repository by an already-exited parent shell, with the
  same stale `forwarder_integrated_cert_product_reality_*` database identity.
  They were classified as a prior interrupted Product Reality UAT, not current
  qualification or unrelated development.
- Only those two proved stale process trees were terminated.  The listener
  ports became free; no `forwarder-shared-e2e-*` runtime namespace or Product
  Reality disposable database remained, and the dead process-owned credential
  context was no longer present.
- A single fresh runner then created its own disposable database, migrated it,
  seeded the complete active RoutePlan/RouteLeg envelope, generated its own
  ephemeral credential, and bound frontend `4174` to backend `5011`.

### Retest results

- `PR01_ROUTE_PLAN = PASS`; `PR01_ROUTE_LEG = PASS`; `PR01_API_ROWS = 8`.
  The authorized Shipment list rendered all eight API rows, survived refresh
  and leave/reopen, kept an inaccessible Project B Shipment absent for the
  restricted actor, and rendered the genuine zero-data empty state for the
  no-ProjectAccess actor.
- `PR01_BROWSER_RETEST = FAIL`: the visible Shipment page also mounts Saved
  View controls for an actor without dashboard permission.  They issued three
  unexpected `403` requests to `/api/v2/dashboards`, reported by Chromium as
  console errors.  This is distinct from the repaired route-envelope fixture;
  it is recorded as a newly observed product defect and was not changed in
  this bounded retest.
- `WORK_QUEUE_NAVIGATION_GUARD = PASS`: for the non-entitled restricted actor,
  Work Queue was not actionable in navigation, did not make a Work Queue or
  attention request, and displayed no Work Queue permission error.  The
  broader Work Queue regression gate remains `FAIL` only because its journey
  starts on the same Shipment page and therefore inherits the unrelated Saved
  View `403` console error.
- `CONTROL_TOWER_REALITY_REGRESSION = PASS`: the normal business view rendered
  without raw technical semantic codes, formulas, or implementation labels.
- `CORRECTIVE_REALITY_ERROR_AUDIT = FAIL`: the three Saved View `403` requests
  above violate the required zero-unexpected-error condition.

`PR02_ARCHITECTURE_GAP = YES` remains open.  No Party Role or Provider
Eligibility work was performed.

### Corrective closure

The independent Saved View finding was confirmed as a real product defect:
the Shipment screen mounted Saved View controls without
`personal_dashboard.read`, causing unauthorized dashboard requests.  The
bounded correction gates those controls behind that permission.  Focused
frontend tests and the production build pass.  The final fresh browser UAT
run passed all three corrective journeys with zero unexpected console errors,
page errors, failed requests, or `401/403/404/409/500` responses.

`PR01_BROWSER_RETEST = PASS`  
`PR01 = PASS`  
`WORK_QUEUE_REALITY_REGRESSION = PASS`  
`CONTROL_TOWER_REALITY_REGRESSION = PASS`  
`CORRECTIVE_REALITY_ERROR_AUDIT = PASS`

## PR02-001 focused closure — 2026-09-09

The reported Carrier-candidate defect was resolved as a qualification timing defect. The role-management page renders Customer rows before all role requests finish; the prior helper could mistake that transient unchecked state for persisted OFF and omit the mutation. No backend eligibility predicate, migration, or production domain behavior changed.

After the harness correction, a fresh disposable run proved that current recorded Carrier and new Carrier eligibility remain separate: Customer B stayed readable on the Execution Unit and in Tracking after deactivation, disappeared from the fresh candidate API and selector, and returned after reactivation. Focused backend API and frontend component regressions pass.

## PR02 complete Run #1 — 2026-09-09

The complete fresh Party Role / Provider Eligibility browser matrix passed after
one bounded UI authorization correction. A Platform Admin direct navigation to
a tenant-only operational route previously mounted the route and produced
unexpected `403` calls; the route now fails closed before any tenant read is
mounted. The successful rerun used a new disposable database, migration,
fixture, credentials, backend, frontend, browser context, and runtime.

All role lifecycle, Carrier selector, dual-role, Tracking, Cargo Owner,
expert/platform denial, tenant isolation, Shipment List, Work Queue, Control
Tower, Saved View, carrier lifecycle, language, and normal-journey error-audit
assertions passed. Carrier deactivation retained recorded execution and
Tracking facts while excluding it from fresh candidates, and reactivation
restored candidate eligibility. Runner cleanup passed, leaving no
qualification DB, processes, runtime directory, or credential. PR02_RUN_2 was
not run; Product Reality remains blocked pending that independent run.

## PR02 independent Run #2 closure — 2026-09-09

An unchanged qualified asset was independently rerun in a fresh disposable
PostgreSQL database, fresh seed, credentials, backend/frontend processes,
Chromium context, and runtime.  All eight complete PR02 browser assertions
passed, including PR02-001 carrier eligibility non-regression and the Platform
Admin tenant-surface guard regression.  Normal positive journeys emitted zero
unexpected console errors, page errors, failed requests, or 401/403/404/409/500
responses.  Cleanup removed the database, processes, runtime and credential.

`RUN_2_ASSET_UNCHANGED_FROM_RUN_1 = PASS`
`PR02_RUN_2_ENVIRONMENT_INDEPENDENT = PASS`
`PR02_RUN_2 = PASS`
`PR02_CLEANUP_RUN_2 = PASS`
`PR02_INDEPENDENT_EXECUTION = PASS`
`PR02_BROWSER = PASS`
`PR02 = PASS`
`PRODUCT_REALITY = PASS`
