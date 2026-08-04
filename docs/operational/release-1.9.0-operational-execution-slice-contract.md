# Release 1.9.0 Operational Execution Slice Contract

- **Status:** Authorized for bounded implementation
- **Implementation status:** Implemented — Not Published — Not Deployed
- **Implementation authority:** YES — Evidence linkage excluded pending ADR-020 acceptance
- **Release theme:** Operational Execution Foundation
- **Baseline:** application candidate 1.8.0; migration `20260811_project_configuration`; Production evidence unchanged at 1.6.1 / `20260809_cargo_catalog_items`

## Accepted scope

- Explicit read-only initialization preview and explicit, idempotent confirmation for eligible OperationalShipments.
- Reuse and extension of existing operational `Milestone`, with immutable ProjectMilestoneDefinition/MilestoneType/point/sequence/target snapshots.
- Bounded lifecycle: PENDING, READY, IN_PROGRESS, COMPLETED, SKIPPED, CANCELLED, BLOCKED; verification remains separate.
- Append-oriented transition/fact history, explicit correction, verification, occurred/recorded timestamps, actor, source, location, note, expected version, and idempotency.
- Administrator-managed DelayReason and ExceptionReason catalogs with no built-in rows.
- One primary structured reason plus optional note for each delay/exception; start and optional resolution time; calculated duration; no severity/risk engine.
- Calculated, non-authoritative operational progress summary.
- Internal organization-scoped API/UI only, Persian RTL and supported English LTR, mobile-safe.

## Initialization acceptance contract

Preview returns configuration source/version, expected rows, inactive/missing references, duplicate/conflict findings, and whether confirmation is allowed. Confirmation repeats authorization and validation under lock, requires an idempotency key and expected Shipment/configuration version, creates all rows atomically, records actor/audit/event evidence, and modifies neither Project configuration nor existing milestones. Replays return the original result; conflicting prior initialization returns 409. No deployment, migration, Shipment creation, or page open initializes anything.

## API authority

Extend the existing `/api/operational-shipments` family; do not create a parallel `/api/v2` execution domain. Normative new resources use opaque public IDs and non-disclosing tenant checks. Candidate extensions are:

- `GET .../{shipment_public_id}/execution/initialization-preview`
- `POST .../{shipment_public_id}/execution/initialize`
- `GET .../{shipment_public_id}/execution`
- command endpoints below `.../milestones/{milestone_public_id}` for start, complete, skip, cancel, block, unblock, correct, and verify
- scoped collections for events, delays, exceptions, timeline, and calculated progress

Authorized capability groups are initialization preview/confirm, milestone list/detail and transitions, event list/create/correct/verify, delay and exception list/create/resolve, timeline, and progress. Evidence link/unlink is not authorized until ADR-020 is Accepted. Routes use bounded pagination/filter/sort, stable validation errors, optimistic concurrency, organization-first authorization, and opaque IDs. Existing internal routes remain compatible; new serialization must not leak numeric IDs. No public, customer, or dashboard endpoints are authorized.

## Permissions

Use existing `OperationalMembership` authorization and organization-first Shipment resolution. Authorized codes are `operational_execution.read`, `operational_execution.manage`, `operational_event.create`, `operational_event.correct`, and `operational_event.verify`; `operational_evidence.attach` is reserved but not authorized in this slice. Admin has the full authorized scope; operations manager manages and verifies where policy permits; supervisor manages/corrects; expert creates events and updates execution where authorized; read-only expert reads only. Roles are mappings, not service logic. Foreign-tenant resources return 404. Unauthenticated access is denied.

## UI flow

```text
Shipment header + Project configuration source
  └─ Execution not initialized
       └─ Preview → inspect rows/problems → Confirm → milestone list

Current milestone + progress summary
  ├─ Start / complete / skip / cancel / block
  ├─ Delay or exception → governed reason + optional note
  └─ Timeline → original fact → correction → verification
```

On narrow screens, sections stack in that order; commands remain at least touch-safe, timeline content wraps, and no horizontal workflow canvas is used. Reason identity always comes from a governed selector. An empty catalog explains that an administrator must create a reason; it never offers Seed.

## Explicit exclusions

Dashboards, BI, KPI screens, reports, SLA analytics, charts, bottleneck analysis, customer reporting, predictive analytics, ETA, GIS/maps, route optimization, allocation, notifications, escalation, visibility engine, automatic Shipment status, automatic/lazy initialization, required-evidence enforcement, all Evidence linkage pending ADR-020, document approval workflow, OCR, AI, portal/customer/public APIs, financial penalties, risk scoring, generic workflow/BPMN/rule/state-machine frameworks, business calendars, Reference Data population, and historical backfill.

## Data and migration contract

The future migration is additive, preserves one Alembic head, adds no Reference Data rows, creates no milestones for existing shipments, mutates no history, and has a safe downgrade before dependent data. No Release 1.9.0 migration identifier, including `20260812`, is reserved. The Security Track is complete: `security_credential_remediation` is the exact required parent. No task may create a competing head.

## Verification, performance, rollout, rollback, and acceptance

Implementation tests must cover transition matrices, idempotent initialization, optimistic concurrency, correction/verification separation, organization isolation and 404 behavior, opaque serialization, reason-catalog inactivity, no backfill, and progress calculation. PostgreSQL verification must cover constraints, indexes, UTC-aware timestamps, query plans, single-head lineage, upgrade/downgrade on a disposable database, and zero Seed rows. Application tests are not run during this documentation closure.

The performance profile requires bounded page sizes, indexed organization/shipment/milestone/time lookups, no N+1 milestone timeline reads, and calculated progress scoped to one authorized Shipment; no cross-tenant aggregate or dashboard workload is authorized. Rollout is additive, opt-in, internal, cohort-controlled, and requires administrator-created DelayReason/ExceptionReason values. Existing Shipments remain uninitialized until an authorized user explicitly previews and confirms. Rollback disables new routes/UI/commands while preserving append-only facts and leaving Project configuration, Shipment status, and existing APIs unchanged.

Acceptance requires PDR-018 Partially Accepted, ADR-029 Accepted, D01–D21 resolved, manual preview/confirm, the seven-state transition contract, append-only history, independent Delay/Exception records, calculated progress, bounded permissions, organization isolation, approved API/UI behavior, no Evidence implementation, no dashboard/reporting, no Seed/backfill, and a migration descended from `security_credential_remediation`. Governance is Accepted and implementation Authorized, but implementation and deployment remain Not Implemented and Not Deployed. Security remediation is complete and is not a remaining blocker.
