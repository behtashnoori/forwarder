# Release 1.6.0 Cargo Governance Closure and Implementation Authorization

- **Status:** Accepted
- **Acceptance date:** 2026-08-02
- **Release:** 1.6.0 — Cargo Catalog and Shipment Cargo Foundation
- **Baseline:** Release 1.5.0, commit `9bc8d83d1611e161105d26227dea152561808176`, tag `v1.5.0`
- **Governed slices:** SLICE-B3 Cargo Catalog and bounded SLICE-B4 Shipment Cargo Item foundation
- **Decision source:** Release 1.6.0 Governance Decision Closure instruction
- **Authority:** This record accepts PDR-013-D05, PDR-013-D06, PDR-013-D07, the internal-only boundary of PDR-013-D11, and ADR-022 solely within the bounded scope below.

## Approvals recorded

| Decision | Approvers | Consultation |
| --- | --- | --- |
| PDR-013-D05 | Product, Data, Architecture, Security | Operations |
| PDR-013-D06 | Product, Data, Security | Architecture |
| PDR-013-D07 | Product, Architecture, Operations, Data, Security | — |
| PDR-013-D11 internal boundary | Product, Security, Data, Operations | Architecture |
| ADR-022 | Architecture, Security, Data, Product, Operations | — |

Approval is recorded by accountable function. This record does not infer individual approver names.

## Accepted decisions

### PDR-013-D05 — Cargo catalog scope and identity

`CargoCatalogItem` is organization-scoped. Its opaque public identifier is the only public identity; its immutable code is unique by `(organization_id, immutable_code)` and cannot change after creation. `CargoType` is required. Default UnitOfMeasure, Part Number, customer item code, HS Code, brand, model, and description are optional. Items support activation/deactivation. A used item cannot be hard-deleted. Cross-organization visibility is prohibited and access is denied if organization ownership cannot be proven. Platform-global and customer-global/shared catalogs and a canonical/global definition link are deferred.

### PDR-013-D06 — Alias policy

`CargoItemAlias` belongs to exactly one `CargoCatalogItem`, inherits organization scope from that parent, and is not an independent catalog item. It stores alias text, deterministic normalized alias, language, alias type, active state, and audit metadata. Normalized alias is unique within one catalog item; ambiguous collisions are rejected, never merged. Part Number and customer item code remain explicit item fields. Inactive aliases remain historically readable but are excluded from new active matching. Aliases prepare internal search only and authorize no public or customer search.

Accepted alias types are `COMMON_NAME`, `CUSTOMER_TERM`, `ABBREVIATION`, `LEGACY_TERM`, and `OTHER_GOVERNED`. Accepted language values are `fa`, `en`, and `und`. Normalization is governed by [Cargo alias normalization v1](cargo-alias-normalization-v1.md).

### PDR-013-D07 — Shipment cargo item contract

`ShipmentCargoItem` is a transactional child of `OperationalShipment`. Catalog linkage is optional and manual creation is allowed. Required fields are parent OperationalShipment, line number, CargoType, positive quantity, UnitOfMeasure, and display-name snapshot. Line number is unique within the parent shipment. UOM conversion, allocation, and delivered quantity are excluded.

Creation snapshots display name; CargoType code and titles; UOM code and symbol; and, when supplied, Part Number, customer item code, HS Code, brand, model, and description. Later catalog or master-data edits never rewrite snapshots, and ordinary updates never silently regenerate them. Historical correction/revision/supersession behavior is deferred; destructive historical rewriting is prohibited.

A linked catalog item must belong to the authorized organization and be active when selected for a new line. Historical links to subsequently inactive items remain readable. Creation or update is rejected when ownership or snapshot evidence is inconsistent. Existing `ShipmentRequest` cargo fields remain readable and unchanged; no automatic conversion, mapping, or backfill is authorized.

### PDR-013-D11 — Internal visibility boundary only

Catalog administration is available only to internal administrative users with explicit permission. Internal operational users may read/select catalog items only where permitted. Shipment cargo items are available only to internal users authorized for the parent OperationalShipment. Unauthorized and cross-organization lookups return a non-disclosing response, normally `404` where consistent with the existing security architecture.

Internal catalog responses may allowlist opaque public ID, immutable code, bilingual names, CargoType, default UOM, description, Part Number, customer item code, HS Code, brand, model, active state, version, and role-permitted audit timestamps. Internal shipment-item responses may allowlist opaque public ID, OperationalShipment-safe reference, line number, snapshots, quantity/UOM, linked/manual indicator, version, and permitted audit metadata. Numeric database IDs, cross-tenant identifiers, unrestricted actor internals, and fields not authorized for the role are prohibited.

Public APIs, customer projection, customer cross-Project search, public HS Code/customer-code/internal-description exposure, and customer dashboards/reports remain unauthorized.

## Release 1.6.0 implementation authorization

Authorized for reconciliation and, only after all technical gates pass, commit consideration:

- `CargoCatalogItem`, `CargoItemAlias`, and `ShipmentCargoItem`.
- Immutable creation-time transactional snapshots.
- Internal/admin APIs and Cargo Catalog administration UI.
- OperationalShipment Cargo Items UI.
- Additive migration `20260809_cargo_catalog_items` with no seed or guessed backfill.
- Tests, release metadata, and release evidence for this bounded scope.

Explicitly unauthorized:

- `ExecutionUnitCargoAllocation`, delivered quantity, split/merge, and correction/supersession implementation.
- Customer Cargo Search, customer cargo projection, public Cargo APIs, PostgreSQL trigram/customer-search architecture, exports, dashboards, and reports.
- `PackagingType`, dangerous/perishable runtime attributes, `ProjectService`, service-package relationships, and new seed catalog values.
- Release packaging, Production migration, deployment, backend restart, IIS switching, push, and tagging.

ADR-023 and ADR-024 remain Proposed. PDR-013-D08, D09, D10, and the customer/public portion of D11 remain Proposed.

## Supersession and fail-safe

This acceptance is superseded only by a later Accepted PDR/ADR that explicitly names the affected decision and compatibility impact. If organization ownership, authorization, catalog state, or snapshot evidence cannot be proven, access or mutation is denied. Deferred behavior remains absent rather than inferred.

