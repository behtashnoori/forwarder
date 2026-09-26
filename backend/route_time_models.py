"""Organization reference durations and immutable explicit planning selections."""
from uuid import uuid4
from sqlalchemy import event, inspect
from backend.extensions import db
from backend.operational_models import BIGINT, utcnow


class OrganizationRouteTime(db.Model):
    __tablename__ = "organization_route_time"
    __table_args__ = (
        db.UniqueConstraint("public_id", name="uq_route_time_public"),
        db.UniqueConstraint("id", "organization_id", name="uq_route_time_id_org"),
        db.ForeignKeyConstraint(["origin_point_id", "organization_id"], ["logistics_point.id", "logistics_point.organization_id"], name="fk_route_time_origin_org", ondelete="RESTRICT"),
        db.ForeignKeyConstraint(["destination_point_id", "organization_id"], ["logistics_point.id", "logistics_point.organization_id"], name="fk_route_time_destination_org", ondelete="RESTRICT"),
        db.CheckConstraint("transport_mode IN ('road','rail','sea','air','multimodal_transfer','customs_handling')", name="ck_route_time_mode"),
        db.CheckConstraint("origin_location_id <> destination_location_id OR COALESCE(origin_point_id,0) <> COALESCE(destination_point_id,0)", name="ck_route_time_distinct"),
    )
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, default=lambda: str(uuid4()))
    organization_id = db.Column(BIGINT, db.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=False)
    origin_location_id = db.Column(BIGINT, db.ForeignKey("canonical_location.id", ondelete="RESTRICT"), nullable=False)
    destination_location_id = db.Column(BIGINT, db.ForeignKey("canonical_location.id", ondelete="RESTRICT"), nullable=False)
    origin_point_id = db.Column(BIGINT)
    destination_point_id = db.Column(BIGINT)
    origin_snapshot = db.Column(db.JSON, nullable=False)
    destination_snapshot = db.Column(db.JSON, nullable=False)
    transport_mode = db.Column(db.String(32), nullable=False)
    actor_user_id = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False)
    recorded_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


db.Index("uq_route_time_key", OrganizationRouteTime.organization_id,
    OrganizationRouteTime.origin_location_id, OrganizationRouteTime.destination_location_id,
    db.func.coalesce(OrganizationRouteTime.origin_point_id, 0),
    db.func.coalesce(OrganizationRouteTime.destination_point_id, 0), OrganizationRouteTime.transport_mode, unique=True)


class OrganizationRouteTimeVersion(db.Model):
    __tablename__ = "organization_route_time_version"
    __table_args__ = (
        db.UniqueConstraint("public_id", name="uq_route_time_version_public"),
        db.UniqueConstraint("id", "organization_id", name="uq_route_time_version_id_org"),
        db.UniqueConstraint("reference_id", "version", name="uq_route_time_version"),
        db.UniqueConstraint("reference_id", "effective_from", name="uq_route_time_effective"),
        db.ForeignKeyConstraint(["reference_id", "organization_id"], ["organization_route_time.id", "organization_route_time.organization_id"], name="fk_route_time_version_org", ondelete="RESTRICT"),
        db.CheckConstraint("version >= 1", name="ck_route_time_version_positive"),
        db.CheckConstraint("(movement_min_minutes IS NULL AND movement_max_minutes IS NULL) OR (movement_min_minutes IS NOT NULL AND movement_max_minutes IS NOT NULL AND movement_min_minutes >= 1 AND movement_max_minutes >= movement_min_minutes AND movement_max_minutes <= 525600)", name="ck_route_time_movement_range"),
        db.CheckConstraint("(stop_min_minutes IS NULL AND stop_max_minutes IS NULL) OR (stop_min_minutes IS NOT NULL AND stop_max_minutes IS NOT NULL AND stop_min_minutes >= 0 AND stop_max_minutes >= stop_min_minutes AND stop_max_minutes <= 525600)", name="ck_route_time_stop_range"),
        db.CheckConstraint("movement_min_minutes IS NOT NULL OR stop_min_minutes IS NOT NULL", name="ck_route_time_defined"),
    )
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, default=lambda: str(uuid4()))
    organization_id = db.Column(BIGINT, db.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=False)
    reference_id = db.Column(BIGINT, nullable=False)
    version = db.Column(db.Integer, nullable=False)
    movement_min_minutes = db.Column(db.Integer)
    movement_max_minutes = db.Column(db.Integer)
    stop_min_minutes = db.Column(db.Integer)
    stop_max_minutes = db.Column(db.Integer)
    effective_from = db.Column(db.DateTime(timezone=True), nullable=False)
    actor_user_id = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False)
    recorded_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class RouteLegTimeBasis(db.Model):
    __tablename__ = "route_leg_time_basis"
    __table_args__ = (
        db.UniqueConstraint("public_id", name="uq_route_time_basis_public"),
        db.UniqueConstraint("route_leg_id", "selection_revision", name="uq_route_time_basis_revision"),
        db.CheckConstraint("selection_revision >= 1", name="ck_route_time_basis_revision"),
        db.ForeignKeyConstraint(["operational_shipment_id", "organization_id"], ["operational_shipment.id", "operational_shipment.organization_id"], name="fk_route_time_basis_shipment", ondelete="RESTRICT"),
        db.ForeignKeyConstraint(["route_plan_id", "operational_shipment_id"], ["route_plan.id", "route_plan.operational_shipment_id"], name="fk_route_time_basis_plan", ondelete="RESTRICT"),
        db.ForeignKeyConstraint(["route_leg_id", "route_plan_id"], ["route_leg.id", "route_leg.route_plan_id"], name="fk_route_time_basis_leg", ondelete="RESTRICT"),
        db.ForeignKeyConstraint(["reference_version_id", "organization_id"], ["organization_route_time_version.id", "organization_route_time_version.organization_id"], name="fk_route_time_basis_version", ondelete="RESTRICT"),
    )
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, default=lambda: str(uuid4()))
    organization_id = db.Column(BIGINT, db.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=False)
    operational_shipment_id = db.Column(BIGINT, nullable=False)
    route_plan_id = db.Column(BIGINT, nullable=False)
    route_leg_id = db.Column(BIGINT, nullable=False)
    reference_version_id = db.Column(BIGINT, nullable=False)
    selection_revision = db.Column(db.Integer, nullable=False)
    leg_basis = db.Column(db.JSON, nullable=False)
    reference_at = db.Column(db.DateTime(timezone=True), nullable=False)
    actor_user_id = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False)
    recorded_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


def _immutable(_mapper, _connection, target):
    if any(inspect(target).attrs[column.key].history.has_changes() for column in target.__table__.columns):
        raise ValueError("Route reference time history is immutable; append a version or selection")


def _no_delete(_mapper, _connection, _target):
    raise ValueError("Route reference time history cannot be deleted")


for _model in (OrganizationRouteTime, OrganizationRouteTimeVersion, RouteLegTimeBasis):
    event.listen(_model, "before_update", _immutable)
    event.listen(_model, "before_delete", _no_delete)
