"""WSGI entrypoint for running the backend with gunicorn or flask."""
import os
import socket
import sys

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import create_app

app = create_app()

# Run pending migrations once on startup (after app is created, to avoid recursion with env.py get_url())
with app.app_context():
    from backend.extensions import db
    from flask import current_app
    from alembic import command
    from sqlalchemy import text
    _migration_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "migrations")
    try:
        with db.engine.connect() as conn:
            with conn.begin():
                conn.execute(text(
                    "ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(255)"
                ))
    except Exception:
        pass
    try:
        config = current_app.extensions["migrate"].migrate.get_config(_migration_dir)
        command.upgrade(config, "head")
        print("Migrations applied.")
    except Exception as _e:
        err_str = str(_e).lower()
        if "duplicatecolumn" in err_str or "duplicatetable" in err_str or "already exists" in err_str:
            try:
                with db.engine.connect() as conn:
                    with conn.begin():
                        conn.execute(text("DELETE FROM alembic_version"))
                        conn.execute(text("INSERT INTO alembic_version (version_num) VALUES (:rev)"), {"rev": "20250220_merge_final"})
                        conn.execute(text("ALTER TABLE shipment_request ADD COLUMN IF NOT EXISTS tracking_code VARCHAR(32)"))
                        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_shipment_request_tracking_code ON shipment_request (tracking_code)"))
                print("Migrations applied (recovery).")
            except Exception as _e2:
                print("Migrations (upgrade) failed:", _e2)
        else:
            print("Migrations (upgrade) failed:", _e)

def _is_port_in_use(host: str, port: int) -> bool:
    """Return True if the given host:port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return False
        except OSError:
            return True


if __name__ == "__main__":
    host = os.getenv("HOST") or os.getenv("FLASK_RUN_HOST", "0.0.0.0")
    port = int(os.getenv("PORT") or os.getenv("FLASK_RUN_PORT") or "8000")
    debug = os.getenv("FLASK_DEBUG", "0").lower() in ("1", "true", "yes")

    if _is_port_in_use(host, port):
        print(f"Port {port} is in use. Stop the other process or set PORT to another value and restart.")
        sys.exit(1)

    app.run(host=host, port=port, debug=debug)
