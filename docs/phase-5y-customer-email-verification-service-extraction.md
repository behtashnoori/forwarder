# Phase 5Y: Customer Email Verification Service Extraction

## 1. Scope

This phase extracts only `GET /api/customer/verify-email` email verification logic from `backend/routes/customer_gamification.py` into `backend/services/customer_gamification_service.py`.

Out of scope:

- customer registration behavior.
- customer profile behavior.
- customer workflow read behavior.
- complete-step behavior.
- leaderboard behavior.
- frontend, schema, migration, auth/security, dependency, or repository changes.

## 2. Before

Before this phase, the route owned the full email verification flow:

- read the `token` query parameter.
- returned the missing-token validation response.
- queried `CustomerGamification` by token and expiry.
- returned the invalid-or-expired token response.
- marked the customer email as verified.
- cleared the verification token and expiry.
- awarded 10 loyalty points.
- created the `email_verified` workflow step with `shipment_request_id=0`.
- committed the transaction.
- rolled back and returned the existing error payloads on failures.

## 3. Characterization Tests

Existing customer gamification contract tests already lock the email verification behavior:

- missing token returns the current 400 payload.
- invalid token returns the current 400 payload.
- expired token is treated like an invalid token.
- success returns the current response shape and mutates verified state.
- success clears token and expiry.
- success adds 10 points and creates the current workflow step.
- commit failure rolls back token, points, and workflow step changes.

No new behavior was introduced.

## 4. Service Design

The email verification service remains small and route-oriented:

- `verify_customer_email(token)`
- `get_customer_by_verification_token(token)`
- `apply_customer_email_verification(customer)`
- `apply_verification_points_and_workflow_effects(customer)`
- `build_email_verification_success_payload(customer)`

The service owns the same transaction and error mapping that the route previously owned. No repository layer was introduced.

## 5. Changes Made

- Moved token lookup, invalid-token handling, verified-state mutation, token clearing, points mutation, workflow-step creation, commit, rollback, and payload construction into `customer_gamification_service.py`.
- Slimmed `GET /api/customer/verify-email` so it reads the query parameter, calls the service, and returns the service payload/status.
- Kept registration, profile, workflow, complete-step, and leaderboard runtime behavior unchanged.

## 6. Endpoint Contract Preservation

Preserved:

- URL: `GET /api/customer/verify-email`
- public/no-auth behavior.
- status codes.
- response shape.
- missing-token payload.
- invalid/expired-token payload.
- success payload keys: `message`, `customer_id`, `loyalty_points`, `customer_level`.
- 500 error payloads.

## 7. Side Effect Preservation

Preserved:

- `is_email_verified=True`.
- `email_verification_token=None`.
- `verification_expires_at=None`.
- `customer.update_loyalty_points(10)`.
- `CustomerWorkflowStep` creation with `shipment_request_id=0`, `step_name="email_verified"`, `step_order=1`, `is_completed=True`, and `points_earned=10`.
- commit on success.
- rollback on database or unexpected failures.

## 8. After

After this phase, the route is a thin controller and the service owns the verification business logic. Customer gamification write-flow behavior is unchanged.

## 9. Deferred Items

- complete-step service extraction.
- email verification behavior redesign, if product requirements change.
- OpenAPI documentation.
- repository layer.
- frontend refactor.
- warning cleanup.
