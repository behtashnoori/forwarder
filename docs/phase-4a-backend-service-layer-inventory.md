# Phase 4A Backend Service Layer Inventory

Date: 2026-05-18

## 1. Scope

Phase 4A is **inventory and design only** for future backend service layer extraction. The work in this phase is limited to reading backend routes, identifying business logic and direct database access inside route/controller modules, and proposing incremental service/repository boundaries.

No runtime code was changed in Phase 4A. Specifically, this phase does **not** perform any service extraction, route refactor, migration, model/schema change, API behavior change, response contract change, frontend change, auth/security logic change, test skip/xfail, or test assertion change.

Inputs reviewed before this inventory:

- `docs/phase-0-baseline.md`
- `docs/phase-1a-quality-triage.md`
- `docs/phase-1b-frontend-lint-fixes.md`
- `docs/phase-1c-backend-test-environment.md`
- `docs/phase-1d-backend-test-final-fix.md`
- `docs/phase-2-security-config-hardening.md`
- `docs/phase-3-migration-cleanup.md`
- `docs/phase-3h-backend-regression-gate.md`

Route modules reviewed:

- `backend/routes/shipment_request.py`
- `backend/routes/expert_console.py`
- `backend/routes/crm.py`
- `backend/routes/user_management.py`
- `backend/routes/admin_panel.py`
- `backend/routes/monitoring.py`
- `backend/routes/site_settings.py`
- `backend/routes/admin_site_settings.py` requested path; file is absent, and admin site settings are implemented in `backend/routes/site_settings.py` via `admin_site_bp`.
- `backend/routes/public_tracking.py`
- `backend/routes/customer_gamification.py`

## 2. Controlled Risk Note

Phase 3H remains `BLOCKED_BY_ENV` in Codex because the Python runtime dependencies required for backend tests are missing and the package index/proxy returned `403 Forbidden` while resolving Flask from the official requirements files. This was accepted as an **environment-only blocker**, not a confirmed code regression.

Phase 4A proceeds under controlled risk because it is documentation/design only. No backend behavior, schema, auth policy, frontend code, or tests are changed. Backend pytest must still be executed in a valid local/CI environment before any Phase 4B+ implementation is merged. If Codex remains `ENV_BLOCKED`, do not spend additional time repeatedly attempting dependency restore; cite Phase 3H and require local/CI pytest evidence.

## 3. Route Inventory

### Summary Table

| Module | Domain | Responsibility | Direct DB access | Business logic density | Suggested service | Suggested repository | Refactor risk | Priority |
|---|---|---|---:|---|---|---|---|---|
| `backend/routes/shipment_request.py` | Public shipment intake | List transport methods and create public shipment requests. | Medium: `TransportMethod`, `ShipmentRequest`, `ShipmentRequestLog`, `CustomerGamification`, `CustomerWorkflowStep`. | High | `shipment_service.py`, `shipment_intake_service.py`, `tracking_code_service.py`, `referral_service.py` | `shipment_repository.py`, `transport_method_repository.py`, `customer_gamification_repository.py` | High: public intake, validation, gamification, tracking-code uniqueness, referral auto-assignment, and transaction ordering. | P2 |
| `backend/routes/expert_console.py` | Expert operations | Expert request queue/detail, assignment, status updates, quotes, messages, notifications, auth helpers, dashboard KPIs. | Very high: many `ShipmentRequest`, geographic, expert, quote, message, notification, log queries and commits. | High | `expert_console_service.py`, `assignment_service.py`, `quote_service.py`, `message_service.py`, `notification_service.py`, `expert_dashboard_service.py` | `shipment_repository.py`, `expert_repository.py`, `expert_console_repository.py`, `quote_repository.py`, `notification_repository.py` | Very high: largest route, many response branches and side effects. | P3 |
| `backend/routes/crm.py` | CRM | Customers, opportunities, activities, and CRM KPI dashboard. | High: customer/opportunity/activity/task/report/expert/request queries and writes. | High | `crm_service.py`, `crm_customer_service.py`, `crm_opportunity_service.py`, `crm_activity_service.py`, `crm_dashboard_service.py` | `crm_repository.py`, `customer_repository.py`, `opportunity_repository.py`, `activity_repository.py` | High: protected endpoints, filters, pagination, aggregates, and response shaping. | P2 |
| `backend/routes/user_management.py` | Admin user and assignment management | Transport methods, expert users, hierarchy/specializations, assignment rules, statistics, manual assignment. | Very high: users, transport methods, specializations, assignment rules/logs, shipment requests. | High | `user_management_service.py`, `transport_method_service.py`, `assignment_rule_service.py`, `manual_assignment_service.py` | `user_repository.py`, `transport_method_repository.py`, `assignment_repository.py`, `shipment_repository.py` | High: admin-only write/destructive operations, password hashing, delete/reassignment safety, manual assignment side effects. | P3 |
| `backend/routes/admin_panel.py` | Admin dashboard and referral | Admin shipment request detail/list, dashboard, assignment summary, referral rules CRUD/preview. | High: shipment, expert, referral rule/state, assignment/referral log queries and commits. | High | `admin_dashboard_service.py`, `admin_request_service.py`, `referral_rule_service.py`, `assignment_report_service.py` | `admin_repository.py`, `shipment_repository.py`, `referral_repository.py`, `expert_repository.py`, `assignment_repository.py` | High: admin response contracts, referral strategy JSON/preview behavior, dashboard metrics. | P3 |
| `backend/routes/monitoring.py` | Monitoring and analytics | Health, metrics, database/business analytics, dashboard, alerts, log retrieval, ping. | Low in route file: delegates to `system_monitor` and `analytics_engine`; no route-level `db.session`. | Medium | `monitoring_service.py`, `alert_service.py`, `analytics_service.py` | Optional future `monitoring_repository.py`; existing monitor/analytics components already encapsulate data access. | Low/Medium: mostly orchestration and pure alert calculation, but ops-facing response shape must remain stable. | P1 |
| `backend/routes/site_settings.py` | Public/admin site settings | Public settings read, admin settings read/update, logo upload, upload serving. | Low: `SiteSetting` read/upsert plus filesystem write for upload. | Medium | `settings_service.py`, `upload_service.py` | `settings_repository.py` | Low: small module and clear boundaries; must preserve upload validation and served paths. | P1 |
| `backend/routes/admin_site_settings.py` | Admin site settings alias | Requested module path is absent. Admin settings routes are in `site_settings.py` under `admin_site_bp`. | N/A | Low | Covered by `settings_service.py` | Covered by `settings_repository.py` | Low if treated as `site_settings.py`; do not introduce a file move in Phase 4A/first extraction. | P1 documentation note |
| `backend/routes/public_tracking.py` | Public tracking | Resolve request id/tracking code and assemble customer-facing shipment tracking response. | Medium: shipment, log, assignment, quote, geography, expert lookups. | High | `tracking_service.py`, `timeline_service.py`, `quote_read_service.py` | `tracking_repository.py`, `shipment_repository.py`, `quote_repository.py`, `assignment_repository.py` | Medium/High: public response contract, timeline semantics, fallback identifiers. | P2 |
| `backend/routes/customer_gamification.py` | Customer gamification | Customer registration/email verification, profile, workflow, complete step, leaderboard. | High: gamification, workflow, shipment, quote queries and commits. | High | `customer_gamification_service.py`, `customer_workflow_service.py`, `verification_service.py`, `leaderboard_service.py` | `customer_gamification_repository.py`, `workflow_repository.py`, `shipment_repository.py`, `quote_repository.py` | High: customer-facing workflow/points side effects and email verification semantics. | P3 |

### Module Details

#### `backend/routes/shipment_request.py`

1. **Primary responsibility**: public shipment request intake and transport-method options.
2. **Main endpoints**: `GET /api/transport-methods`, `POST /api/shipment-request`, `GET /api/shipment-request/ping`.
3. **Business logic in route**:
   - Splits transport methods into international/domestic buckets by method name.
   - Validates domestic vs international origin/destination shape.
   - Normalizes legacy/new transport method fields.
   - Builds a large `ShipmentRequest` payload with default statuses and customer metadata.
   - Generates fallback tracking codes with collision checks.
   - Applies gamification points/workflow side effects when `gamification_customer_id` is provided.
   - Triggers referral-based automatic assignment after initial request commit.
4. **Direct DB queries**: active `TransportMethod` list; `ShipmentRequest` insert and tracking-code collision lookup; `ShipmentRequestLog` insert; `CustomerGamification` lookup/update; `CustomerWorkflowStep` insert.
5. **Validation logic**: shipping type enum, domestic id coercion, international location required fields, phone format, transport method preference enum, and optional customer/gamification payload handling.
6. **Side effects**: request creation, request log creation, tracking code generation, loyalty points, workflow step creation, commit/rollback, referral auto-assignment call, operational logging.
7. **Suggested services**: `shipment_intake_service.py` for request creation/validation orchestration; `tracking_code_service.py` for tracking-code generation; `referral_service.py` adapter around `referral_engine`; `customer_gamification_service.py` for points/workflow side effects.
8. **Suggested repositories**: `shipment_repository.py`, `transport_method_repository.py`, `customer_gamification_repository.py`.
9. **Refactor risk**: **High** because this is a public write path with multiple transaction boundaries and downstream assignment/gamification effects.
10. **Execution priority**: **P2**. Extract after smaller read/orchestration domains are stabilized.

#### `backend/routes/expert_console.py`

1. **Primary responsibility**: expert-facing request operations, assignment/status/quote/message workflows, notifications, login helpers, and dashboard KPIs.
2. **Main endpoints**: `GET /api/expert/requests`, `GET /api/expert/requests/<id>`, assignment/status/quote/message endpoints, notification list/mark-read endpoints, auth login/refresh/logout, dashboard KPIs, mark-read, experts list, ping.
3. **Business logic in route**:
   - Enforces per-request access for non-admin users.
   - Builds complex filtered/sorted/paginated request lists.
   - Resolves geographic labels and assigned expert details for responses.
   - Calculates SLA status and dashboard KPIs.
   - Performs assignment and status transitions.
   - Creates quotes, messages, logs, and notifications.
   - Shapes latest-quote and notification responses.
4. **Direct DB queries**: `ShipmentRequest`, `Province`, `County`, `City`, `ExpertUser`, `ExpertQuote`, `ExpertConsoleLog`, `ExpertConsoleMessage`, `ExpertConsoleNotification`, plus multiple commits/rollbacks.
5. **Validation logic**: request query params, sort allow-list, assignment input, status update payload, quote payload, message payload, mark-read payload, and login payload validation/sanitization.
6. **Side effects**: assignment, status changes, request mark-read, quote creation, message creation, notification creation/mark-read, dashboard metric reads, auth token issue/refresh/logout.
7. **Suggested services**: `expert_console_service.py`, `assignment_service.py`, `status_transition_service.py`, `quote_service.py`, `message_service.py`, `notification_service.py`, `expert_dashboard_service.py`.
8. **Suggested repositories**: `shipment_repository.py`, `expert_repository.py`, `expert_console_repository.py`, `quote_repository.py`, `notification_repository.py`.
9. **Refactor risk**: **Very high** because the route is large, write-heavy, auth-sensitive, and response-shape-heavy.
10. **Execution priority**: **P3**. Defer until characterization tests exist for critical workflows.

#### `backend/routes/crm.py`

1. **Primary responsibility**: CRM customer/opportunity/activity CRUD-style workflows and CRM dashboard metrics.
2. **Main endpoints**: `GET/POST /api/crm/customers`, `GET/PUT /api/crm/customers/<id>`, `GET/POST /api/crm/opportunities`, `GET/POST /api/crm/activities`, `GET /api/crm/dashboard/kpis`, ping.
3. **Business logic in route**:
   - Applies search/status/type filters and pagination.
   - Formats customer detail with opportunities, activities, and requests.
   - Creates/updates customers, opportunities, and activities.
   - Computes dashboard KPIs, monthly customer counts, pipeline value, and recent activity summaries.
4. **Direct DB queries**: `Customer`, `CustomerContact`, `Opportunity`, `Activity`, `Task`, `Report`, `ShipmentRequest`, `ExpertUser` with filters, pagination, joins/aggregates, inserts/updates, and commits.
5. **Validation logic**: mostly implicit payload parsing and enum/default handling; date parsing for activity due dates; route does not yet centralize required-field validation consistently.
6. **Side effects**: customer/opportunity/activity creation and updates, commit/rollback, dashboard aggregate reads, error logging.
7. **Suggested services**: `crm_customer_service.py`, `crm_opportunity_service.py`, `crm_activity_service.py`, `crm_dashboard_service.py`.
8. **Suggested repositories**: `customer_repository.py`, `opportunity_repository.py`, `activity_repository.py`, `crm_repository.py` for shared CRM query composition.
9. **Refactor risk**: **High** due to filters, pagination, dashboard aggregates, and protected business-expert endpoints.
10. **Execution priority**: **P2** for read/query extraction after a smaller Phase 4B candidate; write workflows later.

#### `backend/routes/user_management.py`

1. **Primary responsibility**: admin-only transport method/user/hierarchy/specialization management plus assignment rules, assignment statistics, and manual assignment.
2. **Main endpoints**: transport method list/create, user list/create/update/delete, assignment rule list/create/update, assignment statistics, manual assignment, ping.
3. **Business logic in route**:
   - Serializes user hierarchy, manager, subordinate count, specializations, and workload.
   - Validates required user creation fields and username uniqueness.
   - Hashes passwords and writes specializations.
   - Applies safe delete/reassignment rules.
   - Creates/updates assignment rules.
   - Computes assignment statistics and performs manual request assignment.
4. **Direct DB queries**: `TransportMethod`, `ExpertUser`, `ExpertSpecialization`, `AssignmentRule`, `AssignmentLog`, `ShipmentRequest`, plus related console logs/messages/notifications and CRM entities during delete safety paths.
5. **Validation logic**: required user fields, username conflict, manager/role/specialization input, delete preconditions, assignment rule payload, manual assignment payload.
6. **Side effects**: create/update/delete users, password hashing, specialization replacement, transport method creation, assignment-rule writes, manual assignment status/assignee updates, logs/notifications, commit/rollback.
7. **Suggested services**: `user_management_service.py`, `transport_method_service.py`, `user_specialization_service.py`, `assignment_rule_service.py`, `manual_assignment_service.py`.
8. **Suggested repositories**: `user_repository.py`, `transport_method_repository.py`, `assignment_repository.py`, `shipment_repository.py`, `expert_console_repository.py`.
9. **Refactor risk**: **High** due to admin-destructive operations and workflow side effects.
10. **Execution priority**: **P3**. Defer until smaller services establish transaction and repository conventions.

#### `backend/routes/admin_panel.py`

1. **Primary responsibility**: admin shipment request views, admin dashboard/reporting, and referral rule management.
2. **Main endpoints**: shipment request detail/list, dashboard, assignment summary report, referral rule list/create/update/delete/preview.
3. **Business logic in route**:
   - Serializes admin request details and paginated request lists.
   - Computes dashboard totals, status distributions, recent requests, assignment metrics, and reports.
   - Handles referral rule CRUD including strategy/settings fields.
   - Provides referral preview behavior without changing the candidate request.
4. **Direct DB queries**: `ShipmentRequest`, `ExpertUser`, `AssignmentLog`, `ReferralAssignmentLog`, `ReferralRule`, `ReferralRuleState`, `ReferralAutoAssignState`, request logs, aggregate counts, and commits for rule writes.
5. **Validation logic**: list filter/sort/pagination params, referral rule payload/defaults, rule id existence, preview payload/request lookup.
6. **Side effects**: referral rule create/update/delete, timestamp updates, commit/rollback, preview computation, dashboard/report reads.
7. **Suggested services**: `admin_request_service.py`, `admin_dashboard_service.py`, `assignment_report_service.py`, `referral_rule_service.py`.
8. **Suggested repositories**: `admin_repository.py`, `shipment_repository.py`, `expert_repository.py`, `assignment_repository.py`, `referral_repository.py`.
9. **Refactor risk**: **High** due to admin response contracts and referral rule semantics.
10. **Execution priority**: **P3**. Prefer extracting read-only dashboard/report helpers before referral write workflows.

#### `backend/routes/monitoring.py`

1. **Primary responsibility**: monitoring and analytics API orchestration.
2. **Main endpoints**: health, metrics, database, business, customer/sales/performance analytics, dashboard, alerts, acknowledge alerts, logs, ping.
3. **Business logic in route**:
   - Orchestrates calls to `system_monitor` and `analytics_engine`.
   - Composes dashboard response from several monitor/analytics calls.
   - Calculates memory/CPU/error-rate/response-time alerts from metrics.
   - Parses log query params.
4. **Direct DB queries**: none in route file; data access is delegated to monitoring/analytics components.
5. **Validation logic**: `days` query param, log query params, acknowledge payload. Auth/role behavior must remain unchanged.
6. **Side effects**: alert acknowledgement currently returns a success response; operational error logging; no route-level DB write.
7. **Suggested services**: `monitoring_service.py` for dashboard orchestration; `alert_service.py` for threshold calculation/acknowledgement; `analytics_service.py` as adapter if analytics code is later decomposed.
8. **Suggested repositories**: none required for first extraction; optional `monitoring_repository.py` only if existing monitoring/analytics data access is split later.
9. **Refactor risk**: **Low/Medium** because the route is mostly orchestration and pure computation, but supervisor protections and response contracts are ops-facing.
10. **Execution priority**: **P1** and recommended first Phase 4B candidate.

#### `backend/routes/site_settings.py`

1. **Primary responsibility**: public/admin site settings and logo upload/serving.
2. **Main endpoints**: `GET /api/site-settings`, admin `GET/PUT /api/admin/site-settings`, admin upload, public upload serving.
3. **Business logic in route**:
   - Defines default settings.
   - Merges persisted settings over defaults.
   - Upserts allowed setting keys.
   - Validates upload file presence, filename, extension, and save path.
4. **Direct DB queries**: `SiteSetting` list/read and upsert with commit.
5. **Validation logic**: admin settings JSON keys are limited by defaults; upload file and extension validation.
6. **Side effects**: settings upsert, filesystem directory creation/file save, commit/rollback, serving uploaded assets.
7. **Suggested services**: `settings_service.py`, `upload_service.py`.
8. **Suggested repositories**: `settings_repository.py`.
9. **Refactor risk**: **Low** because it is small and bounded; filesystem behavior still needs careful characterization.
10. **Execution priority**: **P1**, but monitoring is slightly safer as first candidate because it avoids filesystem writes.

#### `backend/routes/admin_site_settings.py`

1. **Primary responsibility**: no separate module exists at this path.
2. **Main endpoints**: N/A; admin site settings are implemented in `site_settings.py`.
3. **Business logic in route**: N/A outside `site_settings.py`.
4. **Direct DB queries**: N/A outside `site_settings.py`.
5. **Validation logic**: N/A outside `site_settings.py`.
6. **Side effects**: N/A outside `site_settings.py`.
7. **Suggested services**: covered by `settings_service.py` and `upload_service.py`.
8. **Suggested repositories**: covered by `settings_repository.py`.
9. **Refactor risk**: **Low** if no file move is introduced. Creating/moving a separate admin module should be deferred because it changes registration/import structure.
10. **Execution priority**: **P1 documentation note** only.

#### `backend/routes/public_tracking.py`

1. **Primary responsibility**: public tracking lookup and customer-facing tracking response assembly.
2. **Main endpoint**: `GET /api/public/track/<identifier>`.
3. **Business logic in route**:
   - Resolves numeric ids and tracking codes with legacy fallback.
   - Derives display tracking number.
   - Builds timeline/workflow step structures from status, assignment time, quote time, and final decision logs.
   - Resolves domestic geographic labels and assigned expert details.
   - Returns latest quote summary.
4. **Direct DB queries**: `ShipmentRequest`, `ShipmentRequestLog`, `ExpertQuote`, `AssignmentLog`, `Province`, `County`, `City`, `ExpertUser`.
5. **Validation logic**: identifier resolution and not-found behavior; no auth required; must not expose additional sensitive fields during extraction.
6. **Side effects**: none expected beyond error logging; read-only public route.
7. **Suggested services**: `tracking_service.py`, `timeline_service.py`, `quote_read_service.py`.
8. **Suggested repositories**: `tracking_repository.py`, `shipment_repository.py`, `assignment_repository.py`, `quote_repository.py`, `expert_repository.py`.
9. **Refactor risk**: **Medium/High** because it is public-facing and response contract/timeline semantics are user-visible.
10. **Execution priority**: **P2** after lower-risk service conventions are established.

#### `backend/routes/customer_gamification.py`

1. **Primary responsibility**: customer registration/verification, gamification profile/workflow, step completion, and leaderboard.
2. **Main endpoints**: register, verify email, profile, workflow, complete step, leaderboard.
3. **Business logic in route**:
   - Generates email verification tokens and expiration.
   - Logs verification-email sending placeholder behavior.
   - Detects existing customers by email.
   - Awards points for verification and workflow step completion.
   - Builds profile, recent steps, recent requests, workflow progress, assigned expert, and latest quote responses.
   - Ranks customers for leaderboard.
4. **Direct DB queries**: `CustomerGamification`, `CustomerWorkflowStep`, `ShipmentRequest`, `ExpertQuote`, and related expert relationships.
5. **Validation logic**: email presence/format-lite, phone format, duplicate email, token presence/expiry, customer/request lookup, duplicate workflow step, allowed step points/order mapping.
6. **Side effects**: customer creation, token persistence, verification state mutation, loyalty points update, workflow step insert/update, commit/rollback, email logging.
7. **Suggested services**: `customer_gamification_service.py`, `verification_service.py`, `customer_workflow_service.py`, `leaderboard_service.py`.
8. **Suggested repositories**: `customer_gamification_repository.py`, `workflow_repository.py`, `shipment_repository.py`, `quote_repository.py`.
9. **Refactor risk**: **High** because points/workflow state transitions are customer-facing and partially coupled to shipment intake.
10. **Execution priority**: **P3**. Defer until tests cover point awards and workflow idempotency.

## 4. Recommended Service Boundaries

Suggested future package: `backend/services/`.

| Service | Responsibility | Initial consumers | Notes |
|---|---|---|---|
| `shipment_service.py` | Shared shipment request read/update/status operations. | shipment intake, expert console, admin panel, tracking, gamification. | Keep transaction ownership explicit. |
| `shipment_intake_service.py` | Public request creation orchestration and intake validation. | `shipment_request.py`. | Extract only after characterization tests for creation, gamification, and referral behavior. |
| `tracking_code_service.py` | Tracking-code generation and uniqueness policy. | shipment intake, tracking. | Pure helper plus repository collision check. |
| `expert_service.py` | Expert lookup/list/workload serialization. | expert console, user management, admin reports. | Do not mix password management into this service. |
| `expert_console_service.py` | Expert queue/detail response assembly. | `expert_console.py`. | Candidate after lower-risk services. |
| `assignment_service.py` | Assignment policy, manual assignment, assignment logs. | expert console, user management, admin reports. | Must preserve side-effect order. |
| `referral_service.py` | Referral auto-assignment and rule orchestration adapter. | shipment intake, admin panel. | Coordinate with existing `referral_engine`. |
| `quote_service.py` | Quote creation and latest/list quote reads. | expert console, tracking, customer workflow. | Separate write vs read methods. |
| `message_service.py` | Expert console message creation/list serialization. | expert console. | May be part of expert console service initially. |
| `notification_service.py` | Notification create/list/mark-read behavior. | expert console, assignment/status/quote workflows. | Preserve unread flags and timestamps. |
| `crm_service.py` | Shared CRM orchestration. | `crm.py`. | Thin umbrella only; prefer domain services below. |
| `crm_customer_service.py` | Customer list/detail/create/update. | `crm.py`. | Include pagination/filter DTO handling. |
| `crm_opportunity_service.py` | Opportunity list/create/update lifecycle. | `crm.py`. | Preserve defaults and date handling. |
| `crm_activity_service.py` | Activity list/create/update lifecycle. | `crm.py`. | Preserve due-date parsing and status defaults. |
| `crm_dashboard_service.py` | CRM KPIs and aggregate reporting. | CRM dashboard, admin reports later. | Read-only extraction candidate after monitoring/settings. |
| `admin_dashboard_service.py` | Admin dashboard metrics and response assembly. | `admin_panel.py`. | Read-only portions before referral writes. |
| `assignment_report_service.py` | Assignment summary metrics. | `admin_panel.py`, user management. | Keep reporting separate from mutation. |
| `referral_rule_service.py` | Referral rule CRUD/preview. | `admin_panel.py`. | Defer write workflows. |
| `user_management_service.py` | Admin user create/update/delete orchestration. | `user_management.py`. | Must preserve password hashing and safe-delete behavior. |
| `transport_method_service.py` | Transport method list/create and public categorization. | shipment intake, user management. | Can centralize current categorization rules. |
| `settings_service.py` | Site setting defaults, get/update/upsert policy. | `site_settings.py`. | Low-risk candidate after monitoring. |
| `upload_service.py` | Logo upload validation and filesystem persistence. | `site_settings.py`. | Keep filesystem config injectable/testable. |
| `tracking_service.py` | Public tracking response assembly. | `public_tracking.py`. | Must not change exposed fields. |
| `timeline_service.py` | Workflow/timeline derivation. | public tracking, customer gamification. | Good pure extraction candidate once behavior is characterized. |
| `customer_gamification_service.py` | Customer registration, profile, points, loyalty levels. | customer gamification, shipment intake. | Needs idempotency tests. |
| `customer_workflow_service.py` | Workflow step definitions, completion, progress response. | customer gamification, tracking. | Extract step mapping as pure data/function. |
| `verification_service.py` | Verification token generation/expiry/email dispatch adapter. | customer gamification. | Existing email behavior is logging-only; do not change behavior. |
| `leaderboard_service.py` | Leaderboard ranking response. | customer gamification. | Low direct complexity but depends on gamification repository. |
| `monitoring_service.py` | Monitoring dashboard orchestration and simple metrics adapters. | `monitoring.py`. | Recommended Phase 4B candidate. |
| `alert_service.py` | Alert threshold calculation and acknowledgement response. | `monitoring.py`. | Pure-ish extraction, low DB risk. |
| `analytics_service.py` | Adapter around `analytics_engine` if needed. | `monitoring.py`. | Optional. |

## 5. Recommended Repository Boundaries

Suggested future package: `backend/repositories/`.

| Repository | Entities/queries | Notes |
|---|---|---|
| `shipment_repository.py` | `ShipmentRequest`, `ShipmentRequestLog`, request list/detail/status queries, tracking-code collision checks. | Shared across intake, expert console, admin, tracking, gamification. |
| `transport_method_repository.py` | `TransportMethod` active/admin list/create queries. | Shared by public intake and user management. |
| `expert_repository.py` | `ExpertUser`, manager/subordinate lookups, active expert lists, workload-support queries. | Keep password hash write policy in services. |
| `user_repository.py` | Admin user CRUD, username uniqueness, specialization persistence. | May wrap `ExpertUser` and `ExpertSpecialization`. |
| `expert_console_repository.py` | `ExpertConsoleLog`, `ExpertConsoleMessage`, `ExpertConsoleNotification`. | Can split into log/message/notification repositories later. |
| `quote_repository.py` | `ExpertQuote` create/latest/list queries. | Shared by expert console, tracking, customer workflow. |
| `crm_repository.py` | Shared CRM query composition across `Customer`, `CustomerContact`, `Opportunity`, `Activity`, `Task`, `Report`. | Prefer finer repositories once services stabilize. |
| `customer_repository.py` | `Customer` list/detail/create/update. | CRM-specific customer entity, not gamification customer. |
| `opportunity_repository.py` | `Opportunity` list/create/update, pipeline aggregates. | CRM domain. |
| `activity_repository.py` | `Activity` list/create/update, recent activity aggregates. | CRM domain. |
| `assignment_repository.py` | `AssignmentLog`, assignment statistics, manual assignment helper queries. | Coordinate with referral assignment logs. |
| `referral_repository.py` | `ReferralRule`, `ReferralRuleState`, `ReferralAutoAssignState`, `ReferralAssignmentLog`. | Used by referral service and admin panel. |
| `settings_repository.py` | `SiteSetting` get/list/upsert. | Small and bounded. |
| `customer_gamification_repository.py` | `CustomerGamification` lookup/create/update, leaderboard. | Shared by intake and customer endpoints. |
| `workflow_repository.py` | `CustomerWorkflowStep` lookup/create/update/list. | Keep points policy in service. |
| `tracking_repository.py` | Identifier resolution, final-decision log lookup, assignment date lookup. | May delegate to shipment/assignment/quote repositories. |
| `geo_repository.py` | `Province`, `County`, `City` display lookups. | Could reduce repeated route-level geographic queries. |
| `monitoring_repository.py` | Future DB-backed monitoring queries only if existing monitor/analytics components are decomposed. | Not required for first Phase 4B candidate. |

## 6. Phase 4B Candidate

**Recommended first implementation candidate: extract monitoring alert/dashboard orchestration from `backend/routes/monitoring.py` into `backend/services/monitoring_service.py` and `backend/services/alert_service.py`.**

### Why this candidate

- It is the smallest low-risk domain in the reviewed set.
- The route file has no route-level `db.session` access; most collection already delegates to `system_monitor` and `analytics_engine`.
- The alert threshold logic is pure enough to characterize and move without changing persistence, schema, auth, or frontend behavior.
- It avoids public/customer-facing write workflows, referral assignment, password hashing, and gamification point mutations.

### Files likely involved in Phase 4B

- `backend/routes/monitoring.py`
- New `backend/services/monitoring_service.py`
- New `backend/services/alert_service.py`
- Optional new `backend/services/__init__.py`
- Tests only if a valid Python dependency environment is available; do not skip or weaken existing tests.

### Tests/checks that should run for Phase 4B

- `pytest -q`
- `pytest backend/tests/test_security_config.py -q` to keep supervisor-role protection intact.
- Targeted monitoring route/service tests if present or newly added.
- `npm run lint`
- `npm run build`
- `npm run check:structure`
- `git diff --check`

If pytest remains `ENV_BLOCKED` in Codex, local/CI pytest in a valid Python environment is required before merge.

### Behaviors that must not change in Phase 4B

- Endpoint URLs, HTTP methods, status codes, and auth/role decorators.
- JSON response keys and nested structures for health, metrics, database, business, analytics, dashboard, alerts, logs, acknowledge, and ping.
- Alert thresholds and alert type/category/message semantics for memory, CPU, error rate, and response time.
- Error messages and failure status behavior.
- No migration, model, schema, frontend, or security-policy change.

## 7. Refactor Rules for Phase 4B+

- Each PR must extract **one bounded domain only**.
- Route behavior must remain stable.
- Response contracts must remain stable.
- URL paths, HTTP methods, status codes, auth decorators, role checks, and CORS/security behavior must remain stable unless a later phase explicitly scopes a security change.
- No migration.
- No model/schema change.
- No frontend change unless explicitly scoped in a later phase.
- No test skip/xfail and no assertion weakening.
- Preserve transaction boundaries and side-effect ordering before moving logic.
- Add characterization tests before extraction when behavior is not already covered.
- Tests must pass in a valid Python environment before merge.
- If pytest is `ENV_BLOCKED` in Codex, local/CI pytest evidence is required before merge.
- Prefer extracting pure computation/serialization helpers first, then read repositories, then write workflows.
- Keep repositories thin: query and persistence only; no response formatting or business policy.
- Keep services framework-light where practical: routes may keep Flask request/response handling while services own business orchestration.
- Do not move large files or split `backend/models.py` as part of service extraction PRs.

## 8. Deferred Items

The following are explicitly outside Phase 4A scope and should remain deferred:

- Actual service extraction.
- Route refactor implementation.
- Model split.
- Database migration.
- Model/schema change.
- Frontend refactor.
- Auth/security logic changes.
- CI/CD changes.
- OpenAPI generation/documentation.
- Existing lint warnings.
- Broad formatting-only churn.
