# Catalog → Operational Cargo → Shared Transport → Tracking qualification

## Scope

This is a focused product-journey qualification.  Shared Transport A–I remains
locked at `PASS`; this document neither reruns nor reinterprets that slice.

## Canonical relationship audit

`CargoCatalogItem` is organization master data. `ShipmentCargoItem` is a
shipment-owned operational instance with its own opaque public identity and an
optional `catalog_item_id` reference. Quantity, UOM, and cargo owner belong to
the operational item. `ExecutionUnitCargoAllocation` references
`shipment_cargo_item_id` and `execution_unit_id`; there is no direct catalog to
execution relationship. Carrier remains on `ExecutionUnit`.

## Browser qualification

Each fresh disposable run seeded one catalog master only:
`CATALOG-JOURNEY-001` / `[CATALOG-JOURNEY] کالای عملیاتی`.
The operational cargo was not seeded. Through the actual product UI the
operator opened Shipment Cargo, selected that existing Catalog Item, supplied
line 2, quantity `12.5`, UOM, and Cargo Owner, then saved it. The browser then
opened Shared Transport, selected the newly created operational Cargo, allocated
it to `SHARED-E2E-UNIT`, and reopened Shipment Tracking.

Assertions covered persisted Catalog linkage, distinct Catalog/Cargo/Allocation/
Execution identities, quantity `12.500000`, UOM, Cargo Owner, shipment and
project lineage, eligible-cargo visibility, canonical allocation, and Tracking
projection. Shipment, Shared Transport, and Tracking were refreshed/reopened.
The test records zero unexpected console, page, or API errors.

The model audit and the exercised operations prove master separation: Catalog
has neither operational quantity nor owner, and allocation targets only the
ShipmentCargoItem. The UI-selected master code/name stayed the same while the
operational record and allocation were created.

## Independent runs and cleanup

| Run | Result | Cleanup |
| --- | --- | --- |
| 1 | PASS | PASS — disposable DB, runtime, processes, and credential removed |
| 2 | PASS | PASS — independent disposable DB, runtime, processes, and credential removed |

Validation: Python compile, TypeScript `--noEmit`, PowerShell runner execution,
two browser runs, and `git diff --check` all passed.
