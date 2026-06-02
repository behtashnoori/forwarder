# Phase 1A Quality Triage

Date: 2026-05-18  
Scope: analysis-only quality triage. No lint fix, test fix, migration, database model change, API behavior change, UI change, feature work, or architecture refactor was performed.

## 1. Scope

Phase 1A is a read-only / documentation-only triage phase. Its purpose is to re-run the Phase 0 quality gates, classify current frontend lint failures and backend test failures, identify likely root causes, and propose a safe execution sequence for Phase 1B/1C/1D.

The technical fixes themselves are intentionally deferred:

- **Phase 1B:** fix frontend lint errors.
- **Phase 1C:** stabilize backend test configuration, app/db fixtures, and test isolation.
- **Phase 1D:** fix remaining backend test failures after the environment/fixture layer is deterministic.
- **Phase 1E:** re-run all gates and update the baseline.

Phase 0 baseline inputs used here:

- Official backend test command: `python -m pytest backend/tests -q`.
- Official frontend checks: `npm run lint`, `npm run build`, `npm run check:structure`.
- Known Phase 0 state: frontend lint failed, frontend build passed with warnings, backend tests failed, structure check passed with migration warnings.
- Known risk register focus: hardcoded/default DB config, runtime-generated secrets, CORS placeholders, sensitive unauthenticated routes, migration drift, test DB isolation, large multi-domain files, and suspicious `/user-management` route wiring.

## 2. Commands Re-run

| Command | Result | Notes | Environment limitation if any |
|---|---:|---|---|
| `git status --short` | PASS | Worktree was clean before Phase 1A documentation was created. | None |
| `sed -n '1,220p' docs/phase-0-baseline.md` | PASS | Baseline document was read before triage. | None |
| `npm run lint` | FAIL | ESLint reported **30 total problems: 13 errors and 17 warnings**. Same failure shape as Phase 0. | None |
| `npm run build` | PASS_WITH_WARNINGS | Vite build completed. Warnings: npm unknown `http-proxy` env config, Browserslist/caniuse-lite data old, main JS chunk >500 kB. | None |
| `npm run check:structure` | PASS_WITH_WARNINGS | Canonical `backend/migrations` exists and root deprecated migrations are flagged. Output order places warnings after pass lines, but warnings remain active. | None |
| `python -m pytest backend/tests -vv` | FAIL | 44 tests collected: **35 passed, 9 failed, 23 warnings**. Verbose output confirmed failing test names and primary categories. | Local PostgreSQL on `127.0.0.1:5432` is unavailable for tests that fall back to real/default DB config. |
| `python -m pytest backend/tests/test_referral_engine.py::test_referral_engine_and_api -vv -s` | FAIL | Isolated referral test shows `create_app()` attempts PostgreSQL connection and raises `SystemExit: 1` during startup DB check. | ENV_BLOCKED / config issue: no local PostgreSQL service for default DB URL; no safe TEST DB override was set. |
| `python -m pytest backend/tests/test_auth.py::TestAuthManager::test_authenticate_user_success backend/tests/test_auth.py::TestAuthManager::test_generate_tokens backend/tests/test_api.py::TestAPIEndpoints::test_expert_login_success backend/tests/test_api.py::TestAPIEndpoints::test_crm_customers_endpoint backend/tests/test_api.py::TestAPIEndpoints::test_cors_headers -vv` | FAIL | Focused run confirmed request/app context problems, mock path mismatch, missing SQLite schema, and CORS header expectation mismatch. | None beyond existing test fixture/config issues. |
| `rg -n "create_app\(|SQLALCHEMY_DATABASE_URI|TESTING|db\.create_all|TEST_DATABASE_URL|app_context|Flask\(__name__\)|app = Flask" backend/tests backend/__init__.py backend/config.py backend/auth.py backend/security.py` | PASS | Test configuration and app factory usage were inspected without code changes. | None |
| `git status --short` | PASS | No generated dependency/lockfile changes were present after checks. Only the new Phase 1A doc was added afterward. | None |

## 3. Frontend Lint Triage

### 3.1 Error Categories

| Category | Count | Files | Risk level | Suggested fix phase | Notes |
|---|---:|---|---|---|---|
| `@typescript-eslint/no-explicit-any` | 7 errors | `src/components/LocationForm.tsx` (2), `src/components/RequestConfirmation.tsx` (1), `src/lib/api.ts` (2), `src/pages/ExpertConsole.tsx` (1), `src/pages/UserManagement.tsx` (1) | Medium | Phase 1B | Usually safe if replaced with existing domain types or `unknown` plus narrowing. Higher risk in API payload/error handling paths if types are guessed instead of derived from actual data shape. Suggested order: API response/error payload types first, then component callback/form data types. |
| `@typescript-eslint/no-empty-object-type` / empty interface | 2 errors | `src/components/ui/command.tsx`, `src/components/ui/textarea.tsx` | Low | Phase 1B | Usually safe for shadcn-style components: convert empty interfaces to type aliases of inherited props or remove redundant interface declaration. Low behavior risk. Suggested early fix. |
| `no-constant-binary-expression` / constant truthiness | 2 errors | `src/pages/CustomerRequestDetail.tsx`, `src/pages/PublicTracking.tsx` | Medium | Phase 1B | Could reveal unreachable/incorrect conditional rendering. Requires reading the JSX expression and preserving intended output. Fix after simple type/interface errors. |
| `no-empty` / empty block | 1 error | `src/pages/RequestDetail.tsx` | Low-to-Medium | Phase 1B | Empty catch/block may be intentional swallow. Safe fix if replaced with a clear comment only when lint permits, or minimal logging only if behavior impact is accepted. Avoid behavior changes in triage. |
| `@typescript-eslint/no-require-imports` / require/import issue | 1 error | `tailwind.config.ts` | Low | Phase 1B | Likely replace `require()` plugin import with ESM import compatible with the current TypeScript/Tailwind config. Usually safe but should run build after change. |
| Other lint errors | 0 errors | N/A | N/A | N/A | No additional error categories in current output. |

### 3.2 Warning Categories

| Category | Count | Files | Risk level | Suggested fix phase | Notes |
|---|---:|---|---|---|---|
| `react-refresh/only-export-components` | 9 warnings | `src/components/ui/badge.tsx`, `src/components/ui/button.tsx`, `src/components/ui/form.tsx`, `src/components/ui/navigation-menu.tsx`, `src/components/ui/sidebar.tsx`, `src/components/ui/sonner.tsx`, `src/components/ui/toggle.tsx`, `src/contexts/SiteSettingsContext.tsx` (2) | Low-to-Medium | Phase 1B or later | These warnings affect development Fast Refresh behavior, not production build. Fix may require moving constants/hooks/helpers out of component modules; avoid broad UI refactor. |
| `react-hooks/exhaustive-deps` | 8 warnings | `src/pages/AdminPanel.tsx`, `src/pages/CustomerDashboard.tsx`, `src/pages/CustomerRequestDetail.tsx`, `src/pages/ExpertConsole.tsx` (2), `src/pages/PublicTracking.tsx`, `src/pages/RequestDetail.tsx`, `src/pages/UserManagement.tsx` | Medium-to-High | Phase 1B after errors | Adding dependencies can change fetch timing or loops. Treat as behavior-sensitive; fix after lint errors and with focused smoke testing. |

### 3.3 Suggested Phase 1B Order

1. Fix low-risk syntax/type lint errors first: empty interfaces and `require()` import.
2. Fix `no-explicit-any` by using local/domain types already present, not broad architecture changes.
3. Fix constant truthiness expressions after confirming intended render behavior.
4. Fix the empty block with a behavior-preserving approach.
5. Re-run `npm run lint` and `npm run build`.
6. Only after errors are clean, triage warnings. Start with Fast Refresh warnings; handle hook dependency warnings last because they can change runtime behavior.

## 4. Backend Test Failure Triage

| Test file | Test name | Failure summary | Root cause category | Production bug or test issue | Suggested fix phase | Notes |
|---|---|---|---|---|---|---|
| `backend/tests/test_api.py` | `TestAPIEndpoints::test_expert_login_success` | Expected 200 but got 401. Logs show real ORM query against SQLite and `no such table: expert_user`. | `missing test database/schema` + `mock path mismatch` | Primarily test issue / fixture issue | Phase 1C | Test patches `backend.models.ExpertUser`, but login/auth path uses imported `backend.auth.ExpertUser`. Test app also does not call `db.create_all()`. After fixture stabilization, verify whether bcrypt password setup is also needed. |
| `backend/tests/test_api.py` | `TestAPIEndpoints::test_crm_customers_endpoint` | Expected 200 or 401 but got 500. Logs show real query against SQLite and `no such table: customer`. | `missing test database/schema` + `mock path mismatch` | Test issue / fixture issue; route auth policy also needs product review | Phase 1C, then Phase 1D if auth behavior is clarified | Test patches `backend.models.Customer`, while CRM route imported `Customer` directly and uses `db.session.query(Customer)`. The absence/presence of auth on CRM endpoints is a separate security/product decision, not a Phase 1A fix. |
| `backend/tests/test_api.py` | `TestAPIEndpoints::test_cors_headers` | OPTIONS `/api/health/ping` has `Access-Control-Allow-Origin` but not `Access-Control-Allow-Methods`. | `auth/security test issue` / CORS contract mismatch | Uncertain: either test expectation mismatch or CORS implementation gap | Phase 1D | Need decide official CORS preflight contract. Current automatic Flask OPTIONS response differs from custom before_request path that only adds method headers when an Origin is present and handled. |
| `backend/tests/test_auth.py` | `TestAuthManager::test_authenticate_user_success` | `RuntimeError: Working outside of request context` while patching/accessing Flask `request` LocalProxy. | `fixture problem` + `auth/security test issue` | Test issue | Phase 1C | Uses bare `Flask(__name__)` and patches `backend.auth.request`, which is a LocalProxy. Needs request context or a safer patch seam. Also mock user lacks realistic bcrypt password hash, which may become the next failure after context is fixed. |
| `backend/tests/test_auth.py` | `TestAuthManager::test_authenticate_user_invalid_credentials` | `RuntimeError: Working outside of request context`. | `fixture problem` + `auth/security test issue` | Test issue | Phase 1C | Same LocalProxy/request-context problem as success case. |
| `backend/tests/test_auth.py` | `TestAuthManager::test_authenticate_user_locked_out` | `RuntimeError: Working outside of request context`. | `fixture problem` + `auth/security test issue` | Test issue, possibly latent test data bug | Phase 1C | The test calls `authenticate_user()` without request context. It also stores `last_attempt` as a string, while production code compares it to `datetime.utcnow()`; after context fix, this may need a test-data correction. |
| `backend/tests/test_auth.py` | `TestAuthManager::test_generate_tokens` | `RuntimeError: Working outside of application context` when reading `current_app.config['JWT_ACCESS_TOKEN_EXPIRES']`. | `fixture problem` + `auth/security test issue` | Test issue | Phase 1C | `AuthManager.generate_tokens()` expects a Flask app context. The test creates a bare Flask app but does not push `app.app_context()` and does not initialize security defaults. |
| `backend/tests/test_auth.py` | `test_security_headers` | Bare Flask test client returns 404 without security headers; expected `X-Frame-Options`, `X-Content-Type-Options`, `X-XSS-Protection`. | `fixture problem` + `auth/security test issue` | Test issue | Phase 1C | Fixture uses raw `Flask(__name__)`, not `create_app()` or `security.init_app(app)`, so security after_request middleware is absent. |
| `backend/tests/test_referral_engine.py` | `test_referral_engine_and_api` | `SystemExit: 1` during `create_app()` startup DB check after PostgreSQL connection refused at `127.0.0.1:5432`. | `environment/config issue` + `real DB connection attempt` + `startup side effects` | Test config issue; app startup side-effect risk | Phase 1C | Test only sets `SQLALCHEMY_DATABASE_URI` if `TEST_DATABASE_URL` exists. Without it, `create_app()` uses env/default DB and exits during startup DB check. No migration or DB action was performed in Phase 1A. |

## 5. Test Environment Findings

### 5.1 DATABASE_URL / Database Selection

- `backend/tests/test_api.py`, `backend/tests/test_cors.py`, `backend/tests/test_health_provinces_transport.py`, and `backend/tests/test_public_tracking_timeline.py` pass `SQLALCHEMY_DATABASE_URI='sqlite:///:memory:'` into `create_app()`.
- `backend/tests/test_referral_engine.py` passes only `TESTING=True` unless `TEST_DATABASE_URL` is set. In the current environment, that means the app falls back to `.env` / default PostgreSQL config and attempts to connect to `127.0.0.1:5432`.
- The local PostgreSQL server expected by the fallback path is not available in this environment, causing `SystemExit: 1` in the referral test.

### 5.2 TESTING=True and Startup Side Effects

- Tests that call `create_app({... 'TESTING': True ...})` do set `TESTING=True` on the Flask app.
- `TESTING=True` prevents migrations/verify/seed from running in `create_app()` because startup migration work is guarded by `if not app.config.get('TESTING') and not skip_startup`.
- However, `create_app()` still performs a DB connectivity check (`SELECT 1`) inside an app context before route registration. This is a startup side effect that can fail tests before fixtures create schema or before a test can control DB state.

### 5.3 Schema Creation / Migration in Tests

- There is no shared `backend/tests/conftest.py` fixture observed.
- Some modules create schema explicitly with `db.create_all()`:
  - `backend/tests/test_health_provinces_transport.py`
  - `backend/tests/test_public_tracking_timeline.py`
  - `backend/tests/test_referral_engine.py`, but only if `TEST_DATABASE_URL` is set.
- `backend/tests/test_api.py` uses SQLite in-memory but does **not** call `db.create_all()`, so endpoints touching tables fail with `no such table` when mocks do not intercept the actual route imports.
- No tests observed run migrations as the normal schema setup path. Schema setup is ad hoc via `db.create_all()` in some modules.

### 5.4 Fixture Consistency and Isolation

- Fixture strategy is inconsistent:
  - Some tests use `create_app()` with SQLite in-memory.
  - Some tests use bare `Flask(__name__)` without app factory middleware, security headers, routes, or extension initialization.
  - Some tests rely on mocks without matching the actual import path used by production modules.
- SQLite in-memory apps can be isolated per module/test, but only if schema is created consistently and app contexts are handled correctly.
- `AuthManager` tests do not push request/app contexts for code that reads `request.remote_addr` and `current_app.config`.
- Referral tests mix integration behavior, direct engine behavior, real DB setup, optional env-based DB URL, and API login flow in one test function; this should be stabilized after the test DB fixture is deterministic.

### 5.5 Security Risks Affecting Test Stability

- **Default database config / `.env` loading:** If tests omit `SQLALCHEMY_DATABASE_URI`, `create_app()` can use real/default PostgreSQL and exit. This directly breaks `test_referral_engine_and_api`.
- **Startup DB check:** Even with `TESTING=True`, `create_app()` performs `SELECT 1`; this makes test construction depend on DB availability.
- **Auth decorator / AuthManager context expectations:** Auth code reads Flask `request` and `current_app`; tests need request/app contexts or narrower unit seams.
- **Runtime-generated JWT secrets:** Not the direct cause of the current 9 failures where tests set or mock secrets, but it can cause instability in integration tests that create multiple apps or expect token validity across app instances.
- **Security headers middleware:** Bare Flask fixtures do not initialize security middleware, so security header tests fail even though app-factory based tests see those headers.

## 6. Recommended Phase 1 Execution Plan

### Phase 1B: Fix Frontend Lint Errors

1. Fix `no-empty-object-type` in shadcn-style UI components.
2. Replace `require()` in `tailwind.config.ts` with an ESM-compatible import.
3. Replace `any` usages with existing local/domain types or `unknown` with narrowing.
4. Fix constant truthiness expressions after confirming intended rendering behavior.
5. Fix the empty block in `RequestDetail` without changing user-visible behavior.
6. Re-run `npm run lint` and `npm run build`.
7. Triage warnings only after errors are clean; hook dependency warnings should be last and tested carefully.

### Phase 1C: Stabilize Backend Test Config and Fixtures

1. Add/standardize a shared test app fixture strategy (likely `backend/tests/conftest.py`) using SQLite in-memory or a clearly named `TEST_DATABASE_URL`.
2. Ensure every app-factory test sets `TESTING=True`, stable `SECRET_KEY`, stable `JWT_SECRET_KEY`, and a deterministic test DB URI.
3. Ensure schema setup is consistent (`db.create_all()` for SQLite unit/integration tests, or one approved migration-based test DB path if explicitly chosen later).
4. Avoid real/default PostgreSQL fallback in tests unless explicitly requested via `TEST_DATABASE_URL`.
5. Push app/request contexts where AuthManager methods require Flask `current_app` or `request`.
6. Align mocks to actual import paths, or prefer real in-memory DB records where integration behavior is intended.
7. Keep this phase behavior-preserving for production code unless a minimal testability guard is approved and documented.

### Phase 1D: Fix Remaining Backend Test Failures

1. Re-run the full backend suite after Phase 1C.
2. Separate remaining failures into true production bugs vs test expectation mismatches.
3. Decide official CORS preflight/header contract and update tests or implementation accordingly.
4. Stabilize auth tests with realistic bcrypt hashes or appropriate AuthManager seams.
5. Split the large referral integration test only if needed for determinism, without changing production referral behavior.

### Phase 1E: Re-run Quality Gates and Update Baseline

1. Run `npm run lint`.
2. Run `npm run build`.
3. Run `npm run check:structure`.
4. Run `python -m pytest backend/tests -q` and, if failures remain, `python -m pytest backend/tests -vv`.
5. Update baseline docs with new pass/fail counts and remaining risks.

## 7. Do Not Fix Yet

The following remain intentionally out of scope for Phase 1A:

- Security hardening.
- Architecture refactor.
- Migration cleanup or deletion of deprecated root migrations.
- Frontend API client split.
- Backend service-layer extraction.
- Backend model decomposition.
- Production readiness hardening.
- UI redesign.
- API behavior changes.
- New tests being skipped, xfailed, or rewritten to hide failures.
- New migrations or database model changes.
