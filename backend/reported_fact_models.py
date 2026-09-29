"""Typed context and explicit impacts for the existing OperationalEvent SOR."""
from sqlalchemy import event

from backend.extensions import db
from backend.operational_models import BIGINT

REPORTED_EVENT_TYPE = "phase3_reported_fact"
SOURCES = {
    "CARRIER_REPORT": "گزارش شرکت حمل", "DRIVER_REPORT": "گزارش راننده",
    "INTERNAL_EXPERT": "ثبت کارشناس", "OTHER_OPERATIONAL_SOURCE": "منبع عملیاتی دیگر",
}
KINDS = {"LOCATION": "گزارش موقعیت", "PROGRESS": "گزارش پیشرفت",
         "TRANSPORT_CHANGE": "تغییر حمل", "EFFECT": "اثر عملیاتی"}
SCOPES = {"SHIPMENT": "پرونده حمل", "ROUTE_STAGE": "مرحله مسیر",
          "EXECUTION_UNIT": "اجرای حمل", "CARGO": "کالا"}
SCOPE_CHECK = (
    "(scope = 'SHIPMENT' AND route_plan_id IS NULL AND route_leg_id IS NULL AND execution_unit_id IS NULL AND cargo_item_id IS NULL) OR "
    "(scope = 'ROUTE_STAGE' AND route_plan_id IS NOT NULL AND route_leg_id IS NOT NULL AND execution_unit_id IS NULL AND cargo_item_id IS NULL) OR "
    "(scope = 'EXECUTION_UNIT' AND route_plan_id IS NULL AND route_leg_id IS NULL AND execution_unit_id IS NOT NULL AND cargo_item_id IS NULL) OR "
    "(scope = 'CARGO' AND route_plan_id IS NULL AND route_leg_id IS NULL AND execution_unit_id IS NULL AND cargo_item_id IS NOT NULL)"
)


class OperationalEventReportContext(db.Model):
    __tablename__ = "operational_event_report_context"
    __table_args__ = (
        db.UniqueConstraint("operational_event_id", "operational_shipment_id", name="uq_report_event_shipment"),
        db.ForeignKeyConstraint(["operational_event_id", "organization_id"],
            ["operational_event.id", "operational_event.organization_id"], name="fk_report_event_org", ondelete="RESTRICT"),
        db.ForeignKeyConstraint(["operational_shipment_id", "organization_id"],
            ["operational_shipment.id", "operational_shipment.organization_id"], name="fk_report_shipment_org", ondelete="RESTRICT"),
        db.ForeignKeyConstraint(["route_plan_id", "operational_shipment_id"],
            ["route_plan.id", "route_plan.operational_shipment_id"], name="fk_report_plan_shipment", ondelete="RESTRICT"),
        db.ForeignKeyConstraint(["route_leg_id", "route_plan_id"],
            ["route_leg.id", "route_leg.route_plan_id"], name="fk_report_leg_plan", ondelete="RESTRICT"),
        db.ForeignKeyConstraint(["execution_unit_id", "organization_id"],
            ["execution_unit.id", "execution_unit.organization_id"], name="fk_report_unit_org", ondelete="RESTRICT"),
        db.ForeignKeyConstraint(["operational_event_id", "execution_unit_id"],
            ["operational_event.id", "operational_event.execution_unit_id"], name="fk_report_event_unit", ondelete="RESTRICT"),
        db.ForeignKeyConstraint(["cargo_item_id", "operational_shipment_id"],
            ["shipment_cargo_item.id", "shipment_cargo_item.operational_shipment_id"], name="fk_report_cargo_shipment", ondelete="RESTRICT"),
        db.CheckConstraint(SCOPE_CHECK, name="ck_report_exact_scope"),
        db.CheckConstraint("kind IN ('LOCATION','PROGRESS','TRANSPORT_CHANGE','EFFECT')", name="ck_report_kind"),
        db.CheckConstraint("customer_effect IN ('CHANGE','DELAY')", name="ck_report_customer_effect"),
        db.Index("ix_report_shipment_event", "operational_shipment_id", "operational_event_id"),
    )
    operational_event_id = db.Column(BIGINT, db.ForeignKey("operational_event.id", ondelete="RESTRICT"), primary_key=True)
    organization_id = db.Column(BIGINT, nullable=False)
    operational_shipment_id = db.Column(BIGINT, nullable=False)
    scope = db.Column(db.String(24), nullable=False)
    route_plan_id = db.Column(BIGINT)
    route_leg_id = db.Column(BIGINT)
    execution_unit_id = db.Column(BIGINT)
    cargo_item_id = db.Column(BIGINT)
    kind = db.Column(db.String(24), nullable=False)
    customer_effect = db.Column(db.String(12), nullable=False)
    correction_reason = db.Column(db.String(500))
    event = db.relationship("OperationalEvent", foreign_keys=[operational_event_id], lazy="joined")


class OperationalEventCargoImpact(db.Model):
    __tablename__ = "operational_event_cargo_impact"
    __table_args__ = (
        db.ForeignKeyConstraint(["operational_event_id", "operational_shipment_id"],
            ["operational_event_report_context.operational_event_id", "operational_event_report_context.operational_shipment_id"],
            name="fk_report_impact_context_shipment", ondelete="RESTRICT"),
        db.ForeignKeyConstraint(["cargo_item_id", "operational_shipment_id"],
            ["shipment_cargo_item.id", "shipment_cargo_item.operational_shipment_id"],
            name="fk_report_impact_cargo_shipment", ondelete="RESTRICT"),
    )
    operational_event_id = db.Column(BIGINT, primary_key=True)
    cargo_item_id = db.Column(BIGINT, primary_key=True)
    operational_shipment_id = db.Column(BIGINT, nullable=False)


class OperationalEventRouteProgress(db.Model):
    """One immutable measurable progress fact on one exact route-stage execution."""

    __tablename__ = "operational_event_route_progress"
    __table_args__ = (
        db.ForeignKeyConstraint(
            ["operational_event_id", "organization_id"],
            ["operational_event.id", "operational_event.organization_id"],
            name="fk_route_progress_event_org", ondelete="RESTRICT",
        ),
        db.ForeignKeyConstraint(
            ["operational_event_id", "execution_unit_id"],
            ["operational_event.id", "operational_event.execution_unit_id"],
            name="fk_route_progress_event_unit", ondelete="RESTRICT",
        ),
        db.ForeignKeyConstraint(
            ["operational_event_id", "operational_shipment_id"],
            ["operational_event_report_context.operational_event_id",
             "operational_event_report_context.operational_shipment_id"],
            name="fk_route_progress_report_context", ondelete="RESTRICT",
        ),
        db.ForeignKeyConstraint(
            ["operational_shipment_id", "organization_id"],
            ["operational_shipment.id", "operational_shipment.organization_id"],
            name="fk_route_progress_shipment_org", ondelete="RESTRICT",
        ),
        db.ForeignKeyConstraint(
            ["route_plan_id", "operational_shipment_id"],
            ["route_plan.id", "route_plan.operational_shipment_id"],
            name="fk_route_progress_plan_shipment", ondelete="RESTRICT",
        ),
        db.ForeignKeyConstraint(
            ["route_leg_id", "route_plan_id"],
            ["route_leg.id", "route_leg.route_plan_id"],
            name="fk_route_progress_leg_plan", ondelete="RESTRICT",
        ),
        db.ForeignKeyConstraint(
            ["route_stage_execution_id", "route_plan_id", "route_leg_id", "execution_unit_id"],
            ["route_stage_execution.id", "route_stage_execution.route_plan_id",
             "route_stage_execution.route_leg_id", "route_stage_execution.execution_unit_id"],
            name="fk_route_progress_exact_stage", ondelete="RESTRICT",
        ),
        db.ForeignKeyConstraint(
            ["route_leg_time_basis_id", "route_leg_id", "organization_id"],
            ["route_leg_time_basis.id", "route_leg_time_basis.route_leg_id",
             "route_leg_time_basis.organization_id"],
            name="fk_route_progress_exact_basis", ondelete="RESTRICT",
        ),
        db.CheckConstraint("progress_kind = 'DISTANCE_REMAINING_KM'", name="ck_route_progress_kind"),
        db.CheckConstraint("distance_remaining_km >= 0", name="ck_route_progress_nonnegative"),
        db.CheckConstraint(
            "planned_distance_km IS NULL OR (planned_distance_km > 0 AND distance_remaining_km <= planned_distance_km)",
            name="ck_route_progress_distance_bounds",
        ),
        db.CheckConstraint(
            "(route_leg_time_basis_id IS NULL AND planned_distance_km IS NULL) OR "
            "(route_leg_time_basis_id IS NOT NULL AND planned_distance_km IS NOT NULL)",
            name="ck_route_progress_basis_pair",
        ),
        db.Index("ix_route_progress_plan_leg_occurred", "route_plan_id", "route_leg_id", "operational_event_id"),
    )
    operational_event_id = db.Column(
        BIGINT, db.ForeignKey("operational_event.id", ondelete="RESTRICT"), primary_key=True
    )
    organization_id = db.Column(BIGINT, nullable=False)
    operational_shipment_id = db.Column(BIGINT, nullable=False)
    route_plan_id = db.Column(BIGINT, nullable=False)
    route_leg_id = db.Column(BIGINT, nullable=False)
    route_stage_execution_id = db.Column(BIGINT, nullable=False)
    execution_unit_id = db.Column(BIGINT, nullable=False)
    route_leg_time_basis_id = db.Column(BIGINT)
    progress_kind = db.Column(db.String(32), nullable=False, default="DISTANCE_REMAINING_KM")
    distance_remaining_km = db.Column(db.Numeric(12, 3), nullable=False)
    planned_distance_km = db.Column(db.Numeric(12, 3))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())


def _immutable(_mapper, _connection, _target):
    raise ValueError("reported operational facts are immutable; append a correction")


for model in (OperationalEventReportContext, OperationalEventCargoImpact, OperationalEventRouteProgress):
    event.listen(model, "before_update", _immutable)
    event.listen(model, "before_delete", _immutable)
