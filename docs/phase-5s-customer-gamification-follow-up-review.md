# Phase 5S: Customer Gamification Follow-up Review

## 1. Scope

Review/documentation only.

No runtime code, route refactor, API behavior, frontend, schema/model, migration, auth/security, dependency, or repository-layer change was made.

## 2. Route Inventory

| endpoint | method | auth/public behavior | responsibility | read/write | service used | remaining logic | risk level |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `/api/customer/register` | POST | Public | Register a customer, normalize email/name fields, create verification token, attempt email send, commit customer row. | Write | None | Validation, duplicate email lookup, token generation, email-send call, insert, flush/commit, rollback/error mapping all remain in route. | High |
| `/api/customer/verify-email` | GET | Public | Verify email token, clear token fields, award points, create workflow step, commit. | Write | None | Token validation, customer lookup, point mutation, workflow-step insert, commit/rollback, response payload remain in route. | High |
| `/api/customer/profile/<customer_id>` | GET | Public | Return customer profile, recent workflow steps, and recent requests. | Read | None | Customer lookup, recent step query, recent request query, assigned expert payload, response payload, not-found/error mapping remain in route. | Medium |
| `/api/customer/workflow/<customer_id>` | GET | Public | Return workflow state and request detail for one customer-owned shipment request. | Read | None | Request id parsing, ownership check, workflow definition list, workflow status payload, assigned expert payload, latest quote lookup, public tracking helper call, error mapping remain in route. | Medium |
| `/api/customer/complete-step` | POST | Public | Mark workflow step complete and award points. | Write | None | Required payload validation, duplicate completion behavior, step creation/update, customer point mutation, commit/rollback, response payload remain in route. | High |
| `/api/customer/leaderboard` | GET | Public | Return verified customer ranking by loyalty points. | Read | `customer_gamification_service.list_leaderboard_payload` | Route keeps only service call, `jsonify`, success status, and generic error mapping. | Low |

## 3. Current Service Coverage

`backend/services/customer_gamification_service.py` currently handles only leaderboard read behavior.

It contains:

- `list_leaderboard_payload()`
- `build_leaderboard_entry(customer, rank)`

The service preserves:

- verified-only filter
- ordering by `loyalty_points DESC`
- limit `20`
- rank starting at `1`
- anonymous-name fallback
- response shape with `leaderboard` and `total_customers`

No registration, email verification, profile, workflow, completion, or point mutation logic has been extracted.

## 4. Remaining Business Logic

The following still remains inside `backend/routes/customer_gamification.py`:

- email verification token generation helper
- email-send helper and frontend verification URL construction
- registration validation and normalization
- duplicate email behavior
- registration insert, flush, commit, rollback
- email verification token lookup and expiration check
- point mutation for email verification
- request-less workflow step creation for email verification
- profile customer lookup
- profile recent steps and recent requests queries
- workflow request id parsing
- workflow request ownership check
- hard-coded workflow step definitions
- workflow status payload construction
- latest quote lookup and payload construction
- workflow summary fields
- complete-step duplicate behavior
- complete-step workflow insert/update
- complete-step point mutation
- write-flow commit/rollback behavior

The remaining highest-risk logic is in write flows. The remaining lowest-risk service extraction is profile read.

## 5. Test Coverage Review

Current characterization coverage in `backend/tests/test_customer_gamification_contract.py` includes:

- Registration:
  - required fields
  - invalid email
  - invalid phone
  - success shape
  - duplicate email behavior
  - email/name normalization
  - verification token creation

- Email verification:
  - missing token
  - invalid token
  - success point mutation
  - customer level/points response

- Profile:
  - missing customer `404`
  - success top-level response shape
  - customer email field
  - recent step ordering/current first item
  - recent request assigned expert payload

- Workflow:
  - missing request id
  - invalid request id
  - wrong-customer ownership `404`
  - success identifiers
  - workflow step count
  - completed step count
  - total points earned
  - latest quote amount and creator

- Complete step:
  - missing fields
  - success point mutation
  - duplicate completion behavior
  - persisted single workflow step

- Leaderboard:
  - success response shape
  - verified-only behavior
  - ordering by loyalty points
  - limit `20`
  - rank values
  - anonymous-name fallback

Missing or weaker areas:

- registration email-send failure branch
- registration database rollback behavior under injected failure
- verify-email rollback behavior under injected failure
- complete-step rollback behavior under injected failure
- profile limit behavior for more than 10 steps or 5 requests
- workflow full payload key set
- workflow no-quote behavior
- workflow assigned-expert null behavior

The current tests are strong enough for a small read-only extraction, especially profile read. They are not yet broad enough to safely extract write flows without additional characterization.

## 6. Closure Decision

Decision: `NEEDS_ONE_MORE_EXTRACTION`

Rationale:

- Leaderboard is already service-backed and low risk.
- Profile and workflow reads still contain direct DB access and payload-building logic in the route.
- Write flows remain high risk and should not be extracted before stronger rollback and side-effect tests.
- A final small read-only extraction would reduce route complexity without touching mutation behavior.

## 7. Recommended Next Phase

Recommended next phase: `Phase 5T: Customer Profile Read Service Extraction`

Smallest safe slice:

- `GET /api/customer/profile/<customer_id>`

Why this slice:

- read-only
- no commit/rollback
- no point mutation
- no email token mutation
- no workflow completion side effects
- current characterization already covers missing customer, success top-level shape, recent steps, recent requests, and assigned expert payload

Out of scope for the next phase:

- registration
- email verification
- workflow completion
- point mutation
- leaderboard, because it is already extracted
- workflow read, because it is larger and includes request ownership, quote shape, hard-coded workflow definitions, and public tracking helper behavior

## 8. Deferred Items

- repository layer
- frontend refactor
- OpenAPI documentation
- deployment pipeline
- warning cleanup
- email delivery integration
- write-flow rollback characterization
- workflow read service extraction
- registration/email verification/complete-step service extraction
