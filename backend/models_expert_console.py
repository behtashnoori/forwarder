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


class ExpertUser(db.Model):
    """Represents an expert user who can handle shipment requests."""
    
    __tablename__ = "expert_user"
    
    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    role = db.Column(db.String(20), default="expert")  # expert, supervisor
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_login_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    assigned_requests = db.relationship("ShipmentRequest", backref="assigned_expert", lazy=True)
    created_logs = db.relationship("ExpertConsoleLog", backref="created_by_user", lazy=True)
    created_messages = db.relationship("ExpertConsoleMessage", backref="created_by_user", lazy=True)
    
    def __repr__(self) -> str:
        return f"<ExpertUser id={self.id} username={self.username}>"


class ExpertConsoleLog(db.Model):
    """Extended log for expert console with detailed tracking."""
    
    __tablename__ = "expert_console_log"
    
    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    shipment_request_id = db.Column(
        SQLITE_COMPAT_BIGINT, db.ForeignKey("shipment_request.id"), nullable=False
    )
    expert_user_id = db.Column(
        SQLITE_COMPAT_BIGINT, db.ForeignKey("expert_user.id"), nullable=True
    )
    action = db.Column(db.String(50), nullable=False)  # status_change, assignment, note, etc.
    old_status = db.Column(db.String(32), nullable=True)
    new_status = db.Column(db.String(32), nullable=True)
    note = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self) -> str:
        return f"<ExpertConsoleLog id={self.id} action={self.action}>"


class ExpertConsoleMessage(db.Model):
    """Messages and notes for expert console."""
    
    __tablename__ = "expert_console_message"
    
    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    shipment_request_id = db.Column(
        SQLITE_COMPAT_BIGINT, db.ForeignKey("shipment_request.id"), nullable=False
    )
    expert_user_id = db.Column(
        SQLITE_COMPAT_BIGINT, db.ForeignKey("expert_user.id"), nullable=False
    )
    message_type = db.Column(db.String(20), nullable=False)  # internal_note, customer_message
    subject = db.Column(db.String(200), nullable=True)
    content = db.Column(db.Text, nullable=False)
    is_read_by_customer = db.Column(db.Boolean, default=False)
    customer_response = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<ExpertConsoleMessage id={self.id} type={self.message_type}>"


class ExpertConsoleNotification(db.Model):
    """Notifications for expert console."""
    
    __tablename__ = "expert_console_notification"
    
    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    expert_user_id = db.Column(
        SQLITE_COMPAT_BIGINT, db.ForeignKey("expert_user.id"), nullable=False
    )
    shipment_request_id = db.Column(
        SQLITE_COMPAT_BIGINT, db.ForeignKey("shipment_request.id"), nullable=False
    )
    notification_type = db.Column(db.String(50), nullable=False)  # new_request, status_change, etc.
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self) -> str:
        return f"<ExpertConsoleNotification id={self.id} type={self.notification_type}>"


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
    "ExpertUser",
    "ExpertConsoleLog",
    "ExpertConsoleMessage",
    "ExpertConsoleNotification",
]



