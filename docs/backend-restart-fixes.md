# Backend restart fixes — cascading 500 errors (permanent solution)

## What was failing

After backend restarts we saw:

- Health check failing or not reflecting real readiness
- `/api/transport-methods` returning **500**
- `/api/provinces` returning **500**
- Frontend reporting “backend health failure”
- Sometimes no access from outside the server

So the problem was not only network/port: the backend was either not starting cleanly or was returning 500 on first requests because of **internal** issues (DB, migrations, missing tables, unhandled exceptions).

## Why it happened

1. **No strict startup validation** — Missing or wrong `DATABASE_URL` could still start the app with a hardcoded fallback; no explicit “environment OK” step.
2. **Health endpoint did not check DB** — `/api/health` always returned “ok” even when the database was down or tables were missing, so probes and frontend could not see real readiness.
3. **No global error handler** — Unhandled exceptions in routes (e.g. missing table, broken DB) produced generic 500 responses (sometimes HTML) with **no full stack trace in logs**, so debugging was hard.
4. **Routes not defensive** — `/api/provinces` had no try/except; any DB error caused an unhandled 500. `/api/transport-methods` caught errors but only logged `str(e)`, not the full traceback.
5. **Empty critical tables** — After a fresh DB or restart, `transport_method` and `province` could be empty; no automatic minimal seed, so the app depended on manual seed scripts.
6. **Table existence not verified at startup** — If migrations failed or tables were missing, the app still started and failed only on first request with a 500.

## What was fixed

1. **Strict startup validation (before `app.run`)**
   - **Env:** `DATABASE_URL` is required when starting via `python -m backend.run`; if missing, the process logs clearly and exits with code 1.
   - **DB:** Existing “SELECT 1” check in `create_app()` kept; log message aligned to `[startup] Database connection OK`.
   - **Critical tables:** After migrations, the startup checks that `province` and `transport_method` exist (e.g. `SELECT 1 FROM ... LIMIT 1`). If any check fails, the process logs and exits(1).
   - **Logs:** `[startup] Environment OK`, `[startup] Database connection OK`, `[startup] Routes registered`, `[startup] Critical tables OK.`

2. **Meaningful `/api/health`**
   - Health endpoint now runs a DB check (e.g. `SELECT 1`).
   - **When OK:** Returns JSON with `status: "ok"`, `database: "connected"`, and `port`.
   - **When DB down:** Returns HTTP 500 with JSON (`status: "error"`, `database: "disconnected"`, `message`) and logs full traceback.
   - `/api/health/ping` left as a lightweight “ok” without DB check for load balancers.

3. **Global error handler**
   - Registered app-level handlers so that **every** unhandled exception and 500:
     - Logs **full stack trace**, **route path**, **request method**, and **request body** (safe, truncated).
     - Returns **JSON** only (e.g. `{"error": "Internal server error", "message": "..."}`) with status 500.
   - No more silent 500s; every 500 has a traceback in logs and a consistent JSON response.

4. **Fixed `transport-methods` and `provinces` routes**
   - **`/api/transport-methods`:** On exception, log with `logger.exception(...)` (full traceback) and return JSON 500 with a clear message.
   - **`/api/provinces`:** Wrapped in try/except; on success return list (empty list if no rows); on exception log full traceback and return JSON 500. Same idea for the direct `/provinces` route (full traceback on error).

5. **Safe boot / minimal seed**
   - New `backend/startup_seed.py` runs **after** migrations and table checks.
   - If `transport_method` table is **empty**, it inserts a minimal set of transport methods (no delete).
   - If `province` table is **empty**, it inserts a minimal set of Iranian provinces.
   - On seed failure: log and exit(1), so startup fails fast instead of first request failing with 500.
   - Ensures `/api/transport-methods` and `/api/provinces` can serve after a fresh DB or restart without manual seed.

6. **External access and docs**
   - Backend already bound to `0.0.0.0`; startup logs show “Listening on” and health URL.
   - **docs/backend.md** added: describes binding, external check with `curl http://<SERVER_IP>:<PORT>/api/health`, and what to do if health returns 500 (check DB and startup logs).

Errors are not masked: the real exception is always in the logs, and fixes address root causes (env, DB, migrations, missing tables, missing seed) rather than hiding them.
