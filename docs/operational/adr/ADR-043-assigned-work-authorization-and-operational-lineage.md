# ADR-043: Assigned-Work Authorization and Operational Lineage

- Status: ACCEPTED
- Date: 2026-08-30
- Owners / decision authority: Product Owner (work model); Architecture Owner; Security Owner; Operations Owner; Assignment/Referral Owner; CRM Domain Owner; Reporting/Monitoring Owner
- Parent / related decisions: ADR-042 (parent authority and capability model); ADR-037 (Basic Expert CRM context); ADR-006; ADR-011; ADR-017; ADR-018; ADR-019; ADR-030; ADR-031; ADR-033; ADR-034; ADR-035; MT-0; Admin multi-tenant security.
- Decision traceability: Product Owner approved direction for canonical root assignment with certified inherited child access, 2026-08-30; Product Owner acceptance of ADR-043, 2026-08-30; final architecture assurance: `ADR_043_ASSURANCE = READY_FOR_OWNER_ACCEPTANCE`; assigned-work authorization analysis, 2026-08-30; `docs/architecture/FORWARDER-ARCHITECTURE-BASELINE.md`; `docs/architecture/multi-tenant-architecture-contract.md` (MT-0); `docs/architecture/admin-multi-tenant-security.md`.

## Context

ADR-042 separates canonical authority, tenant membership, governed capability, work relationship, business eligibility, and scoring. It requires Basic Expert work to remain assigned/workflow-authorized rather than tenant-wide by default. ADR-037 remains authoritative for the narrow Basic Expert request-parented CRM customer-context projection.

Current authorization is fragmented. Expert-console request workflows resolve one tenant and generally restrict non-legacy-admin access to the assigned request. Newer operational services commonly resolve one tenant and check a membership permission, but do not consistently prove a current work relationship. `ShipmentRequest` has a primary assignee and accepted-quote `OperationalShipment` records retain a request link, but downstream authorization does not currently use that lineage. Direct shipments may have no request root. `OperationalWorkItem` and OIP have separate assignee concepts that are not canonical work roots. Legacy `role=admin` still broadens some request workflows.

This ADR defines the target assigned-work authorization contract. It does not authorize implementation, schema/data changes, migration, backfill, permission grants, deployment, or production changes.

## Problem statement

An ordinary Expert must be able to work on assigned operational work without gaining visibility of every tenant operational record. The architecture needs one consistent, auditable answer to: “is this actor currently authorized to know this work exists and to perform this action?” It must preserve tenant isolation, distinguish assignment from scoring and capability, and prevent legacy-role compatibility from becoming canonical authority.

## Decision

Adopt **canonical root assignment with certified inherited child access**.

For tenant operational work, authorization evaluates in this order:

```text
authenticated active identity
-> canonical authority
-> exactly one server-derived active tenant context
-> resource tenant ownership and non-disclosure boundary
-> current work relationship OR approved Organization Admin oversight
-> action capability
-> workflow/business invariants
-> allow
```

A capability never establishes membership, tenant scope, resource ownership, or work assignment. Eligibility and business scoring determine who may be considered for assignment; they do not establish current work access or an action capability. Client-supplied organization, root, parent, or work identifiers are never authority evidence.

## Canonical root-work model

### Request-based work

`ShipmentRequest` is the canonical assignment root when operational work originates from a request. Its current primary assignment establishes the Basic Expert’s current work relationship. An accepted-quote `OperationalShipment` and its certified tenant-consistent descendants may inherit access from that root:

```text
ShipmentRequest (primary assignee)
-> OperationalShipment
-> RoutePlan / RouteLeg / Checkpoint / Milestone
-> tracking / operational events / document readiness
-> eligible execution objects and other certified children
```

The root assignee must not be copied onto every child merely to implement authorization.

### Direct shipment work

An `OperationalShipment` created without a `ShipmentRequest` is a canonical operational root. When it is intended for ordinary Expert operational work, it must have a valid responsible Expert/primary assignee. Its certified children inherit work authorization from that direct-shipment root. This ADR defines the contract, not a column name or implementation form.

### Certified authorization lineage

For every resource type eligible for inherited assigned-work authorization, the architecture and implementation must declare one canonical authorization lineage rule. The lineage is server-derived, based on trusted persisted relationships, tenant-consistent at every hop, deterministic, declared by resource type, and non-client-selectable. Before implementation, the `CERTIFIED_ROOT_CHILD_LINEAGE_MATRIX` must record the resource type, canonical persisted parent field/relationship, next parent, canonical root type, tenant-consistency rule, ambiguity rule, and orphan behavior.

Inherited authorization is valid only if the declared lineage proves that: the child belongs to its trusted parent; each parent is in the resolved tenant; the lineage reaches one canonical root; the actor has a current work relationship to that root; the action capability is present where required; and workflow/business state allows the action. The evaluator must not try parents until one authorizes. Missing, null where required, broken, cross-tenant, conflicting, ambiguous, stale/inconsistent, or competing-root lineage fails closed. A client cannot choose a root, parent, organization, or lineage path for authorization. Security-significant forged, conflicting, or cross-tenant lineage attempts require the applicable ADR-042 security-boundary audit evidence without disclosing sensitive resource existence.

Project-only execution objects that lack certified Request or Direct Shipment root lineage do not become Basic Expert work through same-tenant membership, creator identity, broad read permission, or project existence. They fail closed for Basic Expert access until a separately accepted root/lineage decision exists.

## Work relationship, assignment, and participation

For Basic Expert, tenant membership alone does not establish work access. The primary work relationship is the current Request or Direct Shipment primary assignment. Historical involvement, creator/audit fields, eligibility, and scoring do not preserve or establish current access.

`OperationalWorkItem.assignee_user_id` represents responsibility within already-authorized root work; it does not create a new canonical work root or independently grant root access. OIP’s optional assignee likewise does not establish canonical work authorization; OIP remains governed by its existing domain and permission policy until a later explicit decision.

No generic multi-participant WorkAssignment model is introduced. Current evidence supports a primary-assignee model. Collaborators, reviewers, observers, and execution participants require a future explicit decision when a real workflow needs them.

## Capability semantics

For an ordinary Expert, operational capabilities are evaluated only after a current work relationship is proven. Target semantics are:

| Capability | Target meaning for an ordinary Expert |
| --- | --- |
| `operational_shipment.read` | Read OperationalShipments within current authorized work scope. |
| `work_item.read` | Read WorkItems belonging to authorized root work. |
| `operational_execution.read` | Read execution information belonging to authorized work. |
| `route_plan.read` | Read route information belonging to authorized work. |
| `document_readiness.read` | Read readiness belonging to authorized work. |
| `execution_unit.read` | Read only where certified lineage reaches authorized work. |
| `checkpoint.report` | Perform reporting only on authorized work and in a permitted workflow state. |

Tenant-wide visibility, queues, reports, or exports must be granted through explicit approved Organization Admin oversight or separately governed delegation; they must not be achieved by redefining assignment or by granting a Basic Expert a broad tenant read.

`BASIC_EXPERT_BASELINE_V1 = []` means no broad membership capability key is automatically granted merely because authority is `EXPERT`. It does not mean an assigned Expert has zero possible actions. An **intrinsic assigned-work action** is a narrowly defined ordinary action in the approved canonical workflow contract. It is allowed only when the actor is authenticated and active; has `EXPERT` authority; has exactly one active server-derived tenant membership; accesses a resource in that tenant; has a current valid root-work relationship; has certified child lineage where applicable; requests an action explicitly classified as intrinsic; and satisfies workflow/state/business invariants. An intrinsic action never implies tenant-wide visibility or bypasses root-work authorization; absence from the approved intrinsic-action contract denies it.

All broader operational, sensitive, administrative, verification, correction, override, financial, reporting, assignment-management, or other elevated actions require an explicit governed capability in addition to valid tenant/work authorization. `EXPERT` authority and root assignment do not permit arbitrary actions. Before implementation enforcement, owners must approve a `BASIC_EXPERT_INTRINSIC_ACTION_MATRIX` mapping action to resource, root relationship, workflow state, backend enforcement point, and intrinsic-versus-capability-governed classification. `logistics_point.read` remains conditional, not baseline. A selector used within authorized work should ultimately be purpose-bounded and tenant-fenced rather than relying on unnecessarily broad tenant logistics visibility.

## Organization Admin oversight

Organization Admin oversight and work assignment are separate authorization bases. `ORGANIZATION_ADMIN` plus valid tenant context plus an approved oversight action category/capability is the required basis for a tenant oversight action where applicable; Organization Admin authority alone does not imply unrestricted operational write authority. The approved oversight matrix must separately define tenant-wide operational read oversight, assignment/reassignment management, operational write actions, high-risk verification/correction/override, economics/financial actions, reporting/export, and configuration/reference administration. ADR-042’s high-risk exclusions and governed-capability rules remain authoritative.

An Organization Admin remains bound to exactly one active server-derived tenant and is never represented as assigned to every root. It remains denied foreign-tenant work, Platform-only diagnostics, and global governance. Before implementation enforcement, owners must approve an `ORGANIZATION_ADMIN_OVERSIGHT_MATRIX` containing the applicable action category, read/write scope, capability, tenant boundary, and high-risk exclusion.

## Platform Admin boundary

Platform Admin without membership has no tenant operational work relationship. The following must deny non-disclosively unless a future separately accepted support/break-glass design establishes trusted tenant context:

```text
PLATFORM_ADMIN + tenant work identifier + client-supplied organization identifier
```

Legacy behavior that treats Platform Admin as tenant assignment-capable is compatibility/migration debt, not target architecture.

## Reassignment

Every protected backend operation must evaluate current authorization when the operation executes. Authorization established at login, an earlier page load/list/API call, frontend route entry, cached response, or long-running UI session is not durable proof of current work authorization. On root reassignment from Expert A to Expert B, subsequent protected operations by A fail, B becomes current assignee under the root contract, and certified child access follows the root automatically. Child permissions or grants are not copied. Historical drafts, tracking, documents, events, and audit remain immutable business history but never preserve A’s current authorization.

Implementation must address authorization-aware cache binding or invalidation, stale collection results, concurrent requests, reassignment races, and transactional consistency where required. Stale frontend state, cached authorization/list results, old sessions, and previously discovered opaque child identifiers must not broaden current access.

Every root assignment and reassignment requires tenant-scoped audit evidence containing at least actor, tenant, root-work identifier, prior assignee where applicable, new assignee, timestamp, reason/provenance, and correlation/request identifier where the architecture audit pattern requires it. Compatibility fallback usage and high-value boundary denials follow ADR-042’s audit rules.

## Collection, search, and disclosure rules

For ordinary Experts, work-relationship filtering occurs before pagination, counts, totals, sorting where unauthorized records could affect output, search, autocomplete, exports, dashboards, cache materialization, and serialization. Tenant filtering alone is insufficient. An Expert receives only resources they are authorized to know exist. Filtering must prevent disclosure through returned records; total/page counts; page numbers; meaningful empty-page behavior; pagination and serialization metadata; suggestions/autocomplete; aggregate/dashboard values; export contents; export-job metadata or status; observable cache/materialized results; and differentiated error shapes. No unassigned or foreign work existence or approximate quantity may be disclosed through collection metadata, subject to any more specific accepted non-disclosure contract.

Foreign-tenant, same-tenant-unassigned, broken-lineage, invalid-lineage, and reassigned-away opaque identifiers follow Forwarderet’s accepted non-disclosing failure contract. Authorization succeeds before side effects, including audit/outbox/cache/storage effects, except required safe security-denial evidence.

## Legacy compatibility

`role=admin` is not canonical authorization evidence and never proves `PLATFORM_ADMIN`. Its current broad request visibility is compatibility debt whose target replacement is approved Organization Admin oversight; assignment/reassignment maps to tenant-bound Organization Admin authority or an approved delegated capability. No role-based fallback may survive final migration certification.

The legacy `business_expert` scoring advantage remains an unresolved business-scoring decision. It is neither a work relationship nor an action capability.

## CRM relationship

ADR-037 remains authoritative and is not amended. Basic Expert CRM remains request-parented and read-only under its parent authorization contract. This ADR grants no standalone CRM, list/search/write authority. Direct Shipment root assignment establishes an operational work relationship only: it grants no CRM/customer authority and cannot create ADR-037 request-parented customer-context authority because it has no `ShipmentRequest` parent. Any customer information specifically required for Direct Shipment execution needs a separately accepted minimal operational-data contract or architecture decision. Broader CRM still requires ADR-042’s separately accepted companion CRM authorization decision.

## E2E certification requirements

Before removal of legacy assigned-work fallback, direct backend/API certification must prove:

1. Basic Expert: assigned Request allowed; unassigned same-tenant and foreign Request denied non-disclosively.
2. Request-derived Shipment: authorized-root access allowed only with applicable capability/workflow; unassigned same-tenant and foreign Shipment denied.
3. Direct Shipment: assigned Expert allowed only with applicable capability/workflow; another Expert denied.
4. WorkItem, route, tracking, and document children: authorized-root access allowed only as applicable; unauthorized-root and broken-lineage attempts denied.
5. Reassignment: A loads a resource, the root is reassigned to B, and A’s subsequent update is denied; A’s old session/token and previously discovered child opaque identifier cannot preserve access; stale list/cache/UI visibility cannot establish backend action authority; concurrent reassignment versus protected mutation permits no stale-authorization mutation where current assignment is required.
6. Missing or multiple active memberships: fail closed.
7. Forged or conflicting lineage: forged parent/root/organization input, cross-tenant parent relationship, orphan child, competing lineage, and client-selected lineage all deny non-disclosively.
8. List/search/count/export: no unassigned-work disclosure through records, metadata, suggestions, aggregates, exports, export-job state, cache, or differentiated errors.
9. Organization Admin: only approved oversight categories/actions and assignment/reassignment are allowed without fake assignment; foreign tenant denied.
10. Platform Admin without membership: tenant work denied; client-supplied organization identifier cannot establish tenant scope or work relationship.
11. Legacy `role=admin`: `role=admin` + `authority=EXPERT` with valid single membership, no membership, and multiple active memberships cannot establish Platform authority; hidden frontend/navigation bypass and direct API calls are denied where the active canonical evaluator denies; fallback use remains observable during migration and is removed only after exit criteria pass.

## Migration and rollback strategy

Use an additive, controlled sequence:

```text
ACCEPT -> DEFINE CERTIFIED ROOT/CHILD MATRIX -> ADD ROOT SUPPORT WHERE REQUIRED
-> CENTRALIZE ASSIGNED-WORK EVALUATION -> SHADOW -> DUAL AUTHORIZATION EVIDENCE
-> CONTROLLED COHORT SWITCH -> BACKEND/API E2E -> REMOVE LEGACY FALLBACK
-> CONTRACT LATER
```

No guessed backfill, destructive first-step migration, or privilege broadening is permitted. During shadow evaluation, legacy authorization remains the active enforcement path for its controlled cohort while canonical authorization is observational; differences are recorded and analyzed. Canonical `ALLOW` must not broaden active access merely because it returned `ALLOW`. `ALLOW = legacy_allow OR canonical_allow` is prohibited. Before controlled enforcement, cohort-specific switch semantics must identify the sole active enforcement authority for each cohort/action; no user gains access merely because one competing evaluator allowed. Compatibility adapters may preserve legacy behavior temporarily only with explicit mapping, audit, cohort, rollback, and final-removal criteria. Rollback may disable the canonical evaluator during controlled migration, but must retain audit evidence and must not restore cross-tenant or Platform Admin tenant-work access. Additive structures and historical evidence remain; authorization switching must not require destructive data rollback.

## Consequences

The model gives Basic Experts a consistent assigned-work boundary while enabling approved Organization Admin oversight without fake assignment. It requires certified parent lineage, centralized authorization evaluation, collection filtering, explicit direct-shipment responsibility, migration evidence, and eventual retirement of legacy role bypasses.

## Risks

- A parent path that is not tenant-consistent can leak work across tenants.
- Treating creator, eligibility, WorkItem, or OIP assignment as root authority would create unintended access.
- Collection metadata can disclose unassigned work even when detail routes are protected.
- Direct shipments and project-only execution require explicit handling; inferred authorization is unsafe.
- Compatibility mapping can preserve legacy overreach unless cohort and exit controls are enforced.

## Rejected alternatives

- **Tenant-wide Basic Expert operational reads:** rejected because membership and broad permission do not establish assigned work.
- **Copy root assignee to every child:** rejected because copied state drifts on reassignment and obscures lineage.
- **Generic multi-participant assignment now:** rejected under YAGNI; current evidence supports a primary assignee.
- **Treat WorkItem or OIP assignee as a new root:** rejected without a separate explicit decision.
- **Treat `role=admin` as Platform or tenant-work authority:** rejected by ADR-042, MT-0, and Admin multi-tenant security.
- **Use client-selected tenant/root identifiers:** rejected because they are not authoritative evidence.

## Open follow-up decisions

1. Project-only execution root and lineage model.
2. Any independent WorkItem authorization model.
3. Any independent OIP lineage/assignment model.
4. Generic multi-participant work model if a real workflow requires it.
5. Exact delegated Expert operational actions and high-risk verification/correction/override governance.
6. Broader CRM, delegated reporting, economics, and legacy `business_expert` scoring successor decisions retained by ADR-042 and their companion decisions.

## Implementation prerequisites

Before implementation authorization: approve the `BASIC_EXPERT_INTRINSIC_ACTION_MATRIX`, `CERTIFIED_ROOT_CHILD_LINEAGE_MATRIX`, and `ORGANIZATION_ADMIN_OVERSIGHT_MATRIX`; define Direct Shipment responsibility representation; define centralized effective work-relationship evaluation; identify all detail and collection surfaces; prove tenant ownership and lineage data quality; define assignment/reassignment, lineage-failure, and security-denial audit records; design reassignment/cache/concurrency behavior; establish legacy compatibility mapping, observational shadow evaluation, cohort-specific switch semantics, rollback controls, and direct backend/API E2E evidence plans. Any schema/data migration remains subject to ADR-006, ADR-011, explicit execution, sole-head, rollback, and PostgreSQL evidence gates.

## Exit criteria for legacy assigned-work fallback removal

Legacy fallback may be removed only after: (1) every enabled root has a certified work-relationship basis or is safely excluded; (2) all enabled children have proven tenant-consistent lineage; (3) collection, count, export, and cache filtering is certified; (4) root reassignment revokes prior access immediately; (5) Organization Admin oversight is explicit and tenant-bound; (6) no Platform Admin or `role=admin` fallback establishes tenant work authority; (7) audit/security-denial evidence is certified; (8) shadow and direct backend/API E2E scenarios pass without unresolved discrepancy; and (9) Architecture, Security, Product, and Operations owners approve fallback retirement.

## Relationship to existing ADRs and contracts

- **ADR-042:** parent decision. It owns personas, membership/capability separation, and governed capability principles; this ADR owns work relationship, root assignment, inherited child access, and assigned-work collection filtering.
- **ADR-037:** remains authoritative for Basic Expert request-parented CRM context; this ADR does not broaden CRM.
- **ADR-017, ADR-018, ADR-019, ADR-030, ADR-031, ADR-034, ADR-035:** remain authoritative for their Project, execution, event, document, OIP, lineage, and logistics scopes; this ADR adds no implementation change to them.
- **ADR-006 and ADR-011:** migration and execution controls remain additive and explicit.
- **MT-0, Admin multi-tenant security, and the Forwarder Architecture Baseline:** remain mandatory constraints and are not replaced.

## Status history

- 2026-08-30: PROPOSED — formal companion draft for owner review. It is not implementation authorization.
- 2026-08-30: ACCEPTED — Product Owner accepted the assigned-work authorization and operational-lineage architecture following final architecture assurance. Acceptance does not authorize implementation, schema/data changes, migration, deployment, backfill, permission changes, or production changes.
