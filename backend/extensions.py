"""Application extensions module."""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate


# Global SQLAlchemy instance to be initialized with the Flask app.
db = SQLAlchemy()
migrate = Migrate()

__all__ = ["db", "migrate"]
