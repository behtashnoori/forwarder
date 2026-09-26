"""Explicit post-closure command boundaries; never an authorization grant.

Call only from an already authorized command. The row fence serializes a command
with closing even when its source row does not exist yet. Document repair and
independent work lifecycles deliberately do not pass through an all-write gate.
"""
from datetime import timezone
from sqlalchemy import or_, select
from backend.extensions import db
from backend.closure_models import ClosureDecision
from backend.operational_models import OperationalShipment, RouteStageExecution


def current(shipment):
    with db.session.no_autoflush:
        return db.session.scalar(select(OperationalShipment).where(
            OperationalShipment.id == shipment.id
        ).with_for_update().execution_options(populate_existing=True))


def _fail(code, message):
    from backend.services.operational_service import OperationalError
    raise OperationalError(code, message, 409)


def deny_new(shipment):
    if current(shipment).lifecycle_status == "closed":
        _fail("SHIPMENT_CLOSED", "پرونده بسته شده است؛ عملیات تازه مجاز نیست.")


def prior_fact(shipment, occurred_at):
    if current(shipment).lifecycle_status != "closed":
        return
    decision = db.session.scalar(select(ClosureDecision).where(
        ClosureDecision.operational_shipment_id == shipment.id))
    def aware(value):
        return value.replace(tzinfo=timezone.utc) if value and value.tzinfo is None else value
    if decision is None or occurred_at is None or aware(occurred_at) > aware(decision.occurred_at):
        _fail("POST_CLOSURE_PRIOR_FACT_REQUIRED", "پس از بستن فقط واقعیت مربوط به زمان پیش از بستن قابل ثبت است.")


def correction(shipment, reason):
    if current(shipment).lifecycle_status == "closed" and not (isinstance(reason, str) and reason.strip()):
        _fail("POST_CLOSURE_CORRECTION_REASON_REQUIRED", "دلیل اصلاح سابقهٔ پرونده بسته‌شده الزامی است.")


def unit_shipments(unit):
    # Include both legacy direct ownership and every stage sharing this unit.
    from backend.cargo_models import ExecutionUnitCargoAllocation
    stages = select(RouteStageExecution.operational_shipment_id).where(RouteStageExecution.execution_unit_id == unit.id)
    allocations = select(ExecutionUnitCargoAllocation.operational_shipment_id).where(ExecutionUnitCargoAllocation.execution_unit_id == unit.id)
    return db.session.scalars(select(OperationalShipment).where(or_(
        OperationalShipment.id == unit.operational_shipment_id,
        OperationalShipment.id.in_(stages), OperationalShipment.id.in_(allocations)
    )).order_by(OperationalShipment.id).with_for_update().execution_options(populate_existing=True)).all()


def unit_new(unit):
    for shipment in unit_shipments(unit):
        deny_new(shipment)


def unit_prior_fact(unit, occurred_at, reason=None, require_reason=False):
    for shipment in unit_shipments(unit):
        prior_fact(shipment, occurred_at)
        if require_reason:
            correction(shipment, reason)
