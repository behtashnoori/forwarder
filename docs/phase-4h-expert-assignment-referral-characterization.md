# Phase 4H: Expert Console / Assignment / Referral Characterization & Service Boundary Planning

Date: 2026-05-18

## 1. Scope

Phase 4H is characterization and service-boundary planning only. It intentionally does **not** refactor expert console, assignment, or referral runtime code.

Allowed work completed in this phase:

- Reviewed expert console, user management assignment, admin referral, referral engine, related models, and existing tests.
- Added focused characterization tests for current behavior.
- Documented current workflows, route inventory, business logic embedded in routes, direct DB access, side effects, extraction risks, and service-boundary proposals.

Out of scope and not changed:

- No migrations.
- No model/schema changes.
- No API contract changes.
- No response shape/status-code changes.
- No auth/role changes.
- No frontend changes.
- No expert/assignment/referral route refactor.
- No new dependencies.

## 2. Current Workflow Map

### Expert console

1. Expert authentication uses `/api/expert/auth/login`, `/api/expert/auth/refresh`, and `/api/expert/auth/logout`.
   - Login validates username/password through `AuthManager`, returns expert profile and token payload, and adds CORS compatibility headers.
   - Refresh validates a refresh token and returns a new token payload.
   - Logout currently returns a success message; token blacklist is noted as future production work.
2. Expert request list uses `/api/expert/requests`.
   - Any authenticated user can call it.
   - Non-admin users only see requests assigned to their user id.
   - Admin users may optionally filter by `assigned_to`.
   - The route applies status, priority, search, sort, pagination, location lookup, assignee lookup, SLA status calculation, and response serialization inline.
3. Expert request detail uses `/api/expert/requests/<request_id>`.
   - Admin can read any request; non-admin users can read only assigned requests.
   - The route loads shipment request, locations, assigned expert, timeline logs, messages, latest quote, SLA status, and serializes a large detail payload inline.
4. Expert mutations include assignment, status updates, quote creation, message creation, notification reads/updates, mark-read, and expert list.
   - Most mutations write the request, add one or more log rows, optionally add notifications, and commit.
   - Errors rollback where mutation code already does so.

### Assignment

1. Expert-console assignment endpoint `/api/expert/requests/<request_id>/assign` requires authentication and access to the request.
   - Despite the docstring saying only admin can assign, the actual access check allows admin or the current assignee.
   - It sets `assigned_to`, status `assigned`, `has_unread_for_assignee=True`, creates an `ExpertConsoleLog`, creates an assignment notification, and commits.
2. User-management assignment rules under `/api/user-management/assignment-rules` are admin-only.
   - Rule reads deserialize JSON conditions and include creator metadata.
   - Rule writes serialize conditions JSON and commit.
3. User-management manual assignment endpoint `/api/user-management/manual-assignment` is admin-only but currently returns `500` before validation due to local variable shadowing of Flask `request` by a later local `request = db.session.query(...)` assignment. Phase 4H only characterizes this current behavior; it does not fix it.

### Referral

1. Admin referral rules under `/api/admin/referral-rules` are admin-only.
   - Rule reads deserialize `conditions` and `action`, compute `action_type`, `pool_expert_count`, and `strategy`, and return `referral_rules`.
   - Create/update/delete validate action shapes and write JSON fields directly in route code.
2. Referral preview `/api/admin/referral-rules/preview` is admin-only.
   - It validates `request_id` and delegates dry-run selection to `referral_engine.preview_assignment`.
3. Auto assignment is currently in `backend/referral_engine.py`.
   - It selects active `expert`/`business_expert` users via time-based round-robin using `ReferralAssignmentLog` history.
   - It updates `ShipmentRequest.assigned_to`, sets status `assigned`, creates `ReferralAssignmentLog`, creates `ExpertConsoleLog`, creates notification, optionally creates gamification workflow step/points, and commits.

## 3. Route Inventory

| module | endpoint | method | auth/role | responsibility | direct DB access | side effects | risk level |
|---|---:|---|---|---|---|---|---|
| `expert_console.py` | `/api/expert/auth/login` | POST/OPTIONS | input validation only | login, token response, CORS compatibility headers | via `AuthManager` | updates `last_login_at` in auth layer | Medium |
| `expert_console.py` | `/api/expert/auth/refresh` | POST | input validation only | refresh access/refresh token payload | via `AuthManager` | none | Low |
| `expert_console.py` | `/api/expert/auth/logout` | POST | `require_auth` | logout success response | no direct DB in route | none currently | Low |
| `expert_console.py` | `/api/expert/requests` | GET | `require_auth` | filter/paginate expert requests; serialize list cards | `ShipmentRequest`, `Province`, `County`, `City`, `ExpertUser` | none | Medium |
| `expert_console.py` | `/api/expert/requests/<id>` | GET | `require_auth` + owner/admin check | request detail, timeline, messages, latest quote serialization | `ShipmentRequest`, locations, `ExpertConsoleLog`, `ExpertConsoleMessage`, `ExpertQuote`, `ExpertUser` | none | High |
| `expert_console.py` | `/api/expert/requests/<id>/assign` | POST | `require_auth` + owner/admin check | assign/reassign request | `ShipmentRequest`, `ExpertUser` | request update, `ExpertConsoleLog`, notification, commit | High |
| `expert_console.py` | `/api/expert/requests/<id>/status` | POST | `require_auth` + owner/admin check | validate/set request status | `ShipmentRequest` | request update, SLA set for assigned, `ExpertConsoleLog`, optional notification, commit | High |
| `expert_console.py` | `/api/expert/requests/<id>/quote` | POST | `require_auth` + owner/admin check | validate amount/date; create quote; set waiting status | `ShipmentRequest`, `ExpertUser`, `ExpertQuote` | quote insert, request update, log, notification, commit | Medium |
| `expert_console.py` | `/api/expert/requests/<id>/quote/latest` | GET | `require_auth` + owner/admin check | latest quote serialization | `ShipmentRequest`, `ExpertQuote` | none | Low |
| `expert_console.py` | `/api/expert/requests/<id>/messages` | POST | `require_auth` + owner/admin check | create internal/customer message | `ShipmentRequest`, `ExpertUser`, `ExpertConsoleMessage` | message insert, log insert, optional request status/touch update, commit | Medium |
| `expert_console.py` | `/api/expert/notifications` | GET | `require_auth` | notification list and unread count | `ExpertConsoleNotification` | none | Low |
| `expert_console.py` | `/api/expert/notifications/mark-read` | POST | `require_auth` | mark selected/all notifications read | `ExpertConsoleNotification` | bulk update, commit | Low |
| `expert_console.py` | `/api/expert/dashboard/kpis` | GET | `require_auth` | per-user/admin KPI counters | `ShipmentRequest` | none | Medium |
| `expert_console.py` | `/api/expert/requests/<id>/mark-read` | POST | `require_auth` + owner/admin check | mark request as read | `ShipmentRequest` | request update, commit | Low |
| `expert_console.py` | `/api/expert/experts` | GET | `require_auth` | list active experts | `ExpertUser` | none | Low |
| `user_management.py` | `/api/user-management/assignment-rules` | GET | `require_role("admin")` | assignment rule list | `AssignmentRule`, creator relationship | none | Low |
| `user_management.py` | `/api/user-management/assignment-rules` | POST | `require_role("admin")` | create assignment rule | `AssignmentRule` | insert, commit | Medium |
| `user_management.py` | `/api/user-management/assignment-rules/<id>` | PUT | `require_role("admin")` | update assignment rule | `AssignmentRule` | update JSON fields, commit | Medium |
| `user_management.py` | `/api/user-management/assignment-statistics` | GET | `require_role("admin")` | return assignment engine statistics | delegates `assignment_engine` | none | Low |
| `user_management.py` | `/api/user-management/manual-assignment` | POST | `require_role("admin")` | intended manual assignment | intended `ShipmentRequest`, `ExpertUser`, `AssignmentLog` | currently fails before intended side effects | High |
| `admin_panel.py` | `/api/admin/referral-rules` | GET | `require_role("admin")` | list referral rules and computed action metadata | `ReferralRule` | none | Low |
| `admin_panel.py` | `/api/admin/referral-rules` | POST | `require_role("admin")` | validate/create referral rule | `ReferralRule` | insert, commit | Medium |
| `admin_panel.py` | `/api/admin/referral-rules/<id>` | PUT | `require_role("admin")` | validate/update referral rule | `ReferralRule` | update, commit | Medium |
| `admin_panel.py` | `/api/admin/referral-rules/<id>` | DELETE | `require_role("admin")` | delete referral rule/state | `ReferralRule`, `ReferralRuleState` | delete, commit | Medium |
| `admin_panel.py` | `/api/admin/referral-rules/preview` | POST | `require_role("admin")` | preview referral selection | delegates `referral_engine` | none | Low |
| `referral_engine.py` | `auto_assign_request(request_id)` | function | caller-controlled | time-based round-robin assignment | `ShipmentRequest`, `ExpertUser`, `ReferralAutoAssignState`, `ReferralAssignmentLog` | request update, referral log, console log, notification, gamification, commit | High |
| `referral_engine.py` | `preview_assignment(request_id)` | function | caller-controlled | dry-run time-based round-robin preview | `ShipmentRequest`, `ExpertUser`, `ReferralAssignmentLog` | none | Low |

## 4. Characterization Tests Added

Added `backend/tests/test_expert_assignment_referral_contract.py`.

| test | behavior locked | endpoint/function covered |
|---|---|---|
| `test_expert_auth_login_refresh_logout_contract` | login success payload/CORS headers, refresh token payload, logout message | `/api/expert/auth/login`, `/api/expert/auth/refresh`, `/api/expert/auth/logout` |
| `test_expert_request_read_contracts_and_access_errors` | unauthenticated list error, list pagination/card shape, missing detail 404, forbidden detail 403, detail shape | `/api/expert/requests`, `/api/expert/requests/<id>` |
| `test_expert_assignment_status_quote_message_notification_contracts` | assignment validation/success payload and side effects; status validation/success; quote response/latest quote; message validation/success; notification list/mark-read; DB side effects | expert assignment/status/quote/message/notification endpoints |
| `test_assignment_and_referral_rule_read_and_manual_assignment_contracts` | admin role requirement; assignment rule list shape; referral rule list shape; referral preview missing-id and success shape; current manual-assignment 500 behavior caused by route shadowing bug | `/api/user-management/assignment-rules`, `/api/admin/referral-rules`, `/api/admin/referral-rules/preview`, `/api/user-management/manual-assignment` |

## 5. Service Boundary Proposal

### `expert_auth_service.py`

- Responsibility: isolate expert login/refresh/logout response orchestration while keeping `AuthManager` as the lower-level authentication primitive.
- Proposed functions:
  - `login_expert(username, password)`
  - `refresh_expert_tokens(refresh_token)`
  - `build_login_response(user_data, tokens)`
- Related routes:
  - `/api/expert/auth/login`
  - `/api/expert/auth/refresh`
  - `/api/expert/auth/logout`
- Extraction risk: Medium because login has CORS compatibility headers and lockout behavior via `AuthManager`.

### `expert_request_service.py`

- Responsibility: expert request query filters, access checks, list/detail serialization, SLA status, timeline/message/latest quote payloads.
- Proposed functions:
  - `can_access_request(req, current_user)`
  - `list_expert_requests(current_user, filters)`
  - `get_expert_request_detail(current_user, request_id)`
  - `build_expert_request_list_item(req)`
  - `build_expert_request_detail(req)`
  - `calculate_sla_status(req)`
- Related routes:
  - `/api/expert/requests`
  - `/api/expert/requests/<id>`
  - `/api/expert/dashboard/kpis`
  - `/api/expert/requests/<id>/mark-read`
- Extraction risk: High for detail, Medium for list/KPIs because response shapes are large and frontend-sensitive.

### `expert_assignment_service.py`

- Responsibility: manual/console assignment workflow and status changes.
- Proposed functions:
  - `assign_request(current_user, request_id, expert_id, remote_addr)`
  - `update_request_status(current_user, request_id, new_status, note, remote_addr)`
  - `mark_request_read(current_user, request_id)`
  - `create_assignment_log(...)`
  - `create_assignment_notification(...)`
- Related routes:
  - `/api/expert/requests/<id>/assign`
  - `/api/expert/requests/<id>/status`
  - `/api/user-management/manual-assignment`
- Extraction risk: High because assignment has overlapping admin/assignee authorization, logs, notifications, status changes, and the current user-management manual-assignment route has a characterized runtime bug.

### `quote_service.py`

- Responsibility: quote validation, creation, latest quote read, request status transition to waiting-for-customer, quote logs/notifications.
- Proposed functions:
  - `create_quote(current_user, request_id, payload, remote_addr)`
  - `get_latest_quote(current_user, request_id)`
  - `parse_quote_amount(amount)`
  - `parse_valid_until(value)`
  - `build_quote_payload(quote)`
- Related routes:
  - `/api/expert/requests/<id>/quote`
  - `/api/expert/requests/<id>/quote/latest`
- Extraction risk: Medium; bounded workflow with clear characterization coverage and a smaller surface than request detail or assignment.

### `expert_message_service.py`

- Responsibility: message validation/creation, message logs, customer-message request status/touch updates.
- Proposed functions:
  - `add_message(current_user, request_id, payload, remote_addr)`
  - `build_message_payload(message)`
- Related routes:
  - `/api/expert/requests/<id>/messages`
  - request detail message serialization
- Extraction risk: Medium because customer messages mutate request status and unread flags.

### `expert_notification_service.py`

- Responsibility: notification reads, unread counts, mark-read updates, notification creation helpers reused by assignment/status/quote/referral.
- Proposed functions:
  - `list_notifications(expert_id, unread_only=False, limit=50)`
  - `mark_notifications_read(expert_id, notification_ids=None, mark_all=False)`
  - `create_notification(expert_id, request_id, notification_type, title, message)`
- Related routes:
  - `/api/expert/notifications`
  - `/api/expert/notifications/mark-read`
  - assignment/status/quote/referral notification side effects
- Extraction risk: Low for read/mark-read, Medium for shared create helper.

### `assignment_rule_service.py`

- Responsibility: admin assignment rule read/write serialization.
- Proposed functions:
  - `list_assignment_rules()`
  - `create_assignment_rule(current_user, payload)`
  - `update_assignment_rule(rule_id, payload)`
  - `build_assignment_rule_payload(rule)`
- Related routes:
  - `/api/user-management/assignment-rules`
  - `/api/user-management/assignment-statistics`
- Extraction risk: Low for reads, Medium for writes.

### `referral_service.py`

- Responsibility: admin referral rule CRUD serialization/validation and preview orchestration.
- Proposed functions:
  - `list_referral_rules()`
  - `create_referral_rule(current_user, payload)`
  - `update_referral_rule(rule_id, payload)`
  - `delete_referral_rule(rule_id)`
  - `preview_referral_assignment(request_id)`
  - `build_referral_rule_payload(rule)`
- Related routes:
  - `/api/admin/referral-rules`
  - `/api/admin/referral-rules/<id>`
  - `/api/admin/referral-rules/preview`
  - `backend/referral_engine.py`
- Extraction risk: Low for list/preview, Medium for CRUD, High for auto-assignment engine internals.

## 6. Recommended Phase 4I Candidate

Recommended next candidate: **quote service extraction**.

Why this is the best Phase 4I slice:

- It is narrow and bounded to `/api/expert/requests/<id>/quote` and `/api/expert/requests/<id>/quote/latest`.
- It has strong Phase 4H characterization coverage.
- It touches a clear model cluster: `ExpertQuote`, `ShipmentRequest`, `ExpertConsoleLog`, `ExpertConsoleNotification`, `ExpertUser`.
- It avoids the largest/highest-risk areas: request detail serialization, assignment authorization ambiguity, referral engine commits, and the user-management manual-assignment bug.

Suggested Phase 4I constraints:

- No API/status/response/auth changes.
- Add/keep targeted quote characterization tests.
- Move only quote validation, quote creation, latest quote payload, and quote side effects into `backend/services/quote_service.py`.
- Do not change assignment/referral/message/request-list code in Phase 4I.

## 7. Deferred Items

- Full expert console route refactor.
- Assignment workflow refactor.
- Referral engine refactor.
- Fixing the characterized user-management manual-assignment runtime bug.
- Shipment service split.
- Repository layer.
- Model split.
- Frontend refactor.
- CI/CD changes.
- OpenAPI generation/spec cleanup.
- Timezone-aware datetime migration.
