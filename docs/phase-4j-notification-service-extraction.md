# Phase 4J: Expert Notification Service Extraction

## 1. Scope

Phase 4J was a narrow, low-risk extraction of expert notification logic from `backend/routes/expert_console.py` into `backend/services/notification_service.py`.

In scope:

- `GET /api/expert/notifications`
- `POST /api/expert/notifications/mark-read`
- Notification query/filtering, payload construction, unread counts, mark-read updates, and successful commit behavior.
- Existing route-level authentication decorators, request handling, response conversion, and error handling.

Out of scope: database migrations, model/schema changes, frontend changes, auth/security changes, quote logic, assignment/referral logic, request list/detail logic, message logic, new endpoints, dependency changes, and broad refactors.

## 2. Before

Before this extraction, notification logic lived directly in `backend/routes/expert_console.py` inside:

- `get_notifications()` for `GET /api/expert/notifications`
- `mark_notifications_read()` for `POST /api/expert/notifications/mark-read`

The route module directly handled:

- Expert-scoped notification queries.
- `unread_only` filtering.
- `created_at desc` ordering.
- `limit` coercion and capping at 200.
- Notification response payload construction.
- Unread-count query.
- Mark-all and mark-specific update queries.
- Commit on successful mark-read.
- Rollback on mark-read exceptions.

Pre-change checks were run before editing:

| Check | Result |
| --- | --- |
| `python -m pytest -q` | Passed: `64 passed` |
| `python -m pytest backend/tests/test_expert_assignment_referral_contract.py -q` | Passed: `4 passed` |
| `npm run lint` | Passed with existing warnings: `0 errors`, `17 warnings` |
| `npm run build` | Passed with existing Vite/Browserslist/chunk-size warnings |
| `npm run check:structure` | Passed |
| `git diff --check` | Passed |

## 3. Characterization Tests

`backend/tests/test_expert_assignment_referral_contract.py` was extended with a focused notification characterization test.

Locked behaviors:

- `GET /api/expert/notifications?unread_only=true&limit=1` returns the existing top-level keys: `notifications` and `unread_count`.
- Unread count remains scoped to the authenticated expert.
- Notification list remains scoped to the authenticated expert.
- Notification ordering remains newest-first by `created_at`.
- `limit` continues to limit returned notifications without changing unread count semantics.
- Empty mark-read payload still returns the existing `400` error payload.
- Specific notification mark-read updates only notifications belonging to the authenticated expert.
- A notification ID belonging to another expert is not marked read by the current expert.
- Successful mark-read payload remains `message` plus `marked_count`.

This test was added because the existing assignment/referral contract test covered notification response shape and mark-all at a high level, but did not explicitly lock user/expert scoping, newest-first ordering, invalid mark-read payload behavior, or cross-expert mark-specific behavior.

## 4. Service Design

| Service file | Function | Previous location | Responsibility | Behavior impact |
| --- | --- | --- | --- | --- |
| `backend/services/notification_service.py` | `list_notifications_for_expert(expert_id, filters=None)` | `get_notifications()` in `backend/routes/expert_console.py` | Query expert notifications with current unread filter, limit cap, ordering, and response payload assembly. | None; same query semantics and payload shape. |
| `backend/services/notification_service.py` | `build_notification_payload(notification)` | Inline loop in `get_notifications()` | Build the per-notification JSON payload. | None; same keys and values. |
| `backend/services/notification_service.py` | `build_notifications_response_payload(notifications, expert_id)` | Inline return payload in `get_notifications()` | Build top-level notifications response and include unread count. | None; same top-level keys. |
| `backend/services/notification_service.py` | `get_unread_count(expert_id)` | Inline count query in `get_notifications()` | Count unread notifications for the authenticated expert. | None; same count filter. |
| `backend/services/notification_service.py` | `mark_notifications_read(expert_id, payload=None)` | `mark_notifications_read()` in `backend/routes/expert_console.py` | Perform mark-all or mark-specific updates for the authenticated expert and commit on success. | None; same update filters, commit behavior, success payload, and invalid-payload signal. |

## 5. Changes Made

| File | Change summary | Reason | API behavior impact | Risk |
| --- | --- | --- | --- | --- |
| `backend/routes/expert_console.py` | Imported `notification_service` and replaced inline notification query/payload/update blocks with service calls. | Keep notification routes as thin controllers. | None intended; URL, method, decorator, status codes, payloads, and error handling preserved. | Low; only two target endpoints changed. |
| `backend/services/notification_service.py` | Added notification listing, payload-building, unread-count, and mark-read helpers. | Move notification business logic to service layer without a repository layer. | None intended; code mirrors previous inline behavior. | Low; no schema/model/dependency changes. |
| `backend/tests/test_expert_assignment_referral_contract.py` | Added notification characterization for scoping, ordering, unread count, invalid payload, and specific mark-read behavior. | Lock behavior around the extracted notification logic. | None; test only. | Low. |
| `docs/phase-4j-notification-service-extraction.md` | Added this phase report. | Document scope, before/after checks, design, preservation notes, and deferred work. | None. | Low. |

## 6. Endpoint Contract Preservation

| Endpoint | Method | Auth/role preserved? | Response shape preserved? | Status code preserved? | Error behavior preserved? | Read/unread behavior preserved? | Commit/rollback behavior preserved? | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `/api/expert/notifications` | `GET` | Yes; existing `@require_auth` retained. | Yes; `{notifications, unread_count}` and per-notification keys retained. | Yes; `200`, auth failure, and `500` behavior retained. | Yes; route keeps existing generic exception handler and Persian error payload. | Yes; `unread_only=true` filter and unread count for current expert retained. | Yes; no write/commit/rollback behavior was added. | Ordering remains `created_at DESC`; limit still defaults to 50 and caps at 200. |
| `/api/expert/notifications/mark-read` | `POST` | Yes; existing `@require_auth` retained. | Yes; success `{message, marked_count}` and invalid payload `{error}` retained. | Yes; `200`, `400`, auth failure, and `500` behavior retained. | Yes; invalid payload and exception payloads retained. | Yes; mark-all updates unread notifications for current expert; mark-specific updates matching current-expert notification IDs. | Yes; service commits on successful update; route still rolls back on exceptions. | No endpoint, model, or auth changes. |

## 7. After

Post-change checks:

| Check | Result |
| --- | --- |
| `python -m pytest -q` | Passed: `65 passed` |
| `python -m pytest backend/tests/test_expert_assignment_referral_contract.py -q` | Passed: `5 passed` |
| Targeted notification/expert tests | Covered by `test_expert_notification_contracts_scope_order_and_mark_read`; passed in targeted expert suite. |
| `npm run lint` | Passed with existing warnings: `0 errors`, `17 warnings` |
| `npm run build` | Passed with existing Vite/Browserslist/chunk-size warnings |
| `npm run check:structure` | Passed |
| `git diff --check` | Passed |

## 8. Deferred Items

Explicitly deferred and not changed in Phase 4J:

- Assignment service extraction.
- Referral service extraction.
- Expert request list/detail extraction.
- Message service extraction.
- Repository layer.
- Model split.
- Frontend refactor.
- CI/CD.
- OpenAPI documentation.
