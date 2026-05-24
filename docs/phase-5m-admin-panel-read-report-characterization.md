# Phase 5M: Admin Panel Reports/Dashboard Characterization

## Route Inventory

| Endpoint | Method | Auth | Responsibility | Current characterization |
| --- | --- | --- | --- | --- |
| `/api/admin/shipment-requests/<id>` | GET | admin | shipment request detail with location names | 200/404 shape locked |
| `/api/admin/shipment-requests` | GET | admin | filtered paginated request list | filter/date/pagination shape locked |
| `/api/admin/dashboard` | GET | admin | aggregate dashboard metrics | metric keys and counts locked |
| `/api/admin/reports/assignment-summary` | GET | admin | assignment report | current 500 payload locked |

Referral-rule routes are already service-backed and were not part of this phase.

## Remaining Business Logic

`backend/routes/admin_panel.py` still contains:

- direct query construction
- filter/date parsing
- bulk location lookup
- dashboard aggregations
- assignment report aggregations
- response payload assembly

## Existing Coverage

Direct admin panel read/report coverage was missing.

## Added Coverage

Added:

- `backend/tests/test_admin_panel_read_contract.py`

The tests cover request detail, list filters, invalid date handling, dashboard counts, and the current assignment-summary error payload.

## Important Finding

`GET /api/admin/reports/assignment-summary` currently returns `500` under the test environment because the route uses legacy SQLAlchemy `case([...])` syntax. This phase documents and locks the current behavior instead of fixing it.

## Suggested Low-Risk Extraction

Recommended next slice:

1. Fix and characterize assignment-summary if product expects it to work.
2. Extract dashboard metrics into `admin_dashboard_service.py`.

## Proposed Service Boundaries

- `admin_dashboard_service.py`: dashboard aggregate payload
- `admin_report_service.py`: assignment-summary report
- `admin_request_service.py`: request list/detail queries and payloads

## Recommended Phase 5N

Phase 5N should be a small admin dashboard/report stabilization phase:

- decide whether to fix assignment-summary 500 first
- then extract dashboard metrics only
