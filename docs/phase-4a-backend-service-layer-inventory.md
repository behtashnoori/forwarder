# Phase 4A Backend Service Layer Inventory

Date: 2026-05-18

## 1. Scope

Phase 4A is documentation/design only. It inventories backend route modules, identifies business logic and direct database access embedded in routes, and proposes service/repository boundaries for future incremental extraction.

No code refactor, migration, model/schema change, API behavior change, response contract change, frontend change, auth/security logic change, test skip/xfail, or assertion change was performed.

## 2. Controlled Risk Note

Phase 3H remains `BLOCKED_BY_ENV` in Codex because Flask and other backend runtime dependencies are not installed and the package index/proxy returns `403 Forbidden` while resolving Flask from the official requirements files. That is an environment-only blocker, not a known code failure. Phase 4A is allowed to proceed with controlled risk because it is documentation/design only and does not change runtime code.

Previously passing non-backend gates remain relevant: frontend lint/build, structure check, and read-only migration graph checks passed in Phase 3H. Backend pytest must still be run in local/CI with valid Python dependencies before any Phase 4B+ implementation merge.

## 3. Route Inventory

| Module | Domain | Responsibility | Direct DB access | Business logic density | Suggested service | Suggested repository | Refactor risk | Priority |
|---|---|---|---:|---|---|---|---|---|
| `backend/routes/shipment_request.py` | Public shipment intake | Public transport methods and shipment request creation. | Medium: `TransportMethod`, `ShipmentRequest`, `ShipmentRequestLog`, gamification models. | High | `shipment_service.py`, `shipment_intake_service.py`, `tracking_code_service.py` | `shipment_repository.py`, `transport_method_repository.py`, `customer_gamification_repository.py` | High: public API, gamification, referral assignment, tracking code fallback, transaction boundaries. | P2 |
| `backend/routes/expert_console.py` | Expert operations | Expert request list/detail, assignment, status changes, quotes, messages, notifications, auth helpers, dashboard KPIs. | Very high: many `ShipmentRequest`, `ExpertUser`, log/message/notification/quote queries and commits. | High | `expert_console_service.py`, `request_assignment_service.py`, `quote_service.py`, `message_service.py`, `notification_service.py`, `expert_dashboard_service.py` | `shipment_repository.py`, `expert_repository.py`, `expert_console_repository.py`, `quote_repository.py`, `notification_repository.py` | Very high: largest route module, many side effects and response-shaping branches. | P3 |
| `backend/routes/crm.py` | CRM | Customers, opportunities, activities, CRM dashboard KPIs. | High: customer/opportunity/activity/task/report/expert/request queries and commits. | High | `crm_service.py`, `crm_customer_service.py`, `crm_opportunity_service.py`, `crm_activity_service.py`, `crm_dashboard_service.py` | `crm_repository.py`, `customer_repository.py`, `opportunity_repository.py`, `activity_repository.py` | High: protected endpoints, many filters, pagination, aggregate KPIs. | P2 |
| `backend/routes/user_management.py` | Admin user/assignment management | Transport methods, expert users, assignment rules, stats, manual assignment. | Very high: users, transport methods, assignment rules/logs, shipment requests. | High | `user_management_service.py`, `assignment_rule_service.py`, `manual_assignment_service.py` | `user_repository.py`, `assignment_repository.py`, `transport_method_repository.py`, `shipment_repository.py` | High: admin-only destructive operations, password hashing, reassignment/delete rules. | P3 |
| `backend/routes/admin_panel.py` | Admin dashboard/referral | Admin shipment request list/detail, dashboard, assignment summary, referral rules CRUD/preview. | High: request/expert/referral/log queries and commits. | High | `admin_dashboard_service.py`, `admin_request_service.py`, `referral_rule_service.py`, `assignment_report_service.py` | `admin_repository.py`, `shipment_repository.py`, `referral_repository.py`, `expert_repository.py` | High: admin response contracts, referral rules JSON validation, preview side-effect constraints. | P3 |
| `backend/routes/monitoring.py` | Monitoring/analytics | System health, metrics, business/customer/sales/performance analytics, alerts, logs. | Low in route module: delegates to `system_monitor` and `analytics_engine`; no route-level `db.session`. | Medium | `monitoring_service.py`, `alert_service.py`, `analytics_service.py` | Existing monitoring/analytics data access may become `monitoring_repository.py` later. | Low/Medium: mostly orchestration, but response fields are admin/ops facing. | P1 |
| `backend/routes/site_settings.py` | Public/admin site settings | Public settings read, admin settings update, logo upload, uploaded asset serving. Includes `admin_site_bp`; no separate `admin_site_settings.py` exists. | Low: `SiteSetting` read/update. | Medium | `settings_service.py`, `upload_service.py` | `settings_repository.py` | Low: small module, clear boundaries, limited DB writes. | P1 |
| `backend/routes/admin_site_settings.py` | Admin site settings alias | Requested module path is absent. Admin site settings routes are implemented in `backend/routes/site_settings.py` via `admin_site_bp`. | N/A | Low | Covered by `settings_service.py` | Covered by `settings_repository.py` | Low if treated as part of `site_settings.py`; high only if introducing a file move, which is out of Phase 4A scope. | P1 documentation note |
| `backend/routes/public_tracking.py` | Public tracking | Resolve tracking identifier, expose request timeline/quote/assignment/customer-facing status. | Medium: request/log/assignment/quote lookups. | High | `tracking_service.py`, `timeline_service.py`, `quote_read_service.py` | `tracking_repository.py`, `shipment_repository.py`, `quote_repository.py`, `assignment_repository.py` | Medium/High: public response contract and timeline semantics are user-facing. | P2 |
| `backend/routes/customer_gamification.py` | Customer gamification | Registration, email verification, profile, workflow, step completion, leaderboard. | High: customer gamification, workflow, shipment, expert, quote queries and commits. | High | `customer_gamification_service.py`, `customer_workflow_service.py`, `email_verification_service.py`, `leaderboard_service.py` | `customer_gamification_repository.py`, `workflow_repository.py`, `shipment_repository.py`, `quote_repository.py` | High: public/customer-facing state changes, loyalty points, workflow semantics. | P3 |

### Per-module detail notes

#### `backend/routes/shipment_request.py`

- **Endpoints:** `GET /api/transport-methods`, `POST /api/shipment-request`, `GET /api/shipment-request/ping`.
- **Business logic in route:** shipping type selection, domestic vs international location validation, phone validation, transport method normalization, request payload assembly, tracking code generation/fallback, gamification points, workflow step creation, referral auto-assignment trigger.
- **Validation logic:** required location fields, phone format, shipping type enum, transport preference enum.
- **Side effects:** creates `ShipmentRequest`, creates `ShipmentRequestLog`, updates gamification customer counters/points, creates customer workflow step, commits request, then triggers referral assignment.
- **Extraction note:** preserve transaction boundaries carefully because request commit occurs before referral assignment.

#### `backend/routes/expert_console.py`

- **Endpoints:** request list/detail, assign, status update, quote create/latest, messages, notifications, login/refresh/logout, dashboard KPIs, mark-read, experts list, ping.
- **Business logic in route:** access checks, role-based list filtering, request detail serialization, assignment selection, status transitions, quote amount/validity handling, customer/expert message handling, notification state, auth response shaping, KPI calculations.
- **Validation logic:** auth token required on most endpoints, request ownership/role checks, JSON validation decorators for auth/refresh, field checks for assignment/status/quote/message payloads.
- **Side effects:** updates assignment/status/unread fields, creates `ExpertConsoleLog`, `ExpertConsoleNotification`, `ExpertConsoleMessage`, `ExpertQuote`, commits multiple workflows.
- **Extraction note:** decompose by workflow; do not attempt one-shot extraction of this 1000+ line module.

#### `backend/routes/crm.py`

- **Endpoints:** customers list/create/detail/update, opportunities list/create, activities list/create, dashboard KPIs, ping.
- **Business logic in route:** filters/search/sort/pagination, customer detail aggregation, opportunity/activity status and due-date mapping, dashboard aggregate calculations.
- **Validation logic:** request body field use is mostly permissive; future service should centralize required-field and enum checks without changing current response contracts.
- **Side effects:** creates/updates customers, opportunities, activities; commits write operations.
- **Extraction note:** split read/list/query-building from write services to keep pagination and payload shape stable.

#### `backend/routes/user_management.py`

- **Endpoints:** transport methods CRUD subset, users CRUD, assignment rules CRUD, assignment statistics, manual assignment, ping.
- **Business logic in route:** admin-only user creation/update/delete, password hashing, role and manager fields, safe delete constraints, assignment rule JSON handling, manual assignment state/log creation.
- **Validation logic:** role/password/username/email presence, self-delete/admin-delete restrictions, assignment payload checks.
- **Side effects:** user create/update/delete, transport method create, assignment rule create/update, manual shipment assignment, assignment log creation, commits/rollbacks.
- **Extraction note:** `delete_user` and `manual_assignment` are highest-risk units due to cascading/reassignment behavior.

#### `backend/routes/admin_panel.py`

- **Endpoints:** admin shipment request detail/list, dashboard, assignment summary report, referral rules CRUD/preview.
- **Business logic in route:** admin list filtering/pagination, dashboard aggregate metrics, assignment summary aggregation, referral rule condition/action JSON validation, preview delegation.
- **Validation logic:** query params, referral rule name/action/strategy/expert_ids/request_id validation.
- **Side effects:** referral rule create/update/delete, referral rule state delete, preview is read-only by contract.
- **Extraction note:** referral rule service should be isolated from admin dashboard service.

#### `backend/routes/monitoring.py`

- **Endpoints:** health, metrics, database, business, analytics, dashboard, alerts, acknowledge alert, logs, ping.
- **Business logic in route:** combines monitor/analytics engine outputs, derives alert thresholds for memory/cpu/error/response-time, shapes log mock data.
- **Validation logic:** `days`, `alert_id`, `type`, `limit` parameters.
- **Side effects:** alert acknowledgement currently returns synthetic success; no persistent DB write in route.
- **Extraction note:** best first candidate because it already delegates most data work.

#### `backend/routes/site_settings.py` and absent `admin_site_settings.py`

- **Endpoints:** public site settings, admin get/update site settings, upload logo, serve upload.
- **Business logic in route:** defaults merge, allowed file extension check, upload filename handling, setting upsert.
- **Validation logic:** allowed file type, upload presence, settings dict body.
- **Side effects:** writes upload files, creates/updates `SiteSetting`, commits settings.
- **Extraction note:** small and low-risk, but includes filesystem writes; keep route response and upload path behavior stable.

#### `backend/routes/public_tracking.py`

- **Endpoints:** `GET /api/public/track/<identifier>`.
- **Business logic in route/helpers:** identifier resolution, final decision from logs, 4-step simplified timeline, assigned date resolution, latest quote extraction, public response assembly.
- **Validation logic:** empty identifier handling and not-found handling.
- **Side effects:** none; read-only public endpoint.
- **Extraction note:** good read-only candidate after monitoring/settings, but user-facing response contract is sensitive.

#### `backend/routes/customer_gamification.py`

- **Endpoints:** register, verify email, profile, workflow, complete step, leaderboard.
- **Business logic in route:** verification token generation, email-link assembly/logging, customer creation, token expiration checks, loyalty point updates, workflow progress construction, leaderboard ranking.
- **Validation logic:** email/phone format, token presence, customer/request/step fields, request ownership by customer id.
- **Side effects:** creates/updates customer gamification rows, creates/updates workflow steps, updates loyalty points, logs email behavior.
- **Extraction note:** public/customer-facing state transitions make this a later candidate after stronger test coverage.

## 4. Recommended Service Boundaries

Suggested future service package: `backend/services/`.

| Service | Primary responsibilities | Candidate route owners |
|---|---|---|
| `shipment_service.py` | Shipment request intake orchestration, request creation payload mapping, request log creation, commit/rollback orchestration. | `shipment_request.py`, later admin/expert read paths. |
| `transport_method_service.py` | Public/admin transport method list/create behavior and domestic/international grouping. | `shipment_request.py`, `user_management.py`. |
| `tracking_code_service.py` | Tracking code generation/collision handling/fallback policy. | `shipment_request.py`, `public_tracking.py`. |
| `referral_service.py` | Referral rule matching, assignment preview, assignment state; coordinate with existing `backend/referral_engine.py`. | `admin_panel.py`, `shipment_request.py`. |
| `expert_console_service.py` | Expert request list/detail/update orchestration and access-aware response shaping. | `expert_console.py`. |
| `assignment_service.py` | Manual assignment, assignment logs, unread flags, assignee changes. | `expert_console.py`, `user_management.py`, `admin_panel.py`. |
| `quote_service.py` | Quote create/latest/read models and quote notification/log side effects. | `expert_console.py`, `public_tracking.py`, `customer_gamification.py`. |
| `message_service.py` | Expert/customer message create/read/unread workflows. | `expert_console.py`. |
| `notification_service.py` | Notification creation, list, mark-read behavior. | `expert_console.py`. |
| `crm_service.py` | CRM customer/opportunity/activity orchestration. | `crm.py`. |
| `crm_dashboard_service.py` | CRM KPIs and aggregate reporting. | `crm.py`, `admin_panel.py`. |
| `admin_dashboard_service.py` | Admin dashboard, request summary, assignment reports. | `admin_panel.py`. |
| `user_management_service.py` | Admin user create/update/delete, password hashing orchestration, safe delete rules. | `user_management.py`. |
| `settings_service.py` | Site setting defaults, get/update/upsert behavior. | `site_settings.py`. |
| `upload_service.py` | Logo upload validation, secure filename, filesystem write policy. | `site_settings.py`. |
| `tracking_service.py` | Public tracking response assembly and timeline orchestration. | `public_tracking.py`. |
| `timeline_service.py` | Workflow step derivation and final-decision timeline semantics. | `public_tracking.py`, `customer_gamification.py`. |
| `customer_gamification_service.py` | Registration, verification, loyalty points, workflow state. | `customer_gamification.py`, `shipment_request.py`. |
| `monitoring_service.py` | System/database/business metrics orchestration and dashboard assembly. | `monitoring.py`. |
| `alert_service.py` | Alert threshold evaluation and acknowledgement policy. | `monitoring.py`. |

## 5. Recommended Repository Boundaries

Suggested future repository package: `backend/repositories/`.

| Repository | Entities/queries | Notes |
|---|---|---|
| `shipment_repository.py` | `ShipmentRequest`, `ShipmentRequestLog`, request list/detail/status queries. | Shared by shipment intake, expert console, admin, tracking. |
| `transport_method_repository.py` | `TransportMethod`. | Shared by public intake and user management. |
| `expert_repository.py` | `ExpertUser` lookup/list/role queries. | Keep password hash writes behind service logic. |
| `expert_console_repository.py` | `ExpertConsoleLog`, `ExpertConsoleMessage`, `ExpertConsoleNotification`. | May split into log/message/notification repositories later. |
| `quote_repository.py` | `ExpertQuote` create/latest/list. | Shared by expert, tracking, customer workflow. |
| `crm_repository.py` | `Customer`, `CustomerContact`, `Opportunity`, `Activity`, `Task`, `Report`. | May split when services stabilize. |
| `assignment_repository.py` | `AssignmentLog`, `ReferralAssignmentLog`, assignment statistics queries. | Coordinate with existing assignment/referral engines. |
| `referral_repository.py` | `ReferralRule`, `ReferralRuleState`, `ReferralAutoAssignState`. | Used by referral service and admin panel. |
| `settings_repository.py` | `SiteSetting` get/upsert/all. | Small first-class candidate. |
| `customer_gamification_repository.py` | `CustomerGamification`, `CustomerWorkflowStep`. | Shared by intake and customer endpoints. |
| `tracking_repository.py` | Tracking identifier resolution, final decision logs, assigned date queries. | May delegate to shipment/assignment/quote repositories. |
| `monitoring_repository.py` | Future DB-backed monitoring queries if `analytics_engine` is decomposed. | Not required for first Phase 4B candidate. |

## 6. Phase 4B Candidate

**Recommended first implementation candidate: Monitoring alert/service extraction from `backend/routes/monitoring.py`.**

### Why this candidate

- It is the lowest-risk route module with limited direct DB access in the route file.
- Most data collection already delegates to `system_monitor` and `analytics_engine`.
- A narrow extraction can move alert threshold calculation and dashboard orchestration into `backend/services/monitoring_service.py` without changing endpoint URLs, auth decorators, response shape, or database schema.
- It avoids public/customer-facing business workflows and avoids write-heavy transaction behavior.

### Files likely involved

- `backend/routes/monitoring.py`
- New `backend/services/monitoring_service.py`
- Optional new `backend/services/__init__.py`
- Tests should be added/updated only if a valid Python environment is available; do not skip existing tests.

### Tests/checks for Phase 4B

- `pytest -q`
- Targeted monitoring route tests if present or newly added.
- `pytest backend/tests/test_security_config.py -q` to ensure supervisor role protections remain intact.
- `npm run lint`
- `npm run build`
- `npm run check:structure`
- `git diff --check`

If Codex remains `ENV_BLOCKED`, local/CI pytest in a valid Python environment is required before merge.

### Behaviors that must not change

- Auth/role decorators and status codes.
- JSON response keys and nested structures for health, metrics, analytics, dashboard, alerts, logs, and ping.
- Alert threshold semantics for memory, CPU, error rate, and response time.
- Error message/status behavior.
- No DB migration, model, or schema change.

## 7. Refactor Rules for Phase 4B+

- Each PR must extract only one bounded domain.
- Route URLs, HTTP methods, auth/role behavior, status codes, and JSON response contracts must remain stable.
- No migration and no model/schema change in service extraction PRs.
- No frontend changes unless a later phase explicitly scopes them.
- No test skip/xfail and no assertion weakening.
- Preserve transaction boundaries and side-effect ordering before moving logic.
- Add characterization tests before extraction when route behavior is not already covered.
- Tests must pass in a valid Python environment before merge.
- If pytest is `ENV_BLOCKED` in Codex, local/CI pytest evidence is required before merge.
- Prefer extracting pure computation/serialization helpers first, then repository access, then write workflows.
- Keep repositories thin: query/persistence only; no response formatting or business policy.
- Keep services framework-light: return domain/results that routes serialize without changing contracts.

## 8. Deferred Items

- Actual service extraction.
- Model split.
- Frontend refactor.
- CI/CD.
- OpenAPI documentation.
- Existing frontend lint warnings.
