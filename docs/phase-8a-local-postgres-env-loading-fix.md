# Phase 8A: Local PostgreSQL Environment Loading Fix

## 1. Problem

Local backend startup accidentally used the development SQLite fallback because `DATABASE_URL` was not detected. Alembic then ran with `SQLiteImpl` and failed on a migration that is intended for the PostgreSQL local database.

The issue was local environment discovery, not the migration itself and not frontend/UI behavior.

## 2. Root Cause

The backend loaded env files from the project root only:

- `.env`
- `.env.backend`

It did not support `backend/.env`, even though developers may naturally place backend-local env files there. The loader also used `override=True` through `python-dotenv`, so values from an env file could overwrite an explicit process environment value.

When no root `.env` existed, startup printed:

```text
[startup] No .env file - using process env only
```

Then `DATABASE_URL` was missing and non-production app startup fell back to `sqlite:///forwarder_dev.db`.

## 3. Fix Applied

Changed `backend/config.py` to:

- load env files independently of the current working directory
- support project-root `.env`
- support `backend/.env`
- keep legacy project-root `.env.backend` support
- preserve process env precedence with `override=False`
- expose safe database diagnostics without printing credentials
- print a clearer local PostgreSQL guidance message before development SQLite fallback

Changed `backend/run.py` to:

- mention both project-root `.env` and `backend/.env` when `DATABASE_URL` is missing
- print a safe `DATABASE_URL` summary when it is present

Changed `scripts/run-backend.js` to:

- preserve process env precedence when it preloads root `.env` before launching `python -m backend.run`

Updated `.env.example` to show a safe PostgreSQL local example with placeholders.

Added focused config tests for:

- process env `DATABASE_URL` precedence
- `backend/.env` support
- password-safe database diagnostics

## 4. Expected Local .env Location

Preferred location:

```text
<project-root>/.env
```

Supported fallback location:

```text
<project-root>/backend/.env
```

Legacy supported location:

```text
<project-root>/.env.backend
```

If multiple files exist, they are loaded in this order and never override values that already exist in process env:

1. project-root `.env`
2. `backend/.env`
3. project-root `.env.backend`

## 5. Safe Local PostgreSQL Example

Use placeholders only in committed docs:

```env
DATABASE_URL=postgresql+psycopg2://forwarder_dev:change_me@localhost:5432/forwarder_dev
SECRET_KEY=dev-secret-change-me
JWT_SECRET_KEY=dev-jwt-secret-change-me
FLASK_ENV=development
```

Do not commit a real `.env` file or real credentials.

## 6. How to Verify Locally

From PowerShell at the project root:

```powershell
cd D:\1-webapp\15-forwarder
echo $env:DATABASE_URL
```

To set it for the current PowerShell session:

```powershell
$env:DATABASE_URL="postgresql+psycopg2://forwarder_dev:change_me@localhost:5432/forwarder_dev"
$env:SECRET_KEY="dev-secret-change-me"
$env:JWT_SECRET_KEY="dev-jwt-secret-change-me"
$env:FLASK_ENV="development"
npm.cmd run backend
```

Or run the Python backend entrypoint directly:

```powershell
python -m backend.run
```

Expected startup signs:

- startup should not say `DATABASE_URL is not set`
- startup should not use `SQLiteImpl`
- database diagnostics should show `dialect=postgresql`, `driver=psycopg2`, host, and database name
- logs must not print the full URL or password

## 7. Why SQLite Migration Compatibility Was Not Changed

SQLite was accidental in this failure path. The local development database is PostgreSQL, and the failing migration uses PostgreSQL-style `ALTER COLUMN` behavior. This phase therefore fixes env loading and startup diagnostics instead of changing migrations to support accidental SQLite execution.

## 8. Verification Results

Baseline before changes:

- `python -m pytest backend/tests/test_security_config.py -q`: `7 passed, 7 warnings`
- `python -m pytest -q`: `86 passed, 724 warnings`
- `npm.cmd run lint`: passed with 13 existing warnings
- `npm.cmd run build`: passed with existing Browserslist/chunk-size warnings
- `npm.cmd run check:structure`: passed
- `git diff --check`: passed

After changes:

- `python -m pytest backend/tests/test_security_config.py -q`: `10 passed, 7 warnings`
- `python -m pytest -q`: `89 passed, 724 warnings`
- `npm.cmd run lint`: passed with 13 existing warnings
- `npm.cmd run build`: passed with existing Browserslist/chunk-size warnings
- `npm.cmd run check:structure`: passed
- `git diff --check`: passed; Git printed existing Windows line-ending notices for changed text files

PostgreSQL was not started inside this Codex environment. The local laptop verification command is:

```powershell
npm.cmd run backend
```

with `DATABASE_URL` set to the local PostgreSQL `forwarder_db` database.
