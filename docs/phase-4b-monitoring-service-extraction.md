# Phase 4B Monitoring Service Extraction

Date: 2026-05-18

## 1. Scope

Phase 4B is a limited monitoring-only service layer extraction. It moves monitoring dashboard orchestration, monitoring/analytics delegation, alert list construction, alert acknowledgement payload construction, and current log payload construction out of `backend/routes/monitoring.py` into small service modules.

This phase does not change API URLs, HTTP methods, auth/role decorators, response contracts, status codes, frontend code, database models, schema, migrations, CORS/security configuration, or unrelated backend domains.

## 2. Controlled Risk Note

Phase 3H documented that backend pytest is `ENV_BLOCKED` in Codex because Flask and other backend runtime dependencies are missing and official dependency installation is blocked by the package index/proxy returning `403 Forbidden` while resolving Flask. The same blocker is still present for Phase 4B in this container: `pytest -q` fails during collection with `ModuleNotFoundError: No module named 'flask'`.

Because this phase changes runtime monitoring code, final merge requires local/CI backend pytest evidence in a valid Python environment. No repeated dependency-install attempt was made in Phase 4B after the known Phase 3H environment blocker was confirmed.

## 3. Before

Before this refactor, monitoring orchestration lived directly in `backend/routes/monitoring.py`:

- `GET /api/monitoring/health` called `system_monitor.get_health_status()` directly.
- `GET /api/monitoring/metrics`, `/database`, and `/business` called `system_monitor` directly.
- `GET /api/monitoring/analytics/customers`, `/analytics/sales`, and `/analytics/performance` called `analytics_engine` directly after reading `days` from query params.
- `GET /api/monitoring/dashboard` assembled the full dashboard payload in the route.
- `GET /api/monitoring/alerts` calculated alert thresholds and counts in the route.
- `POST /api/monitoring/alerts/acknowledge` built the acknowledgement payload in the route.
- `GET /api/monitoring/logs` built the current mock log payload in the route.

Routes reviewed in this phase were limited to `backend/routes/monitoring.py`.

Pre-change checks:

| Check | Result | Notes |
|---|---:|---|
| `pytest -q` | ENV_BLOCKED | Fails during collection with `ModuleNotFoundError: No module named 'flask'`; matches Phase 3H dependency/proxy blocker. |
| `npm run lint` | PASS_WITH_WARNINGS | 0 errors; 17 existing warnings. |
| `npm run build` | PASS_WITH_WARNINGS | Build passed; existing Browserslist/chunk-size warnings remain. |
| `npm run check:structure` | PASS | Canonical migration structure check passed. |
| `git diff --check` | PASS | No whitespace errors before changes. |

## 4. Service Design

| Service file | Function | Previous location | Responsibility | Behavior impact |
|---|---|---|---|---|
| `backend/services/monitoring_service.py` | `get_health_status()` | `backend/routes/monitoring.py` | Delegate health status retrieval to `system_monitor`. | None; same monitor call and route response. |
| `backend/services/monitoring_service.py` | `get_system_metrics()` | `backend/routes/monitoring.py` | Delegate system metrics retrieval to `system_monitor`. | None; same monitor call and route response. |
| `backend/services/monitoring_service.py` | `get_database_metrics()` | `backend/routes/monitoring.py` | Delegate database metrics retrieval to `system_monitor`. | None; same monitor call and route response. |
| `backend/services/monitoring_service.py` | `get_business_metrics()` | `backend/routes/monitoring.py` | Delegate business metrics retrieval to `system_monitor`. | None; same monitor call and route response. |
| `backend/services/monitoring_service.py` | `get_customer_analytics(days)` | `backend/routes/monitoring.py` | Delegate customer analytics retrieval to `analytics_engine`. | None; same `days` query value is passed through. |
| `backend/services/monitoring_service.py` | `get_sales_analytics(days)` | `backend/routes/monitoring.py` | Delegate sales analytics retrieval to `analytics_engine`. | None; same `days` query value is passed through. |
| `backend/services/monitoring_service.py` | `get_performance_analytics(days)` | `backend/routes/monitoring.py` | Delegate performance analytics retrieval to `analytics_engine`. | None; same `days` query value is passed through. |
| `backend/services/monitoring_service.py` | `get_dashboard_summary()` | `backend/routes/monitoring.py` | Compose the dashboard payload from health, system, database, business, and 30-day analytics data. | None; keys and nested shape preserved. |
| `backend/services/monitoring_service.py` | `get_system_logs(log_type, limit)` | `backend/routes/monitoring.py` | Build the current log payload and select a requested log type. | None; `limit` remains accepted and behavior remains fixed-size as before. |
| `backend/services/alert_service.py` | `list_alerts()` | `backend/routes/monitoring.py` | Calculate memory, CPU, error-rate, and response-time alerts and summary counts. | None; thresholds, messages, keys, and count semantics preserved. |
| `backend/services/alert_service.py` | `acknowledge_alert(alert_id)` | `backend/routes/monitoring.py` | Build the current alert acknowledgement payload. | None; validation and status handling remain in the route. |

## 5. Changes Made

| File | Change summary | Reason | API behavior impact | Risk |
|---|---|---|---|---|
| `backend/services/__init__.py` | Added service package marker. | Provide a package for monitoring service modules. | None. | Low. |
| `backend/services/monitoring_service.py` | Added monitoring/analytics wrapper functions, dashboard summary composition, and current log payload construction. | Move monitoring orchestration out of the route while keeping existing monitor/analytics components. | None intended; response contracts preserved. | Low/Medium because dashboard/log shape must remain exact. |
| `backend/services/alert_service.py` | Added alert list construction and acknowledgement payload helpers. | Extract threshold/count logic from route to service. | None intended; alert thresholds/messages/counts preserved. | Low/Medium because alert semantics are ops-facing. |
| `backend/routes/monitoring.py` | Replaced inline monitor/analytics/dashboard/alert/log orchestration with service calls while preserving decorators, request parsing, `jsonify`, status codes, and error handlers. | Keep route focused on request handling and response conversion. | None intended. | Low/Medium. |
| `docs/phase-4b-monitoring-service-extraction.md` | Added this implementation record. | Document scope, controlled risk, design, contract preservation, checks, and deferred items. | Documentation only. | Low. |

## 6. Endpoint Contract Preservation

| Endpoint | Method | Auth/role preserved? | Response shape preserved? | Notes |
|---|---|---:|---:|---|
| `/api/monitoring/health` | GET | Yes; remains public as before. | Yes. | Route still returns monitor health payload or `{"error": "Failed to get health status"}` with 500 on exception. |
| `/api/monitoring/metrics` | GET | Yes; `@require_role("supervisor")` unchanged. | Yes. | Route still reads no query params and returns system metrics. |
| `/api/monitoring/database` | GET | Yes; `@require_role("supervisor")` unchanged. | Yes. | Route still returns database metrics. |
| `/api/monitoring/business` | GET | Yes; `@require_role("supervisor")` unchanged. | Yes. | Route still returns business metrics. |
| `/api/monitoring/analytics/customers` | GET | Yes; `@require_role("supervisor")` unchanged. | Yes. | `days` query param default remains `30`. |
| `/api/monitoring/analytics/sales` | GET | Yes; `@require_role("supervisor")` unchanged. | Yes. | `days` query param default remains `30`. |
| `/api/monitoring/analytics/performance` | GET | Yes; `@require_role("supervisor")` unchanged. | Yes. | `days` query param default remains `30`. |
| `/api/monitoring/dashboard` | GET | Yes; `@require_role("supervisor")` unchanged. | Yes. | Dashboard keys remain `timestamp`, `health`, `system`, `database`, `business`, and nested `analytics`. |
| `/api/monitoring/alerts` | GET | Yes; `@require_role("supervisor")` unchanged. | Yes. | Alert thresholds and summary count keys are preserved. |
| `/api/monitoring/alerts/acknowledge` | POST | Yes; `@require_role("supervisor")` unchanged. | Yes. | Missing `alert_id` still returns `{"error": "Alert ID is required"}` with 400; success payload shape unchanged. |
| `/api/monitoring/logs` | GET | Yes; `@admin_required` unchanged. | Yes. | `type` and `limit` query params remain accepted; invalid type still returns `{"error": "Invalid log type"}` with 400. |
| `/api/monitoring/ping` | GET | Yes; remains public as before. | Yes. | Unchanged except surrounding import cleanup. |

## 7. After

| Check | Result | Notes |
|---|---:|---|
| `pytest -q` | ENV_BLOCKED | Fails during collection with `ModuleNotFoundError: No module named 'flask'`; local/CI pytest required before merge. |
| `pytest backend/tests/test_security_config.py -q` | ENV_BLOCKED | Same missing Flask dependency during backend test collection. |
| Monitoring-specific backend tests | NOT_RUN | No dedicated monitoring test file was present; backend pytest is blocked by missing Flask. |
| `npm run lint` | PASS_WITH_WARNINGS | 0 errors; 17 existing warnings. |
| `npm run build` | PASS_WITH_WARNINGS | Build passed; existing Browserslist/chunk-size warnings remain. |
| `npm run check:structure` | PASS | Canonical migration structure check passed. |
| `git diff --check` | PASS | No whitespace errors. |

## 8. Deferred Items

- CRM service extraction.
- Shipment service extraction.
- Expert console service extraction.
- General repository layer.
- Model split.
- Frontend feature refactor.
- Existing lint warnings.
- CI/CD.
- OpenAPI documentation.
