"""Application extensions module."""
from flask_sqlalchemy import SQLAlchemy


# Global SQLAlchemy instance to be initialized with the Flask app.
db = SQLAlchemy()

__all__ = ["db"]
