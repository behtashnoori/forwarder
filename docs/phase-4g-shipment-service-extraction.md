# Phase 4G: Shipment Request Service Extraction

Date: 2026-05-18

## Scope

Extract a limited, low-risk service layer for public shipment request creation and transport method reads.

Allowed files touched in this phase:

- `backend/routes/shipment_request.py`
- `backend/services/shipment_service.py`
- `backend/tests/test_shipment_request_contract.py`
- `docs/phase-4g-shipment-service-extraction.md`

No validation split into `shipment_validation_service.py` was needed; the validation remained small enough to keep in `shipment_service.py`.

## Before

`backend/routes/shipment_request.py` previously owned all of the following concerns directly:

- `GET /api/transport-methods` querying active `TransportMethod` rows and grouping them into `international_methods` and `domestic_methods`.
- `POST /api/shipment-request` request JSON parsing, shipping type validation, domestic/international location validation, phone validation, customer/cargo/transport normalization, date/number parsing, `ShipmentRequest` construction, tracking code generation, initial `ShipmentRequestLog` creation, optional gamification side effects, commit, post-commit referral assignment, and response payload construction.
- `GET /api/shipment-request/ping` returning `{"message": "pong"}`.

Current endpoint contracts documented before extraction:

- `GET /api/transport-methods` returns `200` with `international_methods`, `domestic_methods`, and `preference_options`; DB errors return `500` with `error` and `message`.
- `POST /api/shipment-request` returns `201` with `message`, `id`, and `tracking_code` on success.
- Invalid shipping type returns `400` with `{"message": "نوع ارسال نامعتبر است."}`.
- Invalid domestic location returns `400` with `{"message": "اطلاعات مبدا و مقصد داخلی نامعتبر است."}`.
- Invalid international location returns `400` with `{"message": "اطلاعات مبدا و مقصد بین‌المللی نامعتبر است."}`.
- Invalid phone returns `400` with `{"message": "شماره تماس نامعتبر است. لطفاً شماره‌ای با پیش‌شماره 09 و ۱۱ رقم وارد کنید."}`.
- Unexpected create errors rollback and return `500` with `{"message": "خطای داخلی سرور: ..."}`.
- `GET /api/shipment-request/ping` returns `200` with `{"message": "pong"}`.

## Characterization Tests

Added `backend/tests/test_shipment_request_contract.py` before extraction to lock current behavior:

- Transport method grouping and `preference_options` response shape.
- Domestic shipment request success response, field normalization, defaults, tracking code, DB commit, and initial log creation.
- International shipment request success response and location/transport field behavior.
- Validation status codes and error formats for invalid shipping type, domestic location, international location, and phone number.

These tests characterize existing behavior; they do not introduce new API behavior.

## Service Design

Added `backend/services/shipment_service.py` with focused helpers:

- `get_transport_methods_payload()` for transport method read payloads.
- `create_shipment_request(payload, remote_addr=None)` for create orchestration and commit.
- `normalize_shipment_payload(payload)` for preserving current validation and normalization.
- `build_shipment_request_data(normalized, timestamp)` for `ShipmentRequest` constructor data.
- `build_shipment_request_payload(shipment_request)` for the public success response.
- Supporting helpers for tracking code generation, gamification side effects, referral assignment, numeric/date parsing, and phone validation.

The route layer remains responsible for reading Flask request JSON, translating service validation exceptions into the existing JSON/status format, preserving existing exception logging/rollback, and returning `jsonify` responses.

## Changes Made

- Simplified `backend/routes/shipment_request.py` so shipment routes call `shipment_service` instead of containing all read/write orchestration inline.
- Moved transport method grouping, shipment request validation/normalization, request creation, tracking code generation, initial log creation, gamification handling, referral assignment, and success response payload building into `backend/services/shipment_service.py`.
- Added characterization tests in `backend/tests/test_shipment_request_contract.py`.

## Endpoint Contract Preservation

Preserved without change:

- URLs and HTTP methods.
- Status codes.
- Response shapes.
- Error formats/messages.
- Domestic and international behavior.
- Legacy and separate transport method behavior.
- Cargo/customer field normalization.
- Default request status and expert console defaults.
- Frontend compatibility.
- Commit on success and rollback on unexpected create errors.
- Optional gamification and referral side-effect workflow behavior.

No migrations were created, no database models/schemas were changed, no frontend files were changed, and no auth/security behavior was changed.

## After

The shipment request route module is now a thin controller for public shipment endpoints. Business logic and serialization live in `backend/services/shipment_service.py`, covered by characterization tests.

## Deferred Items

- Further split of validation into `shipment_validation_service.py` is deferred until validation grows or multiple callers need standalone validation.
- Referral/assignment internals remain untouched; a future phase may characterize and refactor assignment separately if needed.
- Timezone-aware datetime cleanup is deferred because existing models and tests still use naive UTC datetimes broadly.
