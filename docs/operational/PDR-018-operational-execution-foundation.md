# PDR-018 — Operational Execution Foundation

- **Status:** Partially Accepted
- **Date:** 2026-08-04
- **Candidate:** Release 1.9.0
- **Implementation authority:** YES — bounded scope only; Evidence linkage deferred
- **Implementation status:** Implemented — Not Published — Not Deployed (`20260812_operational_execution`)
- **Terminology authority:** [PDR-017](PDR-017-canonical-operational-taxonomy.md)

## Purpose

Convert accepted Project configuration into controlled execution records for one OperationalShipment. The release must answer what is happening, which expected milestone is current, what occurred where and when, who asserted/corrected/verified it, which structured reason applies, and what existing artifact supports the claim. It is not a generic workflow engine.

## Repository-grounded boundary

The existing `operational_milestone` (`Milestone`) is the safest execution-instance base. It already belongs to an active RoutePlan through a RouteLeg or Checkpoint and has planned/projected/occurred times, verification state, version, and append-only `MilestoneEvent` history. It must be extended rather than shadowed by an `OperationalMilestoneInstance` table. `ProjectMilestoneDefinition` remains configuration, not execution.

`OperationalEvent` remains the canonical ExecutionUnit timeline envelope under ADR-019. `MilestoneEvent` remains the specialized milestone transition/fact record and may later project into `OperationalEvent`; neither is an audit log or outbox record. Current `RouteException` remains route reconciliation/work-item state and is not silently relabeled as the governed operational exception proposed here.

## Required distinctions

| Distinction | Proposed meaning |
| --- | --- |
| ProjectMilestoneDefinition / operational Milestone | Mutable Project expectation / shipment-specific execution snapshot with immutable lineage |
| Expected / actual | Snapshotted plan and target / occurred execution fact; configuration edits never rewrite the snapshot |
| Milestone / Shipment status | Local execution state / aggregate shipment lifecycle; no automatic derivation in 1.9.0 |
| Transition / OperationalEvent | Governed state command / append-only fact envelope emitted by the command |
| Activity / Event | Work performed over time / recorded business fact at a time |
| Delay / Exception | Time variance condition / abnormal condition requiring recognition or resolution |
| Exception / Risk | Realized abnormal condition / uncertain future possibility; risk is deferred |
| Note / Reason | Optional narrative / governed primary Reference Data code |
| Document / Evidence | Stored artifact and context / role that a permitted artifact link plays in supporting a fact |
| Requirement / submitted Evidence | Configuration expectation / actual artifact link; no enforcement in this release |
| Correction / deletion | New superseding event / prohibited history removal |
| Timeline / audit log | Business-readable ordered facts / security-administrative record of commands and access |
| Checkpoint / Milestone | Route place/stage container / expected or actual execution achievement |
| LogisticsPoint / event location | Governed reusable master/configuration point / immutable occurrence snapshot/reference |
| Planned sequence / actual time | Expected order / occurrence instant; late entry preserves both occurred and recorded time |
| Automatic / manual initialization | Hidden cross-aggregate side effect / previewed, confirmed, idempotent command; manual is proposed |

## Final decisions D01–D21

Decisions were closed on 2026-08-04. Approver roles describe governance functions; no named signatures are asserted. D11 and D12 are deferred because ADR-020 remains Proposed. All other rows are accepted only within this record's exclusions.

| ID | Options | Recommendation and rationale | Impacts (business / UX / data / security / reporting / migration) | Dependencies, risks, fail-safe, approver roles | Status |
| --- | --- | --- | --- | --- | --- |
| D01 Scope | A minimal; B balanced; C broad | Tightly bounded B, narrowed to defer Evidence: execution, reasons, timestamps, calculated progress. | Useful structured operations / one execution section / additive fields and records / new command permissions / reporting-ready facts only / additive migration later. | ADR-019/027; scope creep. Fail closed to current behavior. Product, Operations, Architecture, Data, Security. | Accepted |
| D02 Milestone model | New instance; extend `Milestone`; use `OperationalEvent` | Extend existing `Milestone`; add Project-definition lineage/snapshot and lifecycle. Avoid duplicate route execution ownership. | Familiar UI / preserves routes / tenant resolution remains via Shipment / stable future dimensions / additive columns. | Existing hard-coded types and ownership constraints need design. Fail-safe: no initialization. Product, Architecture, Data, Operations. | Accepted |
| D03 Initialization | Manual; creation-time automatic; lazy UI | Manual preview plus explicit confirmation. Existing shipments and incomplete configuration must not mutate invisibly. | Visible choice / preview errors / snapshot rows and audit / permissioned command / cohort reporting / no backfill. | Active Project configuration. Fail-safe: atomic refusal, zero rows. Product, Operations, Architecture, Security. | Accepted |
| D04 Status set | Existing verification only; seven-state set; workflow engine | `PENDING`, `READY`, `IN_PROGRESS`, `COMPLETED`, `SKIPPED`, `CANCELLED`, `BLOCKED`; verification remains orthogonal. | Clear current work / badges/actions / new constrained state / command authorization / structured counts / constraint change. | D05/D06. Risk overlap with checkpoint state. Fail-safe: reject unknown state. Product, Operations, Architecture, Data. | Accepted |
| D05 Transitions | Free edit; bounded commands; generic machine | Explicit commands only: PENDING→READY/BLOCKED/SKIPPED/CANCELLED; READY→IN_PROGRESS/SKIPPED/CANCELLED/BLOCKED; IN_PROGRESS→COMPLETED/BLOCKED/CANCELLED; BLOCKED→retained prior non-terminal state or READY, or CANCELLED with authority. Terminal COMPLETED/SKIPPED/CANCELLED; reopen only by explicit correction policy, not ordinary transition. | Predictable operations / contextual controls / append events and version checks / per-command permission / reliable history / additive constraints. | D04/D09. Fail-safe 409 with no mutation. Product, Operations, Architecture, Security. | Accepted |
| D06 Delay | Status; condition; event only | Independent open/resolved Delay condition represented by events/record, never replacing execution status. | Shows delayed plus real state / separate indicator / duration calculable / governed access / delay facts / additive record. | D07. Fail-safe: milestone state remains truthful if delay command fails. Product, Operations, Data. | Accepted |
| D07 DelayReason | Free text; shared catalog; separate catalog | Separate administrator-managed catalog, immutable code, mutable label/active state, one primary reason per delay. | Consistency / selector / Reference Data FK/snapshot / admin security / stable grouping / no seeded rows. | ADR-028; empty catalog. Fail-safe: disable record action with truthful no-active-choice message. Product, Operations, Data, Administration. | Accepted |
| D08 ExceptionReason | Free text; shared catalog; separate catalog | Separate administrator-managed catalog because abnormal conditions and time variance classify differently. | Consistency / selector / reason reference/snapshot / admin security / stable grouping / no seeded rows. | ADR-028. Fail-safe as D07. Product, Operations, Data, Administration. | Accepted |
| D09 History | Mutable/delete; append correction; audit only | Append-oriented events; correction supersedes a named event and preserves the original. No business-event deletion. | Trustworthy claim / visible lineage / immutable rows / correct permission / deterministic projections / additive indexes. | ADR-009/019. Fail-safe: conflict/no-op, never overwrite history. Architecture, Operations, Security, Data. | Accepted |
| D10 Verification | Reporter may verify; separation; none | Separate verifier permission and prohibit self-verification where feasible, reusing current rule. Verification is another event. | Four-eyes control / clear verifier action / actor/time / least privilege / verified-fact dimension / no destructive change. | Staffing may limit separation. Fail-safe: remain unverified. Operations, Security, Product. | Accepted |
| D11 Evidence link | New files; reuse CaseDocumentFile directly; artifact/link boundary | The no-copy artifact/link boundary is accepted architecturally, but Release 1.9.0 implementation is deferred because ADR-020 is not Accepted. | No evidence API, UI, schema, or enforcement in this slice. | ADR-020 remains Proposed with unresolved authorization policy. Product, Architecture, Security, Compliance. | Deferred |
| D12 Required evidence | Enforce; indicator only; omit | Deferred with D11; completion is not evidence-gated in 1.9.0. | No operational deadlock and no implied approval workflow. | D11/ADR-020. Product, Operations, Compliance. | Deferred |
| D13 Timestamps | One time; occurred+recorded; full temporal engine | Separate occurred, recorded, and applicable started/completed/resolved instants in UTC. | Late-entry truth / explicit fields / indexed instants / actor trace / duration readiness / additive columns. | ADR-016. Reject malformed/illogical intervals. Architecture, Data, Operations. | Accepted |
| D14 Expected/actual | Live configuration; snapshots; derived only | Snapshot definition/type/point/sequence/target at initialization; actual facts never rewrite expected values. | Stable expectation / source summary / lineage columns / protected writes / variance readiness / additive fields. | PDR-017/ADR-027. Fail-safe: refuse missing/inactive references before confirmation. Product, Architecture, Data. | Accepted |
| D15 Progress | Mutable aggregate; calculated read model; dashboard | Calculated response: initialized, counts by lifecycle, current milestone, completion percentage, and active delay/exception counts. | Quick orientation / summary strip / no drift / same authorization / reporting-ready / no aggregate table. | Defined ordering/current rule. Fail-safe: return unknown/not-initialized rather than invent progress. Product, Operations, Data. | Accepted |
| D16 Shipment status | Automatic; manual; unchanged | Do not derive automatically in 1.9.0. Existing Shipment status ownership remains unchanged. | No surprise transitions / clearly separate labels / no duplicated state writes / no extra authority / later analysis possible / none. | ADR-007. Fail-safe: milestone completion cannot mutate Shipment. Product, Operations, Architecture. | Accepted |
| D17 Permissions | Reuse broad; new bounded; role hard-code | Add bounded permissions mapped through existing membership: read, manage/init, and event create/correct/verify. Reserve evidence attach for the deferred scope. Roles are mappings, not authorization logic. | Delegation / hidden controls / existing JSON permission mechanism / least privilege / actor attribution / possible System Data update only. | Exact codes accepted before implementation. Fail-safe deny. Security, Operations, Architecture. | Accepted |
| D18 Isolation | Shipment-only; organization-first; public visibility | Organization-first Shipment/Project authorization, opaque public IDs, foreign-tenant 404, no customer/public API. | Safe tenancy / non-disclosing errors / public IDs needed on reused rows / centralized checks / safe dimensions / additive identities. | Existing operational APIs leak numeric IDs and need compatible migration. Fail-safe 404 before lookup/serialization. Security, Architecture. | Accepted |
| D19 Compatibility | Backfill; new shipments only; opt-in all | No automatic backfill. Existing shipments may use explicit preview/init if eligible; all current APIs continue during deprecation. | Opt-in adoption / not-initialized state / nullable additive lineage / unchanged old clients / cohort reporting / no historical mutation. | D03/D18. Fail-safe legacy behavior. Product, Operations, Architecture, Data. | Accepted |
| D20 Migration sequencing | Reserve 20260812; security first; defer ID | No Release 1.9.0 migration ID is reserved. Security remediation is complete; the implementation migration must descend from `security_credential_remediation`. | Avoids branch collision / no user impact now / one future head / security integrity / stable lineage. | `20260812` remains unassigned. Fail-safe: reject any competing or incorrectly parented migration. Architecture, Security, Release Management. | Accepted |
| D21 Authority | Authorize now; governance review; reject | Authorize bounded implementation excluding deferred Evidence and every listed exclusion. | Documentation grants authority; runtime remains unchanged until a separate implementation task. | Product, Operations, Architecture, Data, Security, Release Management. | Accepted |

## Scope exclusions

No dashboards, BI, KPI screens, executive summaries, SLA analytics, delay charts, bottleneck reports, customer reporting, predictive analytics, notifications, escalation, customer visibility, workflow designer, map, ETA prediction, OCR, approval workflow, Evidence linkage/enforcement, financial penalties, risk scoring, automatic Shipment status, automatic/lazy initialization, or Reference Data population.

## Governance closure

D01–D10 and D13–D21 are Accepted. D11–D12 are explicitly Deferred and do not block the remainder. ADR-029 is Accepted. Implementation is authorized only for the bounded non-Evidence scope; it is not implemented or deployed. The Security Track is complete and fixes `security_credential_remediation` as the parent of the future Release 1.9.0 migration; no Release 1.9.0 identifier is assigned here. This record never authorizes Reference Data population, dashboard/reporting work, Production access, packaging, publishing, or deployment.
