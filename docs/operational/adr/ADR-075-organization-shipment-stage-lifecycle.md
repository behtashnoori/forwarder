# ADR-075 — Organization Shipment Stage Lifecycle and Exact Closure Facts

- Status: Accepted — explicit 2026-09-30 Product Owner mission authority
- Scope: Operational Shipment stages, Delivery finality, closure evaluation, and Unified Shipment History
- Supersedes: none

## Context

Project milestone definitions currently supply one execution surface, but a normal Operational Shipment may have no Project. Reusing Project milestones would give Project context ownership of an Organization operational lifecycle and would leave projectless Shipments without stages. Closure also lacks explicit final-delivery and required-stage facts and currently conflates quantity sufficiency with delivery completion.

## Decision

Organization Shipment Stages are a separate Organization/Tenant Master capability and System of Record. A versioned Organization policy owns immutable definition snapshots. Each definition has opaque identity, stable code, localized display name, order, active state, and required-for-completion state. An Operational Shipment instance pins one applicable policy version when its first stage command is accepted; before that, reads may preview the currently applicable version without creating history. No migration creates historical instances or events.

Stage progress is a Transactional/Historical Evidence chain of append-only `STARTED` and `COMPLETED` events. The fixed responsible Expert is the stage-event authority. Server-side transition and tenant rules require ordered progress and reject definition administration by Experts. Deactivation or later policy publication cannot reinterpret a pinned instance or its event history.

Delivery finality is an explicit immutable boolean on each Delivery revision. A qualifying final Delivery is a current, non-superseded Delivery revision explicitly recorded as final for the Shipment. Quantity equality never creates finality. A correcting revision carries an explicit finality choice and supersedes the earlier fact.

Closure policy stays versioned. New policies may contain only the authorized V1 criteria. Blocker/warning classification is fixed by criterion code and cannot be flipped by an administrator. Historical versions containing legacy codes remain readable. `REQUIRED_DOCUMENTS_READY` is vacuously true when the applicable required-document set is empty.

Closure assessment is a read projection, not a new business-fact SOR. Its source facts and fingerprint include the pinned/preview stage version and stage events, current Delivery revisions including finality, document requirements/readiness, issue/work state, allocation dimensions, quantities, ETA, and policy version. Closure decisions remain immutable snapshots.

Unified Shipment History consumes stage events and closure decisions from their domain owners and presents Persian business labels; it does not become a parallel SOR.

## Consequences

- `ProjectMilestoneDefinition != ShipmentOperationalStageDefinition` remains enforceable.
- Projectless Shipments gain the same Organization-governed stage capability.
- First stage mutation pins configuration atomically; later configuration changes affect only unpinned Shipments.
- Final Delivery and Actual Cargo remain independent facts.
- One additive migration is required; old data is preserved without inferred stages or finality.
- Organization Admin configuration and Expert execution require independent positive, negative, and cross-tenant verification.

## Evidence plan

Candidate-bound unit/API/PostgreSQL tests cover version pinning, order, append-only history, inactivity, partial/final semantics, criteria, warnings, closure refusal/success, and tenant isolation. Frontend and browser evidence covers normal navigation and Persian history. Runtime configuration is performed only after qualification through governed application commands, with preservation evidence before and after.

