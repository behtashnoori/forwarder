# Forwarder Final End-to-End UAT Report

- Certification date: 2026-08-21
- Baseline: `d4ae586d9875bad906f812ef33ffaacae8365bd0`
- Branch: `codex/pr-4a-dms-gate-repair`
- Environment: isolated local test processes using repository factories, in-memory/local non-production databases, mocked browser APIs, and the production Vite compiler
- Production access: **NO**
- Production database access: **NO**
- Deployment / push / tag / release: **NO / NO / NO / NO**

## Release decision

The baseline supports a coherent supported workflow from transportation request and assignment through Project, OperationalShipment, cargo, ExecutionUnit execution, LogisticsPoint/location projection, shipment document readiness, certified operational references, and final status/location visibility without a P0 or P1 product gap.

**FORWARDER RELEASE CANDIDATE READY WITH NON-BLOCKING BACKLOG**

**FEATURE DEVELOPMENT FROZEN.** Only a proven release-blocking correction may be accepted before publish. The controlled backlog below is not part of this release candidate.

## Governance and supported-capability matrix

The architecture baseline, development gate, review checklist, ADR index, ADR-016/017/018/022/030/034/035/036/038/039/040, terminology guide, prior gap/readiness/polish reviews, and both tracking authority documents were reviewed. Architecture governance passed and Alembic reported the sole expected head `20260903_external_operational_references`.

| Capability | Supported / primary user | Canonical domain and current authority | Compatibility / deferred work | Release relevance |
| --- | --- | --- | --- | --- |
| Transportation Request | Yes / customer, expert | `ShipmentRequest`; commercial status and tenant/assignee authorization | controlled numeric aliases remain | entry and hand-off |
| Customer context | Bounded / expert | internal organization-scoped `Customer` link | CRM expansion frozen | context only |
| Project | Yes / expert | `Project`; organization-owned coordination | legacy shipment rows may omit it | multi-shipment context |
| Operational Shipment | Yes / expert | `OperationalShipment`; shipment execution lifecycle | request is lineage, not execution | execution root |
| Cargo Catalog / Shipment Cargo | Yes / admin, expert | tenant `CargoCatalogItem`; shipment-owned immutable line snapshot and controlled quantity/UOM | no ExecutionUnit allocation | traceability |
| Execution Unit | Yes / expert | `ExecutionUnit` under one shipment; event-derived unit state | legacy transport unit remains separate | independent execution |
| Legacy expert tracking | Yes / expert | request-owned compatibility aggregate | later ADR-040 transition/retirement | supported compatibility |
| Canonical tracking | Yes / expert | effective non-superseded `OperationalEvent` projection | ADR-040 phases 3–6 deferred | internal authority |
| LogisticsPoint | Yes / admin, expert | tenant location master; immutable event snapshots | legacy selector is not an alias | governed location input |
| Shipment documents/readiness | Yes / expert | shipment requirement + exact request-owned file version + assessment | no unit-owned documents | operational readiness |
| External references | Yes / expert | ADR-039 shipment/unit owner tables; B/L, AWB, CMR only | Iranian candidate types deferred | operational evidence |
| Workload/referral/assignment | Yes / admin, expert | tenant-fenced assignment/referral rules | displayed workload differs from selection rule by design | responsibility |
| Organization administration | Yes / org admin | active membership and tenant authority | none material | access/configuration |
| Platform catalog administration | Yes / platform admin | separate platform authority | none material | governed vocabulary |
| Public tracking | Yes, compatibility / customer | tracking-code allowlist over legacy projection | canonical public migration deferred | supported unchanged path |

## UAT data and personas

Repository UAT factories created two isolated organizations and active/inactive membership variants representing Organization A Admin, Organization A Expert 1, Organization A Expert 2, and Organization B Expert. The scenario modeled industrial gearbox transport from Tehran in a Project with separate air/AWB and road/CMR shipments, distinct cargo snapshots, multiple execution units, events, documents, and references. Fixtures were transaction-scoped and did not create permanent seed/reference data.

## Scenario results

### Scenario A — normal operational flow: PASS

| Step | Result | Evidence |
| --- | --- | --- |
| Assigned request is discoverable and authorization-scoped | PASS | assignment/referral and expert contract suites |
| Opaque request detail/navigation | PASS | opaque-identity backend tests and operational frontend tests |
| Project context and shipment reachability | PASS | project aggregate and operational page tests |
| Cargo lines and quantity/UOM snapshots | PASS | cargo foundation and UI acceptance tests |
| Execution context and back-navigation | PASS | execution-unit API/UI and shipment-detail behavior tests |
| Supported location recording/visibility | PASS | logistics, canonical projection, and execution UI tests |
| Shipment documents independently visible | PASS | MDPM readiness and document component tests |
| Certified external reference association | PASS | ADR-039 lifecycle/adversarial and shipment component coverage |
| Understandable shipment status/location | PASS | shipment detail and ADR-040 projection coverage |

### Scenario B — multi-shipment / multi-unit: PASS

Shipment ownership, cargo separation, independent document requirements, reference ownership, unit ownership, lifecycle/latest-event separation, and cargo reverse traceability passed. ADR-040 location states were explicitly exercised: `UNAVAILABLE`, `SINGLE`, `COMMON`, and `MULTIPLE`; `MULTIPLE` returned `current_location = null` and never selected the newest unit as the whole shipment.

### Documents: PASS

Requirement materialization, eligible artifact filtering, exact active file-version association, authorized reuse, replacement, removal, assessment/readiness, tenant fencing, and shipment independence passed. The implementation preserves `DocumentDefinition != requirement != file != assessment`; upload is not approval.

### External references: PASS

Create, view/history, supersede, cancel, evidence association, normalization, idempotency/request-hash conflict, revision conflict, owner fencing, and non-enumeration passed for `BILL_OF_LADING_NUMBER`, `AIR_WAYBILL_NUMBER`, and `CMR_NUMBER`. Cotage, Warehouse Receipt, Registration Order, and Barfarabaran remain absent by design and are not defects.

### Tracking/current location: PASS

No events, one location event, later non-location events, newer/out-of-order locations, equal occurrence timestamps, correction/supersession, multiple units, common/different locations, and missing/stale/conflicting caches passed. Effective ordering is `occurred_at DESC`, `recorded_at DESC`, `public_id DESC`; superseded events are excluded. Provenance is explicit, UTC serialization is retained, and canonical/legacy sources are not mixed.

### Tenant and authorization adversarial UAT: PASS

Cross-tenant request, project, shipment, unit, cargo, document, LogisticsPoint, reference, assignment, catalog, and administrative access failed closed. Malformed/foreign opaque identities, numeric substitution, stale/former assignment, inactive/duplicate membership, missing permission, and foreign parent/resource substitution were covered by the focused and full suites. Client-supplied organization identity did not establish authority. Same-tenant active authorized paths passed.

### Failure and recovery: PASS

API errors, empty/no-result states, invalid identities/references, ineligible documents, revision conflicts, cancelled/superseded references, missing current location, rollback/fault injection, idempotent retries, and request-hash conflicts produced safe outcomes without duplicate mutation, silent corruption, or cross-tenant disclosure. One frontend test missed an async mock result only while four heavy gates ran concurrently; it passed in isolation and the complete serial frontend suite passed, so this was classified as runner contention rather than a product finding.

## Residual finding adjudication

No new product finding was opened by final UAT. Previously bounded P1 workflow gaps E2E-001 through E2E-005 are verified closed; E2E-006 and authorized ADR-040 phases 1–2 remain closed. The remaining six pre-publish polish items are P3 only.

| Classification | Count | Disposition |
| --- | ---: | --- |
| P0 | 0 | none |
| P1 | 0 | none |
| P2 | 0 | none outstanding |
| P3 | 6 | post-publish backlog |
| Not a defect | 4 groups | intentionally absent reference types, CRM expansion, public canonical migration, numeric compatibility contraction |
| Post-publish architecture work | 1 program | ADR-040 phases 3–6 |

## Regression evidence

| Gate | Result |
| --- | --- |
| Backend focused | PASS — 75 passed |
| Full backend | PASS — 799 passed, 82 environment-gated skipped, 1 expected-failure |
| Frontend focused | PASS — 45 passed |
| Full frontend | PASS — 143 passed; serial rerun after one parallel timing miss |
| TypeScript | PASS — `tsc --noEmit` |
| ESLint | PASS — 0 errors, 12 existing warnings |
| Vite production build | PASS — existing chunk-size advisory only |
| Python compile | PASS — `compileall backend scripts` |
| Ruff | NOT APPLICABLE — documentation-only changed scope; no Python source changed |
| Alembic sole head | PASS — `20260903_external_operational_references` |
| Architecture governance | PASS |
| Git diff check | PASS |
| Changed-scope secret scan | PASS |

PostgreSQL-only test modules were skipped where their explicit environment contract was not present. This certification did not access Production or a Production database and does not claim a Production migration rehearsal.

## Controlled gaps and post-publish backlog

- ADR-040 phases 3–6: canonical-only adopted writes, public canonical cohorts, legacy read-only transition, and retirement, each behind its Accepted gates.
- Deep route, reconciliation, checkpoint, exception, economics, audit, and remaining bilingual control localization.
- CRM expansion/remediation remains on hold.
- Cotage, Warehouse Receipt, Registration Order, and Barfarabaran remain deferred.
- Numeric compatibility contraction only after consumer and tenant-certification evidence.
- Advanced analytics and optional UI/performance polish, including bundle splitting.
- Existing deprecation/lint warnings may be reduced in a bounded post-publish maintenance goal.

## Release recommendation

Freeze `d4ae586d9875bad906f812ef33ffaacae8365bd0` as the Forwarder release-candidate baseline. The exact next controlled Goal is: **publish-readiness rehearsal for this frozen commit in an isolated PostgreSQL release-candidate environment, including backup/rollback evidence and artifact verification, with no feature work and no Production access until a separately authorized release Goal.**

**FORWARDER RELEASE CANDIDATE READY WITH NON-BLOCKING BACKLOG**
