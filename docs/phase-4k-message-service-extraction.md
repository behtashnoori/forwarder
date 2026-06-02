# Phase 4K: Expert Message Service Extraction

## 1. Scope

Phase 4K was a narrow, low-risk extraction of expert message creation logic from `backend/routes/expert_console.py` into `backend/services/message_service.py`.

In scope:

- `POST /api/expert/requests/<int:request_id>/messages`
- Message payload normalization and validation.
- Target request lookup and current expert/admin access checks for message creation.
- Expert existence check.
- Message row creation.
- Message activity log creation.
- Current customer-message side effects on the shipment request.
- Successful commit behavior and existing route rollback behavior on unexpected errors.

Reviewed but not refactored in this phase:

- Message listing currently appears inside `GET /api/expert/requests/<int:request_id>` as part of request detail. That endpoint is request-detail logic, so it was not refactored in Phase 4K to honor the no request list/detail refactor constraint.

Out of scope: database migrations, model/schema changes, frontend changes, auth/security changes, quote logic, notification logic, assignment/referral logic, request list/detail refactors, new endpoints, dependency changes, and broad route-module refactors.

## 2. Before

Before this extraction, message creation logic lived directly in `backend/routes/expert_console.py` inside:

- `add_message()` for `POST /api/expert/requests/<int:request_id>/messages`

The route directly handled:

- Reading JSON body.
- Defaulting `type` to `internal_note`.
- Defaulting `subject` to an empty string.
- Validating required `content`.
- Loading the target `ShipmentRequest`.
- Enforcing the current `_can_access_request` behavior: admin can access any request; non-admin only if assigned.
- Loading the current `ExpertUser`.
- Creating `ExpertConsoleMessage`.
- Creating an `ExpertConsoleLog` with action `message_added`.
- For `customer_message`, setting request status to `waiting_for_customer`, updating `last_customer_touch_at`, and setting `has_unread_for_assignee`.
- Committing on success.
- Rolling back and returning the existing generic error payload on unexpected errors.

Pre-change checks were run before editing:

| Check | Result |
| --- | --- |
| `python -m pytest -q` | Passed: `65 passed` |
| `python -m pytest backend/tests/test_expert_assignment_referral_contract.py -q` | Passed: `5 passed` |
| `npm run lint` | Passed with existing warnings: `0 errors`, `17 warnings` |
| `npm run build` | Passed with existing Vite/Browserslist/chunk-size warnings |
| `npm run check:structure` | Passed |
| `git diff --check` | Passed |

## 3. Characterization Tests

`backend/tests/test_expert_assignment_referral_contract.py` was extended with `test_expert_message_contracts_access_creation_and_listing`.

Locked behaviors:

- A non-assigned expert cannot create a message for a request assigned to another expert and receives the existing `403` payload.
- A missing request returns the existing `404` payload when content validation passes.
- A valid internal note returns the existing success shape: `message` and `message_id`.
- Internal notes do not change the shipment request status.
- Message creation persists the expected `ExpertConsoleMessage` values.
- Message creation adds the expected `message_added` log entry.
- Request-detail message listing keeps the current per-message shape and newest-first behavior for the created message.

The existing mutation characterization test already covered missing content, successful `customer_message`, status side effects, and message row count. The new test fills gaps around access/not-found behavior, internal-note side effects, log creation, and listing payload shape without requiring a real database.

## 4. Service Design

| Service file | Function | Previous location | Responsibility | Behavior impact |
| --- | --- | --- | --- | --- |
| `backend/services/message_service.py` | `create_message_for_request(request_id, payload, user, remote_addr=None)` | `add_message()` in `backend/routes/expert_console.py` | Create an expert console message, create the message log, apply current customer-message request side effects, commit, and return the current success payload. | None; same endpoint behavior and response shape. |
| `backend/services/message_service.py` | `normalize_message_payload(payload)` | Inline code in `add_message()` | Preserve current defaulting and required-content validation. | None; same default values and validation error. |
| `backend/services/message_service.py` | `build_create_message_response_payload(message)` | Inline return payload in `add_message()` | Build the successful POST message response payload. | None; same keys and message text. |
| `backend/services/message_service.py` | `build_message_payload(message)` | Inline request-detail message formatter in `get_shipment_request_detail()` | Centralize the existing per-message payload shape for future request-detail extraction without changing the request-detail endpoint in this phase. | None; helper only, no route behavior change. |
| `backend/services/message_service.py` | `get_message_target_request_or_none(request_id)` | Inline request lookup in `add_message()` | Load the target shipment request. | None; same not-found behavior. |
| `backend/services/message_service.py` | `can_access_message_request(req, user)` | `_can_access_request()` call in `add_message()` | Preserve admin-or-assigned-expert access behavior for message creation. | None; same access rules. |
| `backend/services/message_service.py` | `MessageServiceError` and subclasses | Inline route branches in `add_message()` | Carry current error payload text and HTTP status back to the thin route. | None; same status codes and error payloads. |

## 5. Changes Made

| File | Change summary | Reason | API behavior impact | Risk |
| --- | --- | --- | --- | --- |
| `backend/routes/expert_console.py` | Imported `message_service` and replaced inline message creation logic in `add_message()` with a service call. | Keep the target message route as a thin controller. | None intended; URL, method, decorator, status codes, payloads, and rollback behavior preserved. | Low; only the message creation endpoint changed. |
| `backend/services/message_service.py` | Added message validation, request access, creation, logging, side-effect, commit, response, and service-error helpers. | Move message business logic to the service layer without adding a repository layer. | None intended; logic mirrors the previous inline behavior. | Low; no model/schema/dependency changes. |
| `backend/tests/test_expert_assignment_referral_contract.py` | Added message characterization for access, missing request, internal-note creation, log side effects, status preservation, and listing shape. | Lock behavior around the extracted message logic. | None; test only. | Low. |
| `docs/phase-4k-message-service-extraction.md` | Added this phase report. | Document scope, before/after checks, service design, contract preservation, and deferred work. | None. | Low. |

## 6. Endpoint Contract Preservation

| Endpoint | Method | Auth/role preserved? | Response shape preserved? | Status code preserved? | Error behavior preserved? | Commit/rollback behavior preserved? | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `/api/expert/requests/<int:request_id>/messages` | `POST` | Yes; existing `@require_auth` retained. | Yes; success remains `{message, message_id}` and errors remain `{error}`. | Yes; `200`, `400`, `401`, `403`, `404`, and `500` behavior preserved. | Yes; required content, missing request, forbidden access, missing expert, and generic unexpected-error payloads preserved. | Yes; service commits on success; route still rolls back on unexpected exceptions. | `customer_message` still sets status to `waiting_for_customer`, updates `last_customer_touch_at`, and sets `has_unread_for_assignee`. |

## 7. After

Post-change checks:

| Check | Result |
| --- | --- |
| `python -m pytest -q` | Passed: `66 passed` |
| `python -m pytest backend/tests/test_expert_assignment_referral_contract.py -q` | Passed: `6 passed` |
| Targeted message/expert tests | Covered by `test_expert_message_contracts_access_creation_and_listing`; passed in targeted expert suite. |
| `npm run lint` | Passed with existing warnings: `0 errors`, `17 warnings` |
| `npm run build` | Passed with existing Vite/Browserslist/chunk-size warnings |
| `npm run check:structure` | Passed |
| `git diff --check` | Passed |

## 8. Deferred Items

Explicitly deferred and not changed in Phase 4K:

- Assignment service extraction.
- Referral service extraction.
- Expert request list/detail extraction.
- Repository layer.
- Model split.
- Frontend refactor.
- CI/CD.
- OpenAPI documentation.
