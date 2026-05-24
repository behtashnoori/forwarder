# Phase 5Z: Customer Complete-Step Service Extraction

## 1. Scope

This phase extracts only `POST /api/customer/complete-step` logic from `backend/routes/customer_gamification.py` into `backend/services/customer_gamification_service.py`.

Out of scope:

- customer registration behavior.
- email verification behavior.
- customer profile behavior.
- customer workflow read behavior.
- leaderboard behavior.
- frontend, schema, migration, auth/security, dependency, or repository changes.

## 2. Before

Before this phase, the route owned the complete-step flow:

- read JSON payload.
- validated `customer_id`, `request_id`, and `step_name` with the current truthiness behavior.
- looked up an existing workflow step by customer, request, and step name.
- returned the duplicate-completion response when the existing step was already completed.
- mapped step names to current point values and step order.
- updated an existing incomplete step or created a new completed workflow step.
- looked up the customer and applied points only when the customer existed.
- preserved the current missing-customer behavior by still creating the step and returning `total_points=0`, `customer_level="bronze"`.
- committed on success.
- rolled back and returned existing error payloads on database or unexpected failures.

## 3. Characterization Tests

Existing customer gamification contract tests already lock the complete-step behavior:

- missing payload returns the current 400 payload.
- success creates/completes the workflow step.
- success applies the current points and customer level behavior.
- duplicate completion returns the current 200 payload.
- missing customer still creates a step and returns the current fallback totals.
- commit failure rolls back created step and point mutation.

No new behavior was introduced.

## 4. Service Design

The complete-step service remains route-oriented and intentionally small:

- `complete_customer_workflow_step(payload)`
- `normalize_complete_step_payload(payload)`
- `validate_complete_step_payload(data)`
- `get_existing_customer_workflow_step(customer_id, request_id, step_name)`
- `get_complete_step_points(step_name)`
- `get_complete_step_order(step_name)`
- `create_or_update_completed_workflow_step(data, existing_step, points)`
- `get_customer_for_step_completion(customer_id)`
- `apply_complete_step_points(customer, points)`
- `build_complete_step_response_payload(step_name, points, customer)`

The service owns the same transaction and error mapping that the route previously owned. No repository layer was introduced.

## 5. Changes Made

- Moved complete-step validation, existing-step lookup, duplicate handling, points/order mapping, workflow-step mutation, customer points mutation, commit/rollback, and response construction into `customer_gamification_service.py`.
- Slimmed `POST /api/customer/complete-step` so it reads JSON, calls the service, and returns the service payload/status.
- Updated rollback tests to patch the service transaction boundary.
- Kept registration, email verification, profile, workflow read, and leaderboard runtime behavior unchanged.

## 6. Endpoint Contract Preservation

Preserved:

- URL: `POST /api/customer/complete-step`
- public/no-auth behavior.
- status codes.
- response shapes.
- required-field payload.
- duplicate-completion payload.
- success payload keys: `message`, `points_earned`, `total_points`, `customer_level`.
- 500 error payloads.

## 7. Side Effect Preservation

Preserved:

- existing completed step short-circuit.
- existing incomplete step update behavior.
- new `CustomerWorkflowStep` creation behavior.
- current point values and step order mapping.
- missing-customer behavior, including step creation and fallback response values.
- customer loyalty point mutation when the customer exists.
- commit on success.
- rollback on database or unexpected failures.

No separate reward behavior was present in the current route logic.

## 8. After

After this phase, the complete-step route is a thin controller and the service owns the complete-step business logic. The customer gamification write-side extraction is now service-backed for registration, email verification, and complete-step.

## 9. Deferred Items

- product cleanup for the missing-customer complete-step behavior.
- reward behavior redesign, if needed.
- OpenAPI documentation.
- repository layer.
- frontend refactor.
- warning cleanup.
