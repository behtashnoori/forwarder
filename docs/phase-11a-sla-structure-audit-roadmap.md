# Phase 11A: SLA Structure Audit and Admin Management Roadmap

## 1. Scope

This phase is audit and planning only. No runtime code, backend behavior, frontend behavior, database schema, routing, API contract, or business logic was changed.

The review covered current SLA-related model fields, migrations, backend services/routes, expert/admin frontend usage, OpenAPI/docs, and existing tests so future SLA management can be introduced safely.

## 2. Current SLA Data Model

The primary SLA fields are on `ShipmentRequest` in `backend/models.py`:

| Field | Current behavior |
| --- | --- |
| `sla_due_at` | Nullable `DateTime`. Stores the deadline when it has been assigned. |
| `priority` | String with default `normal`. The model comments elsewhere document `low`, `normal`, `high`, `urgent`, but there is no database enum/check constraint. |
| `status` | Non-null string with default `new`. Expert-console workflow status. |
| `status_request_status` | Non-null string with default `new`. Older/request status field still used in some queries. |
| `assigned_to` | Nullable foreign key to `expert_user.id`. |
| `created_at` | Non-null `DateTime`, default `datetime.utcnow`. |
| `updated_at` | Not present on `ShipmentRequest`; other tables may have update timestamps. |
| `assigned_at` | Not present on `ShipmentRequest`. Assignment timing is inferred from `ExpertConsoleLog` / assignment logs. |
| `sla_status` | Not stored in the database. It is computed on read. |

The expert-console migration `20240924_add_expert_console_fields.py` adds `assigned_to`, `status`, `sla_due_at`, `last_customer_touch_at`, `has_unread_for_assignee`, `priority`, and `estimated_value` to `shipment_request`. It makes `sla_due_at` nullable and `priority` non-null with server default `normal`.

There is no current SLA policy table, SLA rule table, request-to-policy link, or admin-managed SLA configuration model.

## 3. Current SLA Calculation

Current SLA logic is hardcoded and split across routes/services:

- Public shipment creation in `backend/services/shipment_service.py` sets `sla_due_at` to `None`, `priority` to `normal`, and status fields to `new`.
- `backend/routes/expert_console.py` sets `sla_due_at = datetime.utcnow() + timedelta(hours=2)` only when the status update endpoint changes a request to `assigned` and the request does not already have an SLA due date.
- `backend/services/assignment_service.py` assigns an expert and sets `req.status = "assigned"`, but does not set `sla_due_at`.
- `sla_status` is computed on read in expert request list/detail services:
  - default: `on_time`
  - if `now > sla_due_at`: `overdue`
  - else if `now + 2 hours > sla_due_at`: `due_soon`
- Expert KPI SLA counts are calculated in `backend/routes/expert_console.py`:
  - `overdue`: `sla_due_at < now` and status/status_request_status in `assigned` or `in_progress`
  - `due_soon`: `now < sla_due_at <= now + 2 hours` and status/status_request_status in `assigned` or `in_progress`
- Admin assignment summary reporting calculates SLA violations in `backend/services/admin_report_service.py` for requests past due with status in `assigned`, `in_progress`, or `waiting_for_customer`.
- `SLA_HOURS` exists in application configuration and environment docs, but the expert status update route currently uses a literal two-hour deadline rather than that config value.
- No scheduled job/background task was found that persists or updates SLA status. SLA status is computed at read/query time.

## 4. Current SLA Display

Expert Console:

- `src/pages/ExpertConsole.tsx` fetches real KPI data from `fetchKPIs`.
- The `پایش SLA / اولویت پاسخ‌گویی` card uses `kpis.sla.overdue` and `kpis.sla.due_soon` from the backend.
- Request cards show request-level `sla_due_at` and `sla_status` when `sla_due_at` exists.
- This card is not fake/purely presentational, but it is backed by hardcoded SLA rules and can be incomplete when assignment paths do not populate `sla_due_at`.

Request Detail:

- `src/pages/RequestDetail.tsx` displays `sla_due_at` and computed `sla_status` from the expert request detail API.
- The page does not calculate SLA itself beyond formatting labels/classes.

Admin Panel:

- `src/pages/AdminPanel.tsx` does not currently provide SLA management.
- The current dashboard does not expose SLA policy configuration.
- Admin reporting service has an SLA violation count for assignment summary, but that is not an admin SLA policy management feature.

API/OpenAPI:

- `src/lib/api.ts` includes `ExpertRequest.sla_due_at`, `ExpertRequest.sla_status`, and KPI `sla.overdue` / `sla.due_soon`.
- `docs/openapi/openapi.yaml` documents expert dashboard KPI SLA response shape.
- Existing docs mention SLA visibility and status update behavior, but no admin-managed SLA policies.

## 5. Current Priority Structure

Priority is stored on `ShipmentRequest.priority` as a string defaulting to `normal`.

Observed priority values in code/docs/tests include:

- `low`
- `normal`
- `high`
- `urgent`

There is no database enum/check constraint enforcing those values.

Who sets priority today:

- Public shipment request creation sets every new request to `normal`.
- No current customer/admin/expert UI was found that changes shipment request priority.
- Some tests/seed data create high/urgent priorities directly for contract coverage.

How priority behaves today:

- Expert Console priority filter is functional. It sends `priority` as a request-list query parameter.
- `backend/services/expert_request_list_service.py` filters with exact `ShipmentRequest.priority == priority`.
- Priority is not currently connected to SLA calculation. A `high` or `urgent` request only behaves differently for SLA if test/seed data manually gives it a different `sla_due_at`.
- Assignment/referral rules can reference priority conditions, but that is assignment matching, not SLA policy management.

If live production requests are created only through the public shipment flow, they will start as `normal` unless another process modifies the priority.

## 6. Gaps and Risks

- SLA deadline creation is hardcoded to two hours in the expert status update route.
- SLA near-deadline threshold is hardcoded to two hours in list/detail/KPI logic.
- `SLA_HOURS` config exists but is not consistently used by current SLA calculation.
- Direct assignment via `assignment_service.py` changes status to `assigned` without setting `sla_due_at`.
- `sla_status` is computed in more than one place, so future rule changes could drift if not centralized.
- There is no admin-managed SLA policy/rule table.
- There are no admin SLA CRUD endpoints.
- There is no Admin Panel SLA menu.
- Priority is a free string and is not currently managed as part of SLA.
- Current request statuses are hardcoded in multiple places.
- SLA behavior appears partially covered by API contract tests, but not locked as a dedicated SLA characterization suite.
- Existing data may have assigned/in-progress requests with null `sla_due_at`, so any future dashboard counts must handle historical nulls.
- A migration will likely be required for real SLA policy management.

## 7. Recommended SLA Business Definition

A safe first-version SLA definition should be deliberately small:

- SLA starts when a request becomes assigned to an expert.
- `new` requests can be excluded from active SLA until assignment, unless product decides first-response SLA starts at creation.
- Active SLA statuses for v1: `assigned`, `in_progress`.
- Optional pending status: decide explicitly whether `waiting_for_customer` pauses SLA, remains counted, or freezes the deadline.
- Terminal statuses `won`, `lost`, and `closed` should no longer count as pending SLA.
- `normal` priority defaults to the current two-hour response deadline to preserve existing behavior.
- `urgent`, `high`, and `low` deadlines should be policy-defined, not hardcoded.
- `due_soon` should be calculated when remaining time is less than or equal to the policy threshold.
- `overdue` should be calculated when `now > sla_due_at`.
- Existing `sla_due_at` values should not be silently overwritten unless the status transition or admin action clearly calls for recalculation.

Suggested initial default policies:

| Priority | Response deadline | Near-deadline threshold |
| --- | --- | --- |
| `urgent` | 30-60 minutes | 15 minutes |
| `high` | 1 hour | 20 minutes |
| `normal` | 2 hours | 30 minutes |
| `low` | 8 hours | 1 hour |

The exact numbers should be product-approved before implementation.

## 8. Recommended Data/API Design

Recommended new model/table:

`SlaPolicy`

| Field | Purpose |
| --- | --- |
| `id` | Primary key. |
| `name` | Admin-visible policy name. |
| `priority_scope` | Priority this policy applies to, or `all`/nullable for all priorities. |
| `request_status_scope` | Statuses that this policy applies to. Store as JSON or normalized child rows. |
| `transport_method_scope` | Optional transport method filter. |
| `shipping_type_scope` | Optional domestic/international filter. |
| `response_time_minutes` | Deadline duration. |
| `near_deadline_threshold_minutes` | Threshold for `due_soon`. |
| `is_active` | Enable/disable policy without deleting history. |
| `sort_order` | Deterministic conflict resolution if multiple policies match. |
| `created_at` | Audit timestamp. |
| `updated_at` | Audit timestamp. |

Optional later field:

- `shipment_request.sla_policy_id`: useful if the business wants historical traceability of which policy created a request deadline. This is not strictly required for v1 if the system only stores `sla_due_at`, but it is valuable for auditability.

Recommended service design:

- Add one backend SLA service responsible for:
  - resolving the active policy for a request
  - calculating `sla_due_at`
  - calculating `sla_status`
  - calculating remaining time
  - deciding whether a status transition starts, preserves, pauses, freezes, or stops SLA
- Replace duplicated two-hour threshold logic with this service after characterization tests exist.

Recommended future endpoints:

Admin:

- `GET /api/admin/sla-policies`
- `POST /api/admin/sla-policies`
- `PUT /api/admin/sla-policies/<id>`
- `PATCH /api/admin/sla-policies/<id>/disable` or `PATCH /api/admin/sla-policies/<id>`
- Optional: `DELETE /api/admin/sla-policies/<id>` only if hard delete is acceptable. Prefer disable for operational safety.

Expert:

- Keep existing expert request list/detail endpoints compatible.
- Continue returning `sla_due_at` and `sla_status`.
- Consider adding `remaining_time_minutes` later.
- Continue returning `kpis.sla.overdue` and `kpis.sla.due_soon`, but back them with the centralized SLA service/policies.

OpenAPI:

- Document admin SLA policy schemas and endpoints.
- Document any new expert response fields only after they are implemented.

## 9. Admin UI Recommendation

Add a future Admin Panel tab/menu:

`SLA / مهلت پاسخ‌گویی`

Recommended v1 UI:

- Policy list table/cards.
- Create policy form.
- Edit policy form.
- Enable/disable switch.
- Fields for name, priority, status scope, optional shipping/transport scope, response deadline, near-deadline threshold.
- Clear validation for duplicate/conflicting policies.
- Read-only preview of which policy is currently active for each priority/status combination if feasible later.

Keep the UI limited to policy management. Do not mix it with user management, referral rules, or site settings internals.

## 10. Expert UI Recommendation

Once SLA policies are real, Expert Console should show:

- SLA summary card backed by real policy calculations.
- Overdue count.
- Near-deadline count.
- Request-level SLA badge.
- Remaining response time.
- Optional SLA status filter: `همه`, `نزدیک به مهلت`, `گذشته از مهلت`.
- Priority/urgency indicator only when priority is actually set and meaningful.

Request Detail should continue showing:

- SLA due date.
- SLA status.
- Remaining time.
- Optional policy name if request-to-policy tracking is added.

Avoid showing SLA cards as operational truth until `sla_due_at` assignment paths and policy behavior are locked by tests.

## 11. Phased Roadmap

### Phase 11B: SLA Current Behavior Characterization

- Add tests that lock current behavior before changing it.
- Verify public request creation sets `priority = normal` and `sla_due_at = None`.
- Verify status update to `assigned` sets a two-hour `sla_due_at` when empty.
- Verify direct assignment currently does not set `sla_due_at`.
- Verify request list/detail computed `sla_status` values.
- Verify KPI overdue/due-soon counts.
- Verify priority filter exact-match behavior.
- No feature changes.

### Phase 11C: SLA Policy Backend Foundation

- Add SLA policy model/table only after 11B locks current behavior.
- Add admin-only CRUD/disable API.
- Add centralized SLA calculation service.
- Preserve existing expert response shape.
- Migration likely required for `sla_policy`.
- Keep default policy equivalent to current two-hour normal behavior.

### Phase 11D: Priority Rules Design & Backend

- Define how shipment request priority is assigned.
- Prefer automatic priority calculation based on loading/pickup date urgency if the available request data supports it.
- Add an explicit manual override path only after the automatic/default behavior is characterized.
- Keep priority values aligned with the current observed values: `low`, `normal`, `high`, `urgent`.
- Connect priority assignment to SLA policy resolution only through backend services, not frontend-only labels.
- Preserve existing request creation and expert-console response shapes unless a later implementation phase explicitly changes the API.

### Phase 11E: Admin SLA Management UI

- Add Admin Panel SLA tab/menu.
- Build policy list/create/edit/enable-disable UI.
- Use only the new admin SLA API.
- Do not redesign unrelated Admin Panel areas.

### Phase 11F: Expert Console SLA Integration

- Make Expert Console SLA cards/badges use real centralized SLA policy outputs.
- Add remaining-time display if API supports it.
- Add SLA filter only if backend supports it.
- Preserve existing request actions, filters, routing, and pagination.

### Phase 11G: Final SLA Smoke & Closure

- End-to-end smoke test admin policy creation and expert SLA display.
- Verify migrations on fresh and existing databases.
- Verify OpenAPI/docs alignment.
- Confirm no legacy hardcoded two-hour logic remains outside default policy setup.

## 12. Recommended Phase 11B Prompt

```text
You are working on the Forwarder project.

Phase 11B: SLA Current Behavior Characterization

Goal:
Add characterization tests and documentation that lock the current SLA behavior before implementing admin-managed SLA policies.

Important:
This phase is testing/characterization only.
Do not implement SLA management.
Do not add admin SLA menus.
Do not add API endpoints.
Do not change business behavior.
Do not create policy tables.
Do not refactor runtime code unless a tiny testability fix is absolutely required and approved by the existing behavior.

Areas to characterize:
- Shipment request creation SLA defaults.
- Expert status update to assigned.
- Direct assignment behavior.
- Expert request list/detail SLA status serialization.
- Expert dashboard KPI SLA counts.
- Priority filter behavior.
- Admin assignment summary SLA violation count if existing tests do not already cover it.

Expected current behavior to lock:
- New public shipment requests have priority normal.
- New public shipment requests have sla_due_at null.
- sla_status is not stored in the database.
- Status update to assigned sets sla_due_at to approximately now + 2 hours if it was empty.
- Direct assignment through assignment_service sets status assigned but does not set sla_due_at.
- Request list/detail compute sla_status as on_time, due_soon, or overdue based on sla_due_at and a hardcoded two-hour near-deadline window.
- Expert KPI overdue/due_soon counts are based on sla_due_at and active statuses.
- Priority filter performs exact-match filtering on ShipmentRequest.priority.

Allowed files:
- backend/tests/* existing relevant contract/characterization test files
- docs/phase-11b-sla-current-behavior-characterization.md

Avoid changing:
- frontend files
- backend runtime files
- migrations
- API response shapes
- AdminPanel
- ExpertConsole
- RequestDetail

Verification:
Run:
- npm.cmd run lint
- npm.cmd run build
- npm.cmd run check:structure
- python -m pytest -q
- git diff --check

Final report:
1. Changed files
2. Tests added/adjusted
3. Current SLA defaults locked
4. Current SLA assignment behavior locked
5. Current SLA status computation locked
6. Current KPI behavior locked
7. Current priority filter behavior locked
8. Runtime behavior changed or not
9. Test/build results
10. Whether Phase 11B is acceptable

Do not enter Phase 11C.
Do not implement SLA management.
```

## Verification

Recorded after this audit document was added:

- `npm.cmd run lint`: passed with 10 existing warnings and 0 errors. Warnings are the existing React fast-refresh/shared-export warnings plus the existing `UserManagement.tsx` hook dependency warning.
- `npm.cmd run build`: passed. Vite reported the existing browserslist age notice and chunk-size warning.
- `npm.cmd run check:structure`: passed.
- `python -m pytest -q`: blocked in this environment because `python` is not available in PATH.
- `git diff --check`: passed. Git emitted a line-ending notice for `src/pages/ExpertConsole.tsx`, but no whitespace errors.
