# Phase 0 Baseline & Stabilization Setup

Date: 2026-05-18  
Scope: Baseline documentation only. No feature work, database model change, migration generation, API behavior change, UI redesign, or broad refactor was performed.

## 1. Project Snapshot

- **Project name:** Forwarder
- **Product purpose:** shipment/forwarding request management system with public request intake, expert operations, CRM, admin, assignment/referral, customer tracking, gamification, site settings, and monitoring domains.
- **Frontend stack:** React 18, TypeScript, Vite, React Router, TanStack Query, Tailwind CSS, Radix UI/shadcn-style components, React Hook Form, Zod.
- **Backend stack:** Flask, Flask-SQLAlchemy, Flask-Migrate/Alembic, SQLAlchemy, Flask-CORS, PyJWT, bcrypt, Gunicorn.
- **Database:** PostgreSQL is the documented primary database; some test/development paths use SQLite-compatible behavior.
- **Deployment tooling:** Docker, Docker Compose, Nginx frontend container, Gunicorn backend container, PostgreSQL 16, Adminer.
- **Main backend entrypoints:** `backend/wsgi.py` for WSGI/Gunicorn and `python -m backend.run` for canonical dev startup.
- **Main frontend entrypoint:** Vite dev server via `npm run dev`.
- **Canonical migrations directory:** `backend/migrations`.
- **Deprecated migration directory still present:** root `migrations` contains version files and `migrations/alembic.ini`; do not add new migrations there.
- **Env files and examples observed:** `.env`, `.env.example`, `backend/env.docker.example`, `backend/env.production.example`.
- **Large/high-risk files observed:**
  - `backend/models.py` - 837 lines; contains many domains in one ORM module.
  - `src/lib/api.ts` - 1029 lines; contains many frontend API domains in one client module.
  - `backend/routes/expert_console.py` - 1041 lines; large route/controller module.

## 2. Official Run Commands

| Purpose | Official / Proposed Command | Status | Notes |
|---|---|---:|---|
| Backend dev | `python -m backend.run` | Official | Uses centralized backend config, port fallback, writes `.backend-port`, then runs migrations/verify/seed before serving. Requires `DATABASE_URL` in environment or `.env` for this entrypoint. |
| Backend WSGI | `gunicorn -w 2 -b 0.0.0.0:5000 wsgi:app` from backend container context | Official for container | Matches `backend/Dockerfile`. |
| Frontend dev | `npm run dev` | Official | Starts Vite dev server. `/api` is proxied by `vite.config.ts`. |
| Docker dev | `docker compose up --build` | NEEDS_CONFIRMATION | Compose file exists. Not executed in Phase 0 to avoid creating/changing volumes or live DB state. |
| Docker production | `docker compose -f docker-compose.production.yml up --build -d` | NEEDS_CONFIRMATION | Production compose exists. Not executed in Phase 0. |
| Frontend lint | `npm run lint` | Official | Executed; currently fails. |
| Frontend build | `npm run build` | Official | Executed; currently passes with warnings. |
| Backend test | `python -m pytest backend/tests -q` | Official/proposed | Executed; currently fails. |
| Structure check | `npm run check:structure` | Official | Executed; passes with migration warnings. |
| App import check | `python -c "import backend; print('backend import OK:', callable(backend.create_app))"` | Safe check | Executed. Imports the package without calling `create_app`, avoiding startup migrations. |
| Migration status | NOT_RUN | N/A | Alembic/Flask migration commands may instantiate the app and connect to DB. Phase 0 used file inspection and `check:structure` only. |

## 3. Current Quality Baseline

| Check | Result | Summary |
|---|---:|---|
| Dependency install | NOT_RUN | `node_modules` and Python dependencies were already present; no install was needed. No package/lockfile changes were made. |
| Frontend lint: `npm run lint` | FAIL | ESLint reported **30 problems: 13 errors and 17 warnings**. Main categories: `no-explicit-any`, empty interface types, constant truthiness expressions, empty block, React hooks dependency warnings, Fast Refresh warnings, and `require()` import in `tailwind.config.ts`. |
| Frontend build: `npm run build` | PASS with warnings | Vite production build succeeded. Warnings: Browserslist/caniuse-lite data is old; main JS chunk is larger than 500 kB after minification. |
| Structure check: `npm run check:structure` | PASS with warnings | Canonical `backend/migrations` exists and `backend/migrations/alembic.ini` exists. Warnings: deprecated root `migrations/versions` contains 7 version files; root `migrations/alembic.ini` exists. |
| Backend tests: `python -m pytest backend/tests -q` | FAIL | **44 tests collected/run: 35 passed, 9 failed, 23 warnings**. Failures include auth/API tests expecting mocked DB behavior while real DB queries occur, SQLite `no such table` errors, and at least one path attempting PostgreSQL connection to `127.0.0.1:5432` with connection refused. |
| Backend import check | PASS | `import backend` succeeded and confirmed `backend.create_app` is callable. `create_app()` was not invoked in this check to avoid startup side effects. |
| Migration status | NOT_RUN | No migration command was executed. Baseline relies on file inspection and structure check only. |
| Docker status | FILE_REVIEW_ONLY | `docker-compose.yml`, `docker-compose.production.yml`, `Dockerfile.frontend`, `Dockerfile`, and `backend/Dockerfile` were inspected. Docker was not executed to avoid creating or mutating volumes/databases. |
| Git worktree before doc | CLEAN | No pre-existing tracked changes were reported before creating this baseline document. |

### Backend Test Failure Classification

- **Likely environment/config related:** PostgreSQL connection refused on `127.0.0.1:5432`; this indicates no local PostgreSQL service available for paths using the default/non-test DB URL.
- **Likely test isolation/schema related:** SQLite `no such table: expert_user` and `no such table: customer` indicate app/test fixtures are not consistently creating required schema for tests that hit real ORM queries.
- **Likely test/mocking mismatch:** Some tests patch `backend.models.*`, while route/auth modules import concrete model classes and still execute real queries.
- **Not fixed in Phase 0:** Failures are documented only; no test, app, DB, or fixture behavior was changed.

### Migration Baseline

- Canonical migration path is `backend/migrations`.
- Root `migrations` is deprecated but still present.
- `npm run check:structure` found 7 Python migration files under root `migrations/versions` and warned that root `migrations/alembic.ini` exists.
- No new migration was generated.
- No database schema operation was performed.

### Docker Baseline

- `docker-compose.yml` defines `frontend`, `api`, `db`, and `adminer` services.
- `docker-compose.production.yml` defines production-oriented `frontend`, `api`, `db`, `adminer`, network, healthcheck, restart policy, and persistent volume.
- Docker was not run in Phase 0.

## 4. Risk Register

| Risk ID | Area | Finding | Severity | Evidence/File | Recommended Phase | Notes |
|---|---|---|---|---|---|---|
| R-001 | Backend config | Hardcoded fallback `DATABASE_URL` exists in app factory. Credential value is intentionally masked in this report. | Critical | `backend/__init__.py` | Phase 1 | Production/test behavior can silently use unintended DB if env is missing outside `backend.run`. |
| R-002 | Security | `SECRET_KEY` and `JWT_SECRET_KEY` default to runtime-generated values when env is absent. | High | `backend/security.py` | Phase 1 | Tokens/sessions may become invalid after restart; production must require stable secrets. |
| R-003 | CORS | Example/env config includes placeholder domain and allow-all style development setting. | High | `.env.example`, `backend/env.production.example`, `backend/cors_config.py` | Phase 1 | Need explicit production CORS policy; do not rely on placeholder or broad origin behavior. |
| R-004 | Auth/Authorization | CRM endpoints appear to be route-exposed without auth decorators in the route module. | Critical | `backend/routes/crm.py` | Phase 1 | Customer, opportunity, activity, and dashboard data are sensitive. Confirm if upstream middleware exists; otherwise protect. |
| R-005 | Auth/Authorization | Customer gamification profile/workflow endpoints appear public by route decorator inspection. | High | `backend/routes/customer_gamification.py` | Phase 1 | Some public customer flows may be intentional; profile/workflow access should be reviewed for ownership/token requirements. |
| R-006 | Migration management | Migration drift risk: canonical `backend/migrations` exists but deprecated root `migrations` still contains versions and `alembic.ini`. | High | `backend/migrations`, `migrations`, `scripts/check-structure.js` | Phase 1 | Must define cleanup/archival plan before future migrations. No deletion in Phase 0. |
| R-007 | Tests/DB isolation | Backend tests fail due to missing SQLite tables and attempts to connect to local PostgreSQL. | High | `backend/tests`, pytest output | Phase 1 | Need deterministic test DB config and schema fixture. |
| R-008 | Backend maintainability | `backend/models.py` is 837 lines and contains many domains. | Medium | `backend/models.py` | Phase 2 | Refactor later only after test baseline is reliable; no model changes in Phase 0. |
| R-009 | Frontend maintainability | `src/lib/api.ts` is 1029 lines and mixes many API domains. | Medium | `src/lib/api.ts` | Phase 2 | Split by domain after behavior-preserving tests exist. |
| R-010 | Backend maintainability | `backend/routes/expert_console.py` is 1041 lines and mixes route/controller/business logic. | Medium | `backend/routes/expert_console.py` | Phase 2 | Candidate for service-layer extraction later. |
| R-011 | Frontend routing | `/user-management` route renders `AdminPanel` while `UserManagement` is imported. | Medium | `src/App.tsx` | Phase 1 | Likely wiring mistake; confirm intended product behavior before changing. |
| R-012 | Frontend quality | ESLint currently fails with 13 errors. | Medium | `npm run lint` output | Phase 1 | Blocks CI quality gate. Do not fix in Phase 0. |
| R-013 | Frontend performance | Production build passes but main JS chunk is >500 kB. | Low | `npm run build` output | Phase 2 | Code splitting can wait until behavior is stabilized. |
| R-014 | Secrets/docs hygiene | Several docs/scripts mention sample passwords or placeholder secrets. | Medium | docs and seed/test scripts | Phase 1 | Review for real credentials before public distribution; keep samples clearly marked. |
| R-015 | Startup side effects | `create_app()` can connect to DB and run migrations/seed unless testing or `skip_startup=True`. | High | `backend/__init__.py`, `backend/run.py` | Phase 1 | Tooling and migration commands need safe/non-destructive invocation patterns. |

## 5. No-Change Freeze Rules

Until the stabilization phase is explicitly complete, the following are frozen:

1. No new product features.
2. No new migrations.
3. No database model changes.
4. No destructive database actions, including dropping tables, dropping databases, or deleting volumes.
5. No broad refactors or architecture rewrites.
6. No route/API behavior changes.
7. No unnecessary UI redesign or visual change.
8. No security behavior changes without tests and documentation.
9. No package/lockfile changes unless required to run baseline checks and explicitly documented.
10. No cleanup of deprecated migrations until a migration-governance plan is approved.

## 6. Phase 1 Entry Checklist

| Item | Status | Notes |
|---|---:|---|
| Baseline document created | DONE | `docs/phase-0-baseline.md` created. |
| Current failing checks documented | DONE | Lint and backend test failures recorded. |
| Official commands documented | DONE | Backend, frontend, Docker, test, build, lint, structure commands listed. |
| Risks prioritized | DONE | Risk register contains severity and recommended phase. |
| No product behavior changed | DONE | Documentation-only change. |
| No database destructive action done | DONE | No DB drop, no volume deletion, no migration generation. |
| No migration created | DONE | No migration command executed. |
| Docker not mutating state | DONE | Compose/Dockerfiles inspected only; Docker not executed. |
| Phase 1 readiness decision | CONDITIONAL | Project can enter Phase 1 planning/execution only after stakeholders accept this baseline and the no-change freeze remains in force. Phase 1 blockers are failing lint/tests and unresolved config/security risks. |

## Appendix A: Commands Executed

```bash
git status --short
test -d node_modules && echo node_modules:present || echo node_modules:missing
python -c "import flask, sqlalchemy, pytest; print('python deps:present')"
npm run lint
npm run build
npm run check:structure
python -m pytest backend/tests -q
python -c "import backend; print('backend import OK:', callable(backend.create_app))"
find . -maxdepth 3 \( -name '.env*' -o -name 'env.*.example' -o -name '*env*example*' \) -type f -print | sort
wc -l backend/models.py src/lib/api.ts backend/routes/expert_console.py src/pages/AdminPanel.tsx
```

## Appendix B: Commands Intentionally Not Run

| Command / Action | Reason |
|---|---|
| `npm install` / `npm ci` | Existing `node_modules` was present; no install required. Avoided package/lockfile churn. |
| `pip install -r backend/requirements.txt` | Required Python dependencies were already importable. Avoided unnecessary environment changes. |
| Docker Compose up/build | Avoided creating/mutating Docker volumes or live database state in Phase 0. |
| `flask db current`, `flask db upgrade`, Alembic status commands | Avoided app startup side effects and DB connection/migration behavior. Migration state was inspected via files and `npm run check:structure`. |
| Any migration generation | Explicitly forbidden in Phase 0. |
| Any database drop/reset | Explicitly forbidden in Phase 0. |
