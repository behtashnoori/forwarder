"""Database models for expert console functionality."""
from datetime import datetime
from enum import Enum

from backend.extensions import db

# SQLite compatibility for BIGINT
SQLITE_COMPAT_BIGINT = db.BigInteger().with_variant(db.Integer, "sqlite")


class RequestStatus(Enum):
    """Enum for shipment request statuses."""
    NEW = "new"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    QUOTED = "quoted"
    WAITING_FOR_CUSTOMER = "waiting_for_customer"
    WON = "won"
    LOST = "lost"
    CLOSED = "closed"


class MessageType(Enum):
    """Enum for message types."""
    INTERNAL_NOTE = "internal_note"
    CUSTOMER_MESSAGE = "customer_message"
    STATUS_CHANGE = "status_change"
    ASSIGNMENT = "assignment"


# ExpertUser model is imported from models.py to avoid duplication


# Expert console models are imported from models.py to avoid duplication


# Update the existing ShipmentRequest model with expert console fields
# This will be added via migration
EXPERT_CONSOLE_FIELDS = """
# Expert Console fields for ShipmentRequest:
assigned_to = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("expert_user.id"), nullable=True)
status = db.Column(db.String(32), nullable=False, default="new")  # Updated status field
sla_due_at = db.Column(db.DateTime, nullable=True)
last_customer_touch_at = db.Column(db.DateTime, nullable=True)
has_unread_for_assignee = db.Column(db.Boolean, default=True)
priority = db.Column(db.String(10), default="normal")  # low, normal, high, urgent
estimated_value = db.Column(db.Float, nullable=True)
"""

__all__ = [
    "RequestStatus",
    "MessageType", 
    "ExpertConsoleLog",
    "ExpertConsoleMessage",
    "ExpertConsoleNotification",
]




