# Backend (Flask API)

## Binding and external access

The backend server binds to **`0.0.0.0:PORT`** (configurable via `HOST` and `PORT` in `.env`). This makes the API reachable from other machines on the network, not only from localhost.

- **Default port:** 8000 (or set `PORT` / `FLASK_RUN_PORT` in `.env`)
- **Local:** `http://localhost:PORT`
- **From network:** `http://<SERVER_IP>:PORT`

## Checking backend health from outside

From another machine (or from the same server), you can verify that the backend is up and the database is connected:

```bash
curl http://<SERVER_IP>:<PORT>/api/health
```

**Expected when OK:**

```json
{"status": "ok", "database": "connected", "port": 8000}
```

**When DB is down or backend not ready:**

- HTTP 500 with body like `{"status": "error", "database": "disconnected", "message": "..."}`

If health returns 500 or you cannot reach the URL at all:

1. **Check that the backend process is running** (e.g. `python -m backend.run`).
2. **Check startup logs** for:
   - `[startup] Environment OK` — `DATABASE_URL` must be set in `.env`.
   - `[startup] Database connection OK` — DB must be reachable.
   - `[startup] Migrations applied.` and `[startup] Critical tables OK.`
3. **Check database:** PostgreSQL is running and `DATABASE_URL` in `.env` is correct.
4. **Firewall:** Ensure port `PORT` is open for inbound connections if you need external access.

## Lightweight ping (no DB check)

For load balancers or simple “process up” checks:

```bash
curl http://<SERVER_IP>:<PORT>/api/health/ping
```

This returns `{"status": "ok", "message": "..."}` without checking the database.
