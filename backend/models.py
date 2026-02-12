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


class Country(db.Model):
    """Represents a country for international shipping."""

    __tablename__ = "country"

    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    name_en = db.Column(db.String(100), nullable=False)
    name_fa = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(3), nullable=False, unique=True)  # ISO country code
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    cities = db.relationship("InternationalCity", back_populates="country", lazy=True)

    def __repr__(self) -> str:
        return f"<Country id={self.id} name_fa={self.name_fa!r}>"


class InternationalCity(db.Model):
    """Represents a city or port in a country for international shipping."""

    __tablename__ = "international_city"

    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    name_en = db.Column(db.String(100), nullable=False)
    name_fa = db.Column(db.String(100), nullable=False)
    country_id = db.Column(
        SQLITE_COMPAT_BIGINT, db.ForeignKey("country.id"), nullable=False
    )
    city_type = db.Column(db.String(20), nullable=False, default="city")  # city, port, airport
    is_major_port = db.Column(db.Boolean, default=False)
    is_major_airport = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    country = db.relationship("Country", back_populates="cities")

    def __repr__(self) -> str:
        return f"<InternationalCity id={self.id} name_fa={self.name_fa!r}>"


class ExpertUser(db.Model):
    """Represents an expert user who can handle shipment requests."""
    
    __tablename__ = "expert_user"
    
    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    role = db.Column(db.String(20), default="expert")  # expert, supervisor, crm_manager, business_expert
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_login_at = db.Column(db.DateTime, nullable=True)
    
    # Hierarchy fields
    manager_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("expert_user.id"), nullable=True)
    department = db.Column(db.String(50), nullable=True)  # crm, business, operations, etc.
    specialization = db.Column(db.Text, nullable=True)  # JSON string for additional specializations
    
    # Relationships
    manager = db.relationship("ExpertUser", remote_side=[id], backref="subordinates")
    assigned_requests = db.relationship("ShipmentRequest", back_populates="assigned_expert", lazy=True)
    created_logs = db.relationship("ExpertConsoleLog", back_populates="created_by_user", lazy=True)
    created_messages = db.relationship("ExpertConsoleMessage", back_populates="created_by_user", lazy=True)
    
    def __repr__(self) -> str:
        return f"<ExpertUser id={self.id} username={self.username}>"
    
    def get_specializations(self):
        """Get expert's transport method specializations."""
        return [spec for spec in self.specializations if spec.transport_method.is_active]
    
    def can_handle_transport_method(self, transport_method_id):
        """Check if expert can handle a specific transport method."""
        return any(spec.transport_method_id == transport_method_id for spec in self.get_specializations())
    
    def get_workload(self):
        """Get current workload (number of assigned requests)."""
        return len([req for req in self.assigned_requests if req.status in ['assigned', 'in_progress']])


class CustomerGamification(db.Model):
    """Represents a customer who can track their requests with gamification."""
    
    __tablename__ = "customer_gamification"
    
    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    first_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=True)
    is_email_verified = db.Column(db.Boolean, default=False)
    email_verification_token = db.Column(db.String(100), nullable=True)
    verification_expires_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_login_at = db.Column(db.DateTime, nullable=True)
    
    # Gamification fields
    total_requests = db.Column(db.Integer, default=0)
    completed_requests = db.Column(db.Integer, default=0)
    loyalty_points = db.Column(db.Integer, default=0)
    customer_level = db.Column(db.String(20), default="bronze")  # bronze, silver, gold, platinum
    
    # Relationships
    requests = db.relationship("ShipmentRequest", back_populates="gamification_customer", lazy=True)
    
    def __repr__(self) -> str:
        return f"<CustomerGamification id={self.id} email={self.email}>"
    
    def update_loyalty_points(self, points: int):
        """Update customer loyalty points and level."""
        self.loyalty_points += points
        
        # Update level based on points
        if self.loyalty_points >= 1000:
            self.customer_level = "platinum"
        elif self.loyalty_points >= 500:
            self.customer_level = "gold"
        elif self.loyalty_points >= 100:
            self.customer_level = "silver"
        else:
            self.customer_level = "bronze"


class CustomerWorkflowStep(db.Model):
    """Tracks customer workflow steps for gamification."""
    
    __tablename__ = "customer_workflow_step"
    
    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    customer_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("customer_gamification.id"), nullable=False)
    shipment_request_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("shipment_request.id"), nullable=False)
    step_name = db.Column(db.String(50), nullable=False)  # email_verified, request_submitted, expert_assigned, etc.
    step_order = db.Column(db.Integer, nullable=False)
    is_completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    points_earned = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    customer = db.relationship("CustomerGamification", backref="workflow_steps")
    shipment_request = db.relationship("ShipmentRequest", backref="workflow_steps")
    
    def __repr__(self) -> str:
        return f"<CustomerWorkflowStep id={self.id} step={self.step_name}>"


class ShipmentRequest(db.Model):
    """Represents a shipment request submitted by a user."""

    __tablename__ = "shipment_request"

    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    
    # Shipping type: 'domestic' or 'international'
    shipping_type = db.Column(db.String(20), nullable=False, default="domestic")
    
    # Domestic shipping fields (nullable for international)
    origin_province_id = db.Column(
        SQLITE_COMPAT_BIGINT, db.ForeignKey("province.id"), nullable=True
    )
    origin_county_id = db.Column(
        SQLITE_COMPAT_BIGINT, db.ForeignKey("county.id"), nullable=True
    )
    origin_city_id = db.Column(
        SQLITE_COMPAT_BIGINT, db.ForeignKey("city.id"), nullable=True
    )
    dest_province_id = db.Column(
        SQLITE_COMPAT_BIGINT, db.ForeignKey("province.id"), nullable=True
    )
    dest_county_id = db.Column(
        SQLITE_COMPAT_BIGINT, db.ForeignKey("county.id"), nullable=True
    )
    dest_city_id = db.Column(
        SQLITE_COMPAT_BIGINT, db.ForeignKey("city.id"), nullable=True
    )
    
    # International shipping fields (nullable for domestic)
    origin_country = db.Column(db.String(100), nullable=True)
    origin_city_international = db.Column(db.String(100), nullable=True)
    origin_address_international = db.Column(db.Text, nullable=True)
    dest_country = db.Column(db.String(100), nullable=True)
    dest_city_international = db.Column(db.String(100), nullable=True)
    dest_address_international = db.Column(db.Text, nullable=True)
    
    # Iran entry point fields (for international shipping to Iran)
    iran_entry_port = db.Column(db.String(100), nullable=True)
    iran_entry_province = db.Column(db.String(100), nullable=True)
    iran_entry_port_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("iran_port.id"), nullable=True)
    iran_entry_province_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("province.id"), nullable=True)
    
    contact_phone = db.Column(db.String(32), nullable=False)
    # Customer details (optional)
    customer_first_name = db.Column(db.String(100), nullable=True)
    customer_last_name = db.Column(db.String(100), nullable=True)
    transport_method = db.Column(db.String(32), nullable=True)  # Legacy field, kept for backward compatibility
    # Separate transport methods for international and domestic shipping
    international_transport_method = db.Column(db.String(32), nullable=True)
    domestic_transport_method = db.Column(db.String(32), nullable=True)
    transport_method_preference = db.Column(db.String(20), nullable=True, default="customer_choice")  # customer_choice, forwarder_suggestion
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
    gamification_customer_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("customer_gamification.id"), nullable=True)

    logs = db.relationship("ShipmentRequestLog", backref="shipment_request", lazy=True)
    expert_logs = db.relationship("ExpertConsoleLog", backref="shipment_request", lazy=True)
    expert_messages = db.relationship("ExpertConsoleMessage", backref="shipment_request", lazy=True)
    expert_notifications = db.relationship("ExpertConsoleNotification", backref="shipment_request", lazy=True)
    assigned_expert = db.relationship("ExpertUser", back_populates="assigned_requests")
    customer = db.relationship("Customer", back_populates="requests")
    gamification_customer = db.relationship("CustomerGamification", back_populates="requests")

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
    
    created_by_user = db.relationship("ExpertUser", back_populates="created_logs")
    
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
    
    created_by_user = db.relationship("ExpertUser", back_populates="created_messages")
    
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
    requests = db.relationship("ShipmentRequest", back_populates="customer", lazy=True)
    
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


class TransportMethod(db.Model):
    """Represents different transport methods available in the system."""
    
    __tablename__ = "transport_method"
    
    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # English name
    name_fa = db.Column(db.String(100), nullable=False)  # Persian name
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    expert_specializations = db.relationship("ExpertSpecialization", backref="transport_method", lazy=True)
    
    def __repr__(self) -> str:
        return f"<TransportMethod id={self.id} name={self.name_fa}>"


class ExpertSpecialization(db.Model):
    """Represents expert specializations in different transport methods."""
    
    __tablename__ = "expert_specialization"
    
    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    expert_user_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("expert_user.id"), nullable=False)
    transport_method_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("transport_method.id"), nullable=False)
    proficiency_level = db.Column(db.String(20), default="intermediate")  # beginner, intermediate, advanced, expert
    is_primary = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    expert_user = db.relationship("ExpertUser", backref="specializations")
    
    def __repr__(self) -> str:
        return f"<ExpertSpecialization expert={self.expert_user_id} transport={self.transport_method_id}>"


class AssignmentRule(db.Model):
    """Represents rules for automatic assignment of shipment requests."""
    
    __tablename__ = "assignment_rule"
    
    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    rule_type = db.Column(db.String(50), nullable=False)  # transport_method, location, priority, workload
    conditions = db.Column(db.Text, nullable=False)  # JSON string for rule conditions
    priority = db.Column(db.Integer, default=1)  # Higher number = higher priority
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("expert_user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    creator = db.relationship("ExpertUser", backref="created_assignment_rules")
    assignment_logs = db.relationship("AssignmentLog", backref="assignment_rule", lazy=True)
    
    def __repr__(self) -> str:
        return f"<AssignmentRule id={self.id} name={self.name}>"


class AssignmentLog(db.Model):
    """Logs automatic assignments for tracking and analysis."""
    
    __tablename__ = "assignment_log"
    
    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    shipment_request_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("shipment_request.id"), nullable=False)
    assigned_expert_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("expert_user.id"), nullable=False)
    assignment_rule_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("assignment_rule.id"), nullable=True)
    assignment_method = db.Column(db.String(20), nullable=False)  # automatic, manual, override
    assignment_reason = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    shipment_request = db.relationship("ShipmentRequest", backref="assignment_logs")
    assigned_expert = db.relationship("ExpertUser", backref="assignment_logs")
    
    def __repr__(self) -> str:
        return f"<AssignmentLog id={self.id} request={self.shipment_request_id} expert={self.assigned_expert_id}>"


class IranPort(db.Model):
    """Represents major ports in Iran for international shipping entry points."""
    
    __tablename__ = "iran_port"
    
    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    name_fa = db.Column(db.String(100), nullable=False)
    name_en = db.Column(db.String(100), nullable=False)
    port_type = db.Column(db.String(20), nullable=False, default="sea")  # sea, air, land
    province_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("province.id"), nullable=False)
    is_major_port = db.Column(db.Boolean, default=True)
    is_active = db.Column(db.Boolean, default=True)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    province = db.relationship("Province", backref="ports")
    
    def __repr__(self) -> str:
        return f"<IranPort id={self.id} name_fa={self.name_fa!r}>"


class PortProvinceMapping(db.Model):
    """Maps which ports are suitable for which provinces based on logistics efficiency."""
    
    __tablename__ = "port_province_mapping"
    
    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    port_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("iran_port.id"), nullable=False)
    province_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("province.id"), nullable=False)
    suitability_score = db.Column(db.Float, default=1.0)  # 0.0 to 1.0, higher is better
    transport_method = db.Column(db.String(50), nullable=True)  # road, rail, air, sea
    estimated_days = db.Column(db.Integer, nullable=True)  # estimated transport days
    is_recommended = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    port = db.relationship("IranPort", backref="province_mappings")
    province = db.relationship("Province", backref="port_mappings")
    
    def __repr__(self) -> str:
        return f"<PortProvinceMapping port={self.port_id} province={self.province_id}>"


__all__ = [
    "Province",
    "County",
    "City",
    "Country",
    "InternationalCity",
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
    # Hierarchy and Assignment Models
    "TransportMethod",
    "ExpertSpecialization",
    "AssignmentRule",
    "AssignmentLog",
    # Iran Ports Models
    "IranPort",
    "PortProvinceMapping",
]