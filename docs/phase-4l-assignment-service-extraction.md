# Phase 4L: Expert Assignment Service Extraction

## 1. Scope

Phase 4L was a narrow, low-risk extraction of expert assignment logic into `backend/services/assignment_service.py`.

In scope:

- `POST /api/expert/requests/<int:request_id>/assign`
- The currently documented `POST /api/user-management/manual-assignment` behavior, which remains a `500` response with no side effects.
- Assignment payload validation.
- Target shipment request lookup.
- Target expert lookup.
- Current assignment access behavior.
- Assignment side effects on `ShipmentRequest`.
- Expert-console assignment log creation.
- Expert-console assignment notification creation.
- Successful commit behavior and existing route rollback behavior on unexpected errors.

Reviewed but not refactored in this phase:

- Assignment rule read/create/update endpoints under `/api/user-management/assignment-rules`; these are assignment-rule administration endpoints, not the direct request assignment flow.
- Assignment statistics; this delegates to the existing assignment engine and was not part of limited assignment extraction.

Out of scope: database migrations, model/schema changes, frontend changes, auth/security changes, quote logic, message logic, notification listing/mark-read logic, referral logic, request list/detail refactors, assignment rule redesign, manual assignment behavior fixes, new endpoints, dependency changes, and broad route-module refactors.

## 2. Before

Before this extraction, direct request assignment logic lived directly in `backend/routes/expert_console.py` inside:

- `assign_request()` for `POST /api/expert/requests/<int:request_id>/assign`

The route directly handled:

- Reading JSON body.
- Validating required `expert_id`.
- Loading the target `ShipmentRequest`.
- Preserving current access behavior: admin can assign any request; non-admin can assign only requests currently assigned to them.
- Loading the target `ExpertUser`.
- Setting `assigned_to`, `status = "assigned"`, and `has_unread_for_assignee = True`.
- Creating an `ExpertConsoleLog` with action `assignment`.
- Creating an `ExpertConsoleNotification` with type `assignment`.
- Committing on success.
- Rolling back and returning the existing generic error payload on unexpected errors.

`POST /api/user-management/manual-assignment` was also reviewed. Its current behavior is documented by characterization tests as `500` for both empty and nominal valid payloads, with no assignment side effects. Phase 4L preserves that behavior and does not fix it.

Pre-change checks were run before editing:

| Check | Result |
| --- | --- |
| `python -m pytest -q` | Passed: `66 passed` |
| `python -m pytest backend/tests/test_expert_assignment_referral_contract.py -q` | Passed: `6 passed` |
| `npm run lint` | Passed with existing warnings: `0 errors`, `17 warnings` |
| `npm run build` | Passed with existing Vite/Browserslist/chunk-size warnings |
| `npm run check:structure` | Passed |
| `git diff --check` | Passed |

## 3. Characterization Tests

`backend/tests/test_expert_assignment_referral_contract.py` was extended with `test_expert_assignment_contracts_access_not_found_and_side_effects`.

Locked behaviors:

- A non-assigned expert cannot assign a request assigned to another expert and receives the existing `403` payload.
- A missing request returns the existing `404` payload.
- A missing target expert returns the existing `404` payload.
- A successful assignment returns the existing success shape: `message` plus `assigned_to` with `id` and `name`.
- A successful assignment sets `assigned_to` to the target expert.
- A successful assignment sets request status to `assigned`.
- A successful assignment sets `has_unread_for_assignee` to `True`.
- A successful assignment creates the expected expert-console assignment log.
- A successful assignment creates the expected expert-console assignment notification.

Existing tests continue to lock required `expert_id` validation, the larger mutation flow after assignment, assignment-rule read behavior, and the documented current `manual-assignment` `500` behavior.

## 4. Service Design

| Service file | Function | Previous location | Responsibility | Behavior impact |
| --- | --- | --- | --- | --- |
| `backend/services/assignment_service.py` | `assign_request_to_expert(request_id, expert_id=None, actor=None, payload=None, remote_addr=None)` | `assign_request()` in `backend/routes/expert_console.py` | Validate payload, load request/expert, enforce current access behavior, apply assignment side effects, create log/notification, commit, and return current response payload. | None; same endpoint behavior and response shape. |
| `backend/services/assignment_service.py` | `normalize_assignment_payload(payload)` | Inline code in `assign_request()` | Preserve required `expert_id` validation. | None; same validation error. |
| `backend/services/assignment_service.py` | `get_assignment_target_request_or_none(request_id)` | Inline request lookup in `assign_request()` | Load target shipment request. | None; same not-found behavior. |
| `backend/services/assignment_service.py` | `get_assignment_target_expert_or_none(expert_id)` | Inline expert lookup in `assign_request()` | Load target expert. | None; same not-found behavior. |
| `backend/services/assignment_service.py` | `can_assign_request(req, actor)` | `_can_access_request()` call in `assign_request()` | Preserve current admin-or-current-assignee assignment access rule. | None; same forbidden behavior. |
| `backend/services/assignment_service.py` | `create_assignment_log(...)` | Inline log creation in `assign_request()` | Create the existing expert-console assignment log. | None; same log fields. |
| `backend/services/assignment_service.py` | `create_assignment_notification_if_needed(...)` | Inline notification creation in `assign_request()` | Create the existing assignment notification. | None; same notification fields. |
| `backend/services/assignment_service.py` | `build_assignment_response_payload(expert)` | Inline return payload in `assign_request()` | Build successful assignment response. | None; same keys and text. |
| `backend/services/assignment_service.py` | `preserve_manual_assignment_failure()` | Current broken route behavior in `manual_assignment()` | Preserve the documented `500` manual-assignment behavior without side effects. | None; external API behavior remains the same. |
| `backend/services/assignment_service.py` | `AssignmentServiceError` and subclasses | Inline route branches in `assign_request()` | Carry current error payload text and HTTP status back to the thin route. | None; same status codes and error payloads. |

## 5. Changes Made

| File | Change summary | Reason | API behavior impact | Risk |
| --- | --- | --- | --- | --- |
| `backend/routes/expert_console.py` | Imported `assignment_service` and replaced inline direct assignment logic in `assign_request()` with a service call. | Keep the direct assignment route as a thin controller. | None intended; URL, method, decorator, status codes, payloads, side effects, and rollback behavior preserved. | Low; only the direct assignment endpoint changed. |
| `backend/routes/user_management.py` | Imported `assignment_service` and delegated manual-assignment to a service helper that preserves the currently documented `500` behavior. | Keep the manual assignment endpoint behavior explicitly preserved without redesigning or fixing it in this phase. | None intended; documented `500` behavior and no side effects preserved. | Low; behavior intentionally unchanged. |
| `backend/services/assignment_service.py` | Added assignment validation, request/expert lookup, access checks, assignment side effects, log/notification creation, commit, response, and error helpers. | Move direct assignment business logic to the service layer without adding a repository layer. | None intended; logic mirrors previous inline behavior. | Low; no model/schema/dependency changes. |
| `backend/tests/test_expert_assignment_referral_contract.py` | Added assignment characterization for access, missing request/expert, assignment side effects, log creation, and notification creation. | Lock behavior around the extracted assignment logic. | None; test only. | Low. |
| `docs/phase-4l-assignment-service-extraction.md` | Added this phase report. | Document scope, before/after checks, service design, contract preservation, and deferred work. | None. | Low. |

## 6. Endpoint Contract Preservation

| Endpoint | Method | Auth/role preserved? | Response shape preserved? | Status code preserved? | Error behavior preserved? | Side effects preserved? | Commit/rollback behavior preserved? | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `/api/expert/requests/<int:request_id>/assign` | `POST` | Yes; existing `@require_auth` retained. | Yes; success remains `{message, assigned_to}` and errors remain `{error}`. | Yes; `200`, `400`, `401`, `403`, `404`, and `500` behavior preserved. | Yes; missing expert id, missing request, forbidden access, missing expert, and generic unexpected-error payloads preserved. | Yes; `assigned_to`, `status`, `has_unread_for_assignee`, expert-console log, and assignment notification are preserved. | Yes; service commits on success; route still rolls back on unexpected exceptions. | Current access rule remains admin-or-current-assignee, matching existing `_can_access_request` behavior. |
| `/api/user-management/manual-assignment` | `POST` | Yes; existing `@require_role("admin")` retained. | Yes; documented failure remains `{error: "خطا در ارجاع دستی"}`. | Yes; documented current `500` behavior preserved. | Yes; generic manual-assignment failure payload preserved. | Yes; documented no-side-effect behavior preserved. | Yes; route still rolls back on exception. | Manual assignment behavior fix is explicitly deferred. |

## 7. After

Post-change checks:

| Check | Result |
| --- | --- |
| `python -m pytest -q` | Passed: `67 passed` |
| `python -m pytest backend/tests/test_expert_assignment_referral_contract.py -q` | Passed: `7 passed` |
| Targeted assignment/expert tests | Covered by `test_expert_assignment_contracts_access_not_found_and_side_effects`; passed in targeted expert suite. |
| `npm run lint` | Passed with existing warnings: `0 errors`, `17 warnings` |
| `npm run build` | Passed with existing Vite/Browserslist/chunk-size warnings |
| `npm run check:structure` | Passed |
| `git diff --check` | Passed |

## 8. Deferred Items

Explicitly deferred and not changed in Phase 4L:

- Referral service extraction.
- Expert request list/detail extraction.
- Assignment rule redesign.
- Manual assignment behavior fix.
- Repository layer.
- Model split.
- Frontend refactor.
- CI/CD.
- OpenAPI documentation.
