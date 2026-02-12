"""WSGI entrypoint for running the backend with gunicorn or flask."""
import os
import sys

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import create_app

app = create_app()

if __name__ == "__main__":
    host = os.getenv("FLASK_RUN_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_RUN_PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "0").lower() in ("1", "true", "yes")
    app.run(host=host, port=port, debug=debug)
