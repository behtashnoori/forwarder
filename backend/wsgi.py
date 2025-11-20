"""WSGI entrypoint for running the backend with gunicorn or flask."""
import sys
import os

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import create_app

app = create_app()


if __name__ == "__main__":
    host = os.getenv("FLASK_RUN_HOST", "127.0.0.1")
    port = int(os.getenv("FLASK_RUN_PORT", "8501"))
    debug_env = os.getenv("FLASK_DEBUG", "1")
    debug = debug_env.lower() in {"1", "true", "yes", "on"}
    app.run(host=host, port=port, debug=debug)
