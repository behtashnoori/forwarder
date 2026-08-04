# Release 1.9.0 Operational Execution Governance Closure

- **Date:** 2026-08-04
- **Governance:** Accepted
- **Implementation:** Authorized for bounded scope; Not Implemented
- **Deployment:** Not Deployed; Production unchanged
- **Migration:** Release 1.9.0 identifier unassigned; parent fixed as `security_credential_remediation`
- **Outcome:** RELEASE 1.9.0 BOUNDED IMPLEMENTATION AUTHORIZED

## Accepted scope and exclusions

The accepted Option B scope extends the existing operational `Milestone`; provides manual previewed initialization from `ProjectMilestoneDefinition`; defines its bounded lifecycle; retains append-only `MilestoneEvent`; records structured Delay and Exception conditions; exposes a calculated progress read model; authorizes internal APIs and a mobile-safe Persian RTL/English LTR operational UI; and applies existing organization isolation, permissions, optimistic concurrency, opaque IDs, and audit patterns.

Evidence linkage is excluded from implementation because ADR-020 remains Proposed. Also excluded are dashboards, BI, KPI/reporting UI, Shipment-status derivation, automatic or lazy initialization, workflow/BPMN/rule/escalation/notification engines, SLA/penalty/business-calendar analytics, ETA/GIS/maps/optimization/allocation, customer/public APIs or portal changes, evidence approval/enforcement, OCR, AI, Production changes, Reference Data population, backfill, and deployment.

## D01–D21 closure

| Decision | Result |
| --- | --- |
| D01 | Accepted — tightly bounded Option B, narrowed to defer Evidence |
| D02 | Accepted — reuse and extend existing operational Milestone |
| D03 | Accepted — manual preview plus explicit idempotent confirmation |
| D04 | Accepted — PENDING, READY, IN_PROGRESS, COMPLETED, SKIPPED, CANCELLED, BLOCKED |
| D05 | Accepted — explicit bounded transitions; no generic state machine |
| D06 | Accepted — Delay is an independent condition, not status |
| D07 | Accepted — DelayReason is administrator-managed Reference Data; no Seed |
| D08 | Accepted — ExceptionReason is administrator-managed Reference Data; no Seed |
| D09 | Accepted — append-only history; corrections append |
| D10 | Accepted — verification authority separated where feasible |
| D11 | Deferred — no-copy artifact/link boundary retained for later; ADR-020 is Proposed |
| D12 | Deferred — required Evidence enforcement |
| D13 | Accepted — distinct UTC-aware effective and recorded timestamps |
| D14 | Accepted — expected snapshot/reference separated from actual events |
| D15 | Accepted — calculated non-authoritative progress read model |
| D16 | Accepted — automatic Shipment-status derivation deferred |
| D17 | Accepted — bounded codes through existing permission architecture |
| D18 | Accepted — organization-first lookup, opaque IDs, foreign-tenant 404 |
| D19 | Accepted — no automatic backfill; explicit opt-in for eligible existing Shipments |
| D20 | Accepted — Security Track complete; future migration parent fixed as `security_credential_remediation` |
| D21 | Accepted — bounded implementation authority only |

## Aggregate, initialization, and lifecycle policy

The required boundary is `ProjectMilestoneDefinition → explicit initialization → operational Milestone → append-only MilestoneEvent`. Project configuration remains configuration. Preview returns expected milestones, sequence, point/target metadata, missing or inactive references, and conflicts. Confirm revalidates under authorization and concurrency control, is atomic and idempotent, records audit evidence, and never modifies configuration. Shipment creation, page open, migration, and deployment have no initialization side effect.

Allowed ordinary transitions are PENDING→READY; READY→IN_PROGRESS; PENDING/READY/IN_PROGRESS→BLOCKED; BLOCKED→its retained prior non-terminal state or READY according to the accepted command rule; IN_PROGRESS→COMPLETED; PENDING/READY→SKIPPED; and PENDING/READY/IN_PROGRESS→CANCELLED with authority and reason. COMPLETED, SKIPPED, and CANCELLED are terminal. Reopen/correction is an elevated, reasoned, append-only command and never a silent rewrite. Optimistic concurrency is mandatory.

## Event, Delay, Exception, and Evidence policy

Every applicable MilestoneEvent carries opaque public identity, organization, milestone, event type, effective and recorded instants, actor, source channel, optional governed point/reason/note, correction linkage, verification state, and audit metadata. Events are never hard-deleted or silently changed; correction and verification append facts while preserving the original. All history queries are tenant-scoped.

Delay and Exception are separate active/resolved operational records linked to the organization and OperationalShipment, optionally a Milestone. Each has opaque identity, one administrator-managed primary reason, occurrence/start and optional resolution time, optional note, actor/audit, and calculated duration where applicable. Neither changes Shipment status or introduces severity, risk, penalty, escalation, or reporting engines. No catalog rows are seeded or deployed.

ADR-020 is Proposed and therefore does not safely authorize its artifact/attachment model for this implementation. The future boundary remains a link to an existing artifact, without binary duplication or approval/OCR/automatic validation/customer exposure, but all Evidence API, UI, schema, and enforcement work is deferred. This narrowing does not block the coherent remainder.

## Progress, permissions, and internal product surface

Progress is calculated per authorized Shipment from operational facts: total and lifecycle counts, current milestone, completion percentage under the implementation rule, and active Delay/Exception counts. It is not mutable state, a KPI, a dashboard, a Shipment-status source, or a cross-tenant aggregate.

Existing authorization mechanisms are extended with `operational_execution.read`, `operational_execution.manage`, `operational_event.create`, `operational_event.correct`, and `operational_event.verify`. `operational_evidence.attach` is reserved for the deferred Evidence scope. Role intent is admin full bounded authority; operations manager manage/verify where approved; supervisor manage/correct; expert create events/update execution where authorized; read-only expert read only. Organization-first Shipment authorization, opaque IDs, foreign-tenant 404, and separate correction/verification authority apply.

Internal APIs may provide initialization preview/confirm, milestone list/detail/transitions, event list/create/correct/verify, Delay and Exception list/create/resolve, timeline, and progress. They require stable validation errors and bounded pagination/filter/sort. The UI may provide the Shipment header, initialization action, current and ordered milestones, transition and Delay/Exception controls, immutable timeline, correction/verification, and progress. Evidence controls, public/customer endpoints, numeric ID leakage, dashboard endpoints, maps, ETA, and workflow designers are not authorized.

## Migration, rollout, and rollback

No Release 1.9.0 migration number is reserved. The Security Track is complete and its accepted head is `security_credential_remediation`; a later Release 1.9.0 migration must use that exact parent, and only one head is permitted. Data population and a competing head remain blocked. Release 1.9.0 is waiting only for implementation.

Rollout is additive, internal, opt-in, and cohort-controlled after implementation verification. Existing Shipments are not automatically backfilled. Administrators create governed reason values through the authorized Reference Data path. Rollback disables new commands, routes, and UI while retaining append-only facts and audit, preserving configuration, and leaving Shipment status and existing APIs unchanged. Production is unchanged by this closure.

## Decision records and approver roles

ADR-029 is Accepted. PDR-018 is Partially Accepted because D11–D12 remain Deferred; its bounded non-Evidence portions authorize implementation. Deferred material remains Deferred/Proposed and does not authorize dashboards, automation, SLA analytics, or customer visibility.

Required approver roles are Product, Operations, Architecture, Data, Security, and Release Management. This record identifies roles only and does not fabricate named signatures.
