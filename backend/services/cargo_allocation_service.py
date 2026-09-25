"""P3-05 commands and read projection on the canonical execution allocation SOR."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json

from sqlalchemy import select

from backend.cargo_models import (
    CargoAllocationRevision,
    CargoAllocationTransfer,
    ExecutionUnitCargoAllocation,
    ShipmentCargoItem,
)
from backend.extensions import db
from backend.models import Customer, ExpertUser
from backend.operational_models import (
    ExecutionTransportRevision,
    OperationalShipment,
    RouteCargoDestination,
    RouteLeg,
    RouteStageExecution,
    utcnow,
)
from backend.services.assigned_work_authorization import authorize_document_management
from backend.services.operational_service import OperationalError, require_permission, scoped_shipment


ZERO = Decimal("0")


def _fail(code: str, message: str, status: int = 422):
    raise OperationalError(code, message, status)


def _payload_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _key(value: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > 100:
        _fail("IDEMPOTENCY_KEY_REQUIRED", "A valid Idempotency-Key header is required.", 400)
    return value.strip()


def _quantity(value, *, allow_zero=False) -> Decimal:
    if isinstance(value, bool) or value in (None, ""):
        _fail("INVALID_QUANTITY", "Quantity must be a valid non-negative decimal.")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        _fail("INVALID_QUANTITY", "Quantity must be a valid non-negative decimal.")
    if not result.is_finite() or result < 0 or (result == 0 and not allow_zero) or result.as_tuple().exponent < -6 or result > Decimal("999999999999.999999"):
        _fail("INVALID_QUANTITY", "Quantity has invalid sign or precision.")
    return result


def _instant(value):
    if value in (None, ""):
        return utcnow()
    if not isinstance(value, str):
        _fail("INVALID_TIME", "occurred_at must be an ISO-8601 timestamp with timezone.")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        _fail("INVALID_TIME", "occurred_at must be an ISO-8601 timestamp with timezone.")
    if result.tzinfo is None:
        _fail("INVALID_TIME", "occurred_at must include a timezone.")
    return result.astimezone(timezone.utc)


def _reason(value, *, field="reason", limit=500):
    if value is None:
        return None
    if not isinstance(value, str) or len(value.strip()) > limit:
        _fail("VALIDATION_FAILED", f"{field} must be short text.")
    return value.strip() or None


def _shipment(shipment_public_id: str, user: dict, *, write=False) -> OperationalShipment:
    shipment = scoped_shipment(shipment_public_id, user)
    require_permission(user, "operational_shipment.create" if write else "operational_shipment.read")
    if write and not authorize_document_management(user, shipment).allowed:
        _fail("OWNING_TRANSPORT_EXPERT_REQUIRED", "Only the owning Transport Expert may change Cargo allocation.", 403)
    return shipment


def _cargo(shipment: OperationalShipment, cargo_public_id: str, *, lock=False) -> ShipmentCargoItem:
    query = select(ShipmentCargoItem).where(
        ShipmentCargoItem.public_id == cargo_public_id,
        ShipmentCargoItem.operational_shipment_id == shipment.id,
    )
    if lock:
        query = query.with_for_update()
    row = db.session.scalar(query)
    if row is None:
        _fail("NOT_FOUND", "Cargo not found.", 404)
    return row


def _cargo_owner(cargo: ShipmentCargoItem, shipment: OperationalShipment):
    owner = db.session.get(Customer, cargo.cargo_owner_customer_id) if cargo.cargo_owner_customer_id else None
    if owner is None or owner.operational_organization_id != shipment.organization_id:
        _fail("CARGO_OWNER_REQUIRED", "Cargo owner must belong to this organization.", 409)


def _stage(shipment: OperationalShipment, public_id: str) -> RouteStageExecution:
    row = db.session.scalar(select(RouteStageExecution).where(
        RouteStageExecution.public_id == public_id,
        RouteStageExecution.operational_shipment_id == shipment.id,
        RouteStageExecution.organization_id == shipment.organization_id,
    ))
    if row is None:
        _fail("NOT_FOUND", "Route-stage execution not found.", 404)
    unit = row.execution_unit
    if (unit is None or unit.organization_id != shipment.organization_id
            or unit.operational_shipment_id != shipment.id
            or unit.unit_type != "transport_execution"
            or row.route_leg is None or row.route_leg.route_plan_id != row.route_plan_id):
        _fail("CARGO_STAGE_MISMATCH", "Route-stage execution has invalid Shipment or unit scope.", 409)
    if db.session.scalar(select(ExecutionTransportRevision.id).where(
            ExecutionTransportRevision.execution_unit_id == unit.id).limit(1)) is None:
        _fail("EXECUTION_REVISION_REQUIRED", "A recorded transport execution is required.", 409)
    return row


def _branch_covers(cargo: ShipmentCargoItem, stage: RouteStageExecution):
    destination = db.session.scalar(select(RouteCargoDestination).where(
        RouteCargoDestination.route_plan_id == stage.route_plan_id,
        RouteCargoDestination.operational_shipment_id == cargo.operational_shipment_id,
        RouteCargoDestination.shipment_cargo_item_id == cargo.id,
    ))
    if destination is None:
        _fail("CARGO_ROUTE_REQUIRED", "Cargo has no route branch in this plan.", 409)
    leg_id = destination.destination_route_leg_id
    seen = set()
    while leg_id is not None and leg_id not in seen:
        if leg_id == stage.route_leg_id:
            return
        seen.add(leg_id)
        leg = db.session.get(RouteLeg, leg_id)
        leg_id = leg.parent_route_leg_id if leg and leg.route_plan_id == stage.route_plan_id else None
    _fail("CARGO_STAGE_MISMATCH", "This stage is not on the Cargo route branch.", 409)


def _current(cargo_id: int, stage_id: int, dimension: str, *, lock=False):
    query = select(ExecutionUnitCargoAllocation).where(
        ExecutionUnitCargoAllocation.shipment_cargo_item_id == cargo_id,
        ExecutionUnitCargoAllocation.route_stage_execution_id == stage_id,
        ExecutionUnitCargoAllocation.dimension == dimension,
        ExecutionUnitCargoAllocation.is_current.is_(True),
    )
    if lock:
        query = query.with_for_update()
    return db.session.scalar(query)


def _assert_allocation_scope(row: ExecutionUnitCargoAllocation | None, stage: RouteStageExecution):
    if row is not None and (row.execution_unit_id != stage.execution_unit_id
                            or row.operational_shipment_id != stage.operational_shipment_id):
        _fail("CARGO_STAGE_MISMATCH", "Allocation does not belong to this exact Shipment stage.", 409)


def _revision(row, shipment, before, after, action, user, key, request_hash, occurred_at, reason, transfer=None):
    db.session.add(CargoAllocationRevision(
        organization_id=shipment.organization_id,
        shipment_cargo_item_id=row.shipment_cargo_item_id,
        allocation_id=row.id,
        revision_number=row.version,
        action=action,
        before_quantity=before,
        after_quantity=after,
        occurred_at=occurred_at,
        recorded_by_user_id=int(user["id"]),
        reason=reason,
        transfer_id=transfer.id if transfer else None,
        idempotency_key=key,
        request_hash=request_hash,
    ))


def _replay(shipment, key, request_hash):
    old = db.session.scalar(select(CargoAllocationRevision).where(
        CargoAllocationRevision.organization_id == shipment.organization_id,
        CargoAllocationRevision.idempotency_key == key,
    ))
    if old is None:
        return None
    if old.request_hash != request_hash:
        _fail("IDEMPOTENCY_CONFLICT", "Idempotency key was used for a different command.", 409)
    return db.session.get(ExecutionUnitCargoAllocation, old.allocation_id)


def set_allocation(shipment_public_id: str, cargo_public_id: str, stage_public_id: str, payload: dict, user: dict, idempotency_key: str):
    """Create/revise/correct/release one stage distribution row, caller commits."""
    shipment = _shipment(shipment_public_id, user, write=True)
    key = _key(idempotency_key)
    dimension = payload.get("dimension")
    if dimension not in ("PLANNED", "ACTUAL"):
        _fail("INVALID_DIMENSION", "dimension must be PLANNED or ACTUAL.")
    request_hash = _payload_hash({"operation": "set", "shipment": shipment_public_id, "cargo": cargo_public_id, "stage": stage_public_id, "payload": payload})
    replay = _replay(shipment, key, request_hash)
    if replay is not None:
        return replay, True
    # A Cargo row serializes all allocations and transfers of this physical Cargo.
    cargo = _cargo(shipment, cargo_public_id, lock=True)
    _cargo_owner(cargo, shipment)
    replay = _replay(shipment, key, request_hash)
    if replay is not None:
        return replay, True
    stage = _stage(shipment, stage_public_id)
    _branch_covers(cargo, stage)
    quantity = _quantity(payload.get("quantity"), allow_zero=True)
    reason = _reason(payload.get("reason"))
    occurred_at = _instant(payload.get("occurred_at"))
    row = _current(cargo.id, stage.id, dimension, lock=True)
    _assert_allocation_scope(row, stage)
    try:
        expected = int(payload.get("expected_version", -1))
    except (ValueError, TypeError):
        expected = -1
    if isinstance(payload.get("expected_version"), bool) or expected != (row.version if row else 0):
        _fail("VERSION_CONFLICT", "Allocation changed; reload and retry.", 409)
    if row is None and quantity == ZERO:
        _fail("INVALID_QUANTITY", "There is no current allocation to release.")
    if row is None:
        row = ExecutionUnitCargoAllocation(
            execution_unit_id=stage.execution_unit_id,
            route_stage_execution_id=stage.id,
            dimension=dimension,
            shipment_cargo_item_id=cargo.id,
            operational_shipment_id=shipment.id,
            project_id=shipment.project_id,
            allocated_quantity=quantity,
            is_current=True,
            version=1,
            created_by=int(user["id"]),
            updated_by=int(user["id"]),
        )
        db.session.add(row)
        db.session.flush()
        before = ZERO
        action = "CREATE"
    else:
        before = row.allocated_quantity
        if before == quantity:
            return row, False
        row.version += 1
        row.updated_by = int(user["id"])
        if quantity == ZERO:
            row.is_current = False
            action = "RELEASE"
        else:
            row.allocated_quantity = quantity
            action = "PLAN_REVISION" if dimension == "PLANNED" else "ACTUAL_CORRECTION"
        db.session.flush()
    _revision(row, shipment, before, quantity, action, user, key, request_hash, occurred_at, reason)
    return row, False


def _downstream(source: RouteStageExecution, target: RouteStageExecution):
    if source.route_plan_id != target.route_plan_id:
        _fail("STAGE_RELATIONSHIP_INVALID", "Transfer stages must share an exact route plan.", 409)
    if source.route_leg_id == target.route_leg_id:
        return False
    leg_id = target.route_leg_id
    seen = set()
    while leg_id is not None and leg_id not in seen:
        if leg_id == source.route_leg_id:
            return True
        seen.add(leg_id)
        leg = db.session.get(RouteLeg, leg_id)
        leg_id = leg.parent_route_leg_id if leg and leg.route_plan_id == source.route_plan_id else None
    _fail("STAGE_RELATIONSHIP_INVALID", "Target is not downstream on the same route branch.", 409)


def transfer(shipment_public_id: str, cargo_public_id: str, payload: dict, user: dict, idempotency_key: str):
    """Move within a stage; across stages, record a handoff without erasing prior-stage actual."""
    shipment = _shipment(shipment_public_id, user, write=True)
    key = _key(idempotency_key)
    request_hash = _payload_hash({"operation": "transfer", "shipment": shipment_public_id, "cargo": cargo_public_id, "payload": payload})
    existing = db.session.scalar(select(CargoAllocationTransfer).where(
        CargoAllocationTransfer.organization_id == shipment.organization_id,
        CargoAllocationTransfer.idempotency_key == key,
    ))
    if existing:
        if existing.request_hash != request_hash:
            _fail("IDEMPOTENCY_CONFLICT", "Idempotency key was used for a different transfer.", 409)
        return existing, True
    cargo = _cargo(shipment, cargo_public_id, lock=True)
    _cargo_owner(cargo, shipment)
    existing = db.session.scalar(select(CargoAllocationTransfer).where(
        CargoAllocationTransfer.organization_id == shipment.organization_id,
        CargoAllocationTransfer.idempotency_key == key,
    ))
    if existing:
        if existing.request_hash != request_hash:
            _fail("IDEMPOTENCY_CONFLICT", "Idempotency key was used for a different transfer.", 409)
        return existing, True
    source_stage = _stage(shipment, str(payload.get("source_stage_execution_public_id", "")))
    target_stage = _stage(shipment, str(payload.get("target_stage_execution_public_id", "")))
    if source_stage.id == target_stage.id:
        _fail("STAGE_RELATIONSHIP_INVALID", "Source and target executions must differ.", 409)
    _branch_covers(cargo, source_stage)
    _branch_covers(cargo, target_stage)
    cross_stage = _downstream(source_stage, target_stage)
    quantity = _quantity(payload.get("quantity"))
    occurred_at = _instant(payload.get("occurred_at"))
    reason = _reason(payload.get("reason"))
    context = _reason(payload.get("context"), field="context", limit=300)
    # Lock current rows in deterministic primary-key order after locking Cargo.
    rows = db.session.scalars(select(ExecutionUnitCargoAllocation).where(
        ExecutionUnitCargoAllocation.shipment_cargo_item_id == cargo.id,
        ExecutionUnitCargoAllocation.route_stage_execution_id.in_((source_stage.id, target_stage.id)),
        ExecutionUnitCargoAllocation.dimension == "ACTUAL",
        ExecutionUnitCargoAllocation.is_current.is_(True),
    ).order_by(ExecutionUnitCargoAllocation.id).with_for_update()).all()
    by_stage = {row.route_stage_execution_id: row for row in rows}
    source = by_stage.get(source_stage.id)
    target = by_stage.get(target_stage.id)
    _assert_allocation_scope(source, source_stage)
    _assert_allocation_scope(target, target_stage)
    if source is None or source.allocated_quantity < quantity:
        _fail("TRANSFER_SOURCE_INSUFFICIENT", "Source has less recorded actual quantity than the transfer.", 409)
    for field, row in (("expected_source_version", source), ("expected_target_version", target)):
        try:
            expected = int(payload.get(field, -1))
        except (ValueError, TypeError):
            expected = -1
        if isinstance(payload.get(field), bool) or expected != (row.version if row else 0):
            _fail("VERSION_CONFLICT", "Allocation changed; reload and retry.", 409)
    if target is None:
        target_before = ZERO
        target = ExecutionUnitCargoAllocation(
            execution_unit_id=target_stage.execution_unit_id,
            route_stage_execution_id=target_stage.id,
            dimension="ACTUAL",
            shipment_cargo_item_id=cargo.id,
            operational_shipment_id=shipment.id,
            project_id=shipment.project_id,
            allocated_quantity=quantity,
            is_current=True,
            version=1,
            created_by=int(user["id"]),
            updated_by=int(user["id"]),
        )
        db.session.add(target)
    else:
        target_before = target.allocated_quantity
        target.allocated_quantity += quantity
        target.version += 1
        target.updated_by = int(user["id"])
    source_before = source.allocated_quantity
    if cross_stage:
        source_after = source_before
        source.version += 1
    else:
        source_after = source_before - quantity
        source.version += 1
        if source_after == ZERO:
            source.is_current = False
        else:
            source.allocated_quantity = source_after
    source.updated_by = int(user["id"])
    db.session.flush()
    movement = CargoAllocationTransfer(
        organization_id=shipment.organization_id,
        shipment_cargo_item_id=cargo.id,
        source_allocation_id=source.id,
        target_allocation_id=target.id,
        quantity=quantity,
        occurred_at=occurred_at,
        recorded_by_user_id=int(user["id"]),
        context=context,
        reason=reason,
        idempotency_key=key,
        request_hash=request_hash,
    )
    db.session.add(movement)
    db.session.flush()
    _revision(source, shipment, source_before, source_after, "HANDOFF_OUT" if cross_stage else "TRANSFER_OUT", user, hashlib.sha256(f"{key}:source".encode()).hexdigest(), request_hash, occurred_at, reason, movement)
    _revision(target, shipment, target_before, target_before + quantity, "HANDOFF_IN" if cross_stage else "TRANSFER_IN", user, hashlib.sha256(f"{key}:target".encode()).hexdigest(), request_hash, occurred_at, reason, movement)
    return movement, False


def _allocation_view(row):
    return {
        "public_id": row.public_id,
        "stage_execution_public_id": row.route_stage_execution.public_id if row.route_stage_execution else None,
        "execution_unit_public_id": row.execution_unit.public_id,
        "dimension": row.dimension,
        "quantity": str(row.allocated_quantity if row.is_current else ZERO),
        "version": row.version,
        "current": row.is_current,
    }


def trace(shipment_public_id: str, cargo_public_id: str, user: dict):
    shipment = _shipment(shipment_public_id, user)
    cargo = _cargo(shipment, cargo_public_id)
    rows = db.session.scalars(select(ExecutionUnitCargoAllocation).where(
        ExecutionUnitCargoAllocation.shipment_cargo_item_id == cargo.id,
        ExecutionUnitCargoAllocation.route_stage_execution_id.is_not(None),
    ).order_by(ExecutionUnitCargoAllocation.id)).all()
    revisions = db.session.scalars(select(CargoAllocationRevision).where(
        CargoAllocationRevision.shipment_cargo_item_id == cargo.id,
        CargoAllocationRevision.organization_id == shipment.organization_id,
    ).order_by(CargoAllocationRevision.recorded_at, CargoAllocationRevision.id)).all()
    transfers = db.session.scalars(select(CargoAllocationTransfer).where(
        CargoAllocationTransfer.shipment_cargo_item_id == cargo.id,
        CargoAllocationTransfer.organization_id == shipment.organization_id,
    ).order_by(CargoAllocationTransfer.recorded_at, CargoAllocationTransfer.id)).all()
    stages = db.session.scalars(select(RouteStageExecution).where(
        RouteStageExecution.operational_shipment_id == shipment.id,
        RouteStageExecution.organization_id == shipment.organization_id,
    ).join(RouteLeg, RouteLeg.id == RouteStageExecution.route_leg_id).order_by(RouteStageExecution.route_plan_id, RouteLeg.sequence_number, RouteStageExecution.id)).all()
    grouped = {}
    for stage in stages:
        try:
            _branch_covers(cargo, stage)
        except OperationalError:
            continue
        leg = stage.route_leg
        grouped.setdefault((stage.route_plan_id, leg.id), {"route_plan_id": stage.route_plan_id, "route_leg_id": leg.id, "sequence_number": leg.sequence_number, "origin": leg.origin_snapshot, "destination": leg.destination_snapshot, "executions": [], "planned_total": ZERO, "actual_total": ZERO, "planned_recorded": False, "actual_recorded": False})
        revision = db.session.scalar(select(ExecutionTransportRevision).where(ExecutionTransportRevision.execution_unit_id == stage.execution_unit_id).order_by(ExecutionTransportRevision.revision_number.desc()).limit(1))
        allocations = [_allocation_view(row) for row in rows if row.route_stage_execution_id == stage.id and row.is_current]
        for row in rows:
            if row.route_stage_execution_id != stage.id or not row.is_current:
                continue
            grouped[(stage.route_plan_id, leg.id)]["planned_total" if row.dimension == "PLANNED" else "actual_total"] += row.allocated_quantity
            grouped[(stage.route_plan_id, leg.id)]["planned_recorded" if row.dimension == "PLANNED" else "actual_recorded"] = True
        grouped[(stage.route_plan_id, leg.id)]["executions"].append({
            "stage_execution_public_id": stage.public_id,
            "execution_unit_public_id": stage.execution_unit.public_id,
            "unit_code": stage.execution_unit.unit_code,
            "means": revision.means_type_fa_snapshot if revision else None,
            "means_identifier": revision.means_identifier if revision else None,
            "equipment": [{"type": equipment.equipment_type_fa_snapshot, "identifier": equipment.identifier} for equipment in revision.equipment] if revision else [],
            "allocations": allocations,
        })
    stage_views = []
    previous_actual = None
    previous_plan = None
    for stage in grouped.values():
        if previous_plan != stage["route_plan_id"]:
            previous_actual = None
            previous_plan = stage["route_plan_id"]
        planned, actual = stage.pop("planned_total"), stage.pop("actual_total")
        warnings = []
        if cargo.planned_quantity is not None and stage["planned_recorded"] and planned != cargo.planned_quantity:
            warnings.append({"code": "PLAN_UNDER" if planned < cargo.planned_quantity else "PLAN_OVER", "difference": str(abs(planned - cargo.planned_quantity))})
        if stage["planned_recorded"] and stage["actual_recorded"] and planned != actual:
            warnings.append({"code": "ACTUAL_VS_PLAN", "difference": str(actual - planned)})
        elif cargo.planned_quantity is not None and stage["actual_recorded"] and actual != cargo.planned_quantity:
            warnings.append({"code": "ACTUAL_VS_CARGO_PLAN", "difference": str(actual - cargo.planned_quantity)})
        if cargo.actual_quantity is not None and stage["actual_recorded"] and actual != cargo.actual_quantity:
            warnings.append({"code": "ACTUAL_VS_KNOWN", "difference": str(actual - cargo.actual_quantity)})
        if previous_actual is not None and stage["actual_recorded"] and actual != previous_actual:
            warnings.append({"code": "STAGE_CONTINUITY", "difference": str(actual - previous_actual)})
        if stage["actual_recorded"]:
            previous_actual = actual
        stage.update({
            "planned_total": str(planned), "actual_total": str(actual),
            "planned_remaining": str(cargo.planned_quantity - planned) if cargo.planned_quantity is not None else None,
            "actual_unrecorded": str(cargo.actual_quantity - actual) if cargo.actual_quantity is not None else None,
            "warnings": warnings,
        })
        stage_views.append(stage)
    return {
        "cargo": {"public_id": cargo.public_id, "name": cargo.display_name_snapshot, "requested_quantity": str(cargo.requested_quantity) if cargo.requested_quantity is not None else None, "planned_quantity": str(cargo.planned_quantity) if cargo.planned_quantity is not None else None, "actual_quantity": str(cargo.actual_quantity) if cargo.actual_quantity is not None else None, "uom": cargo.uom_symbol_snapshot},
        "stages": stage_views,
        "legacy_allocations": [_allocation_view(row) for row in db.session.scalars(select(ExecutionUnitCargoAllocation).where(ExecutionUnitCargoAllocation.shipment_cargo_item_id == cargo.id, ExecutionUnitCargoAllocation.route_stage_execution_id.is_(None), ExecutionUnitCargoAllocation.is_current.is_(True))).all()],
        "history": [{"public_id": item.public_id, "allocation_public_id": db.session.get(ExecutionUnitCargoAllocation, item.allocation_id).public_id, "action": item.action, "before": str(item.before_quantity), "after": str(item.after_quantity), "recorded_at": item.recorded_at.isoformat(), "occurred_at": item.occurred_at.isoformat(), "actor_name": db.session.get(ExpertUser, item.recorded_by_user_id).full_name, "reason": item.reason, "transfer_public_id": db.session.get(CargoAllocationTransfer, item.transfer_id).public_id if item.transfer_id else None} for item in revisions],
        "transfers": [{"public_id": item.public_id, "quantity": str(item.quantity), "source_allocation_public_id": db.session.get(ExecutionUnitCargoAllocation, item.source_allocation_id).public_id, "target_allocation_public_id": db.session.get(ExecutionUnitCargoAllocation, item.target_allocation_id).public_id, "occurred_at": item.occurred_at.isoformat(), "recorded_at": item.recorded_at.isoformat(), "actor_name": db.session.get(ExpertUser, item.recorded_by_user_id).full_name, "context": item.context, "reason": item.reason} for item in transfers],
    }
