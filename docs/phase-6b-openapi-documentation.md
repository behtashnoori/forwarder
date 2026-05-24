# Phase 6B: OpenAPI Documentation

## 1. Scope

This phase is API documentation only.

No runtime code, API behavior, frontend code, schema/model, migrations, auth/security logic, dependencies, routes, or services were changed.

## 2. Sources Used

Route files:

- `backend/routes/shipment_request.py`
- `backend/routes/public_tracking.py`
- `backend/routes/expert_console.py`
- `backend/routes/crm.py`
- `backend/routes/user_management.py`
- `backend/routes/admin_panel.py`
- `backend/routes/customer_gamification.py`
- `backend/routes/site_settings.py`

Service files used for behavior context:

- `backend/services/shipment_service.py`
- `backend/services/tracking_service.py`
- `backend/services/expert_request_list_service.py`
- `backend/services/expert_request_detail_service.py`
- `backend/services/quote_service.py`
- `backend/services/message_service.py`
- `backend/services/notification_service.py`
- `backend/services/assignment_service.py`
- `backend/services/crm_service.py`
- `backend/services/crm_write_service.py`
- `backend/services/crm_dashboard_service.py`
- `backend/services/user_service.py`
- `backend/services/user_delete_service.py`
- `backend/services/assignment_rule_service.py`
- `backend/services/transport_method_service.py`
- `backend/services/assignment_statistics_service.py`
- `backend/services/admin_dashboard_service.py`
- `backend/services/admin_report_service.py`
- `backend/services/admin_shipment_request_service.py`
- `backend/services/referral_service.py`
- `backend/services/customer_gamification_service.py`
- `backend/services/settings_service.py`
- `backend/services/upload_service.py`

Contract tests:

- `backend/tests/test_shipment_request_contract.py`
- `backend/tests/test_public_tracking_timeline.py`
- `backend/tests/test_expert_assignment_referral_contract.py`
- `backend/tests/test_crm_read_contract.py`
- `backend/tests/test_crm_write_contract.py`
- `backend/tests/test_user_management_contract.py`
- `backend/tests/test_admin_panel_read_contract.py`
- `backend/tests/test_customer_gamification_contract.py`

Phase documentation:

- Phase 4 service extraction docs.
- Phase 5 user-management, admin-panel, and customer-gamification docs.

## 3. OpenAPI Structure

Created:

- `docs/openapi/openapi.yaml`
- `docs/openapi/README.md`

The OpenAPI spec uses OpenAPI 3.0.3 and a placeholder local server URL: `http://localhost:5000`.

Tags:

- Public Shipment
- Public Tracking
- Expert Auth
- Expert Console
- CRM
- User Management
- Admin Panel
- Customer Gamification
- Site Settings

Auth schemes:

- `bearerAuth` documents the current JWT bearer-token style used by protected endpoints.

Auth conventions:

- public endpoints omit `security`.
- expert endpoints use bearer token auth.
- admin endpoints use bearer token auth plus backend admin-role decorators.
- CRM endpoints use bearer token auth plus backend `business_expert` role decorators.

Response conventions:

- common `400`, `401`, `403`, `404`, and `500` responses use a flexible `ErrorResponse` schema because the current backend uses both `message` and `error` payload keys depending on route.
- response schemas are intentionally flexible where tests characterize important keys but not every nested field.
- imperfect current behavior is documented rather than corrected.

Known limitation:

- This is an initial documentation pass, not a generated or fully strict schema. Some payloads are marked best-effort and should be tightened only after additional contract tests or explicit product decisions.

## 4. API Groups Documented

| group | endpoints covered | confidence level | notes |
| --- | --- | --- | --- |
| Public shipment request | `GET /api/transport-methods`, `POST /api/shipment-request` | Medium-High | Based on route/service and shipment contract tests; shipment body remains best-effort because form fields vary by shipping type. |
| Public tracking | `GET /api/public/track/{identifier}` | Medium | Important contract keys are covered by public tracking tests; nested schema remains flexible. |
| Expert auth | login, refresh, logout | Medium | Login/refresh/logout behavior is route-based and tested through expert/auth contracts; token internals remain flexible. |
| Expert console | request list/detail, assignment, quote latest/create, messages, notifications, mark-read | Medium | Main endpoints covered; some extra expert endpoints remain outside primary Phase 6B scope. |
| CRM | customer read/write, opportunities, activities, dashboard KPIs | Medium | Read/write contracts exist; request/response bodies remain flexible pending stricter schema tests. |
| User management | users CRUD, assignment rules, transport methods, assignment statistics, manual assignment | Medium-High | Recent Phase 5 contract tests provide good coverage. |
| Admin panel | dashboard, assignment summary, shipment request list/detail, referral rules | Medium-High | Recent Phase 5N-5R tests and service extraction docs provide strong coverage for read/report endpoints. |
| Customer gamification | register, verify email, profile, workflow, complete step, leaderboard | High | Phase 5K-5AA characterization and extraction tests cover read/write behavior, rollback, token, points, and workflow mutation. |
| Site settings | public/admin settings, upload, uploaded file serving | Medium | Based on route/service behavior and Phase 4C docs; upload payload remains best-effort. |

## 5. Known Gaps

- Some schemas use `additionalProperties: true` until stricter contract tests lock every nested field.
- Expert console endpoints outside the primary requested list, such as status update, request mark-read, experts list, and KPI endpoint, are not fully expanded in this initial spec.
- Location, health, and monitoring endpoints are not in the primary Phase 6B scope.
- Exact role names are documented from decorators and auth conventions, but OpenAPI cannot enforce role-level authorization beyond `bearerAuth`.
- Multipart upload validation and served-file MIME behavior are documented at a high level only.
- Some current localized error payloads are documented via common schemas rather than exhaustive per-route examples.

## 6. Verification

Before documentation:

- `python -m pytest -q` -> `86 passed, 724 warnings`
- `npm.cmd run lint` -> passed with 17 existing warnings
- `npm.cmd run build` -> passed with existing Browserslist/chunk-size warnings
- `npm.cmd run check:structure` -> passed
- `git diff --check` -> passed with existing CRLF warnings

After documentation:

- `python -m pytest -q` -> `86 passed, 724 warnings`
- `npm.cmd run lint` -> passed with 17 existing warnings
- `npm.cmd run build` -> passed with existing Browserslist/chunk-size warnings
- `npm.cmd run check:structure` -> passed
- `git diff --check` -> passed with existing CRLF warnings
- `docs/openapi/openapi.yaml` parsed successfully with PyYAML in the local environment

## 7. Deferred Items

- generated API clients
- Swagger UI hosting
- frontend API refactor
- stricter schema validation
- repository layer
- production deployment docs
- full documentation for location, monitoring, health, and every expert-console auxiliary endpoint
