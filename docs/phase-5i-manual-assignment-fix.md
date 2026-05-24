# Phase 5I: Manual Assignment Fix

## Scope

This phase fixes only `POST /api/user-management/manual-assignment`.

No migration, model/schema change, frontend change, auth decorator change, repository layer, or assignment statistics change is included.

## Before

The endpoint ignored the request body, called `assignment_service.preserve_manual_assignment_failure()`, raised an intentional `RuntimeError`, rolled back, and returned:

```json
{"error": "خطا در ارجاع دستی"}
```

with status `500`.

## New Contract

The endpoint remains admin-only and now requires:

- `request_id`
- `expert_id`

Responses:

- Missing `request_id`: `400`, `{"error": "شناسه درخواست الزامی است"}`
- Missing `expert_id`: `400`, `{"error": "شناسه کارشناس الزامی است"}`
- Missing request: `404`, `{"error": "درخواست یافت نشد"}`
- Missing expert: `404`, `{"error": "کارشناس یافت نشد"}`
- Inactive expert: `400`, `{"error": "کارشناس غیرفعال است"}`
- Success: `200`, shared assignment payload with `message` and `assigned_to`

## Service Design

`assignment_service.manual_assign_request(payload, actor, remote_addr)` validates the manual payload and delegates to `assign_request_to_expert`.

`assign_request_to_expert` now rejects inactive experts before mutating the request.

## Side Effects

Successful manual assignment uses the shared direct assignment path:

- updates `ShipmentRequest.assigned_to`
- sets `ShipmentRequest.status = "assigned"`
- sets `ShipmentRequest.has_unread_for_assignee = True`
- creates `ExpertConsoleLog(action="assignment")`
- creates `ExpertConsoleNotification(notification_type="assignment")`
- commits atomically

It does not create `AssignmentLog`, matching the current direct assignment behavior.

## Tests

Coverage was updated in:

- `backend/tests/test_user_management_contract.py`
- `backend/tests/test_expert_assignment_referral_contract.py`

The tests cover validation, not-found cases, inactive expert rejection, success side effects, no `AssignmentLog`, and rollback after staged side effects.

## Deferred Items

- Manual assignment statistics semantics.
- Optional future `AssignmentLog(assignment_method="manual")` if product decides manual stats must count this endpoint.
- Frontend copy or UX updates, if needed.
