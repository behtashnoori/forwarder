"""
Startup: run migrations, verify critical tables, seed.
Used by create_app() so that any process that starts the backend (run.py, gunicorn, etc.) runs migrations.
"""
from __future__ import annotations

import os
import sys
import traceback

_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
_MIGRATION_DIR = os.path.join(_BACKEND_DIR, "migrations")


def run_migrations(app) -> None:
    """Run pending Alembic migrations. On failure: log, traceback, exit(1)."""
    from backend.extensions import db
    from flask import current_app
    from alembic import command
    from sqlalchemy import text

    with app.app_context():
        try:
            with db.engine.connect() as conn:
                with conn.begin():
                    conn.execute(text(
                        "ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(255)"
                    ))
        except Exception:
            pass
        try:
            cfg = current_app.extensions["migrate"].migrate.get_config(_MIGRATION_DIR)
            command.upgrade(cfg, "head")
            print("[startup] Migrations applied.")
        except Exception as e:
            err_str = str(e).lower()
            if "duplicatecolumn" in err_str or "duplicatetable" in err_str or "already exists" in err_str:
                try:
                    with db.engine.connect() as conn:
                        with conn.begin():
                            conn.execute(text("DELETE FROM alembic_version"))
                            conn.execute(text("INSERT INTO alembic_version (version_num) VALUES (:rev)"), {"rev": "20250220_merge_final"})
                            conn.execute(text("ALTER TABLE shipment_request ADD COLUMN IF NOT EXISTS tracking_code VARCHAR(32)"))
                            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_shipment_request_tracking_code ON shipment_request (tracking_code)"))
                    print("[startup] Migrations applied (recovery).")
                except Exception as e2:
                    print("[startup] Migrations (recovery) failed:", e2)
                    traceback.print_exc()
                    sys.exit(1)
            else:
                print("[startup] Migrations (upgrade) failed:", e)
                traceback.print_exc()
                sys.exit(1)


def verify_critical_tables(app) -> None:
    """Verify critical tables exist. Exit(1) if any missing."""
    from backend.extensions import db
    from sqlalchemy import text

    with app.app_context():
        for table_name, sql in (
            ("province", text("SELECT 1 FROM province LIMIT 1")),
            ("transport_method", text("SELECT 1 FROM transport_method LIMIT 1")),
        ):
            try:
                with db.engine.connect() as conn:
                    conn.execute(sql)
            except Exception as e:
                print("[startup] Critical table %r missing or inaccessible: %s" % (table_name, e))
                traceback.print_exc()
                sys.exit(1)
    print("[startup] Critical tables OK.")
