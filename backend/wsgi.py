"""WSGI entrypoint for running the backend with gunicorn or flask."""
from backend import create_app

app = create_app()
