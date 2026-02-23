"""Run database migrations (upgrade) once. Use from project root: python -m backend.run_upgrade"""
import logging
import os
import sys

# Ensure project root is on path
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

os.chdir(_project_root)

# Ensure we see flask_migrate errors (they use log.error then sys.exit(1))
_h = logging.StreamHandler(sys.stderr)
_h.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
logging.getLogger("flask_migrate").addHandler(_h)
logging.getLogger("flask_migrate").setLevel(logging.DEBUG)


def main():
    from backend import create_app
    from flask import current_app
    from alembic import command
    from alembic.util import CommandError
    app = create_app()
    with app.app_context():
        from backend.extensions import db
        from sqlalchemy import text
        migration_dir = os.path.join(os.path.dirname(__file__), "migrations")
        print("Running upgrade, directory:", migration_dir, flush=True)
        try:
            # Widen alembic_version.version_num if needed (revision IDs can be >32 chars)
            try:
                with db.engine.connect() as conn:
                    with conn.begin():
                        conn.execute(
                            text(
                                "ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(255)"
                            )
                        )
            except Exception:
                pass  # column may already be wide or table not exist
            config = current_app.extensions["migrate"].migrate.get_config(
                migration_dir
            )
            try:
                command.upgrade(config, "head")
            except Exception as upgrade_err:
                # If upgrade fails due to already-applied schema (multiple branches),
                # set DB to head and ensure tracking_code column exists
                err_str = str(upgrade_err).lower()
                if "duplicatecolumn" in err_str or "duplicatetable" in err_str or "already exists" in err_str:
                    head_rev = "20250220_merge_final"
                    print("Setting alembic_version to", head_rev, "and ensuring tracking_code.", flush=True)
                    try:
                        with db.engine.connect() as conn:
                            with conn.begin():
                                conn.execute(text("DELETE FROM alembic_version"))
                                conn.execute(text(
                                    "INSERT INTO alembic_version (version_num) VALUES (:rev)"
                                ), {"rev": head_rev})
                                conn.execute(text(
                                    "ALTER TABLE shipment_request ADD COLUMN IF NOT EXISTS tracking_code VARCHAR(32)"
                                ))
                                conn.execute(text(
                                    "CREATE UNIQUE INDEX IF NOT EXISTS ix_shipment_request_tracking_code ON shipment_request (tracking_code)"
                                ))
                        print("Recovery done. Retrying upgrade to head.", flush=True)
                        command.upgrade(config, "head")
                    except Exception as e:
                        print("Recovery step failed:", e, file=sys.stderr)
                        raise
                else:
                    raise
            print("Migrations applied successfully.", flush=True)
            return 0
        except CommandError as e:
            print("Migration error:", e, file=sys.stderr)
            return 1
        except SystemExit as e:
            print("Migrations exited with code:", e.code, file=sys.stderr)
            return int(e.code) if e.code is not None else 1
        except Exception as e:
            import traceback
            print("Migrations failed:", e, file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            return 1


if __name__ == "__main__":
    sys.exit(main())
