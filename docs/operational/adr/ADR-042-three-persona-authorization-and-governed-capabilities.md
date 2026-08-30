# ADR-042: Three-persona authorization and governed tenant capabilities

- Status: ACCEPTED
- Date: 2026-08-29
- Owners / decision authority: Product Owner (product direction); Architecture Owner; Security Owner; Operations Owner; CRM Domain Owner; Reporting/Monitoring Owner; Assignment/Referral Owner
- Affected domain: Platform authority, tenant authorization, OperationalMembership, governed capabilities, CRM, reporting, assignment/referral, legacy RBAC migration
- Decision traceability: Product Owner approval request, 2026-08-29; Product Owner acceptance of ADR-042, 2026-08-30; final architecture assurance: `ADR_042_ASSURANCE = READY_FOR_OWNER_ACCEPTANCE`; `docs/architecture/FORWARDER-ARCHITECTURE-BASELINE.md`; `docs/architecture/multi-tenant-architecture-contract.md` (MT-0); `docs/architecture/admin-multi-tenant-security.md`; ADR-037; ADR-041; ADR-033; ADR-006; ADR-011.

## Context

Forwarderet currently has global, hierarchical legacy roles (`admin`, `crm_manager`, `supervisor`, `business_expert`, `expert`) alongside `OperationalMembership`. The role hierarchy conflates platform authority, organization administration, operational work, CRM access, reporting, assignment behavior, and business ranking. Legacy membership resolution requires exactly one active membership in an active organization at runtime, but the database can represent multiple active memberships. The existing global `role=admin` is explicitly not proof of Platform Admin or organization authority.

MT-0 makes backend-derived tenant context, fail-closed membership resolution, tenant fencing, and non-authoritative frontend visibility mandatory. ADR-037 accepts only a narrow request-parented CRM customer-context projection for a Basic Expert. ADR-041 already separates Platform Admin global governance from organization adoption/operation and requires Platform Admin to be membership-free by default. Existing assignment, referral, workload, CRM, report, and monitoring behavior has legacy and, in places, unproven tenant ownership; assignment/referral does not establish data ownership.

## Problem statement

Forwarderet needs a canonical authorization direction that makes platform governance, organization administration, and ordinary operational expertise intelligible and least-privilege while preserving tenant security. It must decouple authorization from business eligibility, routing preference, and workflow state without silently changing approved behavior or guessing privileges during migration.

This ADR defines the target authorization architecture and migration gates. It does not authorize code, schema, data, deployment, permission, or production changes.

## Current state

- Legacy global role rank is used by multiple surfaces and is not a safe tenant or platform boundary.
- `OperationalMembership` is the tenant-context evidence for tenant staff; client-supplied organization identifiers are not authoritative.
- Existing platform/organization administration separation is documented, but canonical three-persona authority and capability governance are not yet implemented.
- CRM access for Basic Experts is bounded by ADR-037; broader CRM access is not approved by an Accepted CRM authorization decision.
- Legacy supervisor monitoring and `business_expert` assignment/scoring behavior are not a reusable authorization contract.

## Decision

Adopt the following target conceptual model:

```text
Authority:       PLATFORM_ADMIN | ORGANIZATION_ADMIN | EXPERT
Tenant context:  OperationalMembership
Capability:      governed permission / capability grant
Business scope:  specialization, assignment, workload, workflow state
```

Authority determines who an actor is. Membership determines the one valid tenant runtime context. Capability determines which governed action is permitted inside that tenant. Business attributes, assignment state, capacity, specialization, and workflow state determine eligibility, ownership, and prioritization when they are business rules. Permissions must not encode business scoring preference. UI visibility is UX only and is never a security boundary.

`PLATFORM_ADMIN`, `ORGANIZATION_ADMIN`, and `EXPERT` are the canonical authority personas. Authority is not inferred from legacy role, UI route, membership count, client input, or a capability grant. This accepted ADR supplies no implementation authority; implementation requires separately authorized prerequisites and scope.

## Authority model

| Authority | Required runtime tenant context | Scope | Automatic tenant/operational authority |
| --- | --- | --- | --- |
| `PLATFORM_ADMIN` | None by default | Platform control plane and approved global governance | None |
| `ORGANIZATION_ADMIN` | Exactly one active `OperationalMembership` in one active organization | That organization only | Only explicit organization-admin contract and separately governed capabilities |
| `EXPERT` | Exactly one active `OperationalMembership` in one active organization | Authorized tenant work only | Narrow baseline only; no administrative surface |

No persona hierarchy implies another persona's scope. A Platform Admin does not become an operational tenant actor by platform authority. An Organization Admin does not gain platform diagnostics, global governance, arbitrary high-risk powers, or every operational mutation. An Expert is not made an administrator by specialization, assignment, reporting, or CRM capability.

## Membership and tenant-context rules

- Organization Admin and Expert runtime actions require exactly one active membership in an active organization.
- The server resolves organization context from authoritative current authorization evidence. Body, path, query, header, host, session UI state, or frontend selector cannot select or broaden it.
- Missing, inactive, ambiguous, conflicting, or multiple active memberships fail closed. A valid permission never bypasses tenant fencing.
- Platform Admin is membership-free by default. A future explicit support/break-glass tenant access design requires a separately approved decision, audit, and non-disclosure contract.
- Tenant ownership must be proven before lookup, disclosure, mutation, audit side effect, cache use, export, background work, or storage access. Foreign identifiers fail non-disclosively where required.

## Capability model

Capabilities are explicit, tenant-scoped, governed grants. They are not raw unrestricted permission editing and do not alter authority identity. The permitted design categories include narrowly defined operational work, approved CRM, approved tenant reporting, and approved logistics/reference read capability. Each capability must have a named purpose, resource/action scope, tenant scope, grant authority, prohibited combinations, expiry/review rule where applicable, and validation tests.

The Basic Expert baseline remains deliberately narrow and must not include standalone CRM workspace, organization-wide reporting, finance, high-risk correction, verification, override, or administrative authority by default. The exact baseline bundle is an open decision; absence of an explicit grant denies access.

## Platform Admin contract

Platform Admin administers Forwarderet as a platform and may manage organizations, platform/global reference and governance data, global logistics governance, platform configuration, and approved platform diagnostics: health, logs, system/database metrics, and platform/global analytics. These actions require no organization membership.

Platform Admin does not automatically receive tenant membership, tenant permissions, tenant CRM/workload access, tenant operational access, or the ability to use tenant data merely because it is platform authority. Platform and organization governance remain separate.

## Organization Admin contract

An Organization Admin belongs to exactly one active organization at runtime and acts only in that server-derived tenant. Subject to explicit tenant permissions and ownership certification, it may manage tenant users; activate/deactivate tenant users; supervise Experts; view tenant-fenced requests/workload; assign or reassign work under approved policy; manage organization configuration and logistics adoption/configuration; view tenant-fenced dashboards/reports; perform approved CRM oversight; and grant the allowed subset of Expert capabilities.

Organization Admin must not access Platform Admin diagnostics or global governance, grant platform permissions, bypass tenant resolution, grant arbitrary high-risk powers, or receive all operational mutation powers automatically. High-risk financial, verification, correction, and override actions remain separately governed.

## Expert contract

Every ordinary organization user converges on `EXPERT` authority with exactly one active OperationalMembership. An Expert has no administrative surface, sees only tenant-authorized and workflow-authorized data, and works only on assigned/otherwise authorized requests. Its access derives from the narrow baseline plus explicit governed capabilities. It does not gain standalone CRM, organization-wide reporting, finance, high-risk correction, override, or administration by membership or legacy identity.

Legacy `crm_manager`, `supervisor`, and `business_expert` behavior must be decomposed into one or more of capability, specialization/business attribute, assignment/business scoring rule, workflow ownership, and reporting scope. No replacement capability may be inferred just because a legacy role previously admitted an endpoint.

## CRM treatment

ADR-037 remains authoritative for Basic Expert request-parented customer-context access: no standalone CRM workspace, customer list/search/write authority, or broader CRM access through same-organization membership. Basic Expert behavior must continue to use the ADR-037 parent authorization and tenant rules.

The Product Owner direction permits selected Experts to receive a future broader, tenant-fenced CRM capability and Organization Admin to receive future tenant CRM oversight. Such access must be explicitly capability-governed, audited, least-privilege, and tested for negative cross-tenant behavior. It must never broaden from membership alone.

This ADR does **not** amend or supersede ADR-037; ADR-037's field/API/parent-authorization contract remains authoritative. A companion CRM authorization ADR, accepted by the CRM, Security, Product, and Architecture owners, is required before implementing broader CRM capability or Organization Admin CRM oversight. That ADR must define exact permission granularity, read/write/search/list surfaces, field/projection policy, grant/revoke governance, non-disclosure behavior, and ADR-037 compatibility.

## Reporting and monitoring separation

Platform diagnostics—system health, database metrics, logs, platform/global analytics, and system-wide monitoring—belong to Platform Admin only unless a future explicit support authority is accepted.

Tenant request counts, workload, assignment state, Expert performance, operational KPIs, and allowed tenant business/CRM KPIs are organization reporting. Organization Admin has the default tenant-fenced reporting authority only where ownership and authorization are certified. A delegated Expert reporting capability is optional and requires an explicit approved policy, tenant fencing, output filtering, and negative tests. Legacy supervisor monitoring is not inherited wholesale by either Organization Admin or Expert.

## Assignment and referral treatment

Authorization and business ranking are separate. Assignment eligibility uses governed business scope such as active Expert status, specialization, capacity, workload, and policy. The right to assign/reassign belongs to Organization Admin or an explicitly delegated assignment capability. Access to an assigned request follows workflow ownership/assignment rules. Scoring preference is an explicit business scoring factor, not an authorization permission.

The legacy `business_expert` scoring advantage must not silently disappear. Its exact successor is an open follow-up decision owned by the Assignment/Referral and Product owners. No migration, backfill, or implementation may substitute a guessed capability or remove the advantage before that decision is accepted. Existing assignment/referral data must remain subject to MT-0 ownership certification; assignment/referral never proves tenant ownership.

## Legacy role compatibility policy

- The legacy `role` column remains during the first migration phase and is compatibility-only.
- `role=admin` never proves `PLATFORM_ADMIN`; any legacy-admin mapping is an explicit, controlled, human-owned, recorded governance approval, evidenced and fail-closed. It is not inferred implementation evidence.
- `crm_manager`, `supervisor`, and `business_expert` map only to `EXPERT` authority plus individually approved capabilities/business attributes/workflow policies where mapping evidence exists.
- Ambiguous users retain no inferred elevated authority and fail closed.
- Compatibility dual-read may preserve legacy behavior temporarily only behind explicit mapping, audit, cohort, and rollback controls. It must not weaken tenant fencing or create a new default grant.

## Capability grant governance and audit requirements

Organization Admin may grant/revoke only an architecture-approved, tenant-scoped subset of Expert capabilities. It cannot grant platform diagnostics, global governance, cross-tenant authority, unrestricted financial approval, unrestricted correction/verification/override powers, or architecture-reserved capabilities. Exact high-risk grant authority is an open decision.

Every governed capability `GRANT` and `REVOKE` requires an immutable or append-oriented auditable record. The minimum mandatory record contains: actor identity; actor authority; organization/tenant; target user; each capability added or removed; operation type (`GRANT` or `REVOKE`); timestamp; reason, approval, or provenance; resulting effective governed capability set; and correlation/request identifier where the architecture audit pattern requires it. For a bulk change, the evidence must be sufficient per target and per capability, or use an explicitly governed batch record that remains fully reconstructable to that same detail. This minimum grant/revoke evidence is mandatory.

Expiry, mapping exceptions, effective-grant recomputation, and other consequential authorization events must also be auditable under the applicable architecture audit pattern. Audit data must itself be tenant/platform scoped, access-controlled, immutable or append-oriented for consequential changes, redacted where necessary, and retained under repository policy. Audit emission must not disclose foreign resources or turn a denied cross-tenant attempt into a side effect.

### Security-denial audit subset

Security-boundary denials require auditable evidence for attempted cross-tenant access; ambiguous or multiple-membership tenant resolution; Platform Admin attempting tenant authority; Organization Admin attempting platform-only authority; denied capability grant/revoke escalation; a client-supplied tenant identifier attempting to broaden scope; and use of legacy compatibility fallback where audit is required during migration. Ordinary feature denials may follow existing operational logging policy; this does not reduce the mandatory security-boundary denial evidence.

## Security invariants

- Server-derived tenant context and exactly-one-active-membership rules remain authoritative for Organization Admin and Expert.
- Platform Admin is membership-free by default and receives no implicit tenant privilege.
- Missing/inactive/ambiguous membership, unknown authority, missing capability, or uncertified ownership fails closed.
- No client-selected organization authority, permission bypass of tenant fencing, cross-tenant lookup/disclosure, or frontend-only access control is permitted.
- Authorization precedes sensitive lookup, serialization, export, cache, notification, background job, and storage access; errors are non-disclosing where required.
- Permissions/capabilities grant only named actions in a valid tenant context; they cannot make an unowned or foreign record accessible.
- Legacy compatibility, role mapping, and backfill cannot weaken any invariant.

## Migration strategy

The required sequence is:

```text
DECIDE -> EXPAND -> VERIFY -> DUAL-READ / COMPATIBILITY -> CONTROLLED BACKFILL
-> SHADOW / E2E -> SWITCH -> REMOVE LEGACY FALLBACK -> CONTRACT SCHEMA LATER
```

First decide and record authority/capability matrices, open-policy owners, explicit legacy mapping evidence, data-ownership readiness, and rollout cohorts. Expand additively only after implementation authorization. Verify migration constraints and effective-grant calculation before compatibility use. Dual-read must compare legacy and target decisions without privilege guessing. Controlled backfill requires individual explicit mapping evidence; no automatic Platform Admin inference and no bulk capability grants without evidence. Shadow and E2E certification must precede switching. Keep the legacy role column until fallback exit criteria are met; contract/removal is a later, separately approved schema decision.

## Rollback and compatibility strategy

Each phase must be independently reversible at the application-routing/feature/cohort level while retaining audit and migration evidence. On mismatch, denial anomaly, ownership-certification failure, or security regression, disable the new path/cohort and restore the last certified compatibility behavior without broadening access. Rollback must preserve fail-closed membership resolution and must not reintroduce global or cross-tenant authority. Consequential audit/grant history is retained; destructive downgrade or removal is prohibited without an approved retention procedure.

## E2E certification requirements

Before any legacy fallback removal, the following backend/API authorization tests must pass. Frontend-hidden navigation is not sufficient evidence; each relevant case must exercise direct backend/API routes and inputs.

1. **Platform Admin without membership:** deny every tenant-scoped surface, including tenant operational shipment APIs; tenant request/workload APIs; tenant CRM/customer APIs; organization reporting; organization exports; organization administration; tenant logistics/configuration operations; and any tenant route requiring organization context. Platform authority alone must never establish tenant scope. Submit or manipulate an organization/tenant identifier through request input and confirm that it cannot establish or broaden tenant authority.
2. **Organization Admin with exactly one active membership:** permit only certified tenant-scoped authority, and explicitly deny platform-only surfaces: platform diagnostics; system logs; privileged system-health administration; database metrics; global/system monitoring; global governance mutation; platform master/reference governance not delegated to tenant administration; and cross-organization administration.
3. **Basic Expert.**
4. **Operational-capable Expert.**
5. **CRM-capable Expert,** only if the companion CRM ADR permits it.
6. **Reporting-capable Expert,** only if delegated reporting is approved.
7. **Economics-capable Expert.**
8. **Expert with no active membership:** fail closed.
9. **Expert with multiple active memberships:** fail closed.
10. **Legacy `role=admin` direct certification:** test `role=admin` + `authority=EXPERT` with no membership, with ambiguous/multiple active memberships, and with one membership during the compatibility phase. Platform authority is denied in all three cases unless persisted authority is `PLATFORM_ADMIN`. Any temporary tenant-admin compatibility for the one-membership case must be narrowly scoped and time-bounded; ambiguous/multiple membership fails closed.
11. **Cross-tenant negative attempts:** direct backend/API read, search, list, detail, mutation, report, export, cache, and referenced-ID attempts applicable to the implemented scope.

Evidence must cover effective grants; mandatory grant/revoke records; the security-denial audit subset; stale/expired grants where present; tenant ownership certification; non-disclosing failures; and no unauthorized side effects. Existing ADR-specific validation, migration, PostgreSQL, concurrency, and operational gates remain additive requirements.

## Consequences

The model creates a clear platform/organization/Expert boundary, reduces role-rank overreach, preserves least privilege, and makes future delegation reviewable. It introduces a governed capability catalogue, explicit legacy mapping work, more complete audit requirements, and multiple companion decisions before broad behavior can change. It deliberately prevents a quick role rename from masquerading as secure authorization simplification.

## Risks

- Legacy endpoint assumptions may conceal role-rank dependencies or unscoped ownership.
- Incorrect compatibility mapping could create privilege escalation or loss of essential work access.
- Broad CRM/reporting delegation can leak tenant or personal/commercial data if not narrowly specified.
- Removing `business_expert` rank before a scoring successor is accepted can change referral outcomes.
- Multi-membership data and unresolved ownership can make a superficially valid implementation unsafe.

These risks require fail-closed gates, explicit owners, cohort rollout, shadow comparison, and certification rather than inferred mapping.

## Rejected alternatives

- **Retain hierarchical legacy roles as canonical authority:** rejected because it conflates platform, tenant, business, and capability concerns.
- **Treat `role=admin` as Platform Admin:** rejected by MT-0 and the admin multi-tenant security contract; membership/global-role evidence is insufficient.
- **Make Organization Admin a universal tenant superuser:** rejected because high-risk operational/financial/verification/override actions need separate governance.
- **Use membership alone for CRM or reporting:** rejected because same-organization membership is not authorization for broad data access.
- **Use permissions for assignment scoring:** rejected because it hides business prioritization in authorization and cannot preserve/inspect the `business_expert` successor.
- **Remove or bulk-map legacy roles in the first phase:** rejected because privilege guessing and destructive migration violate the approved migration principle.
- **Rely on hidden navigation for security:** rejected because frontend visibility is not authoritative.

## Open follow-up decisions

1. Exact Basic Expert baseline capability bundle.
2. Exact business scoring successor for the legacy `business_expert` advantage.
3. Exact CRM capability granularity and Organization Admin CRM oversight contract (companion CRM ADR required).
4. Exact delegated Expert reporting policy, KPI/projection scope, and grant criteria.
5. Exact grant authority and controls for high-risk capabilities.
6. Exact capability catalogue, named permissions, expiry/review rules, and assignment delegation boundaries.
7. Any explicit Platform Admin support/break-glass tenant-access model.

These are not implementation defaults and must not be invented during delivery.

## Relationship to existing ADRs and contracts

- **ADR-037:** remains ACCEPTED and authoritative for Basic Expert request-parented CRM customer context. This ADR neither supersedes nor amends it; accepted broader CRM work needs a companion CRM authorization ADR.
- **ADR-041:** complemented. Its platform/global logistics governance and organization adoption separation remain intact; Platform Admin remains membership-free by default and Organization Admin remains tenant-fenced.
- **ADR-033:** complemented. Economics access stays separately permission-governed; no authority persona automatically grants economics capability.
- **ADR-006 and ADR-011:** migration must be additive and explicitly executed; no schema contract/removal occurs in the first phase.
- **MT-0 and admin multi-tenant security:** are mandatory security constraints, not replaced by this ADR.

## Implementation prerequisites

Before implementation authorization, the owners must approve or explicitly defer the open decisions with safe deny-by-default behavior; publish the authority/capability matrix; identify all affected endpoints/jobs/reports/exports; prove tenant ownership or quarantine; define authoritative effective-grant evaluation; define audit schema/retention; define explicit legacy mapping evidence and rollback cohorts; and approve validation/E2E evidence plans. Broader CRM implementation additionally requires the accepted companion CRM ADR. Any migration requires the existing additive, explicit-execution, sole-head, rollback, and PostgreSQL evidence gates.

## Exit criteria for removing legacy role fallback

Legacy role fallback may be removed only after: (1) canonical authority is set for every in-scope active identity with no ambiguity; (2) all capability/business/workflow mappings are explicit and approved; (3) no Platform Admin was inferred from `role=admin`; (4) affected data ownership is certified or safely excluded; (5) shadow comparison reports no unresolved authorization or business-scoring discrepancy; (6) grant/revoke audits and effective-grant controls are certified; (7) all required E2E scenarios pass, including cross-tenant and direct-backend negatives; (8) CRM/reporting/high-risk companion decisions are accepted where those behaviors are enabled; (9) rollback/cohort evidence is approved; and (10) Architecture, Security, Product, and Operations owners explicitly approve fallback retirement. Role-column schema contraction is a later separately approved ADR/migration decision.

## Supersedes / superseded by

- Supersedes: none.
- Complements: ADR-006, ADR-011, ADR-033, ADR-037, ADR-041, MT-0, and Admin multi-tenant security.
- Superseded by: none.

## Status history

- 2026-08-29: PROPOSED — formal draft created from Product Owner-approved direction. It is not implementation authorization and requires owner review/acceptance.
- 2026-08-30: ACCEPTED — Product Owner accepted the governing authorization direction following final architecture assurance. Acceptance does not authorize implementation, schema/data changes, migration, deployment, backfill, or production changes.
