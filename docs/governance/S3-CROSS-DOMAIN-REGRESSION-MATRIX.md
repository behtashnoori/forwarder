# S3 — Cross-Domain Regression & Stabilization Matrix

Candidate: `76ba27f`. Development-only verification; no production access.

## Chain evidence

| Chain | Source → consumer | Evidence | Status |
| --- | --- | --- | --- |
| Geography → request | governed Country/InternationalCity → public selector → ShipmentRequest persistence | `test_governed_international_geography.py`, `test_iran_destination_point.py` | PASS |
| Request → shipment | Request and operational shipment remain separately governed aggregates | request/operational contract suites; no invented cargo conversion | NO_CURRENT_BUSINESS_CHAIN |
| Cargo → shipment | organization catalog → shipment cargo snapshot | `test_cargo_traceability.py`, `test_cargo_options_authorization.py` | PASS |
| Global reference → LogisticsPoint | global point → tenant adoption → materialized tenant point | adoption/materialization suites | PASS |
| LogisticsPoint → project | tenant point → ProjectLogisticsPoint | materialization Phase 4B and logistics suites | PASS |
| LogisticsPoint → tracking | tenant point → tracking update/snapshot | Phase 4B and `test_multi_unit_tracking_service.py` | PASS |
| Frontend → backend authorization | organization UI boundary → authenticated API/domain policy | frontend organization tests plus backend adoption/permission tests | PASS |

## Data scope and isolation

The tested scope remains: geography/global points = Platform Reference; adoption = tenant governance; LogisticsPoint/Cargo Catalog = tenant master data; request/shipment/tracking = transactional; shipment cargo snapshots = historical evidence. Focused cross-domain suite passed 54 tests, including tenant-negative and provenance cases. No scope leakage was found.

## Regression memory status

`RG-01..RG-07`, `LN-R01..LN-R08`, `VB-R01`, and `FE-R01..FE-R10`: **IMPLEMENTED**. Their controls remain in the S1, S2, S2.1 and S2.2 contracts/tests; this matrix consolidates evidence without deleting lineage.

## Verification environment and release risk

The active local venv was repaired with declared `jsonschema==4.25.1` and `tzdata`; both import checks pass and `ZoneInfo("Asia/Tehran")` resolves. Full backend verification passed `860 passed, 92 skipped, 1 xfailed`; frontend passed `163 passed`; build passed; lint has zero errors and 12 existing warnings.

The repository migration graph has exactly one head, `20260908_governed_international_geography`. A full clean upgrade was attempted on disposable SQLite and correctly stopped at historical PostgreSQL-only `ALTER COLUMN` DDL. A disposable local PostgreSQL fresh-upgrade/current check remains required before the human Release Gate. This is a **P1 release-gate prerequisite**, not a product defect or reason to alter migration history.
