# ADR-043 authorization implementation design package

- Status: design baseline for later separately authorized implementation
- Date: 2026-08-30
- Governing decisions: ADR-042 and ADR-043 (ACCEPTED); ADR-037 remains authoritative for request-parented CRM.
- Scope: documentation only. This package creates no permission, schema, data, migration, or runtime change.

## 1. Baseline and current-state inventory

HEAD is `7678ce5f1e5d2c61a74745df3b002b53d44a29dd` (`docs(architecture): accept assigned-work authorization ADR`). ADR-042 and ADR-043 are ACCEPTED; ADR-037 is unchanged. The repository currently has unrelated dirty/untracked material; it is outside this package.

The current application has useful tenant and permission controls, but not the accepted single evaluator. `backend/services/operational_service.py` resolves exactly one active membership in `_membership_for_user` and checks membership permission keys in `require_permission`. `backend/services/admin_authorization_service.py` independently resolves canonical authority and one membership, but still admits legacy `role == "admin"` to an organization-admin route. Expert request list/detail/message/quote surfaces (`backend/routes/expert_console.py`, `backend/services/expert_request_list_service.py`, `backend/services/expert_request_detail_service.py`, `backend/services/message_service.py`, `backend/services/quote_service.py`) use `ShipmentRequest.assigned_to`; their direct assignee check is the only current root-like authorization evidence.

| Surface/domain | Current route/service evidence | Current enforcement and consequence | Target disposition |
|---|---|---|---|
| Request list/detail/messages/quote/status | `expert_console.py`; `expert_request_*_service.py`; `message_service.py`; `quote_service.py` | List filters Expert by `ShipmentRequest.assigned_to`; detail/action checks are fragmented; legacy role paths exist | request-root assigned scope; matrix rows below |
| Assignment/referral | `assignment_service.py`, `referral_service.py`, `assignment_engine.py` | assignment membership checks exist; legacy role/scoring (`business_expert`) participates | Organization Admin assignment management; scoring is not authorization |
| OperationalShipment/direct shipment | `operational_service.py:create_direct`; `operational_models.py:OperationalShipment` | one membership plus permission; no direct-root assignee field | direct root requires additive responsibility design |
| WorkItem/routes/checkpoints/milestones/events/execution | `operations.py`, `route_orchestration_service.py`, `operational_execution_service.py` | tenant permission checks; resources relate to shipment but no unified root proof | inherit only through certified shipment lineage |
| Documents/readiness/execution units/exceptions | `case_documents.py`, `document_readiness_service.py`, `execution_unit_service.py`, `route_orchestration_service.py` | permission/tenant checks; no assigned-work evaluator | certified lineage or fail closed |
| CRM/customer projection | `crm.py`, `crm_*_service.py` | legacy `business_expert` role guards; request assignment appears in projection services | ADR-037 only; no direct-shipment CRM |
| OIP/project configuration/monitoring/dashboard/report/export | `oip_service.py`, `project_configuration_service.py`, `monitoring.py`, `admin_report_*` | tenant-wide membership permissions or legacy roles; no root proof | not intrinsic; follow-up, Admin, or governed oversight only |
| Logistics selectors | `expert_scope_service.py`, `logistics_network_service.py` | `logistics_point.read` is automatically provisioned to legacy Expert roles | conditional purpose-bounded selector, never broad Basic Expert baseline |
| User/work management | `user_management.py`, `user_service.py`, `admin_authorization_service.py` | authority/membership plus legacy admin compatibility | Organization Admin oversight with explicit governed capability |

## 2. Normative evaluation contract

Every protected operation must conceptually call `authorize_work_action(actor, resource, action)` at execution time:

1. resolve active authenticated identity and canonical authority;
2. derive exactly one active tenant membership where tenant work applies; missing, multiple, inactive, or client-selected context denies;
3. prove resource tenant ownership before disclosure;
4. resolve the one resource-type-declared lineage and root; do not try alternatives;
5. prove current root work relationship, or the separately permitted Organization Admin oversight category;
6. classify action as intrinsic, governed capability, high-risk, admin-only, CRM-only, follow-up, legacy-only, or deny;
7. evaluate workflow/business invariant; then allow.

Failures are non-disclosing after identity/tenant/resource checks. Audit hooks record actor, canonical tenant, resource type/public identity where safe, action, decision, denial reason class, root/lineage version, membership, correlation ID, and policy/evaluator version. Client organization, root, and parent identifiers are input locators only, never proof.

Collection support is `authorized_scope(actor, resource_type, action)`: compose root/oversight predicates into SQL before pagination, count, totals, search, autocomplete, aggregate, export-job creation, cache materialization, or serialization. Loading a tenant-wide result and filtering in Python is prohibited.

## 3. BASIC_EXPERT_INTRINSIC_ACTION_MATRIX

`BASIC_EXPERT_BASELINE_V1 = []`. The following are normative classifications; an intrinsic row becomes usable only after an implementation maps it at a backend enforcement point and certifies the stated E2E cases. `SR` means current assigned `ShipmentRequest`; `OS-SR` means accepted-quote shipment through SR; `OS-D` means direct shipment through its future primary-responsible-Expert relationship.

| Domain/action | Current endpoint/service | Target classification | Root / lineage / state | Tenant and capability | Effect/disclosure | E2E + / - | Migration note |
|---|---|---|---|---|---|---|---|
| Request list/detail assigned work | expert-console request APIs; `expert_request_*` | INTRINSIC_ASSIGNED_WORK_ACTION | SR; current `assigned_to`; request state allows read | exact membership; no baseline permission | read only; list must root-filter | assigned / same-tenant unassigned hidden | replace scattered assignee checks |
| Request message on assigned request | `message_service.py` | INTRINSIC_ASSIGNED_WORK_ACTION | SR; current assignment; permitted conversation state | exact membership | creates message/audit; no foreign existence | assignee allowed / reassigned expert denied | execution-time evaluator |
| Submit/update quote on assigned request | `quote_service.py` | INTRINSIC_ASSIGNED_WORK_ACTION | SR; current assignment; quote lifecycle | exact membership | commercial workflow side effect | assigned eligible / unassigned denied | not pricing/economics approval |
| Ordinary request status/progress transition | expert-console request routes | INTRINSIC_ASSIGNED_WORK_ACTION | SR; allowed request transition | exact membership | state/audit | allowed transition / invalid state denied explicit | map each transition before build |
| Read request-parented customer projection | ADR-037 services | CRM_ADR_037_ONLY | SR; ADR-037 contract | exact membership and ADR-037 condition | minimal read-only CRM disclosure | qualifying request / direct shipment denied | no broad CRM/list/search |
| Read OS, route, tracking, document, execution child | operations/execution/doc services | INTRINSIC_ASSIGNED_WORK_ACTION only where ordinary read is approved | OS-SR or OS-D; certified child lineage; ordinary state | exact membership; no broad permission | bounded read | assigned root / broken lineage non-disclosing deny | each resource requires lineage certification |
| Report ordinary checkpoint/event | route/execution services | INTRINSIC_ASSIGNED_WORK_ACTION only if action matrix maps exact action | OS root; child lineage; reportable state | exact membership | operational event/audit | assigned root / state or lineage deny | `checkpoint.report` is not implicit |
| Create direct shipment | `create_direct` | CAPABILITY_REQUIRED | OS-D created only with same transaction primary assignment | exact membership + governed create capability | creates root/audit | authorized creator assignment / absent responsibility denied | additive model required |
| Route planning/route-leg change | route orchestration | CAPABILITY_REQUIRED | certified OS root; allowed route state | exact membership + explicit capability | operational write | governed grant / ordinary Expert deny | not intrinsic by default |
| WorkItem read/manage | `operations.py`; `operational_service.py` | FOLLOW_UP_DECISION_REQUIRED | no independent WorkItem root; may inherit only certified OS lineage | exact membership + later action policy | disclosure/write | certified future matrix / current assignee insufficient | current `assignee_user_id` never root |
| OIP read/manage | `oip_service.py` | FOLLOW_UP_DECISION_REQUIRED | no independent OIP root | exact membership + later policy | queue disclosure/write | deny Basic Expert pending decision | OIP assignee never root |
| Document readiness manage, exception resolve, milestone verify/correct | readiness/route services | HIGH_RISK_CAPABILITY_REQUIRED | certified OS root and explicit workflow | exact membership + high-risk capability | correction/override/audit | explicit grant / ordinary Expert deny | ADR-042 high-risk governance |
| Economics, reports, dashboards, exports | economics/admin report/monitoring | HIGH_RISK_CAPABILITY_REQUIRED or ORG_ADMIN_OVERSIGHT_ONLY | no Expert intrinsic root path | explicit capability + approved companion decision | broad/financial disclosure | approved admin / Expert deny | no reporting delegation decided |
| Assignment/reassignment/referral | assignment/referral services | ORG_ADMIN_OVERSIGHT_ONLY | root management | Organization Admin capability | changes current access/audit | authorized admin / Expert deny | not workflow intrinsic |
| User/membership/config/reference management | admin/user/project/logistics services | ADMIN_ONLY or ORG_ADMIN_OVERSIGHT_ONLY | no work root | explicit managed category/capability | tenant-wide effect | appropriate authority / Expert deny | platform global remains Platform-only |
| logistics selector | logistics network services | CAPABILITY_REQUIRED | only within already-authorized work purpose | exact membership + conditional `logistics_point.read` | selector disclosure | bounded lookup / tenant-wide browse denied | remove legacy automatic baseline |
| Legacy role-only CRM/monitoring paths | `crm.py`, `monitoring.py`, `security.py` | LEGACY_ONLY | none | legacy role guard | broad disclosure risk | shadow mismatch captured | retire; no canonical allow |

## 4. CERTIFIED_ROOT_CHILD_LINEAGE_MATRIX

`CERTIFIED_NOW` means schema relationships can prove the stated tenant/root traversal but current authorization still does not enforce it. Every row retains a same-tenant invariant at every persisted edge. Orphan, null-required, cross-tenant, ambiguous, or multiple-root lineage is `DENY_NON_DISCLOSING`; reassignment changes all descendant access immediately.

| Resource | Tenant ownership / one canonical parent | Canonical root and assignment proof | Current status / implementation evidence | Required E2E |
|---|---|---|---|---|
| ShipmentRequest | `operational_organization_id`; no parent | SR; `assigned_to` plus active exact membership | CERTIFIED_NOW; `models.py`, expert request services | assigned/unassigned/foreign/multiple membership |
| Accepted-quote OperationalShipment | `organization_id`; `shipment_request_id` (and accepted quote) | SR; request `assigned_to` | CERTIFIED_NOW subject to data-quality certification; `OperationalShipment` source check | request shipment / broken or cross-tenant link |
| Direct OperationalShipment | `organization_id`; no request parent | OS-D; required future `primary_responsible_expert_id` | REQUIRES_MODEL_CHANGE; current model has creator only | assigned direct / absent or foreign responsible expert |
| RoutePlan | shipment through `operational_shipment_id` | inherited OS root | CERTIFIED_NOW | shipment reassignment / forged plan |
| RouteLeg | RoutePlan through `route_plan_id` | inherited OS root | CERTIFIED_NOW | leg-plan-shipment tenant consistency |
| Checkpoint | declared shipment/route relation in operational models | inherited OS root | REQUIRES_MODEL_CHANGE if any active shape lacks one unambiguous shipment edge | orphan/checkpoint alternate parent deny |
| Milestone | `organization_id`, `operational_shipment_id`; route/checkpoint relation | inherited OS root | CERTIFIED_NOW where OS FK is non-null | milestone report / conflicting route relationship |
| Tracking/transport units/current locations | operational organization; tracking/unit parent edges | SR or OS-D only after declared shipment edge | REQUIRES_MODEL_CHANGE/POLICY_DECISION; current tracking may be request-oriented | tracking from assigned request / detached tracking deny |
| OperationalWorkItem | `organization_id`, `operational_shipment_id` | inherited OS root only | CERTIFIED_NOW for shipment-linked rows; `assignee_user_id` ignored | work item child / standalone work item deny |
| Document readiness/requirements | `organization_id`, `operational_shipment_id` | inherited OS root | CERTIFIED_NOW | document read / orphan deny |
| Case document/artifact | case/request/document relationship varies | SR only when ADR-037/accepted document contract declares it; otherwise no inheritance | REQUIRES_POLICY_DECISION | request artifact / direct shipment CRM deny |
| ExecutionUnit/external reference | `organization_id`, `operational_shipment_id` | inherited OS root | CERTIFIED_NOW | unit/event child and forged shipment |
| Operational event/execution | organization plus shipment/execution-unit relation | inherited OS root only through declared shipment path | CERTIFIED_NOW when FK present; otherwise DENY | event child / stale/reassigned actor |
| Route exception | `organization_id`, `operational_shipment_id` | inherited OS root | CERTIFIED_NOW | read vs high-risk resolution |
| OIP situation/fact/signal | `organization_id`, source polymorphism/assignee | none currently | NOT_ELIGIBLE_FOR_INHERITANCE pending separate OIP decision | Basic Expert deny |
| Project-only configuration/execution | project organization only | none | NOT_ELIGIBLE_FOR_INHERITANCE | Basic Expert fail closed |

## 5. ORGANIZATION_ADMIN_OVERSIGHT_MATRIX

Organization Admin is tenant-bound oversight, never implicit assignment. Authority alone supplies no operational write. `Allowed` below always means exact active tenant membership, category capability, audit, and operation-time policy; `Prohibited` means deny even with tenant membership absent a new accepted decision.

| Category/action | Target | Capability / companion decision | Audit and E2E |
|---|---|---|---|
| TENANT_OPERATIONAL_READ_OVERSIGHT: operational lists/details | Allowed | explicit `operational_shipment.read` oversight grant | actor/tenant/filter decision; no foreign tenant |
| ASSIGNMENT_MANAGEMENT: assign/reassign/referral | Allowed | explicit assignment capability | old/new assignee, reason, correlation; A-to-B race |
| TENANT_OPERATIONAL_WRITE: ordinary governed operation | Allowed only per action | explicit action capability and workflow state | before/after/version; no blanket write |
| REPORTING/EXPORT | FOLLOW_UP_DECISION_REQUIRED | reporting/export companion ADR | output scope, counts, export metadata non-disclosure |
| USER_MANAGEMENT/CONFIGURATION/REFERENCE_DATA | Allowed only defined category | explicit managed capability | tenant scope, immutable admin audit |
| CRM | FOLLOW_UP_DECISION_REQUIRED | ADR-042 companion CRM decision; ADR-037 is not admin broadening | customer disclosure tests |
| ECONOMICS | Prohibited | separate economics governance | deny and audit high-value attempt |
| VERIFICATION/CORRECTION/OVERRIDE/HIGH_RISK_OPERATION | Prohibited unless later accepted | high-risk capability and companion decision | reason/provenance/two-party controls if specified |
| PLATFORM_ONLY global governance/diagnostics | Prohibited | PLATFORM_ADMIN design only | Platform without membership never gains tenant work |

## 6. Permission semantic normalization and legacy map

| Existing key/family | Semantic target | Notes |
|---|---|---|
| `logistics_point.read` | FOLLOW_UP_DECISION / conditional assigned-scope selector | currently legacy Expert baseline in `expert_scope_service.py`; no tenant-wide browse |
| `operational_shipment.read`, `route_plan.read`, `route_leg.*`, `checkpoint.read/report`, `milestone_event.create`, `operational_event.create`, `operational_execution.read` | ASSIGNED_SCOPE_ACTION when exact action matrix permits; otherwise TENANT_OVERSIGHT_ACTION | current permissions alone are insufficient |
| `work_item.*`, `oip.*` | FOLLOW_UP_DECISION | no independent assignee/root |
| `document_readiness.*`, `execution_unit.*`, `route_exception.read` | ASSIGNED_SCOPE_ACTION only through certified OS lineage | manage/resolve can be HIGH_RISK_ACTION |
| `economics.*`, `checkpoint.verify`, `milestone.correct` | HIGH_RISK_ACTION | never Basic Expert intrinsic |
| assignment/referral/manage users | ADMIN_ACTION / TENANT_OVERSIGHT_ACTION | explicit Organization Admin category only |
| reporting/export/monitoring | FOLLOW_UP_DECISION | no implicit delegation |
| CRM keys/legacy `business_expert` role guards | LEGACY_AMBIGUOUS / CRM_ADR_037_ONLY | retain ADR-037 narrow projection only |

Legacy paths: `security.py` role hierarchy; `crm.py` uses `business_expert`; `monitoring.py` uses `supervisor`; `admin_authorization_service.py` accepts legacy `role=admin`; assignment/referral use legacy expert/business_expert eligibility. For each, the compatibility adapter maps legacy decision and canonical decision to an audit-only shadow record. The controlled cohort has exactly one active evaluator. `legacy_allow OR canonical_allow` is prohibited. Cutover requires lineage/data certification, no unresolved shadow discrepancy, direct API/E2E pass, owner approval, and rollback that disables canonical enforcement without restoring cross-tenant or Platform tenant-work access. Final removal requires all enabled resources and cohorts to meet ADR-043 exit criteria.

## 7. Direct Shipment responsibility and reassignment design

Current `OperationalShipment` has `organization_id`, `source_type`, `shipment_request_id`, and `created_by_user_id`, but no responsible Expert. Creator identity cannot be used as authorization. The minimum additive future model is `primary_responsible_expert_id` (nullable only for non-ordinary/direct legacy rows) with a composite same-tenant integrity relationship to an active membership, plus `assigned_at`, `assigned_by_user_id`, `assignment_reason`, and an immutable assignment audit stream. Creation of an ordinary direct shipment atomically validates tenant-active responsible Expert and writes root plus audit; reassignment locks/version-checks the root, records old/new responsibility and correlation ID, then commits. No guessed backfill: existing direct rows are certified, explicitly assigned through a later approved process, or excluded/denied to Basic Expert. Rollback removes new enforcement only, never audit/data or tenant boundaries.

For A-to-B reassignment, authorization and mutation use the same transaction/row version where current responsibility is required. A stale request, cached list, cached authorization, long-lived token, or previously discovered child ID cannot pass a later backend evaluator. Cache keys include actor, tenant, root-assignment version, policy version, and scope; reassignment invalidates root/child scope materializations. Children inherit B immediately only through the certified root; no child grant is copied. Audit includes actor, tenant, root, old/new assignee, reason, timestamp, correlation/request ID, and result.

## 8. Data-quality, migration readiness, and E2E certification

Read-only certification queries must count and sample: tenant-null/quarantined resources; parent-child tenant mismatches; request-to-shipment source-shape violations; children without their declared parent; competing parent/root links; direct shipments with no valid responsible membership; inactive/ambiguous memberships; legacy role/authority mismatches; permission distribution; and rows whose lineage cannot be resolved. Risks are **BLOCKING** for cross-tenant/ambiguous/orphan lineage and direct rows selected for an Expert cohort without responsibility; **MUST_FIX_BEFORE_COHORT** for incomplete coverage of enabled descendants and role/permission mapping; **OBSERVATIONAL** for shadow differences; **NON-BLOCKING** only for safely excluded/quarantined resources. No query implies a backfill rule.

Future E2E evidence must cover PLATFORM_ADMIN, ORGANIZATION_ADMIN, BASIC_EXPERT, Expert with conditional capability, no-membership Expert, multi-membership Expert, and `role=admin + authority=EXPERT`. For each root/child and list/count/search/export surface: assigned is ALLOW only at the stated action/state; unassigned same-tenant, foreign tenant, forged organization/root/parent, broken/competing lineage, hidden route/direct API, and stale A-after-B are DENY_NON_DISCLOSING or FAIL_CLOSED; invalid workflow is DENY_EXPLICIT. Cover request-derived and direct shipments, WorkItem, route/tracking/documents/execution, CRM/direct-shipment boundary, conditional logistics selector, high-risk actions, admin oversight, exports/jobs/caches, and concurrent mutation/reassignment. Evidence includes backend response, database/query-scope assertion, audit record, no side effect, and no metadata disclosure.

## 9. Phased implementation plan (not authorization)

| Phase | Likely modules / impact / exit |
|---|---|
| A evaluator foundation | `operational_service.py`, `admin_authorization_service.py`, tenancy/services; no schema initially; evaluator/audit contract and deny tests; exit: exact tenant/resource decision evidence |
| B Direct Shipment root | `operational_models.py`, `operational_service.py`, migration later; additive responsibility/audit, certification and rollback plan; exit: no enabled unassigned direct roots |
| C request integration | expert request/detail/message/quote services; replace fragmented checks in controlled cohort; exit: request E2E/shadow pass |
| D downstream lineage | operations/route/execution/document/unit services; schema only for unresolved edges; exit: each enabled child certified |
| E collection filtering | query services/reports/exports/cache; SQL predicates before pagination; exit: metadata non-disclosure E2E |
| F admin oversight | admin/user/assignment services; category capabilities and audit; exit: no blanket tenant write |
| G shadow evaluation | evaluator telemetry/audit only; no permissive composition; exit: discrepancy disposition |
| H cohort enforcement | cohort switch configuration; transaction/cache controls and rollback; exit: no stale authorization mutation |
| I E2E certification | backend/API and PostgreSQL evidence; exit: matrix complete, critical scenarios pass |
| J legacy retirement | security/CRM/monitoring/assignment compatibility paths; separately approved removal; exit: ADR-043 fallback criteria approved |

## 10. Assurance and owner decisions

Self-assurance against ADR-042, ADR-043, ADR-037, MT-0, the architecture baseline, and admin multi-tenant security: **PASS**. No CRITICAL, HIGH, or unresolved material MEDIUM design inconsistency remains. The package deliberately records ungoverned scopes as deny/follow-up rather than selecting new business policy.

**OWNER DECISION PACKAGE: NONE.** Open follow-up decisions are already explicitly retained by ADR-042/ADR-043 (project-only root, independent WorkItem/OIP policy, multi-participant work, CRM/reporting/economics/high-risk delegation, and scoring successor); this package neither decides nor blocks documentation of their fail-closed treatment.
