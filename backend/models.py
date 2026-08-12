"""Database models for the shipment request service."""
from datetime import datetime
from uuid import uuid4
from sqlalchemy import event, inspect, select
from sqlalchemy.orm import declared_attr

from backend.extensions import db


# SQLAlchemy does not automatically generate primary keys for BIGINT columns on
# SQLite. Using a variant that maps BIGINT to INTEGER on SQLite keeps
# auto-increment behaviour in development while retaining BIGINT for Postgres.
SQLITE_COMPAT_BIGINT = db.BigInteger().with_variant(db.Integer, "sqlite")


class Province(db.Model):
    """Represents a province."""

    __tablename__ = "province"

    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    code = db.Column(db.String(10), nullable=True, index=True)
    name_fa = db.Column(db.Text, nullable=False)
    country_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("country.id", ondelete="RESTRICT"), nullable=True, index=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    effective_from = db.Column(db.Date, nullable=True)
    effective_to = db.Column(db.Date, nullable=True)
    source_organization = db.Column(db.String(160), nullable=True)
    source_reference = db.Column(db.String(255), nullable=True)
    source_version = db.Column(db.String(100), nullable=True)
    dataset_id = db.Column(db.String(100), nullable=True)

    __table_args__ = (
        db.UniqueConstraint("country_id", "code", name="uq_province_country_code"),
        db.CheckConstraint("effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from", name="ck_province_effective_range"),
    )

    counties = db.relationship("County", back_populates="province", lazy=True)
    cities = db.relationship("City", back_populates="province", lazy=True)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Province id={self.id} name_fa={self.name_fa!r}>"


class County(db.Model):
    """Represents a county within a province."""

    __tablename__ = "county"

    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    code = db.Column(db.String(64), nullable=True, index=True)
    name_fa = db.Column(db.Text, nullable=False)
    province_id = db.Column(
        SQLITE_COMPAT_BIGINT, db.ForeignKey("province.id"), nullable=False
    )

    is_active = db.Column(db.Boolean, nullable=False, default=True)
    effective_from = db.Column(db.Date, nullable=True)
    effective_to = db.Column(db.Date, nullable=True)
    source_organization = db.Column(db.String(160), nullable=True)
    source_reference = db.Column(db.String(255), nullable=True)
    source_version = db.Column(db.String(100), nullable=True)
    dataset_id = db.Column(db.String(100), nullable=True)
    __table_args__ = (
        db.UniqueConstraint("province_id", "code", name="uq_county_province_code"),
        db.CheckConstraint("effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from", name="ck_county_effective_range"),
    )

    province = db.relationship("Province", back_populates="counties")
    cities = db.relationship("City", back_populates="county")

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<County id={self.id} name_fa={self.name_fa!r}>"


class City(db.Model):
    """Represents a city within a county."""

    __tablename__ = "city"

    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    code = db.Column(db.String(64), nullable=True, index=True)
    name_fa = db.Column(db.Text, nullable=False)
    county_id = db.Column(
        SQLITE_COMPAT_BIGINT, db.ForeignKey("county.id"), nullable=False
    )
    province_id = db.Column(
        SQLITE_COMPAT_BIGINT, db.ForeignKey("province.id"), nullable=False
    )

    is_active = db.Column(db.Boolean, nullable=False, default=True)
    effective_from = db.Column(db.Date, nullable=True)
    effective_to = db.Column(db.Date, nullable=True)
    source_organization = db.Column(db.String(160), nullable=True)
    source_reference = db.Column(db.String(255), nullable=True)
    source_version = db.Column(db.String(100), nullable=True)
    dataset_id = db.Column(db.String(100), nullable=True)
    __table_args__ = (
        db.UniqueConstraint("county_id", "code", name="uq_city_county_code"),
        db.CheckConstraint("effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from", name="ck_city_effective_range"),
    )

    county = db.relationship("County", back_populates="cities")
    province = db.relationship("Province", back_populates="cities")

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<City id={self.id} name_fa={self.name_fa!r}>"


class Country(db.Model):
    """Represents a country for international shipping."""

    __tablename__ = "country"
    __table_args__ = (
        db.CheckConstraint("effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from", name="ck_country_effective_range"),
    )

    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    name_en = db.Column(db.String(100), nullable=False)
    name_fa = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(3), nullable=False, unique=True)  # ISO country code
    is_active = db.Column(db.Boolean, default=True)
    effective_from = db.Column(db.Date, nullable=True)
    effective_to = db.Column(db.Date, nullable=True)
    source_organization = db.Column(db.String(160), nullable=True)
    source_reference = db.Column(db.String(255), nullable=True)
    source_version = db.Column(db.String(100), nullable=True)
    dataset_id = db.Column(db.String(100), nullable=True)
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
    __table_args__ = (
        db.CheckConstraint(
            "sla_response_work_minutes BETWEEN 1 AND 10080",
            name="ck_expert_user_sla_response_work_minutes",
        ),
    )
    
    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    role = db.Column(db.String(20), default="expert")  # expert, supervisor, crm_manager, business_expert
    is_active = db.Column(db.Boolean, default=True)
    can_handle_domestic = db.Column(db.Boolean, nullable=False, default=True, server_default="1")
    can_handle_international = db.Column(db.Boolean, nullable=False, default=True, server_default="1")
    sla_response_work_minutes = db.Column(db.Integer, nullable=False, default=120, server_default="120")
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


class RevokedToken(db.Model):
    """Stores revocable JWT identifiers without retaining bearer credentials."""

    __tablename__ = "revoked_token"
    __table_args__ = (
        db.CheckConstraint("token_type IN ('access', 'refresh')", name="ck_revoked_token_type"),
        db.CheckConstraint(
            "reason IN ('logout', 'logout_all', 'refresh_rotated', 'refresh_reuse_detected', "
            "'password_changed', 'account_deactivated', 'account_deleted', 'admin_revoked', 'expired', 'security_event')",
            name="ck_revoked_token_reason",
        ),
    )

    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, unique=True, index=True)
    user_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("expert_user.id", ondelete="SET NULL"), nullable=True, index=True)
    token_type = db.Column(db.String(16), nullable=False)
    revoked_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    reason = db.Column(db.String(32), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class AuthSession(db.Model):
    """Server-side lifecycle state shared by one access/refresh token family."""

    __tablename__ = "auth_session"
    __table_args__ = (
        db.CheckConstraint(
            "revoked_reason IS NULL OR revoked_reason IN ('logout', 'logout_all', 'refresh_reuse_detected', "
            "'password_changed', 'account_deactivated', 'account_deleted', 'admin_revoked', 'expired', 'security_event')",
            name="ck_auth_session_revoked_reason",
        ),
    )

    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    session_id = db.Column(db.String(36), nullable=False, unique=True, index=True)
    user_id = db.Column(
        SQLITE_COMPAT_BIGINT,
        db.ForeignKey("expert_user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    refresh_jti = db.Column(db.String(36), nullable=False, unique=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_rotated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    revoked_at = db.Column(db.DateTime, nullable=True)
    revoked_reason = db.Column(db.String(32), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)


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
    __table_args__ = (
        db.UniqueConstraint("id", "operational_organization_id", name="uq_shipment_request_id_operational_org"),
        db.CheckConstraint(
            "ownership_scope IS NULL OR "
            "(ownership_scope = 'TENANT' AND operational_organization_id IS NOT NULL) OR "
            "(ownership_scope IN ('INTAKE','LEGACY_QUARANTINED') AND operational_organization_id IS NULL)",
            name="ck_shipment_request_ownership_envelope",
        ),
    )

    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    operational_organization_id = db.Column(
        SQLITE_COMPAT_BIGINT, db.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    ownership_scope = db.Column(db.String(24), nullable=True)

    # Public tracking code (unique, non-guessable); used for /customer/track/:identifier
    tracking_code = db.Column(db.String(32), unique=True, nullable=True, index=True)

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
    origin_country_id = db.Column(
        SQLITE_COMPAT_BIGINT,
        db.ForeignKey("country.id", ondelete="RESTRICT"),
        nullable=True,
    )
    origin_international_city_id = db.Column(
        SQLITE_COMPAT_BIGINT,
        db.ForeignKey("international_city.id", ondelete="RESTRICT"),
        nullable=True,
    )
    origin_country = db.Column(db.String(100), nullable=True)
    origin_city_international = db.Column(db.String(100), nullable=True)
    origin_address_international = db.Column(db.Text, nullable=True)
    dest_country_id = db.Column(
        SQLITE_COMPAT_BIGINT,
        db.ForeignKey("country.id", ondelete="RESTRICT"),
        nullable=True,
    )
    dest_international_city_id = db.Column(
        SQLITE_COMPAT_BIGINT,
        db.ForeignKey("international_city.id", ondelete="RESTRICT"),
        nullable=True,
    )
    dest_country = db.Column(db.String(100), nullable=True)
    dest_city_international = db.Column(db.String(100), nullable=True)
    dest_address_international = db.Column(db.Text, nullable=True)
    
    # Iran entry point fields (for international shipping to Iran)
    iran_entry_port = db.Column(db.String(100), nullable=True)
    iran_entry_province = db.Column(db.String(100), nullable=True)
    iran_entry_port_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("iran_port.id"), nullable=True)
    iran_entry_province_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("province.id"), nullable=True)

    # Iran destination point: how the customer names their in-Iran destination.
    # 'port' -> iran_entry_port_id, 'customs' -> iran_dest_customs_office_id, 'city' -> iran_dest_city_id.
    iran_dest_type = db.Column(db.String(10), nullable=True)  # port, customs, city
    iran_dest_customs_office_id = db.Column(
        SQLITE_COMPAT_BIGINT, db.ForeignKey("customs_office.id"), nullable=True
    )
    iran_dest_city_id = db.Column(
        SQLITE_COMPAT_BIGINT, db.ForeignKey("city.id"), nullable=True
    )

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
    project_id = db.Column(
        SQLITE_COMPAT_BIGINT,
        db.ForeignKey("project.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    customer_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("customer.id"), nullable=True)
    gamification_customer_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("customer_gamification.id"), nullable=True)

    logs = db.relationship("ShipmentRequestLog", backref="shipment_request", lazy=True)
    expert_logs = db.relationship("ExpertConsoleLog", backref="shipment_request", lazy=True)
    expert_messages = db.relationship("ExpertConsoleMessage", backref="shipment_request", lazy=True)
    expert_notifications = db.relationship("ExpertConsoleNotification", backref="shipment_request", lazy=True)
    assigned_expert = db.relationship("ExpertUser", back_populates="assigned_requests")
    customer = db.relationship("Customer", back_populates="requests")
    project = db.relationship("Project", back_populates="shipment_requests")
    gamification_customer = db.relationship("CustomerGamification", back_populates="requests")
    origin_country_ref = db.relationship("Country", foreign_keys=[origin_country_id])
    origin_international_city_ref = db.relationship(
        "InternationalCity", foreign_keys=[origin_international_city_id]
    )
    dest_country_ref = db.relationship("Country", foreign_keys=[dest_country_id])
    dest_international_city_ref = db.relationship(
        "InternationalCity", foreign_keys=[dest_international_city_id]
    )
    iran_entry_port_ref = db.relationship("IranPort", foreign_keys=[iran_entry_port_id])
    iran_dest_customs_office = db.relationship("CustomsOffice", foreign_keys=[iran_dest_customs_office_id])
    iran_dest_city = db.relationship("City", foreign_keys=[iran_dest_city_id])
    shipment_tracking = db.relationship(
        "ShipmentTracking",
        back_populates="shipment_request",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<ShipmentRequest id={self.id}>"


class ShipmentTracking(db.Model):
    """Customer tracking enablement and audit state for one shipment."""

    __tablename__ = "shipment_tracking"
    __table_args__ = (
        db.UniqueConstraint("shipment_request_id", name="uq_shipment_tracking_request"),
    )

    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    operational_organization_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=True, index=True)
    shipment_request_id = db.Column(
        SQLITE_COMPAT_BIGINT,
        db.ForeignKey("shipment_request.id", ondelete="CASCADE"),
        nullable=False,
    )
    is_enabled = db.Column(db.Boolean, nullable=False, default=False)
    enabled_at = db.Column(db.DateTime, nullable=True)
    enabled_by_user_id = db.Column(
        SQLITE_COMPAT_BIGINT, db.ForeignKey("expert_user.id", ondelete="SET NULL"), nullable=True
    )
    disabled_at = db.Column(db.DateTime, nullable=True)
    disabled_by_user_id = db.Column(
        SQLITE_COMPAT_BIGINT, db.ForeignKey("expert_user.id", ondelete="SET NULL"), nullable=True
    )
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    shipment_request = db.relationship("ShipmentRequest", back_populates="shipment_tracking")
    enabled_by_user = db.relationship("ExpertUser", foreign_keys=[enabled_by_user_id])
    disabled_by_user = db.relationship("ExpertUser", foreign_keys=[disabled_by_user_id])
    units = db.relationship(
        "ShipmentTransportUnit",
        back_populates="tracking",
        cascade="all, delete-orphan",
        order_by="ShipmentTransportUnit.sort_order, ShipmentTransportUnit.id",
    )


class ShipmentTransportUnit(db.Model):
    """A manually tracked truck, container, wagon, or other transport unit."""

    __tablename__ = "shipment_transport_unit"
    __table_args__ = (
        db.UniqueConstraint("tracking_id", "unit_code", name="uq_tracking_unit_code"),
        db.CheckConstraint("sort_order >= 0", name="ck_tracking_unit_sort_order_nonnegative"),
    )

    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    tracking_id = db.Column(
        SQLITE_COMPAT_BIGINT,
        db.ForeignKey("shipment_tracking.id", ondelete="CASCADE"),
        nullable=False,
    )
    unit_code = db.Column(db.String(64), nullable=False)
    unit_type = db.Column(db.String(32), nullable=False)
    display_name = db.Column(db.String(100), nullable=True)
    vehicle_reference = db.Column(db.String(100), nullable=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_by_user_id = db.Column(
        SQLITE_COMPAT_BIGINT, db.ForeignKey("expert_user.id", ondelete="SET NULL"), nullable=True
    )
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    tracking = db.relationship("ShipmentTracking", back_populates="units")
    created_by_user = db.relationship("ExpertUser", foreign_keys=[created_by_user_id])
    updates = db.relationship(
        "ShipmentTransportUnitUpdate",
        back_populates="unit",
        cascade="all, delete-orphan",
        order_by="ShipmentTransportUnitUpdate.occurred_at, ShipmentTransportUnitUpdate.id",
    )


class TrackingLocationReference(db.Model):
    """Curated internal UI helper for manually reported tracking locations."""

    __tablename__ = "tracking_location_reference"
    __table_args__ = (
        db.UniqueConstraint(
            "internal_key", name="uq_tracking_location_reference_internal_key"
        ),
        db.CheckConstraint(
            "location_type IN ('origin_city','commercial_hub','seaport','rail_terminal',"
            "'road_terminal','border_point','transit_city','iran_gateway',"
            "'destination_city','other')",
            name="ck_tracking_location_reference_type",
        ),
        db.CheckConstraint(
            "reference_status IN ('internal_reference','verified_internal','inactive')",
            name="ck_tracking_location_reference_status",
        ),
        db.CheckConstraint("sort_order >= 0", name="ck_tracking_location_reference_sort_order"),
    )

    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    internal_key = db.Column(db.String(100), nullable=False)
    name_fa = db.Column(db.String(160), nullable=False)
    name_en = db.Column(db.String(160), nullable=True)
    country_code = db.Column(db.String(2), nullable=False)
    location_type = db.Column(db.String(32), nullable=False)
    aliases = db.Column(db.JSON, nullable=True)
    reference_status = db.Column(db.String(32), nullable=False, default="internal_reference")
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    tracking_updates = db.relationship(
        "ShipmentTransportUnitUpdate",
        back_populates="location_reference",
        passive_deletes=True,
    )


class ShipmentTransportUnitUpdate(db.Model):
    """Append-only manually entered status for one transport unit."""

    __tablename__ = "shipment_transport_unit_update"
    __table_args__ = (
        db.Index("idx_tracking_update_unit_occurred", "unit_id", "occurred_at"),
    )

    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    unit_id = db.Column(
        SQLITE_COMPAT_BIGINT,
        db.ForeignKey("shipment_transport_unit.id", ondelete="CASCADE"),
        nullable=False,
    )
    status = db.Column(db.String(32), nullable=False)
    location = db.Column(db.String(255), nullable=True)
    location_reference_id = db.Column(
        SQLITE_COMPAT_BIGINT,
        db.ForeignKey("tracking_location_reference.id", ondelete="RESTRICT"),
        nullable=True,
    )
    location_name_snapshot = db.Column(db.String(160), nullable=True)
    country_code_snapshot = db.Column(db.String(2), nullable=True)
    location_text = db.Column(db.String(255), nullable=True)
    customer_message = db.Column(db.Text, nullable=True)
    internal_note = db.Column(db.Text, nullable=True)
    is_customer_visible = db.Column(db.Boolean, nullable=False, default=True)
    occurred_at = db.Column(db.DateTime, nullable=False)
    created_by_user_id = db.Column(
        SQLITE_COMPAT_BIGINT, db.ForeignKey("expert_user.id", ondelete="SET NULL"), nullable=True
    )
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    unit = db.relationship("ShipmentTransportUnit", back_populates="updates")
    created_by_user = db.relationship("ExpertUser", foreign_keys=[created_by_user_id])
    location_reference = db.relationship("TrackingLocationReference", back_populates="tracking_updates")


@event.listens_for(TrackingLocationReference, "before_delete")
def _protect_referenced_tracking_location(_mapper, connection, target):
    referenced = connection.execute(
        select(ShipmentTransportUnitUpdate.id)
        .where(ShipmentTransportUnitUpdate.location_reference_id == target.id)
        .limit(1)
    ).first()
    if referenced:
        raise ValueError("referenced tracking locations cannot be hard deleted")


class ShipmentRequestLog(db.Model):
    """Log entries for shipment request lifecycle events."""

    __tablename__ = "shipment_request_log"

    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    operational_organization_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=True, index=True)
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
    operational_organization_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=True, index=True)
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


class CRMCustomerLinkAudit(db.Model):
    """Append-only audit trail for CRM customer links on shipment requests."""

    __tablename__ = "crm_customer_link_audit"

    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    shipment_request_id = db.Column(
        SQLITE_COMPAT_BIGINT, db.ForeignKey("shipment_request.id"), nullable=False
    )
    old_customer_id = db.Column(
        SQLITE_COMPAT_BIGINT, db.ForeignKey("customer.id"), nullable=True
    )
    new_customer_id = db.Column(
        SQLITE_COMPAT_BIGINT, db.ForeignKey("customer.id"), nullable=True
    )
    operation = db.Column(db.String(32), nullable=False)
    performed_by_user_id = db.Column(
        SQLITE_COMPAT_BIGINT, db.ForeignKey("expert_user.id"), nullable=True
    )
    performed_by_role = db.Column(db.String(32), nullable=True)
    source = db.Column(db.String(64), nullable=False, default="crm_api")
    reason = db.Column(db.Text, nullable=True)
    request_status_at_time = db.Column(db.String(32), nullable=True)
    assigned_to_at_time = db.Column(SQLITE_COMPAT_BIGINT, nullable=True)
    gamification_customer_id_at_time = db.Column(SQLITE_COMPAT_BIGINT, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    shipment_request = db.relationship("ShipmentRequest", backref="crm_customer_link_audits")
    old_customer = db.relationship("Customer", foreign_keys=[old_customer_id])
    new_customer = db.relationship("Customer", foreign_keys=[new_customer_id])
    performed_by_user = db.relationship("ExpertUser", foreign_keys=[performed_by_user_id])

    def __repr__(self) -> str:
        return (
            "<CRMCustomerLinkAudit "
            f"id={self.id} request={self.shipment_request_id} operation={self.operation}>"
        )


class ExpertConsoleMessage(db.Model):
    """Messages and notes for expert console."""
    
    __tablename__ = "expert_console_message"
    
    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    operational_organization_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=True, index=True)
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
    operational_organization_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=True, index=True)
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


class ExpertQuote(db.Model):
    """Stored quote (preنهاد) for a shipment request. Multiple quotes per request allowed; latest is shown."""
    __tablename__ = "expert_quote"

    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    shipment_request_id = db.Column(
        SQLITE_COMPAT_BIGINT, db.ForeignKey("shipment_request.id"), nullable=False
    )
    amount = db.Column(SQLITE_COMPAT_BIGINT, nullable=False)  # integer amount (e.g. IRR)
    currency = db.Column(db.String(10), nullable=False, default="IRR")
    note = db.Column(db.Text, nullable=True)
    valid_until = db.Column(db.Date, nullable=True)
    created_by_expert_id = db.Column(
        SQLITE_COMPAT_BIGINT, db.ForeignKey("expert_user.id"), nullable=False
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Customer response to the quote: NULL (no response yet), 'accepted', or 'declined'.
    customer_response = db.Column(db.String(10), nullable=True)
    responded_at = db.Column(db.DateTime, nullable=True)
    operational_organization_id = db.Column(
        SQLITE_COMPAT_BIGINT,
        db.ForeignKey("operational_organization.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    __table_args__ = (
        db.CheckConstraint(
            "customer_response IS NULL OR customer_response IN ('accepted', 'declined')",
            name="ck_expert_quote_customer_response",
        ),
    )

    shipment_request = db.relationship("ShipmentRequest", backref=db.backref("quotes", lazy="dynamic"))
    created_by_expert = db.relationship("ExpertUser", backref="created_quotes")

    def __repr__(self) -> str:
        return f"<ExpertQuote id={self.id} request_id={self.shipment_request_id}>"
class Customer(db.Model):
    """Represents a customer in the CRM system."""
    
    __tablename__ = "customer"
    __table_args__ = (
        db.UniqueConstraint("id", "operational_organization_id", name="uq_customer_id_operational_org"),
        db.CheckConstraint(
            "ownership_scope IS NULL OR "
            "(ownership_scope = 'TENANT' AND operational_organization_id IS NOT NULL) OR "
            "(ownership_scope = 'LEGACY_QUARANTINED' AND operational_organization_id IS NULL)",
            name="ck_customer_ownership_envelope",
        ),
    )
    
    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    operational_organization_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=True, index=True)
    ownership_scope = db.Column(db.String(24), nullable=True)
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
    operational_organization_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=True, index=True)
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
    operational_organization_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=True, index=True)
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


class ReferralRule(db.Model):
    """Rules for referral-based assignment with direct or pool actions."""
    __tablename__ = "referral_rule"

    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    priority = db.Column(db.Integer, default=1)  # Lower number = higher priority
    conditions = db.Column(db.Text, nullable=False)  # JSON: shipping_type, transport_method, origin_province, destination_province
    action = db.Column(db.Text, nullable=False)  # JSON: direct_assign { expert_id } | pool_assign { expert_ids, strategy, max_active_assignments_per_expert }
    stop_on_match = db.Column(db.Boolean, default=True)
    created_by = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("expert_user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    creator = db.relationship("ExpertUser", backref="created_referral_rules")
    state = db.relationship("ReferralRuleState", backref="rule", uselist=False, lazy=True)
    referral_logs = db.relationship("ReferralAssignmentLog", backref="rule", lazy=True)

    def __repr__(self) -> str:
        return f"<ReferralRule id={self.id} name={self.name!r}>"


class ReferralRuleState(db.Model):
    """Round-robin state per rule (one row per rule)."""
    __tablename__ = "referral_rule_state"

    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    rule_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("referral_rule.id"), nullable=False, unique=True)
    rr_index = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<ReferralRuleState rule_id={self.rule_id} rr_index={self.rr_index}>"


class ReferralAssignmentLog(db.Model):
    """Log of referral assignments with strategy and debug info."""
    __tablename__ = "referral_assignment_log"

    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    operational_organization_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=True, index=True)
    request_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("shipment_request.id"), nullable=False)
    rule_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("referral_rule.id"), nullable=True)  # None = system auto-assign
    selected_expert_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("expert_user.id"), nullable=False)
    strategy_used = db.Column(db.String(32), nullable=False)  # direct, round_robin, least_workload
    candidate_expert_ids = db.Column(db.Text, nullable=True)  # JSON array of ids
    debug = db.Column(db.Text, nullable=True)  # JSON debug trace
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    shipment_request = db.relationship("ShipmentRequest", backref="referral_assignment_logs")
    selected_expert = db.relationship("ExpertUser", backref="referral_assignment_logs")

    def __repr__(self) -> str:
        return f"<ReferralAssignmentLog id={self.id} request_id={self.request_id} expert_id={self.selected_expert_id}>"


class ReferralAutoAssignState(db.Model):
    """Single-row state for round-robin auto-assignment (no rules)."""
    __tablename__ = "referral_auto_assign_state"

    id = db.Column(db.Integer, primary_key=True)
    last_index = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class IranPort(db.Model):
    """Represents major ports in Iran for international shipping entry points."""
    
    __tablename__ = "iran_port"
    
    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    code = db.Column(db.String(64), nullable=True, index=True)
    name_fa = db.Column(db.String(100), nullable=False)
    name_en = db.Column(db.String(100), nullable=False)
    port_type = db.Column(db.String(20), nullable=False, default="sea")  # sea, air, land
    province_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("province.id"), nullable=False)
    country_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("country.id", ondelete="RESTRICT"), nullable=True, index=True)
    is_major_port = db.Column(db.Boolean, default=True)
    is_active = db.Column(db.Boolean, default=True)
    effective_from = db.Column(db.Date, nullable=True)
    effective_to = db.Column(db.Date, nullable=True)
    source_organization = db.Column(db.String(160), nullable=True)
    source_reference = db.Column(db.String(255), nullable=True)
    source_version = db.Column(db.String(100), nullable=True)
    dataset_id = db.Column(db.String(100), nullable=True)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    province = db.relationship("Province", backref="ports")
    country = db.relationship("Country")

    __table_args__ = (
        db.UniqueConstraint("country_id", "code", name="uq_iran_port_country_code"),
        db.CheckConstraint("effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from", name="ck_iran_port_effective_range"),
    )
    
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
    is_preferred = db.Column(db.Boolean, nullable=False, default=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    effective_from = db.Column(db.Date, nullable=True)
    effective_to = db.Column(db.Date, nullable=True)
    source_organization = db.Column(db.String(160), nullable=True)
    source_reference = db.Column(db.String(255), nullable=True)
    source_version = db.Column(db.String(100), nullable=True)
    dataset_id = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("port_id", "province_id", name="uq_port_province_mapping"),
        db.CheckConstraint("effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from", name="ck_port_province_mapping_effective_range"),
    )
    
    # Relationships
    port = db.relationship("IranPort", backref="province_mappings")
    province = db.relationship("Province", backref="port_mappings")
    
    def __repr__(self) -> str:
        return f"<PortProvinceMapping port={self.port_id} province={self.province_id}>"


CUSTOMS_OFFICE_TYPES = frozenset({
    "seaport", "road_border", "rail", "airport", "inland",
    "free_zone", "special_economic_zone", "other",
})
PORT_CUSTOMS_RELATIONSHIP_TYPES = frozenset({
    "located_at", "serves_port", "associated", "other",
})


class CustomsOffice(db.Model):
    """Canonical customs master data; geography is referenced, never created."""

    __tablename__ = "customs_office"
    __table_args__ = (
        db.CheckConstraint(
            "customs_type IN ('seaport','road_border','rail','airport','inland','free_zone','special_economic_zone','other')",
            name="ck_customs_office_type",
        ),
        db.CheckConstraint("effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from", name="ck_customs_office_effective_range"),
    )

    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    code = db.Column(db.String(64), nullable=False, unique=True)
    name_fa = db.Column(db.String(160), nullable=False)
    name_en = db.Column(db.String(160), nullable=True)
    customs_type = db.Column(db.String(32), nullable=False)
    country_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("country.id", ondelete="RESTRICT"), nullable=False)
    province_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("province.id", ondelete="RESTRICT"), nullable=True)
    county_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("county.id", ondelete="RESTRICT"), nullable=True)
    city_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("city.id", ondelete="RESTRICT"), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    effective_from = db.Column(db.Date, nullable=True)
    effective_to = db.Column(db.Date, nullable=True)
    source_organization = db.Column(db.String(160), nullable=True)
    source_reference = db.Column(db.String(255), nullable=True)
    source_version = db.Column(db.String(100), nullable=True)
    dataset_id = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    country = db.relationship("Country")
    province = db.relationship("Province")
    county = db.relationship("County")
    city = db.relationship("City")


class PortCustomsOffice(db.Model):
    """Explicit association between a port and a customs office."""

    __tablename__ = "port_customs_office"
    __table_args__ = (
        db.UniqueConstraint("port_id", "customs_office_id", "relationship_type", name="uq_port_customs_relationship"),
        db.CheckConstraint(
            "relationship_type IN ('located_at','serves_port','associated','other')",
            name="ck_port_customs_relationship_type",
        ),
        db.CheckConstraint("effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from", name="ck_port_customs_effective_range"),
    )

    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    port_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("iran_port.id", ondelete="CASCADE"), nullable=False)
    customs_office_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("customs_office.id", ondelete="CASCADE"), nullable=False)
    relationship_type = db.Column(db.String(32), nullable=False)
    is_primary = db.Column(db.Boolean, nullable=False, default=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    effective_from = db.Column(db.Date, nullable=True)
    effective_to = db.Column(db.Date, nullable=True)
    source_organization = db.Column(db.String(160), nullable=True)
    source_reference = db.Column(db.String(255), nullable=True)
    source_version = db.Column(db.String(100), nullable=True)
    dataset_id = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    port = db.relationship("IranPort")
    customs_office = db.relationship("CustomsOffice")


PORT_LOCATION_STATUSES = frozenset({"confirmed", "provisional", "historical", "unknown"})


class PortLocation(db.Model):
    """Versionable physical location for a port; never inferred from names."""
    __tablename__ = "port_location"
    __table_args__ = (
        db.CheckConstraint("location_status IN ('confirmed','provisional','historical','unknown')", name="ck_port_location_status"),
        db.CheckConstraint("effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from", name="ck_port_location_effective_range"),
        db.Index("uq_port_location_active_port", "port_id", unique=True, postgresql_where=db.text("is_active IS TRUE"), sqlite_where=db.text("is_active = 1")),
    )
    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    port_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("iran_port.id", ondelete="RESTRICT"), nullable=False, index=True)
    country_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("country.id", ondelete="RESTRICT"), nullable=True, index=True)
    province_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("province.id", ondelete="RESTRICT"), nullable=True, index=True)
    county_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("county.id", ondelete="RESTRICT"), nullable=True, index=True)
    city_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("city.id", ondelete="RESTRICT"), nullable=True, index=True)
    location_status = db.Column(db.String(20), nullable=False, default="unknown")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    effective_from = db.Column(db.Date, nullable=True)
    effective_to = db.Column(db.Date, nullable=True)
    source_organization = db.Column(db.String(160), nullable=True)
    source_reference = db.Column(db.String(255), nullable=True)
    source_version = db.Column(db.String(100), nullable=True)
    dataset_id = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    port = db.relationship("IranPort")
    country = db.relationship("Country")
    province = db.relationship("Province")
    county = db.relationship("County")
    city = db.relationship("City")


class CustomsProvinceMapping(db.Model):
    """Explicit Customs service coverage for a Province."""
    __tablename__ = "customs_province_mapping"
    __table_args__ = (
        db.UniqueConstraint("customs_office_id", "province_id", name="uq_customs_province_mapping"),
        db.CheckConstraint("effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from", name="ck_customs_province_mapping_effective_range"),
    )
    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    customs_office_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("customs_office.id", ondelete="RESTRICT"), nullable=False, index=True)
    province_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("province.id", ondelete="RESTRICT"), nullable=False, index=True)
    is_preferred = db.Column(db.Boolean, nullable=False, default=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    effective_from = db.Column(db.Date, nullable=True)
    effective_to = db.Column(db.Date, nullable=True)
    source_organization = db.Column(db.String(160), nullable=True)
    source_reference = db.Column(db.String(255), nullable=True)
    source_version = db.Column(db.String(100), nullable=True)
    dataset_id = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    customs_office = db.relationship("CustomsOffice")
    province = db.relationship("Province")


MASTER_DATA_DIMENSIONS = frozenset({"COUNT", "WEIGHT", "VOLUME", "LENGTH", "OTHER_GOVERNED"})


class _GovernedMasterDataMixin:
    """Shared persistence contract for organization-independent reference data."""

    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, unique=True, default=lambda: str(uuid4()))
    immutable_code = db.Column(db.String(64), nullable=False, unique=True)
    fa_name = db.Column(db.String(160), nullable=False)
    en_name = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, nullable=True)
    display_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    version = db.Column(db.Integer, nullable=False, default=1)

    @declared_attr
    def __mapper_args__(cls):
        # SQLAlchemy includes the previously-read version in UPDATE predicates,
        # preventing concurrent requests from silently overwriting each other.
        return {"version_id_col": cls.version, "version_id_generator": False}


class CargoType(_GovernedMasterDataMixin, db.Model):
    __tablename__ = "cargo_type"
    __table_args__ = (
        db.CheckConstraint("version >= 1", name="ck_cargo_type_version_positive"),
        db.CheckConstraint("parent_id IS NULL OR parent_id <> id", name="ck_cargo_type_not_self_parent"),
    )
    parent_id = db.Column(
        SQLITE_COMPAT_BIGINT, db.ForeignKey("cargo_type.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    parent = db.relationship("CargoType", remote_side="CargoType.id", backref="children")


class ServiceType(_GovernedMasterDataMixin, db.Model):
    __tablename__ = "service_type"
    __table_args__ = (db.CheckConstraint("version >= 1", name="ck_service_type_version_positive"),)


class UnitOfMeasure(_GovernedMasterDataMixin, db.Model):
    __tablename__ = "unit_of_measure"
    __table_args__ = (
        db.CheckConstraint("version >= 1", name="ck_unit_of_measure_version_positive"),
        db.CheckConstraint(
            "measurement_dimension IN ('COUNT','WEIGHT','VOLUME','LENGTH','OTHER_GOVERNED')",
            name="ck_unit_of_measure_dimension",
        ),
    )
    symbol = db.Column(db.String(32), nullable=False)
    measurement_dimension = db.Column(db.String(32), nullable=False, index=True)


REFERENCE_DATA_SEED_RUN_MODES = frozenset({"apply"})
REFERENCE_DATA_SEED_RUN_STATUSES = frozenset({"started", "succeeded", "failed", "refused"})


class ReferenceDataSeedRun(db.Model):
    """Persistent, secret-safe evidence for explicit reference-data apply runs."""

    __tablename__ = "reference_data_seed_run"
    __table_args__ = (
        db.CheckConstraint("mode IN ('apply')", name="ck_reference_data_seed_run_mode"),
        db.CheckConstraint(
            "status IN ('started','succeeded','failed','refused')",
            name="ck_reference_data_seed_run_status",
        ),
        db.CheckConstraint(
            "planned_count >= 0 AND created_count >= 0 AND unchanged_count >= 0 AND conflict_count >= 0",
            name="ck_reference_data_seed_run_counts_nonnegative",
        ),
        db.Index(
            "ix_reference_data_seed_run_catalog_target",
            "catalog_version",
            "checksum",
            "environment",
        ),
        db.Index(
            "ix_reference_data_seed_run_status_started",
            "status",
            "started_at",
        ),
    )
    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, unique=True, default=lambda: str(uuid4()))
    catalog_version = db.Column(db.String(64), nullable=False)
    checksum = db.Column(db.String(71), nullable=False)
    environment = db.Column(db.String(32), nullable=False)
    mode = db.Column(db.String(16), nullable=False, default="apply")
    planned_count = db.Column(db.Integer, nullable=False, default=0)
    created_count = db.Column(db.Integer, nullable=False, default=0)
    unchanged_count = db.Column(db.Integer, nullable=False, default=0)
    conflict_count = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(16), nullable=False, default="started")
    executed_by = db.Column(db.String(160), nullable=False)
    approval_reference = db.Column(db.String(200), nullable=False)
    started_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    error_summary = db.Column(db.String(500), nullable=True)


@event.listens_for(CargoType, "before_update")
@event.listens_for(ServiceType, "before_update")
@event.listens_for(UnitOfMeasure, "before_update")
def _prevent_master_data_code_change(_mapper, _connection, target) -> None:
    if inspect(target).attrs.immutable_code.history.has_changes():
        raise ValueError("immutable_code cannot be changed")


@event.listens_for(PortLocation, "before_insert")
@event.listens_for(PortLocation, "before_update")
def _validate_port_location_before_write(_mapper, connection, target) -> None:
    """Reject inconsistent supplied hierarchy without creating or inferring rows."""
    if target.province_id is not None:
        province_country = connection.execute(select(Province.country_id).where(Province.id == target.province_id)).scalar_one_or_none()
        if province_country is not None and target.country_id != province_country:
            raise ValueError("port location province/country hierarchy is inconsistent")
    if target.county_id is not None:
        county_province = connection.execute(select(County.province_id).where(County.id == target.county_id)).scalar_one_or_none()
        if target.province_id is None or county_province != target.province_id:
            raise ValueError("port location county/province hierarchy is inconsistent")
    if target.city_id is not None:
        city_parent = connection.execute(select(City.county_id, City.province_id).where(City.id == target.city_id)).one_or_none()
        if city_parent is None or target.county_id is None or tuple(city_parent) != (target.county_id, target.province_id):
            raise ValueError("port location city hierarchy is inconsistent")


class SiteSetting(db.Model):
    """Key-value store for site-wide editable settings (name, logo, footer, nav labels, etc.)."""
    __tablename__ = "site_setting"

    key = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.Text, nullable=True)

    def __repr__(self) -> str:
        return f"<SiteSetting key={self.key!r}>"


class DocumentDefinition(db.Model):
    """Admin policy used when snapshotting requirements onto shipment requests."""

    __tablename__ = "document_definition"
    __table_args__ = (
        db.CheckConstraint("max_file_size_bytes > 0", name="ck_document_definition_max_size"),
        db.CheckConstraint("max_active_file_count > 0", name="ck_document_definition_max_count"),
        db.CheckConstraint(
            "applicability_scope IN ('all', 'domestic', 'international')",
            name="ck_document_definition_scope",
        ),
    )

    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, unique=True, default=lambda: str(uuid4()))
    code = db.Column(db.String(64), nullable=False, unique=True, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    is_required = db.Column(db.Boolean, nullable=False, default=False)
    allowed_formats = db.Column(db.Text, nullable=False)
    max_file_size_bytes = db.Column(SQLITE_COMPAT_BIGINT, nullable=False)
    max_active_file_count = db.Column(db.Integer, nullable=False, default=1)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    applicability_scope = db.Column(db.String(20), nullable=False, default="all")
    revision = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("expert_user.id", ondelete="SET NULL"), nullable=True)
    updated_by = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("expert_user.id", ondelete="SET NULL"), nullable=True)


class CaseDocumentRequirement(db.Model):
    """Immutable policy snapshot attached to the canonical shipment request."""

    __tablename__ = "case_document_requirement"
    __table_args__ = (
        db.UniqueConstraint(
            "shipment_request_id", "source_definition_id", "source_definition_revision",
            name="uq_case_document_requirement_source_revision",
        ),
    )

    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    operational_organization_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=True, index=True)
    shipment_request_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("shipment_request.id", ondelete="CASCADE"), nullable=False, index=True)
    source_definition_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("document_definition.id", ondelete="RESTRICT"), nullable=False, index=True)
    source_definition_code = db.Column(db.String(64), nullable=False)
    source_definition_revision = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    is_required = db.Column(db.Boolean, nullable=False)
    allowed_formats = db.Column(db.Text, nullable=False)
    max_file_size_bytes = db.Column(SQLITE_COMPAT_BIGINT, nullable=False)
    max_active_file_count = db.Column(db.Integer, nullable=False)
    sort_order = db.Column(db.Integer, nullable=False)
    applied_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    applied_by = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("expert_user.id", ondelete="SET NULL"), nullable=True)


class CaseDocumentFile(db.Model):
    """Immutable file metadata; binaries live in private document storage."""

    __tablename__ = "case_document_file"
    __table_args__ = (
        db.CheckConstraint("status IN ('active', 'superseded', 'deleted')", name="ck_case_document_file_status"),
        db.CheckConstraint(
            "(is_miscellaneous AND case_requirement_id IS NULL AND custom_title IS NOT NULL) OR "
            "((NOT is_miscellaneous) AND case_requirement_id IS NOT NULL)",
            name="ck_case_document_file_requirement",
        ),
        db.UniqueConstraint("case_requirement_id", "version_number", name="uq_case_document_file_requirement_version"),
    )

    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    operational_organization_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=True, index=True)
    public_id = db.Column(db.String(36), nullable=False, unique=True, default=lambda: str(uuid4()))
    shipment_request_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("shipment_request.id", ondelete="CASCADE"), nullable=False, index=True)
    case_requirement_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("case_document_requirement.id", ondelete="RESTRICT"), nullable=True, index=True)
    is_miscellaneous = db.Column(db.Boolean, nullable=False, default=False, index=True)
    custom_title = db.Column(db.String(200), nullable=True)
    description = db.Column(db.Text, nullable=True)
    original_filename = db.Column(db.String(255), nullable=False)
    safe_download_filename = db.Column(db.String(255), nullable=False)
    storage_key = db.Column(db.String(500), nullable=False, unique=True)
    canonical_extension = db.Column(db.String(10), nullable=False)
    detected_mime_type = db.Column(db.String(100), nullable=False)
    file_size_bytes = db.Column(SQLITE_COMPAT_BIGINT, nullable=False)
    sha256_hash = db.Column(db.String(64), nullable=False)
    version_number = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.String(20), nullable=False, default="active", index=True)
    uploaded_by = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("expert_user.id", ondelete="SET NULL"), nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    superseded_at = db.Column(db.DateTime, nullable=True)
    superseded_by = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("case_document_file.id", ondelete="SET NULL"), nullable=True)
    deleted_at = db.Column(db.DateTime, nullable=True)
    deleted_by = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("expert_user.id", ondelete="SET NULL"), nullable=True)
    deletion_reason = db.Column(db.Text, nullable=True)


class DocumentAuditEvent(db.Model):
    """Append-only audit trail for document policy and file actions."""

    __tablename__ = "document_audit_event"
    __table_args__ = (
        db.CheckConstraint(
            "scope_type IS NULL OR "
            "(scope_type = 'TENANT' AND operational_organization_id IS NOT NULL) OR "
            "(scope_type = 'PLATFORM' AND operational_organization_id IS NULL)",
            name="ck_document_audit_event_scope",
        ),
    )
    id = db.Column(SQLITE_COMPAT_BIGINT, primary_key=True)
    scope_type = db.Column(db.String(16), nullable=True)
    operational_organization_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=True, index=True)
    event_type = db.Column(db.String(64), nullable=False, index=True)
    actor_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("expert_user.id", ondelete="SET NULL"), nullable=True, index=True)
    shipment_request_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("shipment_request.id", ondelete="SET NULL"), nullable=True, index=True)
    definition_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("document_definition.id", ondelete="SET NULL"), nullable=True)
    document_file_id = db.Column(SQLITE_COMPAT_BIGINT, db.ForeignKey("case_document_file.id", ondelete="SET NULL"), nullable=True)
    details = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)


# Import the bounded operational module after legacy models are declared so its
# foreign-key targets are registered in the same SQLAlchemy metadata.
from backend.operational_models import (  # noqa: E402
    CanonicalLocation,
    Milestone,
    MilestoneEvent,
    DelayReason,
    ExceptionReason,
    OperationalDelay,
    OperationalException,
    OperationalAudit,
    OperationalIdempotency,
    OperationalMembership,
    OperationalOrganization,
    OperationalOutbox,
    OperationalShipment,
    OperationalWorkItem,
    Project,
    RouteLeg,
    RoutePlan,
)
from backend.cargo_models import CargoCatalogItem, CargoItemAlias, ShipmentCargoItem  # noqa: E402
from backend.mdpm_models import (  # noqa: E402
    ArtifactAssociation,
    DocumentAssessment,
    DocumentReadinessAudit,
    OperationalDocumentRequirement,
    RequirementApplicabilityDecision,
    TransitionOverride,
)
from backend.economics_models import (  # noqa: E402
    EconomicAudit, EconomicEvidenceAssociation, EconomicFxRate, EconomicObservationFx,
    EconomicLine, EconomicObservation,
)


__all__ = [
    "CargoCatalogItem",
    "CargoItemAlias",
    "ShipmentCargoItem",
    "CargoType",
    "ServiceType",
    "UnitOfMeasure",
    "ReferenceDataSeedRun",
    "REFERENCE_DATA_SEED_RUN_MODES",
    "REFERENCE_DATA_SEED_RUN_STATUSES",
    "MASTER_DATA_DIMENSIONS",
    "Province",
    "County",
    "City",
    "Country",
    "InternationalCity",
    "ExpertUser",
    "ShipmentRequest",
    "ShipmentRequestLog",
    "ShipmentTracking",
    "ShipmentTransportUnit",
    "ShipmentTransportUnitUpdate",
    "ExpertConsoleLog",
    "CRMCustomerLinkAudit",
    "ExpertConsoleMessage",
    "ExpertConsoleNotification",
    "ExpertQuote",
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
    "ReferralRule",
    "ReferralRuleState",
    "ReferralAssignmentLog",
    "ReferralAutoAssignState",
    # Iran Ports Models
    "IranPort",
    "PortProvinceMapping",
    "CustomsOffice",
    "PortCustomsOffice",
    "PortLocation",
    "CustomsProvinceMapping",
    "PORT_LOCATION_STATUSES",
    "CUSTOMS_OFFICE_TYPES",
    "PORT_CUSTOMS_RELATIONSHIP_TYPES",
    "SiteSetting",
    "DocumentDefinition",
    "CaseDocumentRequirement",
    "CaseDocumentFile",
    "DocumentAuditEvent",
    "OperationalOrganization",
    "Project",
    "OperationalMembership",
    "CanonicalLocation",
    "OperationalShipment",
    "RoutePlan",
    "RouteLeg",
    "Milestone",
    "MilestoneEvent",
    "DelayReason",
    "ExceptionReason",
    "OperationalDelay",
    "OperationalException",
    "OperationalWorkItem",
    "OperationalAudit",
    "OperationalOutbox",
    "OperationalIdempotency",
    "EconomicLine",
    "EconomicObservation",
    "EconomicEvidenceAssociation",
    "EconomicFxRate",
    "EconomicObservationFx",
    "EconomicAudit",
]
