# Phase 3G Dependency Restore & Backend Regression Gate

Date: 2026-05-18

## 1. Scope

Phase 3G is a release gate after Phase 3 Migration Cleanup. The goal was to restore or verify Python backend dependencies and rerun backend regression checks after the root migration archive cleanup.

No feature work, migration generation, model/schema change, API behavior change, business logic change, frontend edit, backend architecture refactor, service layer extraction, test skip, or test xfail was performed.

## 2. Environment

| Item | Result |
|---|---|
| Python version | `Python 3.14.4` |
| Python executable | `/root/.pyenv/shims/python` |
| pip version | `pip 26.1` from `/root/.pyenv/versions/3.14.4/lib/python3.14/site-packages/pip` |
| Active virtualenv | None (`VIRTUAL_ENV` empty; `CONDA_PREFIX` empty). |
| Dependency source | Official project requirements: `requirements.txt` and `backend/requirements.txt`. |
| Requirements observed | Flask, Flask-SQLAlchemy, Flask-Migrate, Flask-Cors, SQLAlchemy, Alembic, python-dotenv, psutil, PyJWT, Werkzeug, bcrypt, gunicorn, psycopg2-binary. |
| Installed backend dependencies before restore | `pytest` was installed, but `flask`, `sqlalchemy`, `flask_migrate`, `dotenv`, `flask_cors`, `jwt`, `bcrypt`, and `alembic` were missing. |
| Restore attempt | `python -m pip install -r requirements.txt` was attempted using only the official project requirements. |
| Package index limitation | Restore failed because the package index/proxy returned `403 Forbidden` for `/simple/flask/`; no dependency was installed and no requirements file was changed. |

Phase 3 had reported `pytest -q` as not runnable because Flask and Alembic were missing in the execution environment. Phase 3G confirmed the same environment limitation and attempted a restore from the official requirements, but the restore was blocked by package-index access.

## 3. Backend Test Results

| Check | Result | Notes |
|---|---:|---|
| `pytest -q` | ENV_BLOCKED | Collection fails at `backend/__init__.py` import with `ModuleNotFoundError: No module named 'flask'`. |
| `pytest backend/tests/test_security_config.py -q` | ENV_BLOCKED | Same missing Flask dependency during `conftest.py` import. |
| `pytest backend/tests/test_api.py::TestAPIEndpoints::test_cors_headers -q` | ENV_BLOCKED | Same missing Flask dependency during `conftest.py` import. |

No backend test assertion was changed, skipped, or xfailed. The backend regression gate could not be completed in this container because Python dependencies could not be restored.

## 4. Frontend and Structure Gates

| Check | Result | Notes |
|---|---:|---|
| `npm run lint` | PASS_WITH_WARNINGS | 0 errors; existing 17 warnings remain. |
| `npm run build` | PASS_WITH_WARNINGS | Build passed; existing Browserslist/chunk-size warnings remain. |
| `npm run check:structure` | PASS | Canonical migrations directory exists and no root migration warnings are emitted. |
| `git diff --check` | PASS | No whitespace errors. |

## 5. Migration Safety Re-check

| Check | Result | Notes |
|---|---:|---|
| Canonical migration path | PASS | `backend/migrations` remains the only executable migration path. |
| Root migration path | PASS | Root `migrations/` is absent. |
| Migration archive | PASS | `docs/migrations-archive/root-migrations-2026-05-18/` exists and contains the archived root migration files for historical/DBA review only. |
| Structure check | PASS | `npm run check:structure` passes without root migration warnings. |
| Canonical graph read-only check | PASS | Parsed `backend/migrations/versions`: 30 revisions, one base `20240917_initial_schema`, one head `20250223_ensure_quote`, and no missing `down_revision` references. |
| Real database migration status | NOT_RUN | No DB connection, upgrade, or downgrade was attempted. |

Remaining DBA review risk: if an existing production database was ever stamped with archived root-only revision `54ea21ea0d9f`, manual DBA review is required before future migration operations. The archived file remains available for that review.

## 6. Decision

**BLOCKED_BY_ENV**

Reason: Python backend dependencies required to run Flask-based pytest collection are missing, and restoring them from the official project requirements was blocked by package-index/proxy `403 Forbidden` responses. The migration safety re-check and frontend/structure gates passed, but the backend regression gate cannot be declared ready until dependencies are restored in an environment with package access and `pytest -q` plus the targeted backend tests pass.

## 7. Deferred Items

The following remain deferred to Phase 4 or later:

- Backend service layer extraction.
- Backend domain refactor.
- Frontend feature-based refactor.
- Existing lint warnings.
- CI/CD.
- OpenAPI documentation.
- DBA review for archived root-only migration `54ea21ea0d9f` if a production database reports that revision.
