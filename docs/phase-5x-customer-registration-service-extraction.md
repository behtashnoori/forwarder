# Phase 5X: Customer Registration Service Extraction

## 1. Scope

Phase 5X extracts only `POST /api/customer/register` registration logic from `backend/routes/customer_gamification.py` into `backend/services/customer_gamification_service.py`.

Out of scope: email verification, profile read, workflow read, complete-step, leaderboard, points/workflow mutation behavior outside registration, frontend changes, schema/model changes, migrations, auth/security changes, dependencies, and repository-layer work.

## 2. Before

Before this phase, the registration route directly handled:

- JSON payload normalization.
- required-field, email, and phone validation.
- duplicate customer lookup.
- verification token generation.
- verification token expiry calculation.
- customer row creation and flush.
- verification email side-effect attempt.
- commit/rollback behavior.
- success, duplicate, validation, and error response payloads.

## 3. Characterization Tests

Phase 5W strengthened `backend/tests/test_customer_gamification_contract.py` around registration behavior:

- success response shape.
- default customer state.
- token and expiry persistence.
- no initial workflow step.
- duplicate registration response.
- email-send false branch behavior.
- rollback on commit failure.

Phase 5X updated the email-failure monkeypatch target to the extracted service helper while preserving the same behavior.

## 4. Service Design

Registration remains in `customer_gamification_service.py` alongside other customer gamification helpers.

Added functions:

- `generate_customer_verification_token()`
- `send_registration_verification_email(email, token, customer_name=None)`
- `normalize_registration_payload(payload)`
- `validate_registration_payload(data)`
- `create_customer_registration_record(data)`
- `build_duplicate_registration_response_payload(customer)`
- `build_registration_response_payload(customer, email_sent)`
- `register_customer(payload)`

No repository layer was introduced.

## 5. Changes Made

- Moved registration validation, duplicate lookup, token generation, customer creation, email-send attempt, commit/rollback, and payload construction into `customer_gamification_service.py`.
- Kept `POST /api/customer/register` as a thin route that reads JSON, calls the service, and returns `jsonify(payload), status_code`.
- Left email verification, profile read, workflow read, complete-step, and leaderboard routes unchanged except for removing registration-only helper code from the route module.

## 6. Endpoint Contract Preservation

Preserved for `POST /api/customer/register`:

- URL and HTTP method.
- public/auth behavior.
- validation status codes and payloads.
- duplicate registration status code and payload.
- success status code and payload.
- database-error and general-error payloads.
- normalized email/name behavior.
- phone validation behavior.

## 7. Side Effect Preservation

Preserved registration side effects:

- `CustomerGamification` row creation.
- verification token generation using secure random token generation.
- 24-hour verification expiry.
- verification email attempt after flush.
- `email_sent=False` still commits customer registration.
- no initial workflow step is created.
- default points and level remain unchanged.
- commit on success.
- rollback on SQLAlchemy/general exception.

## 8. After

The registration route no longer owns registration business logic. The service owns the behavior and returns the same payload/status tuple the route previously produced.

## 9. Deferred Items

- email verification service extraction.
- complete-step service extraction.
- behavior fixes.
- frontend updates.
- OpenAPI documentation.
- repository layer.
- warning cleanup.
