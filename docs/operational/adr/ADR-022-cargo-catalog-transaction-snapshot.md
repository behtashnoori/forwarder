# ADR-022: Cargo Catalog and Transaction Snapshot Architecture

- **Status:** Accepted for Release 1.6.0 bounded cargo catalog and shipment snapshot slice
- **Accepted:** 2026-08-02 under the [Release 1.6.0 Cargo Governance Closure](../release-1.6.0-cargo-governance-closure.md)
- **Approvers:** Architecture, Security, Data, Product, Operations
- **Date:** 2026-08-01
- **Governed slice:** Bounded SLICE-B3 Cargo Catalog and SLICE-B4 Shipment Cargo Item foundation
- **Evidence:** [Discovery and Domain Analysis Report](../discovery-cargo-data-and-scroll-analysis-20260801.md)

## Context

Reusable cargo definitions help entry, but a mutable catalog cannot be the historical truth of what an OperationalShipment carried. Tenant ownership and customer-specific aliases must prevent cross-customer correlation. Release 1.6.0 requires only the internal cargo catalog and shipment snapshot foundation; later allocation and customer-search architecture remains undecided.

## Accepted decision

Separate **CargoCatalogItem** from **ShipmentCargoItem**. CargoCatalogItem is organization-scoped, has an opaque public ID and immutable organization-local code, requires CargoType, supports activation/deactivation, and has organization-inherited typed aliases. Identical part numbers may exist in different organizations. A platform-global catalog and canonical/global definition link are not included in Release 1.6.0. Alias conflicts fail closed.

ShipmentCargoItem belongs to the OperationalShipment aggregate and is a transactional snapshot. It requires a shipment-unique line number, CargoType, positive quantity, UnitOfMeasure, and display name; its same-organization catalog link is optional. Approved catalog, CargoType, and UOM facts are snapshotted at creation. Later source edits and ordinary line updates never silently regenerate snapshots. Destructive rewriting is prohibited; correction/revision/supersession implementation is deferred.

## Security, data, API, and migration

Authorization applies organization scope before item or alias lookup. Release 1.6.0 APIs and UI are internal-only and use role-specific allowlists. APIs use opaque identities, bounded pagination, optimistic concurrency, and never accept tenant scope solely from the client. Adoption is additive: legacy descriptions remain readable, catalog links remain optional, and no guessed backfill occurs.

Catalog items and aliases use activation/deactivation instead of destructive removal after use. A catalog item must be active when selected for a new shipment line; existing historical links remain readable after deactivation. If tenant ownership, permission, catalog state, or snapshot evidence cannot be proven, access or mutation is denied.

## Consequences and alternatives

The split preserves historical meaning, tenant isolation, and reusable entry while intentionally duplicating selected catalog fields. Rejected for this release: catalog-reference-only history, a global shared customer catalog, free-text-only transactions, cross-tenant part-number uniqueness, generic EAV, or a canonical/global catalog-definition link.

## Explicit exclusions

This acceptance does not authorize ExecutionUnitCargoAllocation, delivery quantities, split/merge, correction/supersession implementation, customer cargo projection, customer search, PostgreSQL trigram/customer-search architecture, dashboards, reports, PackagingType, dangerous/perishable runtime attributes, service-package relationships, or new seed values. ADR-023 and ADR-024 remain Proposed.

## Rollback and supersession

Rollback disables catalog/snapshot mutations, retains records for reconciliation, and serves legacy descriptions. This bounded acceptance may be superseded only by a later Accepted ADR that names the affected boundary and reconciles applicable PDR, compatibility, migration, security, and rollback consequences.
