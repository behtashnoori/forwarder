# Phase 5Q: Admin Shipment Request Read Service Extraction

## 1. Scope

Phase 5Q extracts only these admin read endpoints from `backend/routes/admin_panel.py` into a service layer:

- `GET /api/admin/shipment-requests`
- `GET /api/admin/shipment-requests/<id>`

No frontend, schema, migration, auth, dashboard, assignment-summary, referral rule, user management, customer gamification, repository, dependency, or write endpoint changes are included.

## 2. Before

Before this phase, `admin_panel.py` directly owned:

- shipment request detail lookup
- detail location lookups
- assigned expert payload building
- list pagination parsing
- status, transport method, province, and date filters
- list sorting by `created_at` descending
- list bulk location lookup
- list item and pagination payload building

## 3. Characterization Tests

`backend/tests/test_admin_panel_read_contract.py` already covered:

- detail not-found behavior
- detail success shape
- list invalid date behavior
- list filtering by status and province
- list pagination response
- list item location shape

Phase 5Q strengthens characterization for:

- missing-token detail/list auth behavior
- non-admin detail/list role behavior

## 4. Service Design

The new service file is `backend/services/admin_shipment_request_service.py`.

The service exposes:

- `get_admin_shipment_request_detail(request_id)`
- `list_admin_shipment_requests(args)`
- `normalize_admin_request_filters(args)`
- `apply_admin_request_filters(query, filters)`
- `build_admin_request_detail_payload(shipment_request)`
- `build_location_lookups(shipment_requests)`
- `build_admin_request_list_item_payload(req, location_lookups)`
- `build_admin_request_list_response_payload(items, filters, total_count)`

It also defines `AdminShipmentRequestFilterError` for preserving the current invalid-date `400` response without moving Flask response construction into the service.

## 5. Changes Made

- Added `admin_shipment_request_service.py`.
- Moved read query, filter, pagination, sorting, location lookup, and payload-building logic into the service.
- Updated `admin_panel.py` so the two target routes are thin controllers.
- Extended admin read contract tests for auth/role behavior on the target endpoints.

## 6. Endpoint Contract Preservation

Preserved:

- URLs and HTTP methods
- admin role requirement
- status codes
- response shapes
- not-found response for detail
- invalid-date response for list
- list status filter
- list transport method filter
- list province filter
- list date filters
- list pagination
- list sorting by `created_at` descending
- detail payload and assigned expert shape
- route-level generic list error handling

No search behavior was present in the current route logic, so no search behavior was introduced.

## 7. After

After Phase 5Q, `admin_panel.py` keeps the target route decorators, reads path/query inputs, calls the service, and returns `jsonify` responses. The service owns the admin shipment request read logic.

## 8. Deferred Items

- Admin write endpoint extraction, if any write endpoints are introduced later.
- Repository layer extraction.
- SQLAlchemy 2.x cleanup of legacy `Query.get()` calls.
- Broader admin request search behavior, if product requirements define it later.
