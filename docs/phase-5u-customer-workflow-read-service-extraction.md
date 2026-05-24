# Phase 5U: Customer Workflow Read Service Extraction

## 1. Scope

Phase 5U extracts only the read logic for `GET /api/customer/workflow/<customer_id>` from `backend/routes/customer_gamification.py` into `backend/services/customer_gamification_service.py`.

Out of scope: registration, email verification, customer profile behavior, workflow completion, points/reward mutation, leaderboard behavior, frontend changes, schema/model changes, migrations, auth/security changes, dependencies, and repository-layer work.

## 2. Before

Before this phase, the workflow route directly handled:

- shipment request ownership lookup by `customer_id` and `request_id`.
- workflow step query and ordering.
- fixed 8-step workflow definition.
- completed/progress calculations.
- assigned expert payload construction.
- latest quote lookup and payload construction.
- `workflow_steps_simple` payload inclusion.

The route also owned request-id validation and existing response/error payloads.

## 3. Characterization Tests

`backend/tests/test_customer_gamification_contract.py` already covered the workflow endpoint with an isolated SQLite test database.

This phase strengthened the workflow assertions to lock:

- top-level response keys.
- request identity, customer identity, status, shipping type, and created timestamp.
- assigned expert payload.
- workflow step shape, ordering, completion state, and point values.
- progress counters.
- `workflow_steps_simple` presence and length.
- latest quote shape and important fields.
- existing missing/invalid request-id and ownership/not-found errors.

## 4. Service Design

The existing `customer_gamification_service.py` remains a small read-service module.

Added functions:

- `get_customer_workflow_or_none(customer_id, request_id)`
- `list_customer_workflow_step_definitions()`
- `build_workflow_step_payload(step_definition, completed_step)`
- `build_assigned_expert_payload(shipment_request)`
- `build_latest_quote_payload(shipment_request)`
- `build_customer_workflow_payload(shipment_request, customer_id, request_id)`
- `get_customer_workflow_payload(customer_id, request_id)`

No repository layer was introduced.

## 5. Changes Made

- Moved workflow ownership lookup, workflow step payload construction, progress calculations, assigned expert payload construction, latest quote lookup, and final response assembly into `customer_gamification_service.py`.
- Kept request-id presence/type validation in the route to preserve exact existing 400 behavior.
- Kept the route as a thin controller that calls the service, handles the existing 404 ownership/not-found case, returns `jsonify(payload)`, and preserves the existing exception logging/error payload.
- Strengthened workflow characterization tests.

## 6. Endpoint Contract Preservation

Preserved for `GET /api/customer/workflow/<customer_id>`:

- URL and HTTP method.
- public/auth behavior.
- status codes.
- response shape.
- missing/invalid request-id payloads.
- ownership/not-found payload.
- generic error payload.
- workflow fields.
- step fields and fixed 8-step ordering.
- progress fields.
- latest quote fields.
- `workflow_steps_simple` behavior.

## 7. After

The route no longer owns workflow query logic or response assembly. Runtime behavior is intended to be identical, with the current contract locked by characterization tests.

## 8. Deferred Items

- Write-flow extraction for registration, email verification, workflow completion, and points mutation.
- Repository layer.
- Frontend refactor.
- OpenAPI documentation.
- Warning cleanup.
