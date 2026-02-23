# Expert Quote Table Migration

This document explains the `expert_quote` table migration: why the "relation expert_quote does not exist" error occurred, how to apply the migration safely, and how to verify the fix.

## Why the error happened

- The **model** `ExpertQuote` exists in code ([backend/models.py](backend/models.py)) with `__tablename__ = "expert_quote"`.
- The **database table** was never created (or was dropped) in your environment. Common causes:
  - The database was at an older migration head when the `expert_quote` migrations were added, and `flask db upgrade` was never run to head.
  - A previous migration revision (`20250223_quote_fix`) had an upgrade that dropped the table; that upgrade has been changed to a no-op so applying migrations no longer drops the table.

The runtime error you see is:

```text
psycopg2.errors.UndefinedTable: relation "expert_quote" does not exist
```

on `INSERT INTO expert_quote (...)`.

## How to apply the migration safely

The fix is **incremental only**: migrations only **create** the missing `expert_quote` table (and index). They do **not** reset the DB, drop other tables, or delete existing data.

### Option A: Apply migrations on backend startup (recommended)

Migrations run automatically when you start the backend:

```bash
# From the project root (forwarder/)
python -m backend.run
```

This runs `run_migrations(app)` and upgrades the database to `head`, which includes the idempotent "ensure expert_quote table" migration. If the table is missing, it will be created.

### Option B: Apply migrations manually with Flask-Migrate

From the project root, with the same environment you use to run the app (virtualenv, `DATABASE_URL` set):

**Windows (PowerShell):**

```powershell
$env:FLASK_APP = "backend.wsgi"
flask db upgrade
```

**Linux/macOS:**

```bash
export FLASK_APP=backend.wsgi
flask db upgrade
```

This upgrades the database to the latest revision (`head`). The revision `20250223_ensure_quote` uses `CREATE TABLE IF NOT EXISTS`, so it is safe to run even if the table already exists.

### Downgrade (manual only)

Downgrade is **never** run automatically. If you need to remove the `expert_quote` table (e.g. for a rollback), run:

```bash
flask db downgrade -1
```

(Only do this if you understand that it drops the `expert_quote` table and any data in it.)

## How to verify

### 1. Check that the table exists

**PostgreSQL (psql):**

```text
\d expert_quote
```

You should see the table with columns: `id`, `shipment_request_id`, `amount`, `currency`, `note`, `valid_until`, `created_by_expert_id`, `created_at`, plus the index `idx_expert_quote_request_id`.

**SQLite:** Use your DB tool or:

```sql
SELECT name FROM sqlite_master WHERE type='table' AND name='expert_quote';
```

### 2. Confirm the quote API works

- **Create a quote:**  
  `POST /api/expert/requests/<request_id>/quote` with a valid expert auth token and body e.g. `{ "amount": 1000, "currency": "IRR" }`.  
  Expect **200** and a JSON response with `"ok": true` and the created quote.

- **Persist:**  
  Either GET the request detail and check `latest_quote`, or query the DB: `SELECT * FROM expert_quote ORDER BY created_at DESC LIMIT 1;`

Once the table exists and the API returns 200 on create, the migration fix is verified.

## Summary

| Item | Description |
|------|-------------|
| **Cause** | Table `expert_quote` was never created (or had been dropped by an old migration). |
| **Fix** | Incremental migrations: no-op for the previous "fix" upgrade, new idempotent migration that runs `CREATE TABLE IF NOT EXISTS expert_quote` (and index). |
| **Apply** | Start the backend (`python -m backend.run`) or run `flask db upgrade` from project root. |
| **Verify** | `\d expert_quote` in psql and a successful `POST .../quote` with persisted row. |

No DB reset, no drop of other tables, no data loss—only the missing `expert_quote` table is created.
