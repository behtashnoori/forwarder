# S6 — Golden Business Journeys

## Scope and baseline

This is local/test-only LPAF v2.1 assurance evidence.  It began from S5 commit
`50d3efc56e4215c06a4118312a918b679ed63549` on
`stabilization/s6-golden-business-journeys`.  No application, frontend,
backend, migration, package, or test source was changed for S6.

The evidence uses existing API/domain integration contracts and the complete
frontend test suite.  Local test fixtures establish only prerequisites; each
assertion exercises the corresponding authorization, service, persistence, or
reporting path.

## Expected and actual journey results

| Journey | Actor and tenant | Expected result | Actual evidence and result |
| --- | --- | --- | --- |
| GBJ-1: customer to expert | Public customer A, organization A, expert A; expert B is negative control | An explicit host resolves A; request is assigned/referrable and visible to the authorized expert, not B; an unknown host has no fallback. | `test_organization_hostname_routing.py` and `test_expert_assignment_referral_contract.py` cover explicit host resolution, assignment/referral contracts, expert ownership and reassignment side effects. `server.forwarderet.ir`, arbitrary hosts, forged expert identity, and cross-tenant access fail safely. **PASS** |
| GBJ-2: expert operational work | Expert A in organization A | Valid active cargo references, policy-derived requirements, and tenant logistics points persist through supported operational/tracking/project flows; invalid/inactive inputs and invalid transitions fail. | `test_cargo_foundation.py`, `test_organization_document_policy.py`, `test_logistics_network.py`, and `test_global_logistics_point_materialization.py` prove active-reference validation, persisted operational use, document readiness/snapshots, and lifecycle/tracking contracts. Inactive/invalid references and unauthorized tenant use are rejected. **PASS** |
| GBJ-3: admin configuration to runtime | Organization admin A then expert A; B is negative control | A policy change affects new records only; existing captured requirements do not mutate; readiness and expert-visible runtime state remain correct. | `test_organization_document_policy.py` covers enabled/optional/disabled future policy, fresh runtime resolution, historical snapshot preservation, readiness semantics, admin authority, and organization fencing. **PASS** |
| GBJ-4: operations to reporting | Organization admin A, platform admin, expert negative control | Exact tenant metrics are visible to A; platform global is A+B and filtered A is A only; expert is denied; empty and invalid-filter cases are safe. | `test_s4_reporting_oversight.py` asserts exact status, transport, rolling-window and province metrics, null/international geography behavior, A/B fencing, XLSX fencing, zero-state semantics, and authorization. **PASS** |
| GBJ-5: reference to operational network | Platform admin, organization admin A; B is negative control | Platform owns reference catalog; A adoption is tenant-scoped and does not itself make an operational point; explicit materialization creates only A's LogisticsPoint. | `test_global_logistics_point_adoptions.py` and `test_global_logistics_point_materialization.py` prove catalog authority, adoption fencing, idempotent explicit materialization/provenance, and distinct reference/adoption/operational lifecycles. **PASS** |
| Direct organization LogisticsPoint | Organization admin A; B is negative control | A direct tenant point is independently usable operationally, has no reference-catalog side effect, and cannot be used by B. | `test_logistics_network.py` and `test_global_logistics_point_materialization.py::test_phase4b_materialized_point_uses_ordinary_tracking_and_project_contracts` cover tenant-owned operational-point use by project/tracking and cross-tenant rejection. **PASS** |
| Reference-data readiness | Public/request context | A ready country has an active usable city; zero-city countries are excluded; city-country mismatch is rejected without fabricated geography. | `test_iran_destination_point.py` exercises selectable readiness, city ownership/activity and invalid cross-country combinations. **PASS** |

## Cross-role propagation and tenant safety

| Producer → consumer | Persisted outcome | Boundary and evidence |
| --- | --- | --- |
| Customer A → Expert A | Tenant-resolved request/referral/assignment | Expert A can consume only its entitled work; forged identity and expert B access fail (`test_organization_hostname_routing.py`, `test_expert_assignment_referral_contract.py`). |
| Admin A → Expert A | Document-policy runtime requirement | Fresh records receive the current policy; existing snapshots remain historical and B is unaffected (`test_organization_document_policy.py`). |
| Operations A → Admin A reporting | Operational/request state aggregates | Exact tenant dashboard data and exports are fenced before output (`test_s4_reporting_oversight.py`). |
| Platform admin → Organization A | Reference-point adoption | Platform catalog authority is separate from A adoption/materialization; B is not auto-adopted (`test_global_logistics_point_adoptions.py`). |
| Organization admin A → operational use | Tenant LogisticsPoint | Explicit materialization/direct point is available to A's project/tracking flow only (`test_global_logistics_point_materialization.py`, `test_logistics_network.py`). |

Negative coverage includes unknown and wildcard-like hosts, forged organization/expert
identities, role escalation to reporting, invalid organization filters, empty tenant
reporting, inactive/invalid reference data, invalid geography pairs, disabled future
requirements, cross-tenant adoption/materialization, and cross-tenant operational
point use.  These contracts prove A/B isolation, safe unknown-host handling, and no
implicit tenant fallback.

## Lifecycle and configuration evidence

- Valid assignment, reassignment, operational tracking/project use, and point
  materialization paths persist their expected state.
- Invalid reference, authorization, tenant, and state inputs are rejected by the
  existing contracts; historical document requirements are preserved rather than
  retroactively changed.
- Adoption is deliberately not equivalent to an operational LogisticsPoint; the
  explicit materialization action is idempotent and records provenance.

## Verification record

| Layer | Command / scope | Result |
| --- | --- | --- |
| Focused backend journeys | `D:\\Projects\\webapp\\15-forwarder\\.venv\\Scripts\\python.exe -m pytest -q backend/tests/test_organization_hostname_routing.py backend/tests/test_expert_assignment_referral_contract.py backend/tests/test_organization_document_policy.py backend/tests/test_cargo_foundation.py backend/tests/test_global_logistics_point_adoptions.py backend/tests/test_global_logistics_point_materialization.py backend/tests/test_logistics_network.py backend/tests/test_s4_reporting_oversight.py backend/tests/test_iran_destination_point.py` | 84 passed, 0 failed, 0 errors; 37.89s. |
| Full backend regression | `D:\\Projects\\webapp\\15-forwarder\\.venv\\Scripts\\python.exe -m pytest -q` | 844 passed, 92 skipped, 1 xfailed, 0 failed, 0 errors, 0 xpassed; exit 0; 337.76s. |
| Frontend suite | `npm run test:frontend` | 33 files passed; 156 tests passed; exit 0; 22.92s. |
| Production frontend build | `npm run build` | Passed; exit 0; 8.87s. |

## Browser/E2E assessment

No stable repository-supported browser/E2E runner is configured (`playwright`
configuration is absent).  No browser framework was introduced because S6 is not a
test-infrastructure project.  Core cross-role behavior is instead proven by the
existing backend API/domain integration contracts above and the complete frontend
component suite; no screenshot/manual assertion is relied upon for authorization,
tenant, propagation, or persistence claims.

## Defects, changes, and residual risk

- Defects found: none.
- Fixes made: none.
- Migration or data change: none.
- Production access, deployment, or push: none.
- Residual risk: browser-driven rendering of the integrated journeys is not covered
  because the repository has no stable local E2E runner.  This is bounded non-core
  presentation coverage; backend authorization and propagation contracts are covered.
- Deferred: production domain/DNS/IIS/CORS retirement, catalog completion, broader
  UX/RBAC/reporting redesign, and any production data work remain out of scope.

## Closure

All five Golden Business Journeys, the separate direct LogisticsPoint path, tenant
isolation, cross-role propagation, reference-data behavior, negative/error paths,
configuration propagation, lifecycle contracts, frontend suite/build, and full
backend regression are proven by the recorded local evidence.  S6 is **PASS**.
