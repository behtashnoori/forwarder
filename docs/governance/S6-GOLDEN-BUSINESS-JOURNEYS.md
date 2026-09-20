# S6 — Golden Business Journeys

## Scope and baseline

> **Historical evidence notice (2026-09-20):** S6 PASS below remains historical evidence of the tested baseline. References to Request/Shipment reassignment are not target authority after ADR-047. The appended Post-D2 contracts define future acceptance journeys and do not claim implementation PASS.

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

## Post-D2 target journey contracts — reference phase

The following are **NEW ACCEPTED DECISION** journey references under PDR-019 and the LPAF v2.3 Product Integration strong default. Their reference definition is closed; implementation and browser acceptance remain future Build/Verify work.

### A. Optional Multi-Cargo Request

| Contract field | Target |
| --- | --- |
| ENTRY | Customer is signed in and starts or edits a Shipment Request. |
| ACTOR | Customer; authorized staff projection is a downstream reader, not intake owner. |
| ENTITLEMENT | Customer may create/edit only its governed Request; tenant/customer scope is server-derived. |
| DISCOVERY | Normal Customer navigation exposes Request creation/edit and an optional Cargo section. |
| USE | Customer submits with zero Cargo Items or adds/removes `0..N RequestCargoItems`; no Cargo characteristic is required. |
| RESULT | Request is accepted under the existing commercial workflow; any supplied items remain Request-owned commercial facts. |
| LEAVE | Customer may leave after save/submit without creating Shipment, allocation, Execution Unit, vehicle/container, or Route Leg. |
| RETURN | Customer reopens the Request through the normal Request list/detail and sees the same Cargo state, including empty state. |
| DENIAL/ERROR | Foreign/unauthorized Request is non-disclosing; malformed supplied values receive stable field errors; absent Cargo never causes rejection. |
| DOWNSTREAM | Pricing/Expert projection may read Request Cargo; Operations later creates separate Shipment Cargo snapshots/allocation explicitly. |

### B. Dual Calendar presentation

| Contract field | Target |
| --- | --- |
| ENTRY | Entitled user opens a supported Request, Quote, Document, Tracking, Shipment Detail, or Control Tower surface. |
| ACTOR | Customer, owning Transport Expert, or same-organization Admin/Manager as authorized for that surface. |
| ENTITLEMENT | Calendar formatting grants no data access; the underlying surface authorization must already pass. |
| DISCOVERY | Dates appear in their normal existing location; no separate calendar-only route is required. |
| USE | Selected business dates display `Gregorian (Jalali)` from one authoritative Local Date or Instant. |
| RESULT | Both renderings identify the same fact; storage, sort, filter, comparison, and timezone semantics are unchanged. |
| LEAVE | User navigates away through ordinary product navigation. |
| RETURN | Reopening the same record reproduces the same dual rendering for the same authoritative fact. |
| DENIAL/ERROR | Unauthorized records remain hidden/denied; invalid/unknown date facts are not guessed; format failure must not fabricate a Jalali value. |
| DOWNSTREAM | Exports/APIs retain their separately governed authoritative date contract unless a later surface decision explicitly adds presentation. |

### C. Combined Transport Request intent

| Contract field | Target |
| --- | --- |
| ENTRY | Customer creates or edits a Request and reaches the existing transport-intent selector. |
| ACTOR | Customer; authorized Expert/Admin are read-only or act under existing Request workflow authority. |
| ENTITLEMENT | Governed Request create/edit access; catalog visibility does not grant operational planning authority. |
| DISCOVERY | Existing transport selector exposes one deterministic `حمل ترکیبی` choice without duplicate/conflicting Rail choices. |
| USE | Customer selects the one scalar combined intent; no ordered modes or permutations are entered. |
| RESULT | Request summaries round-trip the combined intent consistently. |
| LEAVE | Customer saves/submits and leaves through the normal Request journey. |
| RETURN | Customer and entitled staff reopen Request detail/summary and see the same scalar intent. |
| DENIAL/ERROR | Inactive/invalid catalog identity fails stably; historical values remain readable; actual Route Legs are never fabricated from intent. |
| DOWNSTREAM | Operational planning owns the actual ordered Route Legs; Shipment/Tracking/Control Tower label Request intent and actual route as separate facts. |

### D. Quote communication

| Contract field | Target |
| --- | --- |
| ENTRY | Customer opens a current official Quote through the normal Request/Quote surface. |
| ACTOR | Customer responds; owning/authorized Transport Expert reads response/history and may issue a revised official Quote. |
| ENTITLEMENT | Existing Request/Quote customer capability and tenant/tracking protection; Expert access follows current Request authority before Shipment creation. |
| DISCOVERY | The Quote presents approve, needs discussion, and reject actions; needs discussion reveals a short-message field. |
| USE | Customer chooses one response; `discussion` requires a bounded message; accepted/declined carry no discussion message. |
| RESULT | One governed response/history fact is stored on that official Quote; discussion creates no price/status mutation and accepted alone enables Shipment creation. |
| LEAVE | Customer may leave after a truthful confirmation; no endless conversation UI is implied. |
| RETURN | Customer and entitled Expert reopen bounded Quote history; a later revised Quote remains a separate official record. |
| DENIAL/ERROR | Expired, conflicting, concurrent, foreign, inactive, or unauthorized response follows stable existing error/non-disclosure rules; same-response replay stays idempotent. |
| DOWNSTREAM | Expert may issue a new/revised official Quote; Notification activation is not triggered; accepted-Quote Shipment creation later captures the issuing Expert under ADR-047. |

### E. Documents — owning-Expert management

This target journey is authoritative under PDR-020/ADR-050. It is a reference contract for future design and acceptance, not an implementation or browser PASS.

| Contract field | Target |
| --- | --- |
| ENTRY | The active owning Transport Expert opens the existing Shipment/Case Documents surface through the normal Shipment/Case workflow. |
| ACTOR | Owning Transport Expert only for document management. The System owns history preservation. |
| ENTITLEMENT | Server derives active identity, tenant, authoritative parent, and owning Expert. Same-organization membership, Admin/Manager title, Customer relation, Project access, or a file identifier does not grant management. |
| DISCOVERY | The existing Shipment/Case workflow exposes Documents to the owning Expert; no hidden standalone attachment-management route or unrelated permission is required. |
| USE | Select one or multiple files; upload; append new sibling files; select one current file for targeted replacement; retry only a known failed file. |
| RESULT | Each file receives a truthful file-level result and governed metadata. Successful siblings remain successful. Replacement creates a new current version where applicable while the System preserves the old immutable/auditable version. |
| LEAVE | The Expert returns to the Shipment/Case workflow without an all-or-nothing batch requirement. |
| RETURN | The Expert reopens Documents through normal navigation and sees the governed current set plus authorized history. |
| DENIAL/ERROR | Customer management, Admin/Manager management, other same-Organization Expert, other tenant, inactive/revoked actor, forged parent/owner, and stale/foreign replacement target are denied. For A success, B failure, C success, A/C remain and only B is retryable. |
| DOWNSTREAM | Document readiness evaluates the logical requirement, eligible current evidence, and assessment policy. Historical replaced versions do not count as extra current evidence; `more files` never means `more ready`. |

Read/history/download visibility is evaluated separately. Existing owning-Expert and governed Admin/Manager oversight reads may remain; no Customer read visibility is newly granted, and PDR-008 remains Proposed for generalized projections.

### Reference-phase status

```text
REFERENCE_IMPACT=UPDATE_REQUIRED
REFERENCE_IMPACT_STATUS=CLOSED_FOR_DOCUMENTS_DESIGN
USER_JOURNEY_REFERENCE=A/B/C/D/E DEFINED; IMPLEMENTATION_AND_BROWSER_ACCEPTANCE_PENDING
```
