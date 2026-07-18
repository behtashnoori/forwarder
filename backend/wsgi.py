"""WSGI entrypoint for gunicorn (and thin wrapper for dev: delegates to backend.run)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import create_app

app = create_app()

if __name__ == "__main__":
    # Canonical dev entrypoint: one place for port check, migrations, server start
    from backend.run import main
    main()

