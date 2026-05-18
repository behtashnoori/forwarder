# Phase 2 Security & Config Hardening

Date: 2026-05-18

## 1. Scope

Phase 2 is limited to backend security/configuration hardening. The work intentionally avoids feature changes, frontend/UI edits, migrations, database model changes, schema changes, and backend architecture refactors.

In scope:

- Runtime environment validation for development, testing, and production.
- Database URL fallback hardening.
- SECRET_KEY and JWT_SECRET_KEY handling.
- Production CORS allowlist hardening.
- Minimal auth/role protection for sensitive backend endpoints found during the audit.
- Focused tests for production fail-fast behavior and newly protected endpoints.

Out of scope:

- Migration cleanup.
- Model/schema changes.
- Service-layer extraction or route-module refactors.
- Frontend feature or UI changes.
- CI/CD pipeline setup.

## 2. Before

Quality gate before Phase 2 changes:

| Check | Result | Notes |
|---|---:|---|
| `pytest -q` | PASS | 44 passed, 45 warnings. |
| `npm run lint` | PASS_WITH_WARNINGS | 0 errors, 17 existing warnings. |
| `npm run build` | PASS_WITH_WARNINGS | Build passed; existing Browserslist/chunk-size warnings. |
| `npm run check:structure` | PASS_WITH_WARNINGS | Structure check passed; existing root migration warnings. |

Security/config risks carried forward from Phase 0-1:

- App factory still had a hardcoded production-like PostgreSQL fallback when `DATABASE_URL` was missing.
- `SecurityManager` generated random runtime secrets when `SECRET_KEY`/`JWT_SECRET_KEY` were missing, which is unsafe and non-deterministic for production tokens.
- Production did not fail fast when critical env values were missing.
- CORS defaults included placeholder/example production domains and server-specific defaults outside an explicit production env allowlist.
- `CORS_ALLOW_ALL_ORIGINS` could make broad CORS behavior available without a production guard.
- CRM customer/opportunity/activity/report endpoints exposed sensitive business/customer data without auth decorators.
- Monitoring metrics and analytics endpoints required authentication but did not enforce a management/supervisor role.

## 3. Config and Env Findings

| Finding | File/location | Risk | Fix applied | Production impact | Test impact |
|---|---|---|---|---|---|
| Hardcoded production-like DB fallback | `backend/__init__.py`, `backend/config.py` | Missing `DATABASE_URL` could silently connect to a built-in DB target. | Moved DB selection to `backend.config.get_database_uri`; production requires `DATABASE_URL`; dev fallback is explicitly local SQLite only; test fallback remains `TEST_DATABASE_URL` or in-memory SQLite. | Missing `DATABASE_URL` fails fast before DB connection. | Test apps remain isolated from production/developer DB URLs. |
| Missing env validation | `backend/config.py`, `backend/__init__.py` | Production could start with incomplete config. | Added runtime env helpers and `validate_runtime_config` before DB/session startup. | Production fails fast for missing/unsafe DB, secrets, or CORS. | Added targeted config tests; existing test mode preserved. |
| Runtime-generated secrets | `backend/security.py` | Production tokens/sessions could be invalidated between restarts and missing secrets would be hidden. | Replaced random secret defaults with config-provided test/dev values; production secrets must come from env. | No random production secret generation. | Stable deterministic test secrets remain. |
| Placeholder/open CORS defaults | `backend/cors_config.py`, env examples | Placeholder domains or wildcard CORS could be accepted in production. | Production CORS now uses only explicit env origins, rejects wildcard/allow-all/local/placeholder origins. | Production cannot start with open CORS. | Dev/test localhost preflight behavior remains. |
| Docker production DB password default | `docker-compose.production.yml` | Production compose could default DB password to a weak known value. | Replaced default with required `${DB_PASSWORD:?...}` interpolation. | Compose fails unless DB password is supplied. | No test impact. |
| Incomplete env samples | `.env.example`, `backend/env.docker.example`, `backend/env.production.example` | Samples encouraged broad CORS or placeholder production secrets. | Updated samples to separate development defaults from required production blanks. | Production examples fail fast until real deployment secrets/origins are supplied. | No test impact. |
| Unprotected CRM data endpoints | `backend/routes/crm.py` | Customer/opportunity/activity/KPI data could be read or modified without auth. | Added `@require_role("business_expert")` to all non-ping CRM endpoints. | CRM now requires business-expert-level access or higher. | Added 401/403 tests; existing permissive API test still accepts 401. |
| Monitoring role gap | `backend/routes/monitoring.py` | Any authenticated expert could read operational/business/customer analytics. | Replaced general auth with `@require_role("supervisor")` for metrics, analytics, dashboard, alerts, and alert acknowledgement; logs remain admin-only. | Monitoring data now requires supervisor-level access or higher. | Added targeted 403 test for expert role. |

## 4. Secrets Hardening

- `SECRET_KEY` is selected centrally through `backend.config.get_secret_config`.
- `JWT_SECRET_KEY` is selected centrally through `backend.config.get_secret_config`.
- In testing, deterministic test-only values are used unless explicitly overridden by the test app/config environment. This preserves stable token generation and repeatable backend tests.
- In development, missing secrets use clearly named development-only fallback values and print a generic warning. No real secret value is printed.
- In production, both `SECRET_KEY` and `JWT_SECRET_KEY` must be set through environment variables and must not be empty, test-only, development-only, or documented placeholder values.
- `backend.security.SecurityManager` no longer generates runtime-random secrets as a fallback.

## 5. Database URL Hardening

- Development behavior: if `DATABASE_URL` is provided, it is used; otherwise the backend uses an explicit development-only local SQLite fallback and prints a generic warning.
- Testing behavior: test apps use `TEST_DATABASE_URL` or `sqlite:///:memory:` and do not fall back to developer or production `DATABASE_URL` values.
- Production behavior: missing `DATABASE_URL` raises a `RuntimeError` before DB connection or startup migrations.
- The previous hardcoded production-like PostgreSQL fallback was removed from the app factory.

## 6. CORS Hardening

- Development CORS behavior: localhost and `127.0.0.1` Vite/common dev ports remain allowed; explicit env origins can be added for local development; allow-all remains development/test-only.
- Test CORS behavior: localhost/127.0.0.1 origins remain allowed so the Phase 1D valid preflight test continues to pass.
- Production CORS behavior: only `CORS_ORIGINS`/`CORS_ORIGIN` env values are used; production rejects missing origins, wildcard `*`, `CORS_ALLOW_ALL_ORIGINS=1`, localhost/127.0.0.1 origins, and placeholder domains.
- Placeholder domains such as `yourdomain.com` were removed from runtime CORS config and production env samples.
- Allow-all CORS is forbidden in production.

## 7. Auth Coverage Audit

| Route/module | Endpoint | Data sensitivity | Previous protection | New protection if changed | Required role | Notes |
|---|---|---|---|---|---|---|
| `backend/routes/crm.py` | `GET /api/crm/customers` | Customer PII/business data | Public | `@require_role("business_expert")` | business_expert+ | Protected in Phase 2. |
| `backend/routes/crm.py` | `POST /api/crm/customers` | Customer creation/PII | Public | `@require_role("business_expert")` | business_expert+ | Protected in Phase 2. |
| `backend/routes/crm.py` | `GET/PUT /api/crm/customers/<id>` | Customer detail/PII/opportunities/activities | Public | `@require_role("business_expert")` | business_expert+ | Protected in Phase 2. |
| `backend/routes/crm.py` | `GET/POST /api/crm/opportunities` | Sales/opportunity data | Public | `@require_role("business_expert")` | business_expert+ | Protected in Phase 2. |
| `backend/routes/crm.py` | `GET/POST /api/crm/activities` | CRM activity/task data | Public | `@require_role("business_expert")` | business_expert+ | Protected in Phase 2. |
| `backend/routes/crm.py` | `GET /api/crm/dashboard/kpis` | CRM management KPIs | Public | `@require_role("business_expert")` | business_expert+ | Protected in Phase 2. |
| `backend/routes/crm.py` | `GET /api/crm/ping` | Health ping only | Public | Unchanged | Public | No customer/business data. |
| `backend/routes/admin_panel.py` | `/api/admin/*` shipment/admin/referral endpoints | Admin reports, request details, referral rules | `@require_role('admin')` | Unchanged | admin | Already protected. |
| `backend/routes/user_management.py` | `/api/user-management/*` except ping | Users, roles, assignment rules, manual assignment | `@require_role("admin")` | Unchanged | admin | Already protected. |
| `backend/routes/user_management.py` | `GET /api/user-management/ping` | Health ping only | Public | Unchanged | Public | No sensitive data. |
| `backend/routes/monitoring.py` | `/api/monitoring/metrics`, `/database`, `/business`, analytics, dashboard, alerts, acknowledge | System, DB, business, customer, sales, and operational metrics | `@require_auth` | `@require_role("supervisor")` | supervisor+ | Role tightened in Phase 2. |
| `backend/routes/monitoring.py` | `GET /api/monitoring/logs` | Logs/security events | `@admin_required` | Unchanged | admin | Already admin-only. |
| `backend/routes/monitoring.py` | `GET /api/monitoring/health`, `/ping` | Health/ping only | Public | Unchanged | Public | No sensitive report data. |
| `backend/routes/site_settings.py` | `GET /api/site-settings` | Public site branding/settings | Public | Unchanged | Public | Public frontend needs these settings. |
| `backend/routes/site_settings.py` | `GET/PUT /api/admin/site-settings`, `POST /api/admin/upload` | Site settings mutation/upload | `@require_role("admin")` | Unchanged | admin | Already protected. |
| `backend/routes/site_settings.py` | `GET /api/uploads/<filename>` | Public uploaded logo/assets | Public | Unchanged | Public | Serves public site assets only. |
| `backend/routes/expert_console.py` | `/api/expert/requests`, request detail/actions, quotes, messages, notifications, dashboard, experts | Operational/customer/request data | `@require_auth` plus per-request access checks where applicable | Unchanged | Authenticated expert user | Existing access checks restrict request visibility for non-managers. |
| `backend/routes/expert_console.py` | `POST /api/expert/auth/login`, refresh | Auth token operations | Public by design | Unchanged | Public | Required for obtaining/refreshing tokens. |
| `backend/routes/expert_console.py` | `GET /api/expert/ping` | Health ping only | Public | Unchanged | Public | No sensitive data. |
| `backend/routes/public_tracking.py` | `GET /api/public/track/<identifier>` | Customer-facing tracking info by identifier | Public by design | Unchanged | Public | Public tracking is a product feature; changing it would alter business behavior. |
| `backend/routes/shipment_request.py` | `POST /api/shipments/request` and public lookup helpers | Public request intake | Public by design | Unchanged | Public | Public lead/intake feature; no Phase 2 change. |
| `backend/routes/customer_gamification.py` | register, verify, profile/workflow, complete-step, leaderboard | Customer self-service/gamification | Public by design in current product flow | Unchanged | Public | Customer auth is not present in current architecture; changing this would be a feature/auth redesign and is deferred. |

## 8. Changes Made

| File | Change summary | Reason | Behavior impact | Security impact | Notes |
|---|---|---|---|---|---|
| `backend/config.py` | Added runtime env helpers, DB/secret selection, production validation, and CORS validation helpers. | Centralize security-sensitive config decisions. | Production can fail fast; dev/test behavior explicit. | Removes unsafe production fallbacks. | No secrets printed. |
| `backend/__init__.py` | App factory now consumes hardened config helpers and validates production config before DB startup. | Prevent startup with incomplete production env. | No business API contract change except protected endpoints elsewhere. | Production no longer silently uses unsafe defaults. | Test mode remains isolated. |
| `backend/security.py` | Removed runtime-random fallback secrets from `SecurityManager`. | Avoid non-deterministic production token/session behavior. | Dev/test still get deterministic fallbacks. | Production secrets must be explicit. | CSRF token generation remains random per token. |
| `backend/cors_config.py` | Split dev/test/prod CORS behavior and removed placeholder/domain defaults. | Prevent broad/placeholder production CORS. | Dev/test localhost preflight preserved. | Production CORS comes from env only. | `CORS_ALLOW_ALL_ORIGINS` is dev/test-only. |
| `backend/routes/crm.py` | Added `@require_role("business_expert")` to sensitive CRM endpoints. | Protect customer/opportunity/activity/KPI data. | Unauthenticated/underprivileged calls now return 401/403. | Closes public CRM data exposure. | Ping remains public. |
| `backend/routes/monitoring.py` | Tightened monitoring metrics/analytics/dashboard/alerts from auth-only to supervisor role. | Restrict managerial/operational reports. | Expert role now receives 403. | Reduces report exposure. | Logs remain admin-only. |
| `backend/tests/test_security_config.py` | Added targeted config, CORS, CRM auth, and monitoring role tests. | Verify hardening without real DB connections. | Test-only. | Prevents regression of Phase 2 controls. | No test skips/xfails. |
| `.env.example` | Updated dev/test/prod guidance and safer CORS/secrets examples. | Avoid encouraging open CORS/default production secrets. | Documentation/sample only. | Safer operator defaults. | No real credentials. |
| `backend/env.docker.example` | Updated Docker dev CORS and secret examples. | Make development-only values explicit. | Sample only. | Avoids wildcard CORS sample. | No production secrets. |
| `backend/env.production.example` | Removed placeholder production values; required values are blank. | Ensure copied production sample fails until configured. | Sample only. | Prevents placeholder production startup. | No real credentials. |
| `docker-compose.production.yml` | Removed default Postgres password fallback. | Avoid weak default production DB password. | Production compose requires `DB_PASSWORD`. | Safer production startup. | No migration/schema change. |
| `docs/phase-2-security-config-hardening.md` | Added this Phase 2 record. | Document findings, fixes, audit, and verification. | Documentation only. | Audit trail for security decisions. | No secrets included. |

## 9. After

| Check | Result | Notes |
|---|---:|---|
| `pytest -q` | PASS | 51 passed, 53 warnings. |
| `pytest backend/tests/test_security_config.py -q` | PASS | 7 passed, 9 warnings. |
| `pytest backend/tests/test_api.py::TestAPIEndpoints::test_cors_headers -q` | PASS | Confirms Phase 1D valid preflight remains covered. |
| `npm run lint` | PASS_WITH_WARNINGS | 0 errors, existing frontend warnings remain. |
| `npm run build` | PASS_WITH_WARNINGS | Build passed; existing Browserslist/chunk warnings remain. |
| `npm run check:structure` | PASS_WITH_WARNINGS | Structure check passed; existing root migration warnings remain. |

## 10. Deferred Items

The following remain intentionally deferred to Phase 3 or later:

- Migration cleanup and removal/consolidation of deprecated root migrations.
- Backend domain/module refactor.
- Backend service layer extraction.
- Customer-specific authentication redesign for public customer gamification endpoints.
- Frontend feature-based refactor.
- Existing frontend lint warnings.
- CI/CD pipeline setup.
- Full production deployment hardening beyond config/security basics.
- Deprecation warning cleanup for `datetime.utcnow()`.
- Bundle/code-splitting work for large frontend chunks.
