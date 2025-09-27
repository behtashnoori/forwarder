"""Database models for the shipment request service."""
from datetime import datetime

from backend.extensions import db


# SQLAlchemy does not automatically generate primary keys for BIGINT columns on
# SQLite. Using a variant that maps BIGINT to INTEGER on SQLite keeps
# auto-increment behaviour in development while retaining BIGINT for Postgres.
SQLITE_COMPAT_BIGINT = db.BigInteger().with_variant(db.Integer, "sqlite")


class Province(db.Model):
    """Represents a province."""

    __tablename__ = "province"

    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    code = db.Column(db.String(10), nullable=True)
    name_fa = db.Column(db.Text, nullable=False)

    counties = db.relationship("County", back_populates="province", lazy=True)
    cities = db.relationship("City", back_populates="province", lazy=True)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Province id={self.id} name_fa={self.name_fa!r}>"


class County(db.Model):
    """Represents a county within a province."""

    __tablename__ = "county"

    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    name_fa = db.Column(db.Text, nullable=False)
    province_id = db.Column(
        SQLITE_COMPAT_BIGINT, db.ForeignKey("province.id"), nullable=False
    )

    province = db.relationship("Province", back_populates="counties")
    cities = db.relationship("City", back_populates="county")

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<County id={self.id} name_fa={self.name_fa!r}>"


class City(db.Model):
    """Represents a city within a county."""

    __tablename__ = "city"

    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    name_fa = db.Column(db.Text, nullable=False)
    county_id = db.Column(
        SQLITE_COMPAT_BIGINT, db.ForeignKey("county.id"), nullable=False
    )
    province_id = db.Column(
        SQLITE_COMPAT_BIGINT, db.ForeignKey("province.id"), nullable=False
    )

    county = db.relationship("County", back_populates="cities")
    province = db.relationship("Province", back_populates="cities")

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<City id={self.id} name_fa={self.name_fa!r}>"


class ExpertUser(db.Model):
    """Represents an expert user who can handle shipment requests."""
    
    __tablename__ = "expert_user"
    
    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    role = db.Column(db.String(20), default="expert")
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_login_at = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self) -> str:
        return f"<ExpertUser id={self.id} username={self.username}>"


class ShipmentRequest(db.Model):
    """Represents a shipment request submitted by a user."""

    __tablename__ = "shipment_request"

    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    origin_province_id = db.Column(
        SQLITE_COMPAT_BIGINT, db.ForeignKey("province.id"), nullable=False
    )
    origin_county_id = db.Column(
        SQLITE_COMPAT_BIGINT, db.ForeignKey("county.id"), nullable=False
    )
    origin_city_id = db.Column(
        SQLITE_COMPAT_BIGINT, db.ForeignKey("city.id"), nullable=False
    )
    dest_province_id = db.Column(
        SQLITE_COMPAT_BIGINT, db.ForeignKey("province.id"), nullable=False
    )
    dest_county_id = db.Column(
        SQLITE_COMPAT_BIGINT, db.ForeignKey("county.id"), nullable=False
    )
    dest_city_id = db.Column(
        SQLITE_COMPAT_BIGINT, db.ForeignKey("city.id"), nullable=False
    )
    contact_phone = db.Column(db.String(32), nullable=False)
    # Customer details (optional)
    customer_first_name = db.Column(db.String(100), nullable=True)
    customer_last_name = db.Column(db.String(100), nullable=True)
    transport_method = db.Column(db.String(32), nullable=True)
    # Cargo details (optional)
    cargo_description = db.Column(db.Text, nullable=True)
    cargo_weight = db.Column(db.Float, nullable=True)
    cargo_volume = db.Column(db.Float, nullable=True)
    cargo_value = db.Column(db.Float, nullable=True)
    special_instructions = db.Column(db.Text, nullable=True)
    pickup_date = db.Column(db.Date, nullable=True)
    delivery_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    ready_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    status_request_status = db.Column(db.String(32), nullable=False, default="new")
    request_user_id = db.Column(SQLITE_COMPAT_BIGINT, nullable=True)
    
    # Expert Console fields
    assigned_to = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("expert_user.id"), nullable=True)
    status = db.Column(db.String(32), nullable=False, default="new")
    sla_due_at = db.Column(db.DateTime, nullable=True)
    last_customer_touch_at = db.Column(db.DateTime, nullable=True)
    has_unread_for_assignee = db.Column(db.Boolean, default=True)
    priority = db.Column(db.String(10), default="normal")
    estimated_value = db.Column(db.Float, nullable=True)
    
    # Optional CRM integration
    customer_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("customer.id"), nullable=True)

    logs = db.relationship("ShipmentRequestLog", backref="shipment_request", lazy=True)
    expert_logs = db.relationship("ExpertConsoleLog", backref="shipment_request", lazy=True)
    expert_messages = db.relationship("ExpertConsoleMessage", backref="shipment_request", lazy=True)
    expert_notifications = db.relationship("ExpertConsoleNotification", backref="shipment_request", lazy=True)
    assigned_expert = db.relationship("ExpertUser", backref="assigned_requests")

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<ShipmentRequest id={self.id}>"


class ShipmentRequestLog(db.Model):
    """Log entries for shipment request lifecycle events."""

    __tablename__ = "shipment_request_log"

    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    shipment_request_id = db.Column(
        SQLITE_COMPAT_BIGINT, db.ForeignKey("shipment_request.id"), nullable=False
    )
    created_at = db.Column(db.DateTime, nullable=False)
    note = db.Column(db.Text, nullable=False)
    ip_address = db.Column(db.Text, nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (
            "<ShipmentRequestLog "
            f"id={self.id} shipment_request_id={self.shipment_request_id}>"
        )


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
    action = db.Column(db.String(50), nullable=False)
    old_status = db.Column(db.String(32), nullable=True)
    new_status = db.Column(db.String(32), nullable=True)
    note = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    created_by_user = db.relationship("ExpertUser", backref="created_logs")
    
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
    message_type = db.Column(db.String(20), nullable=False)
    subject = db.Column(db.String(200), nullable=True)
    content = db.Column(db.Text, nullable=False)
    is_read_by_customer = db.Column(db.Boolean, default=False)
    customer_response = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    created_by_user = db.relationship("ExpertUser", backref="created_messages")
    
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
    notification_type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self) -> str:
        return f"<ExpertConsoleNotification id={self.id} type={self.notification_type}>"


# CRM Models - Customer Management
class Customer(db.Model):
    """Represents a customer in the CRM system."""
    
    __tablename__ = "customer"
    
    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    company_name = db.Column(db.String(200), nullable=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    mobile = db.Column(db.String(20), nullable=True)
    website = db.Column(db.String(200), nullable=True)
    industry = db.Column(db.String(100), nullable=True)
    company_size = db.Column(db.String(50), nullable=True)  # small, medium, large, enterprise
    customer_type = db.Column(db.String(20), default="prospect")  # prospect, customer, partner, vendor
    status = db.Column(db.String(20), default="active")  # active, inactive, blocked
    source = db.Column(db.String(50), nullable=True)  # website, referral, cold_call, etc.
    notes = db.Column(db.Text, nullable=True)
    address = db.Column(db.Text, nullable=True)
    city = db.Column(db.String(100), nullable=True)
    province = db.Column(db.String(100), nullable=True)
    postal_code = db.Column(db.String(20), nullable=True)
    country = db.Column(db.String(100), default="Iran")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_contact_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    contacts = db.relationship("CustomerContact", backref="customer", lazy=True)
    opportunities = db.relationship("Opportunity", backref="customer", lazy=True)
    activities = db.relationship("Activity", backref="customer", lazy=True)
    # shipments relationship removed - will be added later when needed
    
    def __repr__(self) -> str:
        return f"<Customer id={self.id} name={self.first_name} {self.last_name}>"


class CustomerContact(db.Model):
    """Represents contacts within a customer organization."""
    
    __tablename__ = "customer_contact"
    
    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    customer_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("customer.id"), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    mobile = db.Column(db.String(20), nullable=True)
    position = db.Column(db.String(100), nullable=True)
    department = db.Column(db.String(100), nullable=True)
    is_primary = db.Column(db.Boolean, default=False)
    is_decision_maker = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self) -> str:
        return f"<CustomerContact id={self.id} name={self.first_name} {self.last_name}>"


# CRM Models - Sales Management
class Opportunity(db.Model):
    """Represents sales opportunities in the CRM."""
    
    __tablename__ = "opportunity"
    
    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    customer_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("customer.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    stage = db.Column(db.String(50), nullable=False)  # lead, qualified, proposal, negotiation, closed_won, closed_lost
    probability = db.Column(db.Integer, default=0)  # 0-100 percentage
    value = db.Column(db.Float, nullable=True)
    currency = db.Column(db.String(3), default="IRR")
    expected_close_date = db.Column(db.Date, nullable=True)
    actual_close_date = db.Column(db.Date, nullable=True)
    source = db.Column(db.String(50), nullable=True)
    assigned_to = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("expert_user.id"), nullable=True)
    status = db.Column(db.String(20), default="open")  # open, won, lost, cancelled
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    activities = db.relationship("Activity", backref="opportunity", lazy=True)
    assigned_expert = db.relationship("ExpertUser", backref="assigned_opportunities")
    
    def __repr__(self) -> str:
        return f"<Opportunity id={self.id} title={self.title}>"


# CRM Models - Activity Management
class Activity(db.Model):
    """Represents activities and interactions with customers."""
    
    __tablename__ = "activity"
    
    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    customer_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("customer.id"), nullable=True)
    opportunity_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("opportunity.id"), nullable=True)
    shipment_request_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("shipment_request.id"), nullable=True)
    expert_user_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("expert_user.id"), nullable=False)
    activity_type = db.Column(db.String(50), nullable=False)  # call, email, meeting, task, note, follow_up
    subject = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default="pending")  # pending, completed, cancelled
    priority = db.Column(db.String(10), default="normal")  # low, normal, high, urgent
    due_date = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    duration_minutes = db.Column(db.Integer, nullable=True)
    outcome = db.Column(db.String(100), nullable=True)  # successful, unsuccessful, rescheduled
    next_action = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    expert_user = db.relationship("ExpertUser", backref="activities")
    
    def __repr__(self) -> str:
        return f"<Activity id={self.id} type={self.activity_type}>"


# CRM Models - Task Management
class Task(db.Model):
    """Represents tasks and to-dos for experts."""
    
    __tablename__ = "task"
    
    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    assigned_to = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("expert_user.id"), nullable=False)
    created_by = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("expert_user.id"), nullable=False)
    priority = db.Column(db.String(10), default="normal")  # low, normal, high, urgent
    status = db.Column(db.String(20), default="pending")  # pending, in_progress, completed, cancelled
    due_date = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    customer_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("customer.id"), nullable=True)
    opportunity_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("opportunity.id"), nullable=True)
    shipment_request_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("shipment_request.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    assigned_expert = db.relationship("ExpertUser", foreign_keys=[assigned_to], backref="assigned_tasks")
    creator = db.relationship("ExpertUser", foreign_keys=[created_by], backref="created_tasks")
    
    def __repr__(self) -> str:
        return f"<Task id={self.id} title={self.title}>"


# CRM Models - Reporting and Analytics
class Report(db.Model):
    """Represents saved reports and dashboards."""
    
    __tablename__ = "report"
    
    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    report_type = db.Column(db.String(50), nullable=False)  # sales, customer, activity, performance
    filters = db.Column(db.Text, nullable=True)  # JSON string of filter criteria
    created_by = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("expert_user.id"), nullable=False)
    is_public = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    creator = db.relationship("ExpertUser", backref="created_reports")
    
    def __repr__(self) -> str:
        return f"<Report id={self.id} name={self.name}>"


__all__ = [
    "Province",
    "County",
    "City",
    "ExpertUser",
    "ShipmentRequest",
    "ShipmentRequestLog",
    "ExpertConsoleLog",
    "ExpertConsoleMessage",
    "ExpertConsoleNotification",
    # CRM Models
    "Customer",
    "CustomerContact", 
    "Opportunity",
    "Activity",
    "Task",
    "Report",
]