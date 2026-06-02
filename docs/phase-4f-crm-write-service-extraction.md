# Phase 4F: CRM Write Service Extraction

Date: 2026-05-18

## Scope

Extract CRM write logic from `backend/routes/crm.py` into `backend/services/crm_write_service.py` while preserving the existing API contract.

## CRM Write Endpoints Identified

Existing write endpoints in `backend/routes/crm.py` before extraction:

- `POST /api/crm/customers` — create customer.
- `PUT /api/crm/customers/<customer_id>` — update customer.
- `POST /api/crm/opportunities` — create opportunity.
- `POST /api/crm/activities` — create activity.

No existing `PUT`/update endpoints were present for opportunities or activities, so Phase 4F did not add them. Adding those routes would change the API surface.

## Characterization Coverage Added Before Extraction

`backend/tests/test_crm_write_contract.py` locks current behavior for:

- Authentication requirement for CRM customer write access.
- Create customer status, response keys/message, default values, and DB commit.
- Update customer status, response message, missing-customer 404 response, and DB commit.
- Create opportunity status, response keys/message, defaults/date parsing, DB commit, invalid-date error response, and rollback/no extra row.
- Current absence of opportunity update route (`PUT /api/crm/opportunities/<id>` remains 404).
- Create activity status, response keys/message, defaults/date parsing, DB commit, invalid-date error response, and rollback/no extra row.
- Current absence of activity update route (`PUT /api/crm/activities/<id>` remains 404).

## Service Functions Added

`backend/services/crm_write_service.py` now owns write orchestration for existing CRM writes:

- `create_customer(data)`
- `update_customer(customer_id, data)`
- `create_opportunity(data)`
- `create_activity(data)`

The route handlers still own request body retrieval, `jsonify` response construction, existing error logging, and rollback on exceptions.

## Contract Preservation

- No migrations were created.
- No models or schemas were changed.
- No frontend files were changed.
- Auth/role decorators were unchanged.
- Existing URLs/methods/status codes/response shapes were unchanged.
- Existing commit-on-success and rollback-on-exception behavior was preserved.
