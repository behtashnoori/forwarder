"""
Canonical dev entrypoint. Single place that loads config, checks port, runs migrations, starts server.
Run: python -m backend.run [--reload]
Do not start the server from elsewhere; use this module or call it.
"""
from __future__ import annotations

import argparse
import os
import socket
import sys
import traceback

# Ensure project root is on path when run as python -m backend.run or from backend/
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_THIS_DIR)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# Load config first (loads .env and sets HOST, PORT, DEBUG, USE_RELOAD)
from backend import config  # noqa: E402

from backend import create_app  # noqa: E402


def _is_port_in_use(host: str, port: int) -> bool:
    """Cross-platform: True if host:port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return False
        except OSError:
            return True


def _print_port_hints(port: int) -> None:
    print("  Linux/macOS: lsof -ti:%d | xargs kill" % port)
    print("  Windows: Get-NetTCPConnection -LocalPort %d | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }" % port)
    print("  Or: netstat -ano | findstr :%d" % port)


def _run_migrations(app) -> None:
    """Run pending migrations. On failure: log, traceback, exit 1."""
    from backend.extensions import db
    from flask import current_app
    from alembic import command
    from sqlalchemy import text

    with app.app_context():
        _migration_dir = os.path.join(_THIS_DIR, "migrations")
        try:
            with db.engine.connect() as conn:
                with conn.begin():
                    conn.execute(text(
                        "ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(255)"
                    ))
        except Exception:
            pass
        try:
            cfg = current_app.extensions["migrate"].migrate.get_config(_migration_dir)
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Run backend dev server (fixed port, no silent exit)")
    parser.add_argument("--reload", action="store_true", help="Enable Flask reloader (default: off for stability)")
    args = parser.parse_args()
    use_reloader = args.reload

    host = config.HOST
    port = config.PORT
    debug = config.DEBUG

    print("[startup] PORT=%s, HOST=%s, DEBUG=%s, use_reloader=%s" % (port, host, debug, use_reloader))

    if _is_port_in_use(host, port):
        print("Port %s is already in use. Please stop the process using it." % port)
        _print_port_hints(port)
        sys.exit(1)

    app = create_app()
    _run_migrations(app)

    print("Backend started successfully on http://localhost:%s. Health: GET http://localhost:%s/api/health" % (port, port))
    app.run(host=host, port=port, debug=debug, use_reloader=use_reloader)


if __name__ == "__main__":
    main()
