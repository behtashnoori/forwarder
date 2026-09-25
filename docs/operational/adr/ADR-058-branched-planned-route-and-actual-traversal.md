# ADR-058: Branched Planned Route and Separate Actual Traversal

- **Status:** ACCEPTED — bounded P3-03 architecture and implementation authority
- **Date:** 2026-09-25
- **Owners:** Product Owner for authorized behavior; Operational Shipment/Route domain for SOR; Security for tenant and owning-Expert enforcement; Data for additive migration
- **Affected domain:** Route planning, Cargo destination association, actual traversal evidence
- **Implementation state:** P3-03 implementation and qualification in progress; release, deployment, and Production use are not established by this ADR
- **Mission authority:** [P3-03 Branched Route Mission Contract](../../product/phase3/P3-03-BRANCHED-ROUTE-MISSION-CONTRACT-FA.md)

## Context

The existing route foundation already owns revisioned `RoutePlan`, ordered `RouteLeg`, checkpoints, dependency DAGs, milestones, occurrences, active-plan uniqueness, and atomic replan. It assumed a linear graph and required mode and planned times at leg creation. It could not represent a shared route followed by multiple Cargo destinations, save an honestly incomplete draft leg, or retain actual traversal evidence whose endpoints differ from the plan.

P3-03 authorizes those missing behaviors but explicitly forbids a second Route SOR, invented stages/times/stops, automatic exception creation from deviation, Carrier/vehicle/equipment work, ETA, P3-07 event-location semantics, and Customer projection.

## Decision

### 1. Extend the existing route graph

`RoutePlan/RouteLeg` remain the only planned-route SOR. `RouteLeg.parent_route_leg_id` is a same-plan composite foreign key. A root leg is the shared section and child legs are continuations or destination branches. `branch_label` is descriptive only. Sequence remains unique and contiguous for deterministic presentation; topology and continuity use the parent edge.

Transport mode and planned departure/arrival become nullable only so a draft can preserve unknowns. Save accepts missing values and creates no milestone for a missing planned time. Activation validation still requires all three fields, one valid root for a branched graph, no parent cycle, same-endpoint continuity, parent/child chronology, and valid checkpoint dependency DAGs. No Product status is added; `draft` remains sufficient and `DN01` stays open.

### 2. Associate Cargo without duplication

`RouteCargoDestination` links one existing `ShipmentCargoItem` to one terminal `RouteLeg` in one plan revision. Composite foreign keys prove Cargo/Shipment, plan/Shipment, and leg/plan equivalence. A branched plan with multiple terminal legs cannot activate until every existing Cargo line has a terminal destination. Reassignment uses optimistic versioning and audit; it never creates Cargo or Shipment records.

Replan clones the branch topology and Cargo associations into the next planned revision with remapped leg identities. Source plan and association history remain readable.

### 3. Keep actual traversal separate from plan

`RouteTraversalFact` is append-only actual evidence beneath the current RoutePlan context. It stores actual endpoints and at least one actual occurrence time, with an optional same-plan planned-leg link. Serialization compares exact canonical/facility endpoints and labels a mismatch as deviation. The service writes audit/outbox evidence but does not update `RouteLeg`, erase planned fields, create `OperationalException`, or invoke exception reconciliation.

Replan does not clone traversal facts. They remain attached to the source revision as historical evidence, while the new plan is a fresh plan revision. Legacy RouteLeg actual/milestone behavior remains supported and is not redefined by this slice.

### 4. Authorization and presentation

P3-03 writes require the exact persisted `OperationalShipment.primary_responsible_expert_id`, active tenant scope, and existing route capability. Organization Admin oversight does not grant mutation. Cross-tenant and cross-plan identifiers fail closed. Existing authorized reads remain unchanged and no Customer-facing route API is added.

The Forwarder UI presents برنامه مسیر and مسیر واقعی separately, labels the shared section and destination branches, shows incomplete fields without fabricated defaults, associates Cargo to terminal destinations, shows route revision history, and explicitly says deviation alone does not create an exception.

## Migration and rollback

Migration `20261002_phase3_branched_route` is additive from the actual P3-02 head `20261001_phase3_cargo_lineage`. It adds nullable RouteLeg fields, one Cargo/Shipment composite identity, association and traversal tables, constraints, and indexes. It backfills no parent, branch, time, actual traversal, or Cargo destination.

Empty downgrade/re-upgrade is supported. Downgrade refuses before destructive DDL when branch data, incomplete leg fields, Cargo destinations, or traversal facts exist. Application rollback may retain the expanded schema until separately authorized reconciliation.

## Reconciliation

- ADR-002/034 retain Request-versus-Shipment separation.
- ADR-022/057 retain Cargo SOR and P3-02 lineage; P3-03 adds only plan-revision association.
- ADR-042/043/047 remain authoritative for assigned work and fixed Shipment ownership.
- Existing route versioning, checkpoint dependency, milestone occurrence, audit, outbox, and active-plan constraints are reused, not replaced.
- ADR-046 execution allocation is unchanged; P3-04 Carrier/vehicle/equipment remains excluded.

## Required validation

Qualification must prove incomplete draft save/reopen, branch continuity and cycle rejection, Cargo terminal association and cross-scope denial, planned-versus-actual separation, deviation without automatic exception, replan topology/history preservation, exact owning-Expert mutation, additive migration and fail-closed downgrade, PostgreSQL 18, browser Product journey/reopen, and full affected regression.

## Open decisions and exclusions

`DN01=OPEN` and `DN10=OPEN`. Out of scope are lifecycle changes, automatic deviation promotion, Carrier/vehicle/equipment assignment, allocation redesign, ETA, event-location taxonomy, Customer projection, delivery/closure, ownership transfer, Production, deployment, and release.

```text
LPAF_REFERENCE_IMPACT=NONE
PROJECT_REFERENCE_IMPACT=UPDATE_REQUIRED_UNTIL_RECONCILED
JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY
SLICE_JOURNEYS=NOT_RUN
INTEGRATED_PRODUCT_JOURNEYS=NOT_RUN
HUMAN_PRODUCT_WALKTHROUGH=NOT_RUN
GLOBAL_PRODUCT_VALIDATION=EVIDENCE_PENDING
RELEASE_READY=NO
```

## Supersession

- **Supersedes:** none
- **Complements:** ADR-002, ADR-022, ADR-034, ADR-042, ADR-043, ADR-046, ADR-047, ADR-057
- **Superseded by:** none
