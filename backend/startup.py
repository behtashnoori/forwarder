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


def ensure_expert_quote_table(app) -> None:
    """Create expert_quote table if missing (e.g. when migration chain doesn't run). No-op if table exists."""
    from sqlalchemy import inspect, text
    from backend.extensions import db

    with app.app_context():
        insp = inspect(db.engine)
        if insp.has_table("expert_quote"):
            return
        dialect_name = db.engine.dialect.name
        with db.engine.connect() as conn:
            with conn.begin():
                if dialect_name == "postgresql":
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS expert_quote (
                            id BIGSERIAL PRIMARY KEY,
                            shipment_request_id BIGINT NOT NULL REFERENCES shipment_request(id) ON DELETE CASCADE,
                            amount BIGINT NOT NULL,
                            currency VARCHAR(10) NOT NULL DEFAULT 'IRR',
                            note TEXT,
                            valid_until DATE,
                            created_by_expert_id BIGINT NOT NULL REFERENCES expert_user(id),
                            created_at TIMESTAMP NOT NULL
                        )
                    """))
                    conn.execute(text(
                        "CREATE INDEX IF NOT EXISTS idx_expert_quote_request_id ON expert_quote (shipment_request_id)"
                    ))
                elif dialect_name == "sqlite":
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS expert_quote (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            shipment_request_id INTEGER NOT NULL REFERENCES shipment_request(id) ON DELETE CASCADE,
                            amount INTEGER NOT NULL,
                            currency VARCHAR(10) NOT NULL DEFAULT 'IRR',
                            note TEXT,
                            valid_until DATE,
                            created_by_expert_id INTEGER NOT NULL REFERENCES expert_user(id),
                            created_at TIMESTAMP NOT NULL
                        )
                    """))
                    conn.execute(text(
                        "CREATE INDEX IF NOT EXISTS idx_expert_quote_request_id ON expert_quote (shipment_request_id)"
                    ))
                else:
                    raise RuntimeError("Unsupported dialect for expert_quote: %s" % dialect_name)
        print("[startup] expert_quote table missing -> created successfully.")


def run_migrations(app) -> None:
    """Run pending Alembic migrations. On failure: log, traceback, exit(1)."""
    from backend.extensions import db
    from flask import current_app
    from alembic import command
    from sqlalchemy import text

    with app.app_context():
        # Ensure expert_quote exists before any migration (no-op if table already there)
        ensure_expert_quote_table(app)
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
            if "no such revision" in err_str or "can't locate revision" in err_str or "resolutionerror" in err_str:
                # DB has a revision not in code (e.g. 20250223_site_settings); ensure expert_quote without touching alembic
                ensure_expert_quote_table(app)
                print("[startup] Migrations skipped (revision mismatch); expert_quote table ensured.")
            elif "duplicatecolumn" in err_str or "duplicatetable" in err_str or "already exists" in err_str:
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
        else:
            ensure_expert_quote_table(app)


def verify_critical_tables(app) -> None:
    """Verify critical tables exist. Exit(1) if any missing."""
    from backend.extensions import db
    from sqlalchemy import text

    with app.app_context():
        for table_name, sql in (
            ("province", text("SELECT 1 FROM province LIMIT 1")),
            ("transport_method", text("SELECT 1 FROM transport_method LIMIT 1")),
            ("expert_quote", text("SELECT 1 FROM expert_quote LIMIT 1")),
        ):
            try:
                with db.engine.connect() as conn:
                    conn.execute(sql)
            except Exception as e:
                print("[startup] Critical table %r missing or inaccessible: %s" % (table_name, e))
                traceback.print_exc()
                sys.exit(1)
    print("[startup] Critical tables OK.")
