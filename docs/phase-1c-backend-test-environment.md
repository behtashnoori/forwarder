# Phase 1C Backend Test Environment Stabilization

Date: 2026-05-18

## 1. Scope

Phase 1C was limited to stabilizing the backend test environment. The changes focus on deterministic test database configuration, test schema creation, test app/request context setup, and test-only seed data needed by existing tests.

No business logic, API response contract, database model, migration, frontend file, UI, Docker config, or production security hardening was changed. The one production-code file touched (`backend/__init__.py`) was changed only to make `create_app(TESTING=True)` use an isolated test database and create schema in test mode; production startup behavior remains unchanged.

## 2. Before

Command run before changes:

```bash
python -m pytest backend/tests -q
```

Result before changes:

- **Total tests:** 44
- **Passed:** 35
- **Failed:** 9
- **Warnings:** 23

Main failure categories before changes:

| Category | Tests / symptoms |
|---|---|
| Real/default PostgreSQL connection attempt | `backend/tests/test_referral_engine.py::test_referral_engine_and_api` attempted to connect to PostgreSQL at `127.0.0.1:5432` and failed with connection refused. |
| Missing SQLite schema / `no such table` | `test_expert_login_success` hit `no such table: expert_user`; `test_crm_customers_endpoint` hit `no such table: customer`. |
| App/request context fixture problem | `TestAuthManager` tests failed outside Flask request/app context. |
| Bare Flask fixture missing app middleware | `test_security_headers` used a raw `Flask(__name__)` app and did not include security headers middleware. |
| CORS contract mismatch | `test_cors_headers` expected `Access-Control-Allow-Methods` on automatic OPTIONS response, but the response did not include it. |

## 3. Test Environment Problems Found

| Problem | File/location | Effect on tests | Fix applied | Production behavior impact |
|---|---|---|---|---|
| `create_app(TESTING=True)` could still use developer/production `DATABASE_URL` when no test URI was passed. | `backend/__init__.py` | Tests could connect to PostgreSQL on `127.0.0.1:5432`. | Test-mode default database URI now uses `TEST_DATABASE_URL` or `sqlite:///:memory:`. | None for production; only applies when `config["TESTING"]` is truthy. |
| Test apps did not consistently have schema. | `backend/__init__.py`, `backend/tests/test_api.py` | SQLite tests failed with `no such table`. | `create_app(TESTING=True)` now runs `db.create_all()`; API test setup also seeds its required expert. | None for production; schema auto-create is test-only. |
| No shared test env guard existed. | `backend/tests/conftest.py` | Tests could inherit unsafe env or miss `TEST_DATABASE_URL`. | Added shared pytest config setting `TEST_DATABASE_URL`, `SECRET_KEY`, and `JWT_SECRET_KEY` defaults for tests. | Test-only file. |
| API login test expected an expert user but did not create one in the actual DB path used by the route. | `backend/tests/test_api.py` | Login route queried an empty SQLite DB and returned 401. | Added a test-only expert seed with bcrypt hash in `setup_method`. | Test-only. |
| Auth manager tests used Flask LocalProxy objects without contexts. | `backend/tests/test_auth.py` | Runtime errors outside request/app context. | Switched auth test setup to app factory, pushed app and request contexts, and popped them in teardown. | Test-only. |
| Auth test mock user did not provide a realistic password hash. | `backend/tests/test_auth.py` | After context stabilization, authentication would not represent production password verification. | Added bcrypt hash to the mock user data. | Test-only. |
| Lockout test used string timestamps instead of `datetime` objects. | `backend/tests/test_auth.py` | After context stabilization, datetime arithmetic would be invalid. | Changed test fixture data to `datetime` values. | Test-only. |
| Security header test used a raw Flask app without security middleware. | `backend/tests/test_auth.py` | Expected headers were absent on 404 response. | Switched the fixture to `create_app(TESTING=True, sqlite)` so middleware/routes/extensions are present. | Test-only. |

## 4. Changes Made

| File | Change summary | Reason | Test-only or production-safe | Notes |
|---|---|---|---|---|
| `backend/__init__.py` | In test mode, default DB URI now resolves to `TEST_DATABASE_URL` or `sqlite:///:memory:` instead of dev/prod `DATABASE_URL`. | Prevent accidental external DB connections in tests. | Production-safe; gated by `TESTING=True`. | Production default path is unchanged. |
| `backend/__init__.py` | In test mode, `db.create_all()` runs after connectivity check and before route tests use the DB. | Standardize test schema availability. | Production-safe; gated by `TESTING=True`. | Migrations/seed/verify still only run outside testing. |
| `backend/tests/conftest.py` | Added shared pytest defaults for test DB URI and test secrets. | Ensure tests have deterministic isolated env defaults. | Test-only. | Does not print or store real secrets. |
| `backend/tests/test_api.py` | Added test-only expert seed in `setup_method`. | Make existing login test use real test DB path rather than unsafe external DB or missing schema. | Test-only. | Assertions unchanged. |
| `backend/tests/test_auth.py` | Replaced bare setup app with `create_app(TESTING=True, sqlite)`, app context, and request context. | Stabilize AuthManager tests around Flask context dependencies. | Test-only. | Assertions unchanged. |
| `backend/tests/test_auth.py` | Added realistic bcrypt hash for mocked user and datetime objects for lockout fixture data. | Keep test fixture data compatible with production auth code. | Test-only. | Assertions unchanged. |
| `backend/tests/test_auth.py` | Switched security header fixture to app factory. | Include security middleware expected by the test. | Test-only. | Assertions unchanged. |

## 5. After

Full backend command after changes:

```bash
python -m pytest backend/tests -q
```

Result after changes:

- **Total tests:** 44
- **Passed:** 43
- **Failed:** 1
- **Warnings:** 45

Remaining failure categories after changes:

| Category | Tests / symptoms |
|---|---|
| CORS contract mismatch | `backend/tests/test_api.py::TestAPIEndpoints::test_cors_headers` still expects `Access-Control-Allow-Methods` on `OPTIONS /api/health/ping`; response contains CORS origin/credentials and security headers but not methods. |

Focused checks after changes:

| Command | Result | Notes |
|---|---:|---|
| `python -m pytest backend/tests/test_auth.py -q` | PASS | 10 passed, 4 warnings. |
| `python -m pytest backend/tests/test_referral_engine.py -q` | PASS | 1 passed, 4 warnings. No PostgreSQL connection attempt remained. |
| `python -m pytest backend/tests/test_api.py::TestAPIEndpoints::test_cors_headers -vv` | FAIL | Confirms remaining failure is CORS header contract, not DB/schema/env. |

## 6. Remaining Failures for Phase 1D

| Test file | Test name | Failure summary | Likely root cause | Suggested Phase 1D action |
|---|---|---|---|---|
| `backend/tests/test_api.py` | `TestAPIEndpoints::test_cors_headers` | `Access-Control-Allow-Origin` exists, but `Access-Control-Allow-Methods` is absent from the automatic OPTIONS response for `/api/health/ping`. | CORS contract / implementation-vs-test expectation mismatch. | Decide official CORS preflight contract. Then either adjust implementation to always add method/header metadata for accepted preflights or update the test to send an explicit preflight Origin/request-method matching the intended contract. |

## 7. Deferred Items

The following were intentionally not fixed in Phase 1C:

- CORS behavior/contract decision and implementation.
- Business logic bugs.
- Non-environment mock mismatch issues, if any reappear after CORS is addressed.
- Full production security hardening.
- Migration cleanup.
- Backend architecture refactor.
- Frontend architecture refactor.
- Frontend lint warnings.
- Deprecation warnings for `datetime.utcnow()`.
