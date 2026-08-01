# ADR-021: Master Data Governance and Explicit Domain Tables

- **Status:** Proposed
- **Date:** 2026-08-01
- **Blocking:** SLICE-B1, SLICE-B2
- **Evidence:** [Discovery and Domain Analysis Report](../discovery-cargo-data-and-scroll-analysis-20260801.md)

## Context

CargoType, ServiceType, and UnitOfMeasure need distinct semantics, constraints, stewardship, localization, and lifecycle. Free text or a generic attribute/value framework would weaken validation, discoverability, authorization, migration, and AI context. CAP-013 owns reference semantics, while Product decisions in PDR-013 remain Proposed.

## Proposed decision

Use explicit domain tables, not generic EAV or unbounded metadata-driven business logic. They share reusable governance and administration conventions: opaque identity, immutable unique code in the approved scope, bilingual display fields, active/inactive lifecycle, provenance, creator/updater and timestamps, optimistic version where edited, and auditable administrative actions. Used values are deactivated, never physically deleted. Foreign keys preserve integrity, and references retain valid historical display even after deactivation.

CargoType is hierarchical with cycle prevention and reserved system records. ServiceType is separate from TransportMode. UnitOfMeasure carries a governed measurement dimension—including count, weight, volume, length, and other explicitly approved dimensions—and forbids structured numeric cargo facts without their required UOM. Conversion factors and organization CargoType extensions are deferred until governed.

## Aggregate, security, data, and migration

Product and Data own domain meaning and stewardship through CAP-013; consumers reference each aggregate but do not mutate it. Administrative writes are permission-controlled, deny-by-default, and audited. Reads expose only approved active values except authorized historical/admin views. Migration is additive and nullable for legacy rows; no values are inferred. `UNCLASSIFIED` preserves unknown history. Expand/verify/switch precedes any contraction.

## Consequences and alternatives

Explicit models give strong constraints, clearer APIs, stable analytics, and permission-filtered AI context at the cost of more tables and stewardship. Rejected alternatives are free-text-only, one polymorphic reference table, generic EAV, deletion/reuse of codes, and immediate conversion.

## Rollback and acceptance

Rollback disables new writes/selectors and returns to legacy reads while retaining reference records and audit. Acceptance requires PDR-013-D01/D02/D04/D12, Data stewardship, reserved-code policy, hierarchy/UOM constraints, migration reconciliation, negative permission tests, and operational ownership.
