# Phase 4D Public Tracking Service Extraction

Date: 2026-05-18

## 1. Scope

Phase 4D is a limited public-tracking-only extraction of read helpers from `backend/routes/public_tracking.py` into service modules. It moves request resolution, quote/assignment/geography reads, public response assembly, and timeline construction while keeping the public route responsible for path handling, service invocation, `jsonify`, status codes, and existing error handling.

No API URL, HTTP method, response contract, auth/security behavior, frontend code, database model/schema, migration, CORS behavior, or unrelated backend domain was changed.

## 2. Before

Before this refactor, public tracking logic lived directly in `backend/routes/public_tracking.py`:

- `GET /api/public/track/<identifier>` resolved numeric ids and tracking codes in the route module.
- The route module queried shipment, geography, expert, assignment, referral assignment, quote, and expert-console log data directly.
- The route module built both `workflow_steps` and `workflow_steps_simple` timeline structures.
- The route module assembled the full public response payload, including route locations, assigned expert, latest quote, timeline fields, and date serialization.
- The route module returned `{"message": "درخواست یافت نشد"}` with 404 when the identifier did not resolve.

Endpoint reviewed in this phase:

- `GET /api/public/track/<identifier>`

Pre-change checks:

| Check | Result | Notes |
|---|---:|---|
| `pytest -q` | PASS_WITH_WARNINGS | 51 passed, 53 existing warnings. |
| `npm run lint` | PASS_WITH_WARNINGS | 0 errors; 17 existing warnings. |
| `npm run build` | PASS_WITH_WARNINGS | Build passed; existing Browserslist/chunk-size warnings remain. |
| `npm run check:structure` | PASS | Canonical migration structure check passed. |
| `git diff --check` | PASS | No whitespace errors before changes. |

## 3. Characterization Tests

A public tracking characterization test was added to `backend/tests/test_public_tracking_timeline.py` because the existing tests covered timeline helper behavior and presence of `workflow_steps_simple`, but did not lock the full public response shape or not-found response.

The new test preserves current behavior by asserting:

- `GET /api/public/track/<id>` remains public and returns 200 without auth.
- Top-level public tracking response keys remain unchanged.
- Missing request ids return 404 with `{"message": "درخواست یافت نشد"}`.
- Fallback tracking number format remains `SR{id:06d}`.
- 7-step and 4-step timeline names and order remain unchanged.
- Empty assigned expert and latest quote values remain `null` for a minimal request.

The test records current behavior only; it does not require a new behavior or a real external database.

## 4. Service Design

| Service file | Function | Previous location | Responsibility | Behavior impact |
|---|---|---|---|---|
| `backend/services/timeline_service.py` | `WORKFLOW_STEP_DEFS`, `STATUS_TO_COMPLETED_UP_TO`, `WORKFLOW_STEP_DEFS_SIMPLE_4` | `backend/routes/public_tracking.py` | Keep public timeline definitions and status completion mapping. | None; constants preserved. |
| `backend/services/timeline_service.py` | `build_workflow_steps_from_status()` | `_workflow_steps_from_status()` | Build the 7-step public workflow timeline. | None; timeline keys, order, completion, and points behavior preserved. |
| `backend/services/timeline_service.py` | `get_final_decision_from_logs()` | `_get_final_decision_from_logs()` | Read latest won/lost decision from expert console logs. | None; query and return shape preserved. |
| `backend/services/timeline_service.py` | `get_assigned_at()` | `_get_assigned_at()` | Read earliest assignment timestamp from assignment/referral/expert logs. | None; date source precedence via minimum date preserved. |
| `backend/services/timeline_service.py` | `build_workflow_steps_simple_4()` | `_workflow_steps_simple_4()` | Build the 4-step customer timeline. | None; step names, titles, completed flags, and closed-without-decision warning preserved. |
| `backend/services/tracking_service.py` | `resolve_request()` | `_resolve_request()` | Resolve numeric id or tracking code to a shipment request. | None; lookup behavior preserved. |
| `backend/services/tracking_service.py` | `get_latest_quote()` | `_get_latest_quote()` | Read and serialize latest quote for the request. | None; quote field names and date/value handling preserved. |
| `backend/services/tracking_service.py` | `date_iso()` | local `_date_iso()` inside route | Serialize optional date/datetime values. | None; `None` and `isoformat` behavior preserved. |
| `backend/services/tracking_service.py` | `build_assigned_expert()` | route body | Read and serialize assigned expert summary. | None; field names and empty string fallbacks preserved. |
| `backend/services/tracking_service.py` | `build_route_summary()` | route body | Read and serialize public origin/destination route summary. | None; nested route shape preserved. |
| `backend/services/tracking_service.py` | `build_tracking_response()` | route body | Assemble the full public tracking response payload. | None; top-level response shape preserved. |
| `backend/services/tracking_service.py` | `get_public_tracking_payload()` | route body | Resolve identifier and return payload or `None`. | None; route still owns 404 response. |

## 5. Changes Made

| File | Change summary | Reason | API behavior impact | Risk |
|---|---|---|---|---|
| `backend/services/timeline_service.py` | Added timeline constants and helper functions for 7-step/4-step timelines, assignment timestamp lookup, and final-decision lookup. | Move timeline read/helper logic out of the route. | None intended; characterization tests cover timeline order and response shape. | Medium because public timeline semantics are user-facing. |
| `backend/services/tracking_service.py` | Added request resolution, quote serialization, assigned expert serialization, route summary construction, and full response assembly. | Move read-heavy public tracking assembly out of the route. | None intended; public contract preserved. | Medium because endpoint is public. |
| `backend/routes/public_tracking.py` | Replaced inline read/helper/response assembly logic with service calls while preserving public endpoint, 404/500 error formats, and status codes; retained compatibility aliases for existing helper tests/imports. | Keep route focused on request path, service call, `jsonify`, and error handling. | None intended. | Low/Medium. |
| `backend/tests/test_public_tracking_timeline.py` | Added response-contract characterization for public tracking success and not-found responses. | Lock public API behavior before/after extraction. | Test-only; no runtime behavior change. | Low. |
| `docs/phase-4d-public-tracking-service-extraction.md` | Added this implementation record. | Document scope, before/after checks, characterization, design, and contract preservation. | Documentation only. | Low. |

## 6. Endpoint Contract Preservation

| Endpoint | Method | Public/auth behavior preserved? | Response shape preserved? | Error behavior preserved? | Notes |
|---|---|---:|---:|---:|---|
| `/api/public/track/<identifier>` | GET | Yes; remains public with no auth decorator. | Yes. | Yes. | Success remains 200 with the same tracking payload keys and timeline structures; missing ids still return 404 with `{"message": "درخواست یافت نشد"}`; database and generic error responses remain unchanged. |

## 7. After

| Check | Result | Notes |
|---|---:|---|
| `pytest -q` | PASS_WITH_WARNINGS | 52 passed, existing warnings. |
| `pytest backend/tests/test_public_tracking_timeline.py -q` | PASS_WITH_WARNINGS | 11 passed, existing warnings. |
| `npm run lint` | PASS_WITH_WARNINGS | 0 errors; 17 existing warnings. |
| `npm run build` | PASS_WITH_WARNINGS | Build passed; existing Browserslist/chunk-size warnings remain. |
| `npm run check:structure` | PASS | Canonical migration structure check passed. |
| `git diff --check` | PASS | No whitespace errors. |

## 8. Deferred Items

- CRM service extraction.
- Shipment service extraction.
- Expert console extraction.
- General repository layer.
- Model split.
- Frontend feature refactor.
- Existing lint warnings.
- CI/CD.
- OpenAPI documentation.
