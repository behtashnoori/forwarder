# Discovery — Operational Execution Foundation

- **Status:** Proposed
- **Date:** 2026-08-04
- **Candidate:** Release 1.9.0
- **Implementation authority:** NO
- **Final outcome:** READY FOR GOVERNANCE REVIEW

## 1. Repository baseline

Discovery ran on `feature/case-document-management-phase1a` at `a7814644b9d0981fb690b473c0aeb0efa10c4dad`, tracking `origin/feature/case-document-management-phase1a` and ahead by one commit. HEAD is the documentation-only administrator-managed Reference Data reconciliation. The tracked worktree was clean before this discovery; unrelated untracked `.codex/` and historical `release-v1.1.0` through `release-v1.7.0` directories were present and untouched.

Release 1.8.0 business work is committed: governance commits `58ca1e6` and `7a1d5b7`, implementation `7e333fe`, publication preparation `1a8c65e`, annotated tag `v1.8.0` (tag object `7d3f2aa`, peeled commit `1a8c65e`), then policy reconciliation `a781464`. Application baseline is 1.8.0 source; migration head is `20260811_project_configuration` after `20260810_logistics_network`. Repository evidence says Production remains 1.6.1 at `20260809_cargo_catalog_items`; Production was not accessed.

The supplied business premise records the 1.8.0 package as rejected/blocked by a separately governed fixed-credential security issue. Repository release documents otherwise describe the candidate as publication-prepared and the historical incident record as rotated/revoked with accepted history risk. Discovery does not reconcile or solve that security-track discrepancy: it records the package blocker as an external release gate, keeps domain design separate, and requires the eventual migration head to be known. No secret value was read or reproduced.

ADR-028 is Accepted and HEAD reconciles the repository to administrator-managed Reference Data: empty catalogs are valid; Admin UI is the population path; Seed/import is optional and never a deployment dependency.

Relevant accepted authorities reviewed include PDR-017; ADR-002/003/004/007/009/010/016/017/018/019/021/025/027/028; the 1.8.0 Slice Contract and RC/publication records; FDD-001; FDM-001; Decision Index; Capability Registry; Roadmap Matrix; and Evolution Map. ADR-020 is Proposed and is therefore a dependency, not accepted evidence authority.

## 2. Current operational maturity and reuse

The platform already executes route/checkpoint milestones and is materially beyond a blank foundation. `OperationalShipment`, active RoutePlan revisions, RouteLegs, Checkpoints, `Milestone`, report/correct/verify `MilestoneEvent`, route timeline reconciliation, overdue work items/exceptions, organization membership permissions, audit/outbox, and a responsive detail UI all exist with focused tests. Separately, `OperationalEvent` supplies an append-only ExecutionUnit timeline envelope.

The gap is semantic breadth and configuration lineage: existing milestones use a hard-coded route taxonomy and `planned/reported/verified` verification state rather than the proposed execution lifecycle; public API paths expose numeric IDs; event rows lack governed reason/location/evidence fields; exception behavior is route reconciliation with fixed type/severity; evidence has only Request-scoped case-document infrastructure; Project configuration does not initialize execution.

See the [domain matrix](operational-execution-domain-matrix.md) for model/migration/API/UI/test/FDD/Production/debt classification.

## 3. Scope options

| Dimension | A — Minimal execution | B — Balanced execution | C — Broad execution |
| --- | --- | --- | --- |
| Business value | Basic controlled lifecycle/history | Complete structured operational claim with reasons/evidence | End-to-end automation/visibility/analytics |
| Complexity | Medium because existing semantics still need repair | Medium-high but bounded by reusable models | Very high; multiple immature domains |
| Migration | Milestone lineage/lifecycle/events | A plus reason catalogs and evidence links | B plus automation/status/SLA/reporting infrastructure |
| Operational change | Manual initialize and commands | A plus structured delay/exception/evidence | Automated side effects, escalation, customer process |
| UI | Preview, milestones, timeline | A plus reason/evidence panels and progress strip | Dashboard, alerts, portal, workflow surfaces |
| Security | New command scopes | A plus evidence/reason authorization | Public visibility, notifications, escalation policies |
| Evidence value | Actor/time history only | Artifact-backed claims and completeness indicators | Enforced workflows and customer proof |
| Reporting readiness | Moderate | High-quality structured facts without reports | Reporting product included |
| Compatibility risk | Medium | Medium-high, controllable by opt-in/additive design | High |
| Governance burden | Lifecycle/event decisions | Lifecycle plus reasons/evidence | Cross-domain policy program |
| Recommended split | Could be 1.9.0 fallback | **Recommended 1.9.0** | Split into later evidence enforcement, automation, visibility, SLA/reporting releases |

## 4. Recommended domain and policies

Adopt bounded Option B. Extend existing `Milestone`; do not add a duplicate instance. Manual initialization is part of 1.9.0 because it is the explicit bridge from 1.8.0 configuration, provided preview/confirm is atomic, idempotent, opt-in, and refuses conflicts. Snapshot definition/type/point/sequence/targets while retaining source lineage.

Use PENDING, READY, IN_PROGRESS, COMPLETED, SKIPPED, CANCELLED, BLOCKED. Keep delay independent. Use explicit transitions in ADR-029, expected version, idempotency, actor and reason requirements, no generic state-machine framework, and no automatic Shipment status. Terminal states reopen only by a separately authorized superseding correction command.

Use append-oriented `MilestoneEvent` for specialized history and project accepted facts into ADR-019 `OperationalEvent` only under a defined mapping. Preserve original events, separate occurred/recorded time, require correction reason, and reverify corrected claims. Timeline and audit remain distinct.

Create separate administrator-managed DelayReason and ExceptionReason catalogs with immutable codes, active lifecycle, one primary reason, optional note, required start/occurred time, optional resolved time, and calculated duration. Add no rows automatically. Do not add severity, risk scoring, penalty, or escalation.

Evidence means proof, not a new file store. Link a permitted existing artifact to a milestone, event, or both; store context metadata/uploader/time/source and preserve the artifact owner. Current CaseDocumentFile is Request-scoped and numeric, while ADR-020's artifact/link architecture is only Proposed. Governance must accept/narrow that bridge before implementation. Evidence is indicated, not required.

## 5. Permission, API, and UI recommendations

Reuse OperationalMembership and service authorization with proposed read/manage/event create/correct/verify/evidence attach permissions. Resolve organization, Project, and Shipment before child lookup; use opaque IDs; return 404 across tenants; keep reporter/verifier separation where feasible; add no public/customer API.

Extend current `/api/operational-shipments` routes with an `/execution` projection and commands. Do not create a parallel v2 domain. Preserve numeric endpoints temporarily for compatibility, but use public IDs for all new normative resources.

The UI is a stacked Operational Execution section: Shipment/config source, not-initialized preview or current milestone, ordered milestones, timestamps/state commands, delay/exception, evidence, then immutable timeline/correction/verification. It is mobile-safe, Persian RTL, supported English LTR, uses governed selectors and optional notes, and includes no map, dashboard, or workflow designer.

## 6. Migration and security sequencing

No migration was created and `20260812_operational_execution` is not reserved. The fixed-credential remediation is a separate track and may create a 20260812 revision. Recommended discovery strategy is Option B: complete documentation without a migration, then create the 1.9.0 additive revision only after the security/business branch order and single Alembic head are known. Existing shipments receive no automatic rows or backfill; configuration/history is not mutated; catalogs remain empty; old APIs remain compatible.

## 7. Dashboard and analytics exclusion

Dashboards, BI, KPI screens, executive summaries, SLA analytics, delay charts, bottleneck reports, customer reporting, and predictive analytics are explicitly excluded and not started. Structured times, reasons, lineage, status, and evidence links make later reporting possible without authorizing a reporting feature.

## 8. Decisions and governance gate

D01–D21 are all **Proposed** in [PDR-018](PDR-018-operational-execution-foundation.md). None is accepted and implementation authority is NO.

| Gate | Result |
| --- | --- |
| Existing Operational Domain Reviewed | YES |
| Project Configuration Boundary | PROPOSED — PRESERVED |
| Operational Milestone Boundary | PROPOSED — REUSE EXISTING |
| Event History Boundary | PROPOSED — APPEND-ORIENTED |
| Delay vs Status Boundary | PROPOSED — INDEPENDENT CONDITION |
| Exception Boundary | PROPOSED — SEPARATE FROM ROUTE RECONCILIATION |
| Evidence Boundary | PROPOSED — LINK, NO FILE DUPLICATION |
| Initialization Policy Assessed | YES — MANUAL RECOMMENDED |
| Status Transitions Assessed | YES |
| Existing APIs Reuse Assessed | YES — EXTEND CURRENT FAMILY |
| Security Permissions Assessed | YES — PROPOSED |
| Tenant Isolation Assessed | YES — ORGANIZATION-FIRST/404 |
| Dashboard Excluded | YES |
| Reporting Excluded | YES |
| Migration Collision Risk Recorded | YES |
| PDR-018 Created | YES |
| ADR-029 Created | YES |
| 1.9.0 Slice Contract Created | YES |
| D01–D21 Prepared | YES — ALL PROPOSED |
| Implementation Authorized | NO |
| Ready for Governance Review | YES |

## 9. Documents and checks

Created PDR-018, ADR-029, the 1.9.0 Slice Contract, this discovery report, and the domain matrix. Minimally reconciled FDD-001, FDM-001, Decision Index, Capability Registry, Roadmap Matrix, Evolution Map, PDR-017 references, and the architecture handbook index.

Documentation checks cover strict UTF-8 decoding, heading/table structure, local Markdown links, Mermaid fence balance/structural review, identifier uniqueness, PDR/ADR/FDD/FDM terminology, migration warning, scope/exclusion alignment, implementation-authority denial, secret-pattern scan, `git diff --check`, and final Git status. Application tests were not run.

## 10. Governance closure note — 2026-08-04

Discovery is complete and superseded for authority by the [Release 1.9.0 Governance Closure](release-1.9.0-operational-execution-governance-closure.md). PDR-018 is Partially Accepted, ADR-029 is Accepted, D01–D10 and D13–D21 are Accepted, and D11–D12 are Deferred because ADR-020 remains Proposed. State is **Governance Accepted — Implementation Authorized — Not Implemented — Not Deployed**. Security Track is complete and fixes `security_credential_remediation` as the future migration parent. Dashboard/reporting exclusions and administrator-managed, zero-Seed Reference Data remain unchanged. The historical Proposed statements above describe the discovery state and do not override the closure.

## 11. Historical discovery outcome and next steps

**READY FOR GOVERNANCE REVIEW.**

Exact governance step: convene Product, Operations, Architecture, Data, and Security to record explicit outcomes for PDR-018 D01–D21 and accept/revise/reject PDR-018, ADR-029, the Slice Contract, and the ADR-020 evidence dependency; Release Management must also record the security/business migration order. Do not infer approval from review attendance.

Exact first implementation step after approval: reconcile/fetch the accepted security-track migration head, verify one Alembic head, then draft (without applying) the additive migration/model change that extends existing `operational_milestone` with opaque identity, configuration lineage/snapshots, and lifecycle—before reason/evidence/API/UI work.
