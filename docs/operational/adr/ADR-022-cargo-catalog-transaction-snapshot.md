# ADR-022: Cargo Catalog and Transaction Snapshot Architecture

- **Status:** Proposed
- **Date:** 2026-08-01
- **Blocking:** SLICE-B3, SLICE-B4
- **Evidence:** [Discovery and Domain Analysis Report](../discovery-cargo-data-and-scroll-analysis-20260801.md)

## Context

Reusable cargo definitions help entry and search, but a mutable catalog cannot be the historical truth of what an OperationalShipment carried. Tenant ownership and customer-specific aliases must also prevent cross-customer correlation.

## Proposed decision

Separate **CargoCatalogItem** from **ShipmentCargoItem**. CargoCatalogItem is organization-owned by default, has an immutable organization-local canonical code, lifecycle/provenance, optional governed platform-definition link, and organization-scoped typed aliases. Identical part numbers may exist in different organizations. Alias conflicts fail closed and require governed reconciliation.

ShipmentCargoItem belongs to the OperationalShipment aggregate and is a transactional snapshot. It requires quantity, UnitOfMeasure, and display name; its catalog link is optional. Supplied part number, HS code, CargoType, and other approved declaration fields are snapshotted. Later catalog edits never rewrite the snapshot. Corrections create auditable revisions/supersession rather than destructive edits.

## Security, data, API, and migration

Authorization applies organization scope before item/alias lookup. Customer and AI projections are explicit allowlists; internal notes, values, and sensitive codes are excluded unless separately permitted. APIs use opaque identities, pagination, expected versions/idempotency for mutations, and never accept tenant scope solely from the client. Adoption is additive: legacy descriptions stay readable, optional links are mapped only with evidence, and new structured writes are feature-gated.

## Consequences and alternatives

The split preserves historical meaning, tenant isolation, and reusable entry/search but duplicates selected catalog fields intentionally. Rejected: catalog-reference-only history, global shared customer catalog, free-text-only transactions, cross-tenant part-number uniqueness, and generic EAV.

## Rollback and acceptance

Disable catalog/snapshot mutations and new projections, retain records for reconciliation, and serve legacy descriptions. Acceptance requires PDR-013-D05–D07/D11/D12, field classification, ownership/uniqueness rules, snapshot correction policy, tenant negative tests, and compatibility evidence.
