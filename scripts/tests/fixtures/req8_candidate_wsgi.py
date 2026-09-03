"""Candidate application WSGI object for the REQ-8 local process harness."""
from backend import create_app

app = create_app(skip_startup=True)
