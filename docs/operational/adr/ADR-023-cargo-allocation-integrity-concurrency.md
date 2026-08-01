# ADR-023: Cargo Allocation Integrity and Concurrency

- **Status:** Proposed
- **Date:** 2026-08-01
- **Blocking:** SLICE-B5
- **Evidence:** [Discovery and Domain Analysis Report](../discovery-cargo-data-and-scroll-analysis-20260801.md)

## Context

Allocating ShipmentCargoItem quantity to concurrently updated ExecutionUnits creates an aggregate-spanning invariant. Application-only prechecks can over-allocate under race conditions, while destructive edits erase operational history.

## Proposed decision

ExecutionUnitCargoAllocation is an explicit relationship from a ShipmentCargoItem snapshot to an eligible ExecutionUnit. Initial invariants are: positive decimal quantity; exact matching UOM; sum of active allocations no greater than shipment item quantity; derived unallocated quantity; same Project; same OperationalShipment by default; and no new allocation to inactive, cancelled, or otherwise ineligible units. Conversion, cross-shipment allocation, split, and merge are deferred.

Mutations execute in one transaction using row locking or equivalent optimistic-concurrency enforcement proven safe in PostgreSQL. Commands require expected version, idempotency key, actor, reason where correcting/reallocating, and audit/correlation. Delivery preserves fulfilled evidence. Cancellation blocks new allocations; correction/reallocation supersedes prior records and never destroys history.

## Ownership, security, and failure behavior

OperationalShipment owns the cargo item; ExecutionUnit owns its lifecycle eligibility; the allocation service coordinates without transferring either source of truth. Backend authorization checks Project, shipment, unit, organization, and action. Stale versions, duplicate keys, unit mismatch, ineligible state, and over-allocation return stable non-mutating errors. AI may recommend allocations but has no additional authority.

## Consequences and alternatives

Integrity and auditability improve at the cost of contention and explicit correction workflows. Rejected: last-write-wins, negative adjustments, destructive updates, implicit conversion, unbounded cross-shipment allocation, and asynchronous eventual enforcement of the quantity ceiling.

## Migration, rollback, and acceptance

No allocations are inferred from legacy text. Rollback disables writes and uses item totals without allocation projections while retaining records. Acceptance requires PDR-013-D08/D09, a proven concurrency design, precision policy, lifecycle matrix, deadlock/retry strategy, race/idempotency tests, audit evidence, and operational correction ownership.
