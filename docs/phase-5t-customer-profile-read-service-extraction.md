# Phase 5T: Customer Profile Read Service Extraction

## 1. Scope

Phase 5T extracts only the read logic for `GET /api/customer/profile/<customer_id>` from `backend/routes/customer_gamification.py` into `backend/services/customer_gamification_service.py`.

Out of scope: registration, email verification, workflow reads, workflow completion, points mutation, leaderboard behavior, frontend changes, schema/model changes, migrations, auth/security changes, dependencies, and repository-layer work.

## 2. Before

Before this phase, the customer profile route directly queried:

- `CustomerGamification` for the target customer.
- `CustomerWorkflowStep` for the 10 most recent workflow steps.
- `ShipmentRequest` for the 5 most recent customer requests.

The route also assembled the full response payload inline and returned the same not-found and error payloads.

## 3. Characterization Tests

`backend/tests/test_customer_gamification_contract.py` already covered the profile endpoint with an isolated SQLite test database.

This phase strengthened the profile assertions to lock:

- public success status code.
- top-level keys: `customer`, `recent_steps`, `recent_requests`.
- customer profile, points, and progress fields.
- recent workflow step shape and values.
- recent request shape and assigned expert payload.
- existing not-found behavior.

## 4. Service Design

The existing `customer_gamification_service.py` remains a small read-service module.

Added functions:

- `get_customer_profile_or_none(customer_id)`
- `build_customer_profile_payload(customer)`
- `get_customer_profile_payload(customer_id)`

No repository layer was introduced.

## 5. Changes Made

- Moved customer profile lookup and payload building into `customer_gamification_service.py`.
- Kept the route as a thin controller that calls the service, handles the existing 404 case, returns `jsonify(payload)`, and preserves the existing exception logging/error payload.
- Strengthened profile characterization tests.

## 6. Endpoint Contract Preservation

Preserved for `GET /api/customer/profile/<customer_id>`:

- URL and HTTP method.
- public/auth behavior.
- status codes.
- response shape.
- not-found payload.
- generic error payload.
- customer profile fields.
- loyalty/points/progress fields.
- recent workflow step fields and ordering/limit.
- recent request fields and ordering/limit.

## 7. After

The route no longer owns the profile query or response assembly. Runtime behavior is intended to be identical, with the existing contract locked by characterization tests.

## 8. Deferred Items

- Workflow read service extraction.
- Write-flow extraction for registration, email verification, workflow completion, and points mutation.
- Repository layer.
- Frontend refactor.
- OpenAPI documentation.
- Warning cleanup.
