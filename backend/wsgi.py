"""Canonical WSGI entrypoint with a non-mutating database readiness gate."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.runtime import create_runtime_app

app = create_runtime_app()

if __name__ == "__main__":
    # Canonical development server wrapper.
    from backend.run import main
    main()
