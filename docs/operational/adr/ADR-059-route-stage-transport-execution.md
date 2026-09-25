# ADR-059: Route-stage transport execution on tenant-owned ExecutionUnit

**Status:** ACCEPTED — P3-04 bounded implementation

**Date:** 2026-09-25

**Extends:** ADR-018, ADR-019, ADR-046, ADR-056 and ADR-058.

**Supersedes:** none.

## Context

ADR-046 makes `ExecutionUnit` the tenant-owned execution SOR and makes its legacy Project/Shipment columns compatibility-only. P3-03 makes `RoutePlan/RouteLeg` the revisioned route SOR. P3-01 supplies distinct governed Means and Equipment types. The current model cannot attribute an execution to an exact route-stage revision, distinguish Means from Equipment, retain a rail chain such as Train→Wagon→Container, or show which transport configuration applied when an existing `OperationalEvent` occurred.

Putting one Carrier on `RouteLeg`, one vehicle on `OperationalShipment`, or making `ExecutionUnit.operational_shipment_id` canonical would prevent multiple executions or regress ADR-046. Reinterpreting legacy `unit_type`/`vehicle_reference` would fabricate history.

## Decision

### Ownership and stage participation

`ExecutionUnit` remains the only execution SOR and remains directly owned by `OperationalOrganization`. A new `RouteStageExecution` association records participation in an exact `OperationalShipment + RoutePlan + RouteLeg`. Composite foreign keys enforce same Shipment, same plan and same tenant. A RouteLeg may have zero, one or many associations. Project and Shipment fields already present on `ExecutionUnit` remain compatibility projections and are not authority.

P3-04 creates a new ExecutionUnit for a stage; it does not introduce reuse/discovery of a permanent fleet asset. Existing tenant-shared units and cross-project allocations remain valid and are not forced into one stage.

### Transport configuration and history

Each stage execution has one immutable ordered sequence of `ExecutionTransportRevision` snapshots. A revision records:

- governed `TransportMeansType` identity plus code/name snapshot;
- optional current Carrier identity plus display snapshot;
- optional means identifier and bounded operational detail;
- optional lightweight driver name/contact;
- effective time, recorded time, actor and optional reason;
- zero or more ordered `ExecutionTransportEquipmentSnapshot` rows, each with governed `TransportEquipmentType`, code/name snapshot, optional identifier and bounded detail.

The ordered equipment list expresses the approved visible chain. It does not create reusable assets, custody, fleet ownership or a general parent/child equipment lifecycle. Train→Wagon→Container is represented as Means=Train and ordered Equipment=[Wagon, Container]. A deeper ownership/containment model requires a separate Product decision.

Current state is the latest revision. `carrier_customer_id` and `vehicle_reference` remain compatibility projections for newly governed rows and are updated transactionally; legacy values are not reinterpreted or backfilled. `unit_type` remains a legacy compatibility field and is not the governed Means type.

### Reference and Carrier rules

New writes accept only a central active definition with an ACTIVE organization activation. Historical revisions continue to render after either central or organization deactivation because they retain reference identity and snapshots. No free-text base type, seed, local-definition or promotion workflow is added.

Carrier is optional for progressive completion. When present it must be an active Customer in the execution tenant with an active `CARRIER` role. Carrier is execution context only: it neither owns the Shipment nor gains read or write authority.

### Progressive detail

Means type is the only mandatory transport field. Carrier, means identifier, equipment rows/identifiers, detail and driver context may be completed later by creating a new revision. Missing optional detail is returned as an incomplete field and never creates Exception, Attention, SLA or lifecycle transition.

### Event context

`OperationalEvent` gains a nullable `transport_revision_id`. Every new event for a governed stage execution pins the latest revision in the same execution; events for legacy/no-revision units retain NULL. Reads show that pinned snapshot, not the execution's latest revision. Therefore an event recorded under Truck A does not appear to have occurred under Truck B after a change. Existing events are not guessed or backfilled.

### Commands and authorization

Create and revise commands require:

- active authenticated Expert identity and exactly one active tenant membership;
- the persisted fixed owning Expert of the Shipment;
- the exact Shipment/plan/leg relationship;
- active allowed references and Carrier role when supplied;
- required idempotency key and request-hash replay protection;
- expected ExecutionUnit version for revision changes.

Organization Admin has read oversight only through existing Shipment read authority; it receives no normal execution mutation. Platform Admin receives no tenant operational authority. Foreign and guessed parents fail closed.

## Data, migration and compatibility

The migration is additive from the verified head `20261002_phase3_branched_route`. It creates the stage association and immutable revision/snapshot tables, adds the ExecutionUnit `(id, organization_id)` candidate key needed by composite tenant FKs, and adds nullable event revision context. It performs no row conversion and no means/equipment/Carrier backfill.

Downgrade is permitted only when no P3-04 stage association, revision or event reference exists; otherwise it refuses before DDL. Legacy ExecutionUnit, tracking and allocation rows remain readable. Existing project/shipment APIs remain adapters and do not become the new SOR.

## Consequences

- Multiple executions and different Carriers per stage are supported without changing route ownership.
- Means and Equipment remain distinct and rail chains are expressible without a fleet registry.
- Progressive details and meaningful change history are explicit.
- Event context remains historically stable across equipment/Carrier changes.
- Reads require bounded latest-revision/equipment loading; suitable indexes are required.
- P3-05 allocation remains unchanged and excluded.

## Rejected alternatives

- `OperationalShipment.vehicle_id`: rejects multiple stages/executions and creates fleet semantics.
- `RouteLeg.carrier_id`: permits only one Carrier per stage and mixes planning with execution.
- canonical `ExecutionUnit.route_leg_id`: regresses ADR-046 tenant-shared ownership and future shared participation.
- overwriting `carrier_customer_id`/`vehicle_reference` only: loses meaningful history and moves old events.
- a reusable Vehicle/Driver/Equipment registry: outside Product authority.
- JSON-only equipment metadata: weakens governed reference and history constraints.
- full event sourcing: unnecessary for this bounded history requirement.

## Qualification

Qualification must prove multiple executions per stage, progressive incomplete detail, road and rail chains, inactive reference historical reads, Carrier/means/equipment revision history, event pinning, same-tenant shared-foundation preservation, cross-tenant and non-owner denial, migration round-trip/guard on PostgreSQL 18, browser normal navigation/reopen, and affected regression. It must not claim Cargo allocation, global integrated journey PASS, Human Product Walkthrough, Release Ready, deployment or Production access.
