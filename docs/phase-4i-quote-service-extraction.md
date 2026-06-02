# Phase 4I: Quote Service Extraction

Date: 2026-05-18

## 1. Scope

Phase 4I is a limited quote-service extraction for the expert console quote endpoints only:

- `POST /api/expert/requests/<id>/quote`
- `GET /api/expert/requests/<id>/quote/latest`

No other expert console, assignment, referral, message, notification, request-list, or request-detail endpoint was refactored.

Out of scope and unchanged:

- No migrations.
- No model/schema changes.
- No frontend changes.
- No auth/role/decorator changes.
- No API contract changes.
- No assignment/referral/message/notification workflow refactor.
- No repository layer or new dependency.

## 2. Before

Before Phase 4I, quote logic lived inline in `backend/routes/expert_console.py`:

- `create_quote()` loaded the current user, parsed/validated quote amount/currency/note/valid-until, loaded the target request, checked access, loaded the expert, created `ExpertQuote`, updated the request status to `waiting_for_customer`, created `ExpertConsoleLog`, optionally created `ExpertConsoleNotification`, committed, and built the response payload.
- `get_latest_quote()` loaded the current user, loaded the target request, checked access, queried the latest quote, and built the `{"quote": ...}` response payload.

Endpoints reviewed:

| endpoint | method | previous location |
|---|---|---|
| `/api/expert/requests/<id>/quote` | POST | `backend/routes/expert_console.py:create_quote` |
| `/api/expert/requests/<id>/quote/latest` | GET | `backend/routes/expert_console.py:get_latest_quote` |

Checks run before runtime refactor:

- `python -m pytest -q` passed with `64 passed`.
- `python -m pytest backend/tests/test_expert_assignment_referral_contract.py -q` passed with `4 passed`.
- `npm run lint` passed with existing warnings.
- `npm run build` passed with existing non-blocking warnings.
- `npm run check:structure` passed.
- `git diff --check` passed.

## 3. Characterization Tests

`backend/tests/test_expert_assignment_referral_contract.py` was extended before extraction to lock additional quote-specific current behavior:

- Forbidden latest-quote access returns `403` with `{"error": "شما به این درخواست دسترسی ندارید"}`.
- Missing target request during quote creation returns `404` with `{"error": "درخواست یافت نشد"}`.
- Missing amount returns `400` with `{"error": "مبلغ الزامی است"}`.
- Non-numeric amount returns `400` with `{"error": "مبلغ باید عدد باشد"}`.
- Negative amount returns `400` with `{"error": "مبلغ نامعتبر است"}`.
- Existing success quote creation, latest quote read, request status side effects, log creation, notification creation, and response shape remain covered by the Phase 4H test.

These tests protect the quote API contract while allowing the implementation to move into a service.

## 4. Service Design

| service file | function | previous location | responsibility | behavior impact |
|---|---|---|---|---|
| `backend/services/quote_service.py` | `create_quote_for_request(request_id, payload, user, remote_addr=None)` | `expert_console.py:create_quote` | orchestrate quote validation, target request lookup, access check, expert lookup, quote creation, request status update, log/notification side effects, commit, and response payload | Preserved |
| `backend/services/quote_service.py` | `get_latest_quote_for_request(request_id, user)` | `expert_console.py:get_latest_quote` | load target request, enforce existing access behavior, return latest quote row or `None` | Preserved |
| `backend/services/quote_service.py` | `build_latest_quote_response_payload(quote)` | `expert_console.py:get_latest_quote` | build `{"quote": ...}` response payload | Preserved |
| `backend/services/quote_service.py` | `build_quote_payload(quote, include_created_by=False)` | both quote endpoints | serialize quote payload for create/latest shapes | Preserved |
| `backend/services/quote_service.py` | `normalize_quote_payload(payload)` | `expert_console.py:create_quote` | parse amount/currency/note/valid-until and preserve tolerant date parsing | Preserved |
| `backend/services/quote_service.py` | `get_quote_target_request_or_none(request_id)` | both quote endpoints | fetch target `ShipmentRequest` | Preserved |
| `backend/services/quote_service.py` | `can_access_quote_request(req, user)` | `_can_access_request` use in quote endpoints | preserve quote access rule: admin or assigned expert | Preserved |

## 5. Changes Made

| file | change summary | reason | API behavior impact | risk |
|---|---|---|---|---|
| `backend/services/quote_service.py` | Added focused quote service and quote-specific exception classes | Move quote business logic out of route while preserving behavior | None | Medium |
| `backend/routes/expert_console.py` | Replaced only POST quote and GET latest quote inline logic with calls to `quote_service`; kept decorators, current-user checks, `jsonify`, and generic error handlers | Thin quote route handlers without touching other expert-console workflows | None | Medium |
| `backend/tests/test_expert_assignment_referral_contract.py` | Extended existing characterization test with quote validation/not-found/forbidden cases | Lock current quote contract before/through extraction | None | Low |
| `docs/phase-4i-quote-service-extraction.md` | Added Phase 4I scope, before/after, tests, service design, contract preservation, and deferred items | Document architecture decision and verification | None | Low |

## 6. Endpoint Contract Preservation

| endpoint | method | auth/role preserved? | response shape preserved? | status code preserved? | error behavior preserved? | commit/rollback behavior preserved? | notes |
|---|---|---|---|---|---|---|---|
| `/api/expert/requests/<id>/quote` | POST | Yes, `@require_auth` unchanged and route still checks `get_current_user()` | Yes: success remains `{"ok", "quote", "request"}` | Yes: success `200`; validation `400`; not found `404`; forbidden `403`; generic error `500` | Yes, same Persian error payloads and debug-only generic error suffix | Yes, service commits on success; route rolls back on unexpected exception as before | Side effects preserved: quote row, request status/touch/unread update, console log, assigned notification |
| `/api/expert/requests/<id>/quote/latest` | GET | Yes, `@require_auth` unchanged and route still checks `get_current_user()` | Yes: `{"quote": null}` or `{"quote": {...}}` | Yes: success `200`; not found `404`; forbidden `403`; generic error `500` | Yes, same error payloads | Yes, read-only; no commit/rollback behavior added | Latest quote ordering remains `created_at DESC` |

## 7. After

Checks run after extraction:

- `python -m pytest -q` passed with `64 passed`.
- `python -m pytest backend/tests/test_expert_assignment_referral_contract.py -q` passed with `4 passed`.
- Targeted quote coverage is included in `backend/tests/test_expert_assignment_referral_contract.py::test_expert_assignment_status_quote_message_notification_contracts`.
- `npm run lint` passed with existing warnings.
- `npm run build` passed with existing non-blocking Browserslist/chunk-size warnings.
- `npm run check:structure` passed.
- `git diff --check` passed.

## 8. Deferred Items

- Assignment service extraction.
- Referral service extraction.
- Expert request list/detail extraction.
- Message service extraction.
- Notification service extraction.
- User-management manual-assignment bug fix/refactor.
- Repository layer.
- Model split.
- Frontend refactor.
- CI/CD.
- OpenAPI documentation.
