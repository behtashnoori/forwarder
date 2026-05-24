# Phase 5W: Customer Write Flow Characterization

## 1. Scope

This phase is characterization/documentation only.

No runtime code, API behavior, frontend, schema/model, migration, auth/security, dependency, behavior fix, or service extraction change was made.

## 2. Route Inventory

| endpoint | method | public/auth behavior | responsibility | side effects | risk level |
| --- | --- | --- | --- | --- | --- |
| `/api/customer/register` | POST | Public | Validate registration payload, normalize email/name fields, reject duplicate email, create customer, generate verification token, attempt verification email, and commit. | Creates `CustomerGamification`; stores token and expiry; attempts email-send helper; commits on success; rolls back on SQLAlchemy/general exception. | High |
| `/api/customer/verify-email` | GET | Public | Validate token, find unexpired customer token, mark email verified, clear token fields, award email-verification points, create workflow step, and commit. | Updates `CustomerGamification`; creates `CustomerWorkflowStep` with `shipment_request_id=0`; mutates points/level; commits on success; rolls back on SQLAlchemy/general exception. | High |
| `/api/customer/complete-step` | POST | Public | Validate required payload fields, create or update workflow step, award step points when customer exists, and commit. | Creates/updates `CustomerWorkflowStep`; updates `CustomerGamification.loyalty_points` when customer exists; commits on success; rolls back on SQLAlchemy/general exception. | High |

## 3. Current Behavior Map

### Registration

- Reads JSON payload with `email`, `phone`, optional `first_name`, and optional `last_name`.
- Requires non-empty normalized `email` and `phone`.
- Rejects invalid email if it lacks `@` or `.`.
- Rejects phone unless it is an 11-digit Iranian mobile-style value beginning with `09`.
- Normalizes email to lowercase and trims whitespace.
- Trims first and last name; stores missing names as `None`.
- If a customer with the normalized email already exists, returns `200` with existing `customer_id` and `is_verified`.
- On new customer:
  - generates a secure token.
  - stores a 24-hour expiry.
  - flushes the customer row.
  - calls `send_verification_email`.
  - commits even when the email helper returns `False`.
  - returns `201` with `message`, `customer_id`, and `email_sent`.
- New registration does not create an initial workflow step and starts with default points/level.
- SQLAlchemy errors roll back and return the current registration database-error payload.

### Email Verification

- Reads `token` from query string.
- Missing token returns `400`.
- Invalid or expired token returns `400` with the same invalid/expired token payload.
- Valid token:
  - sets `is_email_verified=True`.
  - clears `email_verification_token`.
  - clears `verification_expires_at`.
  - awards 10 loyalty points.
  - creates an `email_verified` workflow step with `shipment_request_id=0`.
  - commits.
  - returns `200` with `message`, `customer_id`, `loyalty_points`, and `customer_level`.
- SQLAlchemy errors roll back token, verified state, points, and workflow-step creation.

### Complete Step

- Reads JSON payload with `customer_id`, `request_id`, and `step_name`.
- Missing any required field returns `400`.
- If a matching completed workflow step already exists, returns `200` duplicate-completion payload without adding points again.
- Uses the current fixed step-point map:
  - `email_verified`: 10
  - `request_submitted`: 20
  - `expert_assigned`: 15
  - `expert_contacted`: 25
  - `quote_provided`: 30
  - `contract_signed`: 50
  - `shipment_picked_up`: 40
  - `shipment_delivered`: 100
- Existing incomplete step is marked completed and receives current points.
- Missing step creates a new `CustomerWorkflowStep` with the mapped order and points.
- If the customer exists, loyalty points and level are updated.
- Current behavior when customer lookup misses: the workflow step is still created, response is `200`, `total_points` is `0`, and `customer_level` is `bronze`.
- No related request or quote lookup is performed in this write flow.
- SQLAlchemy errors roll back created/updated step and point mutation.

## 4. Side Effects

Registration side effects:

- Creates one `CustomerGamification` row on successful new registration.
- Persists email verification token and expiration timestamp.
- Attempts email side effect through `send_verification_email`.
- Does not create workflow steps.
- Does not award points.
- Commits after email-send attempt.
- Rolls back flushed customer row on commit failure.

Email verification side effects:

- Updates customer verification state.
- Clears token lifecycle fields.
- Adds 10 loyalty points.
- Updates customer level via `update_loyalty_points`.
- Creates one `CustomerWorkflowStep` row for `email_verified`.
- Commits all changes together.
- Rolls back all staged changes on commit failure.

Complete-step side effects:

- Creates or updates one `CustomerWorkflowStep`.
- Sets `completed_at`, `is_completed`, and `points_earned`.
- Mutates customer points/level only when customer lookup succeeds.
- Current missing-customer behavior can create an orphan-like workflow step in the SQLite test environment.
- Commits step and point mutation together.
- Rolls back all staged changes on commit failure.

## 5. Characterization Tests Added

| test name | behavior locked | endpoint covered |
| --- | --- | --- |
| `test_customer_registration_contract` | Strengthened default new-customer side effects: token expiry exists, unverified state, zero points, bronze level, and no initial workflow step. | `POST /api/customer/register` |
| `test_customer_registration_email_failure_contract` | Email-send helper returning `False` still commits customer and returns `email_sent=False`. | `POST /api/customer/register` |
| `test_customer_registration_rollback_contract` | Commit failure returns current 500 payload and rolls back flushed customer row. | `POST /api/customer/register` |
| `test_customer_email_verification_and_complete_step_contract` | Strengthened expired-token behavior, verified-state mutation, token clearing, point mutation, email workflow-step creation, complete-step persisted fields. | `GET /api/customer/verify-email`, `POST /api/customer/complete-step` |
| `test_customer_complete_step_missing_customer_contract` | Current missing-customer behavior returns `200`, creates workflow step, and reports zero total points/bronze level. | `POST /api/customer/complete-step` |
| `test_customer_email_verification_rollback_contract` | Commit failure rolls back verified state, token clearing, points, and workflow step. | `GET /api/customer/verify-email` |
| `test_customer_complete_step_rollback_contract` | Commit failure rolls back created step and point mutation. | `POST /api/customer/complete-step` |

## 6. Risk Notes

- Email side effects are currently represented by a helper that logs and returns `True`; extraction must preserve the `False` branch because registration still commits.
- Token lifecycle is sensitive: generated token, expiry, clearing on verification, expired-token rejection, and rollback behavior all matter.
- Duplicate registration returns `200` rather than an error.
- Duplicate complete-step returns `200` and does not award points again.
- Points mutation depends on `CustomerGamification.update_loyalty_points`.
- Complete-step currently does not require request ownership validation and does not look up related request/quote rows.
- Complete-step currently creates a step even if customer lookup misses; this is characterized, not fixed.
- Partial commit risk exists in all three write flows, so service extraction must keep transaction boundaries unchanged.

## 7. Recommended Phase 5X

Recommended next phase: `Phase 5X: Customer Registration Service Extraction`

Reasoning:

- Registration is high-value but now has focused characterization around validation, duplicate behavior, token creation, email-send false behavior, default point/workflow state, and rollback.
- It does not mutate points or workflow rows, making it safer than `verify-email` or `complete-step` as the first write-flow extraction.
- `complete-step` should wait because it has point mutation and a currently surprising missing-customer side effect that should be preserved or deliberately fixed in a later product decision phase.

## 8. Deferred Items

- actual service extraction.
- behavior fixes.
- frontend updates.
- OpenAPI documentation.
- repository layer.
- complete-step product behavior decision.
- email delivery integration.
- warning cleanup.
