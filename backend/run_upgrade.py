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
        migration_dir = os.path.join(os.path.dirname(__file__), "migrations")
        print("Running upgrade, directory:", migration_dir, flush=True)
        try:
            config = current_app.extensions["migrate"].migrate.get_config(
                migration_dir
            )
            command.upgrade(config, "head")
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
