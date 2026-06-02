# Phase 4E CRM Read Service Extraction

Date: 2026-05-18

## 1. Scope

Phase 4E is a limited CRM read-helper extraction. It moves read-heavy CRM customer, opportunity, activity, and KPI payload/query construction from `backend/routes/crm.py` into service modules while preserving route URLs, HTTP methods, auth/role decorators, response contracts, status codes, frontend behavior, database models/schema, migrations, CORS behavior, and CRM write workflows.

Write endpoints such as create/update customer, create opportunity, and create activity remain in the route module and were not intentionally refactored beyond import cleanup needed for the read extraction.

## 2. Before

Before this refactor, CRM read logic lived directly in `backend/routes/crm.py`:

- `GET /api/crm/customers` parsed filters/pagination, built a `Customer` query, applied search/type/status/sort behavior, paginated, and shaped customer list rows.
- `GET /api/crm/customers/<id>` queried customer details, contacts, opportunities, recent activities, and shaped the detail payload.
- `GET /api/crm/opportunities` parsed filters/pagination, queried opportunities, resolved customer/expert summaries, and shaped opportunity rows.
- `GET /api/crm/activities` parsed filters/pagination, queried activities, resolved customer/expert summaries, and shaped activity rows.
- `GET /api/crm/dashboard/kpis` built customer/opportunity/activity KPI payloads and recent activity summaries in the route.

Endpoints reviewed in this phase:

- `GET /api/crm/customers`
- `GET /api/crm/customers/<id>`
- `GET /api/crm/opportunities`
- `GET /api/crm/activities`
- `GET /api/crm/dashboard/kpis`

Pre-change checks:

| Check | Result | Notes |
|---|---:|---|
| `pytest -q` | PASS_WITH_WARNINGS | 52 passed with existing warnings. |
| `npm run lint` | PASS_WITH_WARNINGS | 0 errors; 17 existing warnings. |
| `npm run build` | PASS_WITH_WARNINGS | Build passed; existing Browserslist/chunk-size warnings remain. |
| `npm run check:structure` | PASS | Canonical migration structure check passed. |
| `git diff --check` | PASS | No whitespace errors before changes. |

## 3. Characterization Tests

A CRM read characterization test was added in `backend/tests/test_crm_read_contract.py` because existing tests only covered authentication/role denial for CRM customer listing, not the successful read response contract.

The new test records current behavior for read endpoints by asserting:

- `GET /api/crm/customers` still requires authentication.
- A `business_expert` token can read CRM list endpoints.
- Customer list response keys, pagination keys, `per_page` behavior, and customer row field names remain stable.
- Missing customer detail returns 404 with `{"error": "مشتری یافت نشد"}`.
- Customer detail response keys remain stable.
- Opportunities and activities list response wrappers, pagination wrappers, and row field names remain stable.

The test uses the existing app factory and an isolated SQLite test database. It records current behavior only and does not require a real database or introduce new CRM behavior.

## 4. Service Design

| Service file | Function | Previous location | Responsibility | Behavior impact |
|---|---|---|---|---|
| `backend/services/crm_service.py` | `pagination_payload()` | Repeated route pagination dictionaries | Build the existing pagination response shape. | None; keys and values preserved. |
| `backend/services/crm_service.py` | `build_customer_list_item()` | `get_customers()` | Build a customer list row. | None; field names preserved. |
| `backend/services/crm_service.py` | `list_customers(filters)` | `get_customers()` | Apply current customer filters/sort/pagination and return list payload. | None; query param behavior preserved. |
| `backend/services/crm_service.py` | `get_customer_detail(customer_id)` | `get_customer_detail()` | Query customer detail data and return payload or `None`. | None; route still owns 404 response. |
| `backend/services/crm_service.py` | `build_customer_detail_payload()` | `get_customer_detail()` | Build customer detail payload from related rows. | None; response keys preserved. |
| `backend/services/crm_service.py` | `list_opportunities(filters)` | `get_opportunities()` | Apply current opportunity filters/pagination and return list payload. | None; query param behavior preserved. |
| `backend/services/crm_service.py` | `build_opportunity_payload()` | `get_opportunities()` | Build an opportunity row with customer/expert summaries. | None; field names preserved. |
| `backend/services/crm_service.py` | `list_activities(filters)` | `get_activities()` | Apply current activity filters/pagination and return list payload. | None; query param behavior preserved. |
| `backend/services/crm_service.py` | `build_activity_payload()` | `get_activities()` | Build an activity row with customer/expert summaries. | None; field names preserved. |
| `backend/services/crm_dashboard_service.py` | `get_crm_dashboard_kpis()` | `get_crm_dashboard_kpis()` | Build CRM dashboard KPI payload and recent activities. | None intended; existing query/shape preserved. |

## 5. Changes Made

| File | Change summary | Reason | API behavior impact | Risk |
|---|---|---|---|---|
| `backend/services/crm_service.py` | Added CRM read query and payload helpers for customers, customer detail, opportunities, and activities. | Move read-heavy CRM logic out of the route. | None intended; characterization test covers key read contracts. | Medium because CRM is protected business data. |
| `backend/services/crm_dashboard_service.py` | Added dashboard KPI payload helper. | Move read-only KPI aggregation out of the route while preserving the current payload. | None intended. | Medium because dashboard aggregates are business-facing. |
| `backend/routes/crm.py` | Replaced inline read query/payload logic with service calls while preserving request parsing, decorators, `jsonify`, status codes, and error messages; write endpoints remain in the route. | Keep route focused on request handling and response conversion for read endpoints. | None intended. | Low/Medium. |
| `backend/tests/test_crm_read_contract.py` | Added CRM read response contract characterization. | Lock current CRM read response shapes and auth behavior before/after extraction. | Test-only; no runtime behavior change. | Low. |
| `docs/phase-4e-crm-read-service-extraction.md` | Added this implementation record. | Document scope, before/after checks, characterization coverage, service design, and contract preservation. | Documentation only. | Low. |

## 6. Endpoint Contract Preservation

| Endpoint | Method | Auth/role preserved? | Response shape preserved? | Error behavior preserved? | Notes |
|---|---|---:|---:|---:|---|
| `/api/crm/customers` | GET | Yes; `@require_role("business_expert")` unchanged. | Yes. | Yes. | Search/type/status/sort/page/per_page behavior preserved. |
| `/api/crm/customers/<id>` | GET | Yes; `@require_role("business_expert")` unchanged. | Yes. | Yes. | Missing customer still returns 404 with `{"error": "مشتری یافت نشد"}`. |
| `/api/crm/opportunities` | GET | Yes; `@require_role("business_expert")` unchanged. | Yes. | Yes. | Stage/assigned_to/search/page/per_page behavior preserved. |
| `/api/crm/activities` | GET | Yes; `@require_role("business_expert")` unchanged. | Yes. | Yes. | Activity type/expert/customer/status/page/per_page behavior preserved. |
| `/api/crm/dashboard/kpis` | GET | Yes; `@require_role("business_expert")` unchanged. | Yes. | Yes. | Current KPI query and payload shape moved to service. |

## 7. After

| Check | Result | Notes |
|---|---:|---|
| `pytest -q` | PASS_WITH_WARNINGS | 53 passed with existing warnings. |
| `pytest backend/tests/test_crm_read_contract.py -q` | PASS_WITH_WARNINGS | 1 passed with existing warnings. |
| `npm run lint` | PASS_WITH_WARNINGS | 0 errors; 17 existing warnings. |
| `npm run build` | PASS_WITH_WARNINGS | Build passed; existing Browserslist/chunk-size warnings remain. |
| `npm run check:structure` | PASS | Canonical migration structure check passed. |
| `git diff --check` | PASS | No whitespace errors. |

## 8. Deferred Items

- CRM write service extraction.
- Shipment service extraction.
- Expert console extraction.
- General repository layer.
- Model split.
- Frontend feature refactor.
- Existing lint warnings.
- CI/CD.
- OpenAPI documentation.
