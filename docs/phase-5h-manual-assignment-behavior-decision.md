# Phase 5H: Manual Assignment Behavior Decision & Characterization

### 1. Scope

Phase 5H is decision-making and characterization only.

Only this endpoint is in scope:

- `POST /api/user-management/manual-assignment`

No runtime behavior, API contract, status code, response shape, database model, migration, frontend, auth/security logic, assignment side effect, dependency, or manual assignment implementation was changed.

### 2. Current Behavior

The current endpoint is defined in `backend/routes/user_management.py` and is protected by `@require_role("admin")`.

Current runtime behavior:

- The endpoint accepts any request body, but does not currently read or validate it.
- Payloads such as `{}` and `{ "request_id": ..., "expert_id": ..., "reason": ... }` behave the same.
- The route calls `assignment_service.preserve_manual_assignment_failure()`.
- `preserve_manual_assignment_failure()` intentionally raises `RuntimeError("manual assignment currently fails before processing payload")`.
- The route catches the exception in the generic `except Exception` branch.
- The route calls `db.session.rollback()`.
- The route logs `Error in manual assignment: ...`.
- The response status is `500`.
- The response payload is exactly `{ "error": "خطا در ارجاع دستی" }`.
- No shipment assignment is changed.
- No request status is changed.
- No `AssignmentLog` is created.
- No `ExpertConsoleLog` with `action="assignment"` is created.
- No `ExpertConsoleNotification` with `notification_type="assignment"` is created.

This behavior is intentionally preserved in Phase 5H.

### 3. Current Test Coverage

Current characterization coverage lives in:

- `backend/tests/test_user_management_contract.py`
- `backend/tests/test_expert_assignment_referral_contract.py`

The tests now lock:

- missing/empty payload returns `500`;
- valid-looking payload still returns `500`;
- response payload remains `{ "error": "خطا در ارجاع دستی" }`;
- target `ShipmentRequest.assigned_to` remains unchanged;
- target `ShipmentRequest.status` remains unchanged;
- no `AssignmentLog` is created;
- no assignment `ExpertConsoleLog` is created;
- no assignment `ExpertConsoleNotification` is created;
- route rollback removes a staged `AssignmentLog` when the service raises after a flush.

The tests use isolated in-memory SQLite databases and do not connect to a real database.

### 4. Problem Statement

The current `500` behavior is probably not the desired final product behavior.

Reasons:

- A manual assignment endpoint is visible as an admin action and should normally perform a controlled assignment.
- A successful admin manual assignment should likely update the request assignee and status.
- Client errors such as missing `request_id`, missing `expert_id`, missing request, missing expert, or inactive expert should not be represented as generic server errors.
- The endpoint currently ignores payload content, so admin panel users get the same 500 whether the input is malformed or valid.
- The current behavior creates no audit trail, no assignment log, and no notification, which makes the admin action invisible to reporting and expert workflows.
- Assignment statistics include `manual_assignments`, but the current endpoint can never increment that count.

### 5. Proposed Target Behavior

Recommended future behavior for Phase 5I, not implemented in Phase 5H:

- Required input:
  - `request_id`
  - `expert_id`
  - optional `reason`
- Missing `request_id` should return `400` with a validation payload.
- Missing `expert_id` should return `400` with a validation payload.
- Request not found should return `404`.
- Expert not found should return `404`.
- Inactive expert should return `400` or `409`; `400` is simpler if treated as validation, while `409` is better if treated as state conflict.
- Unauthorized/non-admin behavior should remain controlled by the existing `@require_role("admin")` decorator.
- Successful assignment should update:
  - `ShipmentRequest.assigned_to`
  - `ShipmentRequest.status = "assigned"`
  - `ShipmentRequest.has_unread_for_assignee = True`
- Successful assignment should commit atomically.
- Failure after staged side effects should rollback.
- The implementation should probably reuse `assignment_service.assign_request_to_expert` or a shared lower-level helper to stay consistent with direct expert assignment.
- If product wants manual assignment statistics, Phase 5I must decide whether to create `AssignmentLog(assignment_method="manual")` in addition to the existing expert-console assignment log.
- If expert notification parity matters, Phase 5I should create an expert notification consistently with direct assignment or deliberately standardize notification type across assignment flows.
- Direct expert assignment and admin manual assignment should converge on one shared assignment service path unless there is a documented product reason for different audit/logging semantics.

### 6. Proposed Phase 5I Plan

Recommended Phase 5I plan if a real fix is approved:

1. Define the final API contract for validation errors, not found errors, inactive expert errors, and success response.
2. Add characterization tests for the new intended behavior.
3. Add a service function such as `manual_assign_request(payload, actor, remote_addr)`.
4. Reuse `assignment_service.assign_request_to_expert` or extract a shared internal helper so direct and manual assignment share mutation semantics.
5. Decide and test whether manual assignment creates:
   - `ExpertConsoleLog`;
   - `ExpertConsoleNotification`;
   - `AssignmentLog(assignment_method="manual")`.
6. Preserve atomic transaction behavior with rollback on failure.
7. Update frontend/admin panel only if it depends on the current 500 behavior or needs new error display copy.
8. Document the final behavior in API/OpenAPI docs.

### 7. Risks

- API behavior change: fixing this endpoint will change current `500` responses to `2xx`, `4xx`, or possibly `409`.
- Frontend/admin panel impact: UI may currently only see a generic failure and may need success/error handling updates.
- Assignment side effects: request status, assignee, unread flags, logs, notifications, and statistics may begin changing.
- Log/notification duplication: using both direct assignment logging and assignment-engine logging could create duplicate or inconsistent audit records.
- Rollback/commit risk: partial assignment side effects must not persist after failures.
- Reporting risk: creating or not creating `AssignmentLog(assignment_method="manual")` changes assignment statistics.

### 8. Deferred Items

- Actual manual assignment fix.
- Frontend update if needed.
- OpenAPI documentation.
