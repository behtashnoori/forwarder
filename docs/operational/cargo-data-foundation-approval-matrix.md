# Cargo Data Foundation Approval Matrix

- **Status:** Reconciled for B1 and Release 1.6.0 bounded B3/B4 closure
- **Date:** 2026-08-02
- **Authority:** None; this matrix does not accept a decision.
- **Decision record:** [Release 1.6.0 Cargo Governance Closure](release-1.6.0-cargo-governance-closure.md)
- **Discovery evidence:** [Discovery and Domain Analysis Report](discovery-cargo-data-and-scroll-analysis-20260801.md)

Legend: `R` = required approval; `C` = required consultation/review; `—` = not a named approval gate for this record.

| Decision/ADR | Product | Architecture | Operations | Security | Data | Blocking Slice |
|---|---:|---:|---:|---:|---:|---|
| PDR-013-D01 Master Data scope and ownership | R | R | R | C | R | B1 |
| PDR-013-D04 UnitOfMeasure | R | R | R | C | R | B1 |
| PDR-013-D12 Legacy classification | R | R | R | C | R | B1 |
| ADR-021 Explicit master-data tables | C | R | C | C | R | B1 |
| PDR-013-D02 Service cardinality | R | R | R | C | R | B2 |
| PDR-013-D03 Service ownership | R | R | R | R | C | B2 |
| PDR-013-D05 Catalog scope | R | R | C | R | R | B3 |
| PDR-013-D06 Codes and aliases | R | C | C | R | R | B3 |
| ADR-022 Catalog/snapshot architecture | C | R | C | R | R | B3 |
| PDR-013-D07 ShipmentCargoItem fields | R | R | R | R | R | B4 |
| PDR-013-D08 Allocation quantity | R | R | R | R | R | B5 |
| PDR-013-D09 Delivery/correction | R | R | R | R | R | B5 |
| ADR-023 Allocation integrity | C | R | R | R | R | B5 |
| PDR-013-D10 Customer search access | R | R | C | R | R | B6 |
| PDR-013-D11 Sensitive visibility | R | C | R | R | R | B6 |
| ADR-024 Tenant-scoped search | C | R | C | R | R | B6 |

## Approval timing

### Accepted for B1

PDR-013-D01, D04, D12 and ADR-021 were accepted on 2026-08-01 for the bounded SLICE-B1 Master Data Governance Foundation. This acceptance does not extend to other matrix rows.

### Required before B2

All B1 gates plus PDR-013-D02/D03 and B2 applicability confirmation for ADR-021.

### Accepted for bounded B3/B4 in Release 1.6.0

PDR-013-D05, D06, D07, the internal-only boundary of D11, and ADR-022 were accepted on 2026-08-02 by the approver functions recorded in the closure record. Authorization is limited to CargoCatalogItem, CargoItemAlias, ShipmentCargoItem, immutable creation-time snapshots, internal/admin APIs and UI, additive migration `20260809_cargo_catalog_items`, tests, and release evidence.

### Deferrable until allocation

PDR-013-D08/D09 and ADR-023 may remain Proposed through B1–B4. Allocation commands and projections must remain absent/disabled.

### Deferrable until customer search

PDR-013-D10, the customer/public portion of D11, and ADR-024 remain Proposed through B1–B5. The accepted internal-only D11 boundary does not authorize customer-facing catalog/item projection. Cross-Project search remains absent/disabled.

## Authorization verdict

The authoritative [Release 1.6.0 Cargo Governance Closure](release-1.6.0-cargo-governance-closure.md) accepts PDR-013-D05/D06/D07, internal-only D11 handling, and ADR-022 for the bounded CargoCatalogItem, CargoItemAlias, and ShipmentCargoItem implementation. ADR-023 and ADR-024 remain Proposed. Allocation, customer search/projection, dashboards, reports, and seed changes remain unauthorized.

SLICE-B1 is authorized and reconciled. Bounded SLICE-B3/B4 is authorized for Release 1.6.0 reconciliation. B2, B5, B6, and every capability outside the explicit closure scope remain unauthorized.

## Minimum B1 approval recommendation

These B1 rows are retained as historical decision evidence. Their named approvals are recorded; they do not expand the Release 1.6.0 B3/B4 authorization.

| Decision | Recommended Option | Approvers | Blocks B1 | Fail-safe if unresolved |
| --- | --- | --- | --- | --- |
| PDR-013-D01 | Explicit domain tables with shared governance; no generic EAV; Product/Data ownership; permission-controlled administration; immutable codes; deactivate rather than delete after use | Product, Data, Architecture, Operations | YES | Keep structured master-data writes disabled and retain legacy descriptions |
| PDR-013-D04 | Explicit UnitOfMeasure domain with immutable code, measurement dimension, bilingual name/symbol, exact-UOM matching first, conversion deferred, no generic Other, and no structured numeric fact without required UOM | Product, Data, Architecture, Operations | YES | Reject structured quantities that lack an active required UOM; do not infer or convert |
| PDR-013-D12 | Additive nullable adoption; no guessed backfill; legacy remains readable; new transactions use structure after rollout; audited manual classification for open records; closed history remains Unclassified unless curated | Product, Data, Operations, Architecture | YES | Retain the legacy read path and do not classify automatically |
| ADR-021 | Explicit tables for significant concepts; reusable governance infrastructure; FK integrity; bilingual labels; activation/deactivation; audit; historical references; no destructive delete or unbounded metadata-driven business logic | Architecture, Data (Product, Operations, and Security consulted) | YES | Do not implement SLICE-B1 or introduce generic metadata-driven business logic |

**Cargo implementation status: SLICE-B1 and bounded Release 1.6.0 SLICE-B3/B4 are authorized. B2, B5, B6, allocation, customer search/projection, dashboards, reports, and all other later capabilities remain unauthorized.**
