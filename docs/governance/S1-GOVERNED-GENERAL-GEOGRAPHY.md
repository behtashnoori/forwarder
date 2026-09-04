# S1 — Governed General Geography

## Contract

| Concern | Contract |
| --- | --- |
| Domain / scope | Platform/shared reference data for the public international request selector. It is not tenant, tracking, corridor, or logistics-network data. |
| Country authority | ISO 3166-1 alpha-2. `Country.code` is the canonical business identity for newly governed data; `IR` and `TM` are required anchors. Legacy three-character values remain readable for compatibility and are not reinterpreted by S1. |
| International location authority | UNECE UN/LOCODE. `InternationalCity.un_locode`, when populated, stores its five-character code. It is not a Global Logistics Point identity. |
| Approved input | `backend/reference_data/international-geography-v1.json`, dataset `forwarder-international-geography-v1`, snapshot `2025-1`. |
| External authority | ISO and UNECE; the checked-in snapshot is the approved reproducible input, while the database is the runtime System of Record. |
| Owner / change authority | Reference Data Owner. Assignment to a named business person/team remains organizational governance. |
| Runtime network policy | No ISO/UNECE network fetch is permitted at runtime. |
| Reconciliation | Explicit, idempotent, deterministic and non-destructive. It adds missing snapshot rows but never deletes, rewrites stable identity, or reactivates an existing inactive row. |

`InternationalCity` remains the compatibility name. It presently represents the
public selector's city/port/airport-like transport-location projection. A future
rename to `InternationalLocation` requires a separate approved migration.

## Readiness contract

`backend.services.international_geography_readiness.readiness_report()` is a
read-only diagnostic suitable for tests and release/operational checks. It
detects invalid snapshot identity, missing required country/location records,
invalid UN/LOCODE ancestry, duplicate approved identities, and whether a record
exists separately from whether it is active/selectable. Intentional inactivity
is reported; it is not repaired or automatically treated as a missing record.

## Regression memory

| ID | Failure mode | Permanent control | Gate | Status |
| --- | --- | --- | --- | --- |
| RG-01 | Partial country dataset suppresses full reconciliation | partial-dataset S1 test | M6 | implemented |
| RG-02 | Foundational country disappears from selector | selector/readiness test | M6/M7 | implemented |
| RG-03 | Foundational location disappears from selector | required UN/LOCODE readiness test | M6/M7 | implemented |
| RG-04 | Reconciliation reactivates intentional inactive reference | inactive preservation test | M6 | implemented |
| RG-05 | Reconciliation is not idempotent | repeated-run test | M6 | implemented |
| RG-06 | Country/location identity drifts or duplicates | alpha-2 snapshot validation and `(country_id, un_locode)` constraint | M5/M6 | implemented |
| RG-07 | TM exists only in another domain | checked-in TM country + UNECE location test | M6/M7 | implemented |
| RG-08 | IR is active but lacks a governed international continuation or follows an Iran-only route | checked-in IR ISO/UNECE records, non-destructive reconciliation, selector/API origin-and-destination test | M6/M7 | implemented |
| VB-R01 | A governed migration advances the sole repository head while current-state head assertions retain the previous head | Update exact-current-head verification in the governed change or its immediate verification slice; retain the exact-one-head assertion | M5/M6 | implemented |
