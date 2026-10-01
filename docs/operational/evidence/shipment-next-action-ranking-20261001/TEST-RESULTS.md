# Shipment Next-Action Ranking — Test Results

`PRODUCT_SHA=5bf020f29cb1b331e2b5bbc78a2c426027759554`

| Gate | Result | Evidence |
| --- | --- | --- |
| Required ranking cases 1–8 | PASS | `backend/tests/test_guided_operational_projection.py` |
| Affected backend regression | PASS | 56 tests across guided projection, stages, closure, and delivery |
| Affected frontend regression | PASS | 16 tests across Operational Guidance, Shipment Summary, Shipment Stages, and Expert Home |
| Full frontend suite | PASS | 102 files / 486 tests |
| Production frontend build | PASS | Vite production build; advisory chunk-size/Browserslist warnings only |
| ESLint | PASS | 0 errors / 16 pre-existing advisory warnings |
| Guided Workspace browser journeys | PASS | 11 Chrome tests / 13 journey areas; PostgreSQL 18; head `20261015_org_shipment_stages` |
| Shipment stages browser journey | PASS | 1 Chrome test; PostgreSQL 18; head `20261015_org_shipment_stages` |
| Disposable runtime cleanup | PASS | Both owned PostgreSQL clusters and child app runtimes stopped and removed |
| Preserved walkthrough mutations | PASS | 0 business actions; read-only preservation snapshot only |

The focused backend file passed 5 tests, including explicit assertions for all eight required mission cases. The wider 56-test backend set passed with only existing framework warnings. The browser result metadata is recorded in `browser/result.json` and `shipment-stages/result.json`.
