# ADR-029 — Operational Milestone and Event History Boundaries

- **Status:** Accepted
- **Date:** 2026-08-04
- **Candidate:** Release 1.9.0
- **Implementation authority:** YES — bounded Release 1.9.0 scope

## Context

Release 1.8.0 configures Project milestone expectations but intentionally creates no execution rows. The repository already contains route/checkpoint-owned `Milestone`, append-only `MilestoneEvent`, ExecutionUnit-scoped `OperationalEvent`, `OperationalAudit`, `OperationalOutbox`, and route reconciliation exceptions. A second execution aggregate would split authority.

## Decision

1. Extend the existing `Milestone` as the OperationalShipment milestone instance. Preserve RoutePlan ownership and add immutable lineage/snapshots from `ProjectMilestoneDefinition`; do not add a parallel `OperationalMilestoneInstance`.
2. Add a lifecycle state orthogonal to existing verification state. Delay is an independent condition, not a lifecycle state.
3. Keep `MilestoneEvent` as the specialized append-only history of milestone transitions and facts. A command may also emit/project an ADR-019 `OperationalEvent`, an audit row, and an outbox row; those records have different purposes.
4. Corrections append a `CORRECTED` event pointing to the superseded event. Original rows remain readable. No silent update or delete is allowed.
5. Preserve `occurred_at` separately from `recorded_at`, actor, source channel, optional event-location snapshot/reference, optional note, governed reason where required, idempotency key, request hash, and aggregate version.
6. Evidence, when later authorized, is a link from a permitted existing artifact to a milestone, an event, or both and never owns or duplicates a binary. ADR-020 remains Proposed, so Evidence implementation is deferred from Release 1.9.0 without blocking the remaining decision.
7. Operational timeline is a business projection ordered by occurred time with stable recorded-time/id tie-breaking and correction display. Audit remains a security/administrative command trail.

## Transition policy

| From | Allowed targets | Required additions |
| --- | --- | --- |
| PENDING | READY, BLOCKED, SKIPPED, CANCELLED | actor; governed reason for block, skip, or cancel |
| READY | IN_PROGRESS, SKIPPED, CANCELLED, BLOCKED | occurred time; reason for skip/cancel/block |
| IN_PROGRESS | COMPLETED, BLOCKED, CANCELLED | occurred time; reason for block/cancel |
| BLOCKED | retained prior non-terminal state or READY; CANCELLED with authority | unblock or cancel reason; prior state retained for deterministic return |
| COMPLETED, SKIPPED, CANCELLED | none | correction/reopen is a separately authorized superseding command, never an ordinary transition |

Unknown, stale, cross-tenant, out-of-sequence, or forbidden commands make no change. Sequence guidance may make a milestone READY, but Release 1.9.0 must not introduce a generic state-machine engine.

## Verification and correction

Verification appends an event and records verifier/time. The reporting actor cannot verify the same claim where operational staffing permits separation. Correction requires a reason, expected version, target event, and a new asserted occurred time/value. Correcting a verified fact returns it to an explicitly unverified state until a permitted verifier verifies the correction. Deletion is not a correction.

## Consequences

Existing route APIs, UI, and tests supply a strong compatibility base. Implementation still needs opaque milestone/event identity, Project-definition snapshots, a full lifecycle, structured reason records, and consistent event projection. Evidence links await ADR-020 acceptance. Numeric legacy routes may remain temporarily compatible internally but are not the normative new contract.

## Alternatives rejected

- A second operational milestone table: duplicates route/checkpoint ownership and current history.
- Reusing `ProjectMilestoneDefinition` as execution: configuration edits would rewrite history.
- Using only `OperationalEvent`: loses the specialized milestone aggregate/concurrency boundary.
- Treating audit rows as a timeline: audit semantics and audience are different.
- Deleting incorrect events: destroys provenance.
- Making delay a status: hides whether work is pending, active, or blocked.

## Compatibility and rollout boundary

Any later implementation must be additive, opt-in, and based on the resolved Alembic head. Existing shipments receive no rows automatically. Existing operational endpoints remain compatible while opaque-ID commands are introduced by extension, not a parallel v2 domain. Rollback disables new commands/projections while preserving appended events and links.

## Governance and rollback

Product and Operations own lifecycle and correction semantics; Architecture and Data own aggregate/event boundaries and projection; Security owns permissions, verification separation, opaque identity, and tenant isolation; Release Management owns migration sequencing. These are approver roles, not named signatures.

The configuration-to-execution boundary, existing Milestone reuse, append-only history, explicit correction and verification, separate Delay/Exception records, calculated progress, no workflow engine, no hidden creation, no historical rewrite, and tenant isolation are Accepted. Rollback disables new commands and projections while retaining appended events and audit evidence; it never rewrites history or automatically changes Shipment state. Implementation is authorized but is not implemented or deployed by this decision.
