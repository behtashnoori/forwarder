"""Phase 1B multi-leg route-plan and checkpoint orchestration."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import heapq
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from backend.extensions import db
from backend.operational_models import (
    Milestone, MilestoneEvent, OperationalAudit, OperationalCheckpoint,
    OperationalIdempotency, OperationalOutbox, OperationalShipment,
    OperationalWorkItem, RouteDependency, RouteLeg, RoutePlan, utcnow,
)
from backend.services import operational_service as base

PLAN_PERMISSIONS = {
    "read": "route_plan.read", "create": "route_plan.create",
    "activate": "route_plan.activate", "replan": "route_plan.replan",
}
CHECKPOINT_TYPES = {
    "origin_loading", "export_customs", "border_exit", "transit_border_entry",
    "transit_border_exit", "border_entry", "import_customs", "port_entry",
    "port_exit", "terminal_arrival", "transshipment", "destination_arrival",
    "unloading", "final_delivery",
}
TRANSPORT_MODES = {"road", "rail", "sea", "air", "multimodal_transfer", "customs_handling"}
CHECKPOINT_MILESTONES = (
    ("checkpoint_arrival", "planned_arrival_at"),
    ("checkpoint_processing_complete", "planned_departure_at"),
    ("checkpoint_departure", "planned_departure_at"),
)


def _idempotency(org: int, operation: str, resource_type: str, resource_id: int, key: str, payload: dict):
    base._require_idempotency_key(key)
    request_hash = base._hash(payload)
    base._lock_idempotency_scope(org, operation, resource_type, resource_id, key)
    row = db.session.scalar(select(OperationalIdempotency).where(
        OperationalIdempotency.organization_id == org,
        OperationalIdempotency.operation == operation,
        OperationalIdempotency.resource_type == resource_type,
        OperationalIdempotency.command_resource_id == resource_id,
        OperationalIdempotency.idempotency_key == key,
    ))
    if row and row.request_hash != request_hash:
        raise base.OperationalError("IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_PAYLOAD", "Idempotency key payload differs.", 409)
    return row, request_hash


def _reserve_idempotency(org: int, operation: str, resource_type: str, resource_id: int, key: str, request_hash: str, result_id: int):
    db.session.add(OperationalIdempotency(
        organization_id=org, operation=operation, resource_type=resource_type,
        command_resource_id=resource_id, idempotency_key=key,
        request_hash=request_hash, result_resource_id=result_id,
    ))


def _synchronize_checkpoint_actual(checkpoint: OperationalCheckpoint, milestone: Milestone, occurred_at) -> None:
    """Keep checkpoint actuals derived from the currently verified milestone event."""
    milestone.occurred_at = occurred_at
    if milestone.milestone_type == "checkpoint_arrival":
        checkpoint.actual_arrival_at = occurred_at
    elif milestone.milestone_type == "checkpoint_processing_complete":
        checkpoint.status = "ready_to_depart" if occurred_at is not None else "processing"
    elif milestone.milestone_type == "checkpoint_departure":
        checkpoint.actual_departure_at = occurred_at
        checkpoint.status = "completed" if occurred_at is not None else "ready_to_depart"


def _invalidate_checkpoint_actual(checkpoint: OperationalCheckpoint, milestone: Milestone) -> None:
    """Invalidate a corrected verified value until its replacement is re-verified."""
    milestone.occurred_at = None
    if milestone.milestone_type == "checkpoint_arrival":
        checkpoint.actual_arrival_at = None
        # A departure cannot remain current when its prerequisite arrival was corrected.
        checkpoint.actual_departure_at = None
        checkpoint.status = "arrived"
    elif milestone.milestone_type == "checkpoint_processing_complete":
        checkpoint.status = "processing"
    elif milestone.milestone_type == "checkpoint_departure":
        checkpoint.actual_departure_at = None
        checkpoint.status = "ready_to_depart"


def _shipment(shipment_id: int, user: dict, permission: str) -> OperationalShipment:
    base.require_permission(user, permission)
    org = base.organization_for_user(int(user["id"]))
    row = db.session.scalar(select(OperationalShipment).where(
        OperationalShipment.id == shipment_id, OperationalShipment.organization_id == org
    ))
    if row is None:
        raise base.OperationalError("RESOURCE_NOT_FOUND", "Operational shipment was not found.", 404)
    return row


def _plan(shipment_id: int, plan_id: int, user: dict, permission: str, lock=False) -> tuple[OperationalShipment, RoutePlan]:
    shipment = _shipment(shipment_id, user, permission)
    query = select(RoutePlan).where(RoutePlan.id == plan_id, RoutePlan.operational_shipment_id == shipment.id)
    plan = db.session.scalar(query.with_for_update() if lock else query)
    if plan is None:
        raise base.OperationalError("RESOURCE_NOT_FOUND", "Route plan was not found.", 404)
    return shipment, plan


def _location(reference: Any):
    if isinstance(reference, int):
        from backend.operational_models import CanonicalLocation
        row = db.session.get(CanonicalLocation, reference)
        if row:
            return row
    return base.resolve_location(reference or {})


def _serialize_plan(plan: RoutePlan, include_children=True) -> dict:
    data = {
        "id": plan.id, "operational_shipment_id": plan.operational_shipment_id,
        "revision_number": plan.revision_number, "status": plan.status,
        "is_active": plan.is_active, "created_from_plan_id": plan.created_from_plan_id,
        "replan_reason": plan.replan_reason, "effective_at": plan.effective_at.isoformat() if plan.effective_at else None,
        "version": plan.version, "created_at": plan.created_at.isoformat(),
    }
    if include_children:
        legs = db.session.scalars(select(RouteLeg).where(RouteLeg.route_plan_id == plan.id).order_by(RouteLeg.sequence_number)).all()
        checkpoints = db.session.scalars(select(OperationalCheckpoint).where(OperationalCheckpoint.route_plan_id == plan.id).order_by(OperationalCheckpoint.sequence_number)).all()
        dependencies = db.session.scalars(select(RouteDependency).where(RouteDependency.route_plan_id == plan.id)).all()
        data["legs"] = [_serialize_leg(row) for row in legs]
        data["checkpoints"] = [_serialize_checkpoint(row) for row in checkpoints]
        data["dependencies"] = [{"id": d.id, "predecessor_checkpoint_id": d.predecessor_checkpoint_id, "successor_checkpoint_id": d.successor_checkpoint_id, "dependency_type": d.dependency_type} for d in dependencies]
    return data


def _serialize_leg(row: RouteLeg) -> dict:
    return {
        "id": row.id, "sequence_number": row.sequence_number,
        "origin": row.origin_snapshot, "destination": row.destination_snapshot,
        "transport_mode": row.transport_mode, "carrier_reference": row.carrier_reference,
        "planned_departure": row.planned_departure.isoformat(), "planned_arrival": row.planned_arrival.isoformat(),
        "projected_departure": row.projected_departure.isoformat() if row.projected_departure else None,
        "projected_arrival": row.projected_arrival.isoformat() if row.projected_arrival else None,
        "actual_departure": row.actual_departure.isoformat() if row.actual_departure else None,
        "actual_arrival": row.actual_arrival.isoformat() if row.actual_arrival else None,
        "status": row.status, "version": row.version, "source_route_leg_id": row.source_route_leg_id,
    }


def _serialize_checkpoint(row: OperationalCheckpoint) -> dict:
    milestones = db.session.scalars(select(Milestone).where(Milestone.checkpoint_id == row.id).order_by(Milestone.planned_at, Milestone.id)).all()
    return {
        "id": row.id, "route_leg_id": row.route_leg_id, "sequence_number": row.sequence_number,
        "checkpoint_type": row.checkpoint_type, "canonical_location_id": row.canonical_location_id,
        "planned_arrival_at": row.planned_arrival_at.isoformat() if row.planned_arrival_at else None,
        "planned_departure_at": row.planned_departure_at.isoformat() if row.planned_departure_at else None,
        "projected_arrival_at": row.projected_arrival_at.isoformat() if row.projected_arrival_at else None,
        "projected_departure_at": row.projected_departure_at.isoformat() if row.projected_departure_at else None,
        "actual_arrival_at": row.actual_arrival_at.isoformat() if row.actual_arrival_at else None,
        "actual_departure_at": row.actual_departure_at.isoformat() if row.actual_departure_at else None,
        "status": row.status, "verification_state": row.verification_state,
        "responsible_party": row.responsible_party, "notes": row.notes, "version": row.version,
        "source_checkpoint_id": row.source_checkpoint_id,
        "milestones": [{"id":m.id,"type":m.milestone_type,"planned_at":m.planned_at.isoformat(),
            "projected_at":m.projected_at.isoformat() if m.projected_at else None,
            "occurred_at":m.occurred_at.isoformat() if m.occurred_at else None,
            "verification_state":m.verification_state,"version":m.version,
            "source_milestone_id":m.source_milestone_id} for m in milestones],
    }


def list_plans(shipment_id: int, user: dict) -> list[dict]:
    shipment = _shipment(shipment_id, user, PLAN_PERMISSIONS["read"])
    rows = db.session.scalars(select(RoutePlan).where(RoutePlan.operational_shipment_id == shipment.id).order_by(RoutePlan.revision_number.desc())).all()
    return [_serialize_plan(row, False) for row in rows]


def get_plan(shipment_id: int, plan_id: int, user: dict) -> dict:
    _, plan = _plan(shipment_id, plan_id, user, PLAN_PERMISSIONS["read"])
    return _serialize_plan(plan)


def create_plan(shipment_id: int, payload: dict, user: dict) -> dict:
    shipment = _shipment(shipment_id, user, PLAN_PERMISSIONS["create"])
    revision = (db.session.scalar(select(func.max(RoutePlan.revision_number)).where(RoutePlan.operational_shipment_id == shipment.id)) or 0) + 1
    plan = RoutePlan(operational_shipment_id=shipment.id, revision_number=revision, status="draft", is_active=False, created_by_user_id=user["id"])
    db.session.add(plan); db.session.flush()
    for index, item in enumerate(payload.get("legs") or [], 1):
        _add_leg(plan, {**item, "sequence_number": item.get("sequence_number", index)})
    for index, item in enumerate(payload.get("checkpoints") or [], 1):
        _add_checkpoint(plan, {**item, "sequence_number": item.get("sequence_number", index)}, user)
    base._audit(shipment.organization_id, user["id"], "route_plan.created", "RoutePlan", plan.id)
    base._outbox(shipment.organization_id, "route_plan.created", "RoutePlan", plan.id)
    db.session.commit()
    return _serialize_plan(plan)


def _add_leg(plan: RoutePlan, payload: dict) -> RouteLeg:
    if plan.status != "draft":
        raise base.OperationalError("ROUTE_PLAN_NOT_DRAFT", "Only draft plans can be changed.", 409)
    mode = str(payload.get("transport_mode") or "")
    if mode not in TRANSPORT_MODES:
        raise base.OperationalError("ROUTE_PLAN_INVALID", "Unsupported transport mode.")
    origin, destination = _location(payload.get("origin") or payload.get("origin_location_id")), _location(payload.get("destination") or payload.get("destination_location_id"))
    departure = base._parse_utc(payload.get("planned_departure"), "planned_departure")
    arrival = base._parse_utc(payload.get("planned_arrival"), "planned_arrival")
    if arrival < departure:
        raise base.OperationalError("INVALID_ROUTE_TIMELINE", "Arrival cannot precede departure.")
    row = RouteLeg(route_plan_id=plan.id, sequence_number=int(payload.get("sequence_number")),
        origin_location_id=origin.id, destination_location_id=destination.id,
        origin_snapshot=base._location_snapshot(origin), destination_snapshot=base._location_snapshot(destination),
        transport_mode=mode, carrier_reference=payload.get("carrier_reference"),
        planned_departure=departure, planned_arrival=arrival, status="planned")
    db.session.add(row); db.session.flush()
    return row


def add_leg(shipment_id: int, plan_id: int, payload: dict, user: dict) -> dict:
    shipment, plan = _plan(shipment_id, plan_id, user, "route_leg.manage", True)
    row = _add_leg(plan, payload)
    base._audit(shipment.organization_id, user["id"], "route_leg.created", "RouteLeg", row.id)
    base._outbox(shipment.organization_id, "route_leg.created", "RouteLeg", row.id)
    try: db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise base.OperationalError("ROUTE_SEQUENCE_DUPLICATE", "Leg sequence already exists.", 409) from exc
    return _serialize_leg(row)


def update_leg(shipment_id: int, plan_id: int, leg_id: int, payload: dict, user: dict) -> dict:
    _, plan=_plan(shipment_id,plan_id,user,"route_leg.manage",True)
    if plan.status!="draft": raise base.OperationalError("ROUTE_PLAN_NOT_DRAFT","Only draft plans can be changed.",409)
    row=db.session.scalar(select(RouteLeg).where(RouteLeg.id==leg_id,RouteLeg.route_plan_id==plan.id).with_for_update())
    if row is None: raise base.OperationalError("RESOURCE_NOT_FOUND","Route leg was not found.",404)
    if row.version!=payload.get("expected_version"): raise base.OperationalError("STALE_ROUTE_VERSION","Route leg version is stale.",409)
    if row.actual_departure or row.actual_arrival: raise base.OperationalError("ACTUAL_DATA_IMMUTABLE","A leg with actual data cannot be structurally edited.",409)
    if "sequence_number" in payload: row.sequence_number=int(payload["sequence_number"])
    if "carrier_reference" in payload: row.carrier_reference=payload["carrier_reference"]
    row.version+=1
    try: db.session.commit()
    except IntegrityError as exc: db.session.rollback();raise base.OperationalError("ROUTE_SEQUENCE_DUPLICATE","Leg sequence already exists.",409) from exc
    return _serialize_leg(row)


def delete_leg(shipment_id: int, plan_id: int, leg_id: int, user: dict) -> None:
    _,plan=_plan(shipment_id,plan_id,user,"route_leg.manage",True)
    if plan.status!="draft": raise base.OperationalError("ROUTE_PLAN_NOT_DRAFT","Only draft plans can be changed.",409)
    row=db.session.scalar(select(RouteLeg).where(RouteLeg.id==leg_id,RouteLeg.route_plan_id==plan.id).with_for_update())
    if row is None: raise base.OperationalError("RESOURCE_NOT_FOUND","Route leg was not found.",404)
    if row.actual_departure or row.actual_arrival or db.session.scalar(select(MilestoneEvent.id).join(Milestone).where(Milestone.route_leg_id==row.id)):
        raise base.OperationalError("ACTUAL_DATA_IMMUTABLE","A leg with actual/event data cannot be deleted.",409)
    if db.session.scalar(select(OperationalCheckpoint.id).where(OperationalCheckpoint.route_leg_id==row.id)):
        raise base.OperationalError("ROUTE_PLAN_INVALID","Delete associated checkpoints before deleting the leg.",409)
    db.session.delete(row);db.session.commit()


def _add_checkpoint(plan: RoutePlan, payload: dict, user: dict) -> OperationalCheckpoint:
    kind = payload.get("checkpoint_type")
    if kind not in CHECKPOINT_TYPES:
        raise base.OperationalError("ROUTE_PLAN_INVALID", "Unsupported checkpoint type.")
    location = _location(payload.get("location") or payload.get("canonical_location_id"))
    arrival = base._parse_utc(payload["planned_arrival_at"], "planned_arrival_at") if payload.get("planned_arrival_at") else None
    departure = base._parse_utc(payload["planned_departure_at"], "planned_departure_at") if payload.get("planned_departure_at") else None
    if arrival and departure and departure < arrival:
        raise base.OperationalError("INVALID_ROUTE_TIMELINE", "Checkpoint departure cannot precede arrival.")
    leg_id = payload.get("route_leg_id")
    if leg_id is not None and db.session.scalar(select(RouteLeg.id).where(RouteLeg.id == leg_id, RouteLeg.route_plan_id == plan.id)) is None:
        raise base.OperationalError("CROSS_PLAN_REFERENCE_NOT_ALLOWED", "Checkpoint route leg must belong to the same route plan.", 409)
    row = OperationalCheckpoint(route_plan_id=plan.id, route_leg_id=leg_id,
        sequence_number=int(payload.get("sequence_number")), checkpoint_type=kind,
        canonical_location_id=location.id, planned_arrival_at=arrival, planned_departure_at=departure,
        projected_arrival_at=arrival, projected_departure_at=departure,
        responsible_party=payload.get("responsible_party"), notes=payload.get("notes"), created_by_user_id=user["id"])
    db.session.add(row); db.session.flush()
    shipment = db.session.get(OperationalShipment, plan.operational_shipment_id)
    for milestone_type, planned_field in CHECKPOINT_MILESTONES:
        planned = getattr(row, planned_field) or row.planned_arrival_at or row.planned_departure_at
        if planned:
            db.session.add(Milestone(
                organization_id=shipment.organization_id, operational_shipment_id=shipment.id,
                route_plan_id=plan.id, checkpoint_id=row.id, milestone_type=milestone_type,
                planned_at=planned, projected_at=planned,
            ))
    db.session.flush()
    return row


def add_checkpoint(shipment_id: int, plan_id: int, payload: dict, user: dict) -> dict:
    shipment, plan = _plan(shipment_id, plan_id, user, "checkpoint.report", True)
    if plan.status != "draft":
        raise base.OperationalError("ROUTE_PLAN_NOT_DRAFT", "Only draft plans can be changed.", 409)
    row = _add_checkpoint(plan, payload, user)
    base._audit(shipment.organization_id, user["id"], "checkpoint.created", "OperationalCheckpoint", row.id)
    base._outbox(shipment.organization_id, "checkpoint.created", "OperationalCheckpoint", row.id)
    db.session.commit()
    return _serialize_checkpoint(row)


def update_checkpoint(shipment_id:int,plan_id:int,checkpoint_id:int,payload:dict,user:dict)->dict:
    _,plan=_plan(shipment_id,plan_id,user,"checkpoint.report",True)
    if plan.status!="draft": raise base.OperationalError("ROUTE_PLAN_NOT_DRAFT","Only draft plans can be changed.",409)
    row=db.session.scalar(select(OperationalCheckpoint).where(OperationalCheckpoint.id==checkpoint_id,OperationalCheckpoint.route_plan_id==plan.id).with_for_update())
    if row is None: raise base.OperationalError("RESOURCE_NOT_FOUND","Checkpoint was not found.",404)
    if row.version!=payload.get("expected_version"): raise base.OperationalError("STALE_ROUTE_VERSION","Checkpoint version is stale.",409)
    if row.actual_arrival_at or row.actual_departure_at: raise base.OperationalError("ACTUAL_DATA_IMMUTABLE","Actual checkpoint data is immutable.",409)
    if "notes" in payload:row.notes=payload["notes"]
    if "responsible_party" in payload:row.responsible_party=payload["responsible_party"]
    row.version+=1;db.session.commit();return _serialize_checkpoint(row)


def add_dependency(shipment_id: int, plan_id: int, payload: dict, user: dict) -> dict:
    shipment, plan = _plan(shipment_id, plan_id, user, "route_leg.manage", True)
    if plan.status != "draft":
        raise base.OperationalError("ROUTE_PLAN_NOT_DRAFT", "Only draft plans can be changed.", 409)
    predecessor, successor = payload.get("predecessor_checkpoint_id"), payload.get("successor_checkpoint_id")
    checkpoint_ids = set(db.session.scalars(select(OperationalCheckpoint.id).where(
        OperationalCheckpoint.route_plan_id == plan.id,
        OperationalCheckpoint.id.in_([predecessor, successor]),
    )).all())
    if checkpoint_ids != {predecessor, successor}:
        raise base.OperationalError("CROSS_PLAN_REFERENCE_NOT_ALLOWED", "Dependency endpoints must belong to the same route plan.", 409)
    row = RouteDependency(route_plan_id=plan.id, predecessor_checkpoint_id=predecessor,
        successor_checkpoint_id=successor, dependency_type=payload.get("dependency_type") or "finish_to_start")
    db.session.add(row)
    try:
        db.session.flush()
    except IntegrityError as exc:
        db.session.rollback()
        raise base.OperationalError("ROUTE_DEPENDENCY_INVALID", "Dependency is duplicate, self-referential, or cross-plan.", 409) from exc
    if not validate_plan(shipment_id, plan.id, user)["valid"]:
        db.session.rollback()
        raise base.OperationalError("ROUTE_DEPENDENCY_CYCLE", "Dependency creates an invalid route graph.", 409)
    base._audit(shipment.organization_id, user["id"], "route_dependency.created", "RouteDependency", row.id)
    base._outbox(shipment.organization_id, "route_dependency.created", "RouteDependency", row.id)
    db.session.commit()
    return {"id": row.id, "route_plan_id": row.route_plan_id, "predecessor_checkpoint_id": predecessor,
        "successor_checkpoint_id": successor, "dependency_type": row.dependency_type}


def validate_plan(shipment_id: int, plan_id: int, user: dict) -> dict:
    _, plan = _plan(shipment_id, plan_id, user, PLAN_PERMISSIONS["read"])
    legs = db.session.scalars(select(RouteLeg).where(RouteLeg.route_plan_id == plan.id).order_by(RouteLeg.sequence_number)).all()
    checkpoints = db.session.scalars(select(OperationalCheckpoint).where(OperationalCheckpoint.route_plan_id == plan.id).order_by(OperationalCheckpoint.sequence_number)).all()
    errors = []
    def error(code, entity, field, message):
        errors.append({"code": code, "entity_reference": entity, "field": field, "message": message, "severity": "error"})
    if not legs: error("ROUTE_PLAN_INVALID", f"route_plan:{plan.id}", "legs", "At least one leg is required.")
    if [x.sequence_number for x in legs] != list(range(1, len(legs)+1)): error("ROUTE_SEQUENCE_GAP", f"route_plan:{plan.id}", "sequence_number", "Leg sequence must be contiguous.")
    for previous, current in zip(legs, legs[1:]):
        if previous.destination_location_id != current.origin_location_id: error("ROUTE_LOCATION_DISCONTINUITY", f"route_leg:{current.id}", "origin_location_id", "Adjacent legs must be location-continuous.")
        if current.planned_departure < previous.planned_arrival: error("INVALID_ROUTE_TIMELINE", f"route_leg:{current.id}", "planned_departure", "Legs cannot overlap.")
    finals = [x for x in checkpoints if x.checkpoint_type == "final_delivery"]
    if len(finals) > 1: error("CHECKPOINT_SEQUENCE_INVALID", f"route_plan:{plan.id}", "checkpoints", "Final delivery must be unique.")
    if finals and finals[0] is not checkpoints[-1]: error("CHECKPOINT_SEQUENCE_INVALID", f"checkpoint:{finals[0].id}", "sequence_number", "Final delivery must be last.")
    deps = db.session.scalars(select(RouteDependency).where(RouteDependency.route_plan_id == plan.id)).all()
    graph = {c.id: [] for c in checkpoints}
    for dep in deps: graph.setdefault(dep.predecessor_checkpoint_id, []).append(dep.successor_checkpoint_id)
    visiting, visited = set(), set()
    def cycle(node):
        if node in visiting: return True
        if node in visited: return False
        visiting.add(node)
        if any(cycle(n) for n in graph.get(node, [])): return True
        visiting.remove(node); visited.add(node); return False
    if any(cycle(node) for node in graph): error("ROUTE_DEPENDENCY_CYCLE", f"route_plan:{plan.id}", "dependencies", "Dependency graph contains a cycle.")
    return {"valid": not errors, "errors": errors}


def activate_plan(shipment_id: int, plan_id: int, payload: dict, user: dict) -> dict:
    shipment, plan = _plan(shipment_id, plan_id, user, PLAN_PERMISSIONS["activate"], True)
    if plan.status != "draft": raise base.OperationalError("ROUTE_PLAN_NOT_DRAFT", "Only a draft plan can be activated.", 409)
    if plan.version != payload.get("expected_version"): raise base.OperationalError("STALE_ROUTE_VERSION", "Route plan version is stale.", 409)
    result = validate_plan(shipment_id, plan_id, user)
    if not result["valid"]: raise base.OperationalError("ROUTE_PLAN_INVALID", "Route plan validation failed.")
    active = db.session.scalar(select(RoutePlan).where(RoutePlan.operational_shipment_id == shipment.id, RoutePlan.is_active.is_(True)).with_for_update())
    if active:
        active.is_active=False; active.status="superseded"; active.version += 1
        base._audit(shipment.organization_id, user["id"], "route_plan.superseded", "RoutePlan", active.id)
        db.session.flush()
    plan.is_active=True; plan.status="active"; plan.effective_at=utcnow(); plan.version += 1
    base._audit(shipment.organization_id, user["id"], "route_plan.activated", "RoutePlan", plan.id)
    base._outbox(shipment.organization_id, "route_plan.activated", "RoutePlan", plan.id)
    db.session.commit()
    return _serialize_plan(plan)


def _replan_failure(point: str, requested: str | None) -> None:
    """Private deterministic failure hook used to prove transaction rollback."""
    if requested == point:
        raise RuntimeError(f"Injected replan failure at {point}")


def replan(
    shipment_id: int, plan_id: int, payload: dict, user: dict, key: str,
    *, _fail_at: str | None = None,
) -> dict:
    try:
        shipment = _shipment(shipment_id, user, PLAN_PERMISSIONS["replan"])
        # The shipment row is the serialization boundary. It prevents duplicate
        # revision allocation without imposing an organization/global lock.
        shipment = db.session.scalar(select(OperationalShipment).where(
            OperationalShipment.id == shipment.id,
            OperationalShipment.organization_id == shipment.organization_id,
        ).with_for_update())
        source = db.session.scalar(select(RoutePlan).where(
            RoutePlan.id == plan_id,
            RoutePlan.operational_shipment_id == shipment.id,
        ).with_for_update())
        if source is None:
            raise base.OperationalError("ROUTE_PLAN_NOT_FOUND", "Route plan was not found.", 404)
        reason = str(payload.get("reason") or "").strip()
        if not reason:
            raise base.OperationalError("REPLAN_REASON_REQUIRED", "A replan reason is required.")

        org = shipment.organization_id
        replay, request_hash = _idempotency(
            org, "replan", "operational_shipment", shipment.id, key, payload,
        )
        if replay:
            target = db.session.get(RoutePlan, replay.result_resource_id)
            if target is None:
                raise base.OperationalError(
                    "ROUTE_PLAN_REPLAN_CONFLICT",
                    "The stored replan result is no longer available.", 409,
                )
            return _serialize_plan(target)

        active = db.session.scalar(select(RoutePlan).where(
            RoutePlan.operational_shipment_id == shipment.id,
            RoutePlan.is_active.is_(True),
        ).with_for_update())
        if not source.is_active or active is None or active.id != source.id:
            raise base.OperationalError(
                "ROUTE_PLAN_NOT_ACTIVE", "Only the current active route plan can be replanned.", 409,
            )
        if source.version != payload.get("expected_version"):
            raise base.OperationalError(
                "STALE_ROUTE_PLAN_VERSION", "Route plan version is stale.", 409,
            )
        changes = payload.get("changes") or payload.get("graph_changes") or {}
        if not isinstance(changes, dict):
            raise base.OperationalError("INVALID_ROUTE_GRAPH", "changes must be an object.")
        leg_updates = {
            int(item["source_route_leg_id"]): item
            for item in changes.get("legs", [])
            if isinstance(item, dict) and item.get("source_route_leg_id") is not None
        }
        checkpoint_updates = {
            int(item["source_checkpoint_id"]): item
            for item in changes.get("checkpoints", [])
            if isinstance(item, dict) and item.get("source_checkpoint_id") is not None
        }

        revision = (db.session.scalar(select(func.max(RoutePlan.revision_number)).where(
            RoutePlan.operational_shipment_id == shipment.id,
        )) or 0) + 1
        target = RoutePlan(
            operational_shipment_id=shipment.id, revision_number=revision,
            status="draft", is_active=False, created_from_plan_id=source.id,
            replan_reason=reason, created_by_user_id=user["id"],
        )
        db.session.add(target); db.session.flush()
        _replan_failure("target_create", _fail_at)

        legs = db.session.scalars(select(RouteLeg).where(
            RouteLeg.route_plan_id == source.id,
        ).order_by(RouteLeg.sequence_number)).all()
        leg_map = {}
        for leg in legs:
            update = leg_updates.get(leg.id, {})
            if update and (
                leg.status == "completed" or leg.actual_departure is not None
                or leg.actual_arrival is not None
            ):
                raise base.OperationalError(
                    "COMPLETED_ROUTE_SEGMENT_IMMUTABLE",
                    "A completed route leg cannot be changed by replan.", 409,
                )
            planned_departure = (
                base._parse_utc(update["planned_departure"], "planned_departure")
                if "planned_departure" in update else leg.planned_departure
            )
            planned_arrival = (
                base._parse_utc(update["planned_arrival"], "planned_arrival")
                if "planned_arrival" in update else leg.planned_arrival
            )
            if planned_arrival < planned_departure:
                raise base.OperationalError(
                    "INVALID_ROUTE_GRAPH", "Leg arrival cannot precede departure.",
                )
            clone = RouteLeg(
                route_plan_id=target.id, source_route_leg_id=leg.id,
                sequence_number=int(update.get("sequence_number", leg.sequence_number)),
                origin_location_id=leg.origin_location_id,
                destination_location_id=leg.destination_location_id,
                origin_snapshot=leg.origin_snapshot,
                destination_snapshot=leg.destination_snapshot,
                transport_mode=update.get("transport_mode", leg.transport_mode),
                carrier_reference=update.get("carrier_reference", leg.carrier_reference),
                planned_departure=planned_departure,
                planned_arrival=planned_arrival,
                actual_departure=leg.actual_departure,
                actual_arrival=leg.actual_arrival,
                status=leg.status, version=leg.version,
            )
            db.session.add(clone); db.session.flush(); leg_map[leg.id] = clone.id
        _replan_failure("leg_clone", _fail_at)

        checkpoints = db.session.scalars(select(OperationalCheckpoint).where(
            OperationalCheckpoint.route_plan_id == source.id,
        ).order_by(OperationalCheckpoint.sequence_number)).all()
        checkpoint_map = {}
        for row in checkpoints:
            update = checkpoint_updates.get(row.id, {})
            verified = row.verification_state == "verified" or db.session.scalar(
                select(Milestone.id).where(
                    Milestone.checkpoint_id == row.id,
                    Milestone.verification_state == "verified",
                )
            ) is not None
            if update and (
                row.status == "completed" or row.actual_arrival_at is not None
                or row.actual_departure_at is not None or verified
            ):
                raise base.OperationalError(
                    "COMPLETED_ROUTE_SEGMENT_IMMUTABLE",
                    "A completed or verified checkpoint cannot be changed by replan.", 409,
                )
            planned_arrival = (
                base._parse_utc(update["planned_arrival_at"], "planned_arrival_at")
                if "planned_arrival_at" in update else row.planned_arrival_at
            )
            planned_departure = (
                base._parse_utc(update["planned_departure_at"], "planned_departure_at")
                if "planned_departure_at" in update else row.planned_departure_at
            )
            if planned_arrival and planned_departure and planned_departure < planned_arrival:
                raise base.OperationalError(
                    "INVALID_ROUTE_GRAPH",
                    "Checkpoint departure cannot precede arrival.",
                )
            clone = OperationalCheckpoint(
                route_plan_id=target.id, route_leg_id=leg_map.get(row.route_leg_id),
                source_checkpoint_id=row.id,
                sequence_number=int(update.get("sequence_number", row.sequence_number)),
                checkpoint_type=row.checkpoint_type,
                canonical_location_id=row.canonical_location_id,
                planned_arrival_at=planned_arrival,
                planned_departure_at=planned_departure,
                projected_arrival_at=planned_arrival,
                projected_departure_at=planned_departure,
                actual_arrival_at=row.actual_arrival_at,
                actual_departure_at=row.actual_departure_at,
                status=row.status, verification_state=row.verification_state,
                responsible_party=update.get("responsible_party", row.responsible_party),
                notes=update.get("notes", row.notes),
                version=row.version, created_by_user_id=user["id"],
            )
            db.session.add(clone); db.session.flush(); checkpoint_map[row.id] = clone.id
        _replan_failure("checkpoint_clone", _fail_at)

        source_dependencies = db.session.scalars(select(RouteDependency).where(
            RouteDependency.route_plan_id == source.id,
        )).all()
        dependency_payload = changes.get("dependencies")
        dependencies = source_dependencies if dependency_payload is None else dependency_payload
        for dep in dependencies:
            if isinstance(dep, RouteDependency):
                predecessor, successor = (
                    dep.predecessor_checkpoint_id, dep.successor_checkpoint_id,
                )
                dependency_type = dep.dependency_type
            else:
                predecessor = dep.get("predecessor_source_checkpoint_id")
                successor = dep.get("successor_source_checkpoint_id")
                dependency_type = dep.get("dependency_type") or "finish_to_start"
            if predecessor not in checkpoint_map or successor not in checkpoint_map:
                raise base.OperationalError(
                    "INVALID_ROUTE_GRAPH",
                    "Dependency endpoints must identify source-plan checkpoints.",
                )
            db.session.add(RouteDependency(
                route_plan_id=target.id,
                predecessor_checkpoint_id=checkpoint_map[predecessor],
                successor_checkpoint_id=checkpoint_map[successor],
                dependency_type=dependency_type,
            ))
        db.session.flush()
        _replan_failure("dependency_clone", _fail_at)

        milestones = db.session.scalars(select(Milestone).where(
            Milestone.route_plan_id == source.id,
        ).order_by(Milestone.id)).all()
        for row in milestones:
            checkpoint_update = checkpoint_updates.get(row.checkpoint_id, {})
            planned_at = row.planned_at
            if row.milestone_type == "checkpoint_arrival" and "planned_arrival_at" in checkpoint_update:
                planned_at = base._parse_utc(
                    checkpoint_update["planned_arrival_at"], "planned_arrival_at",
                )
            elif row.milestone_type in {
                "checkpoint_processing_complete", "checkpoint_departure",
            } and "planned_departure_at" in checkpoint_update:
                planned_at = base._parse_utc(
                    checkpoint_update["planned_departure_at"], "planned_departure_at",
                )
            db.session.add(Milestone(
                organization_id=shipment.organization_id, operational_shipment_id=shipment.id,
                route_plan_id=target.id, route_leg_id=leg_map.get(row.route_leg_id),
                checkpoint_id=checkpoint_map.get(row.checkpoint_id),
                source_milestone_id=row.id, milestone_type=row.milestone_type,
                planned_at=planned_at, projected_at=planned_at,
                occurred_at=row.occurred_at, projected_state=row.projected_state,
                verification_state=row.verification_state, version=row.version,
            ))
        db.session.flush()
        _replan_failure("milestone_clone", _fail_at)

        validation = validate_plan(shipment_id, target.id, user)
        if not validation["valid"]:
            raise base.OperationalError("INVALID_ROUTE_GRAPH", "Cloned route graph is invalid.")

        now = utcnow()
        old_items = db.session.scalars(select(OperationalWorkItem).where(
            OperationalWorkItem.route_plan_id == source.id,
            OperationalWorkItem.status == "open",
        ).with_for_update()).all()
        for item in old_items:
            item.status = "resolved"
            item.resolved_at = now
            item.resolved_by_user_id = user["id"]
            item.resolution_reason = "PLAN_SUPERSEDED"
            item.version += 1

        source.is_active = False
        source.status = "superseded"
        source.version += 1
        db.session.flush()
        _replan_failure("source_supersede", _fail_at)
        _replan_failure("target_activation", _fail_at)

        target.is_active = True
        target.status = "active"
        target.effective_at = now
        target.version += 1
        graph_summary = {
            "legs": len(legs), "checkpoints": len(checkpoints),
            "dependencies": len(dependencies), "milestones": len(milestones),
            "completed_segments_carried": sum(
                leg.status == "completed" or leg.actual_arrival is not None for leg in legs
            ),
            "future_segments_changed": len(leg_updates) + len(checkpoint_updates)
            + (0 if dependency_payload is None else 1),
            "superseded_work_items": len(old_items),
        }
        _reserve_idempotency(
            org, "replan", "operational_shipment", shipment.id,
            key, request_hash, target.id,
        )
        _replan_failure("before_audit", _fail_at)
        base._audit(org, user["id"], "route_plan.replanned", "RoutePlan", target.id, {
            "shipment_id": shipment.id, "source_plan_id": source.id,
            "target_plan_id": target.id, "source_revision": source.revision_number,
            "target_revision": target.revision_number, "reason": reason,
            "source_status": "superseded", "target_status": "active",
            "graph_summary": graph_summary,
        })
        base._audit(org, user["id"], "route_plan.superseded", "RoutePlan", source.id, {
            "replacement_plan_id": target.id, "reason": reason,
        })
        _replan_failure("before_outbox", _fail_at)
        base._outbox(org, "route_plan.replanned", "RoutePlan", target.id, {
            "shipment_id": shipment.id, "source_plan_id": source.id,
            "target_plan_id": target.id, "source_revision": source.revision_number,
            "target_revision": target.revision_number,
        })
        _replan_failure("before_commit", _fail_at)
        db.session.commit()
        return _serialize_plan(target)
    except IntegrityError as exc:
        db.session.rollback()
        raise base.OperationalError(
            "ROUTE_PLAN_REPLAN_CONFLICT",
            "A concurrent route replan won the race.", 409,
        ) from exc
    except Exception:
        db.session.rollback()
        raise


def checkpoint_command(shipment_id: int, checkpoint_id: int, payload: dict, user: dict, key: str, action: str) -> dict:
    base.require_permission(user, "checkpoint.report")
    shipment = _shipment(shipment_id, user, "operational_shipment.read")
    checkpoint = db.session.scalar(select(OperationalCheckpoint).join(RoutePlan).where(
        OperationalCheckpoint.id == checkpoint_id, RoutePlan.operational_shipment_id == shipment.id
    ).with_for_update())
    if checkpoint is None: raise base.OperationalError("RESOURCE_NOT_FOUND", "Checkpoint was not found.", 404)
    operation = f"checkpoint_{action}_report"
    replay, request_hash = _idempotency(shipment.organization_id, operation, "checkpoint", checkpoint.id, key, payload)
    if replay:
        return _serialize_checkpoint(checkpoint)
    if checkpoint.version != payload.get("expected_version"): raise base.OperationalError("STALE_MILESTONE_VERSION", "Checkpoint milestone version is stale.", 409)
    occurred = base._parse_utc(payload.get("occurred_at"), "occurred_at")
    milestone_type = {"arrive": "checkpoint_arrival", "complete_processing": "checkpoint_processing_complete", "depart": "checkpoint_departure"}[action]
    milestone = db.session.scalar(select(Milestone).where(
        Milestone.route_plan_id == checkpoint.route_plan_id,
        Milestone.checkpoint_id == checkpoint.id,
        Milestone.milestone_type == milestone_type,
    ).with_for_update())
    if milestone is None:
        raise base.OperationalError("REQUIRED_CHECKPOINT_MISSING", "Checkpoint milestone definition was not found.", 409)
    if action == "arrive":
        if checkpoint.status not in {"planned", "approaching"}: raise base.OperationalError("INVALID_CHECKPOINT_TRANSITION", "Checkpoint cannot arrive from its current state.", 409)
        checkpoint.status="arrived"
    elif action == "complete_processing":
        if checkpoint.status not in {"arrived", "processing"}: raise base.OperationalError("INVALID_CHECKPOINT_TRANSITION", "Processing cannot complete from the current state.", 409)
        checkpoint.status="processing"
    elif action == "depart":
        if checkpoint.status != "ready_to_depart": raise base.OperationalError("INVALID_CHECKPOINT_TRANSITION", "Checkpoint must complete processing before departure.", 409)
        blocked = db.session.scalar(select(RouteDependency.id).join(
            OperationalCheckpoint,
            RouteDependency.predecessor_checkpoint_id == OperationalCheckpoint.id,
        ).where(RouteDependency.successor_checkpoint_id == checkpoint.id,
            ~OperationalCheckpoint.status.in_(["departed", "completed"])))
        if blocked:
            raise base.OperationalError("CHECKPOINT_DEPENDENCY_BLOCKED", "A predecessor checkpoint is incomplete.", 409)
        checkpoint.status="departed"
    event = MilestoneEvent(organization_id=shipment.organization_id, milestone_id=milestone.id, event_type="reported", occurred_at=occurred,
        actor_user_id=user["id"], idempotency_key=f"{operation}:{key}", request_hash=request_hash)
    db.session.add(event)
    milestone.occurred_at=occurred; milestone.verification_state="reported"; milestone.projected_state="reported"; milestone.version += 1
    checkpoint.verification_state="reported"; checkpoint.version += 1
    _reserve_idempotency(shipment.organization_id, operation, "checkpoint", checkpoint.id, key, request_hash, checkpoint.id)
    event_name = {"arrive":"checkpoint.arrived","complete_processing":"checkpoint.processing_completed","depart":"checkpoint.departed"}[action]
    base._audit(shipment.organization_id, user["id"], event_name, "OperationalCheckpoint", checkpoint.id)
    base._outbox(shipment.organization_id, event_name, "OperationalCheckpoint", checkpoint.id)
    db.session.commit()
    return _serialize_checkpoint(checkpoint)


def verify_checkpoint_milestone(shipment_id: int, checkpoint_id: int, milestone_id: int, expected_version: int, user: dict, key: str) -> dict:
    base.require_permission(user, "checkpoint.verify")
    shipment = _shipment(shipment_id, user, "operational_shipment.read")
    checkpoint = db.session.scalar(select(OperationalCheckpoint).join(RoutePlan).where(
        OperationalCheckpoint.id == checkpoint_id,
        RoutePlan.operational_shipment_id == shipment.id,
    ).with_for_update())
    milestone = db.session.scalar(select(Milestone).where(
        Milestone.id == milestone_id, Milestone.checkpoint_id == checkpoint_id,
        Milestone.route_plan_id == checkpoint.route_plan_id,
    ).with_for_update()) if checkpoint else None
    if milestone is None: raise base.OperationalError("RESOURCE_NOT_FOUND", "Checkpoint milestone was not found.", 404)
    payload = {"expected_version": expected_version}
    replay, request_hash = _idempotency(
        shipment.organization_id, "checkpoint_milestone_verify", "milestone", milestone.id, key, payload
    )
    if replay:
        return {"checkpoint": _serialize_checkpoint(checkpoint), "milestone": {
            "id": milestone.id, "version": milestone.version, "verification_state": milestone.verification_state,
        }}
    if milestone.version != expected_version: raise base.OperationalError("STALE_MILESTONE_VERSION", "Milestone version is stale.", 409)
    if milestone.verification_state != "reported":
        raise base.OperationalError("INVALID_MILESTONE_TRANSITION", "Only a reported milestone can be verified.", 409)
    report = db.session.scalar(select(MilestoneEvent).where(
        MilestoneEvent.milestone_id == milestone.id,
        MilestoneEvent.event_type.in_(["reported", "corrected"]),
    ).order_by(MilestoneEvent.recorded_at.desc(), MilestoneEvent.id.desc()))
    if report is None: raise base.OperationalError("INVALID_CHECKPOINT_TRANSITION", "No report is available to verify.", 409)
    if report.actor_user_id == user["id"]:
        raise base.OperationalError("REPORTER_CANNOT_VERIFY_OWN_EVENT", "Reporter and verifier must be different users.", 403)
    event = MilestoneEvent(organization_id=shipment.organization_id, milestone_id=milestone.id, event_type="verified", occurred_at=report.occurred_at,
        actor_user_id=user["id"], supersedes_event_id=report.id,
        idempotency_key=f"verify:{key}", request_hash=request_hash)
    db.session.add(event); milestone.verification_state="verified"; milestone.version += 1
    checkpoint.verification_state="verified"; checkpoint.version += 1
    _synchronize_checkpoint_actual(checkpoint, milestone, report.occurred_at)
    db.session.flush()
    _reserve_idempotency(
        shipment.organization_id, "checkpoint_milestone_verify", "milestone",
        milestone.id, key, request_hash, event.id,
    )
    base._audit(shipment.organization_id, user["id"], "checkpoint.milestone_verified", "Milestone", milestone.id)
    base._outbox(shipment.organization_id, "checkpoint.milestone_verified", "Milestone", milestone.id)
    db.session.commit()
    return {"checkpoint": _serialize_checkpoint(checkpoint), "milestone": {"id": milestone.id, "version": milestone.version, "verification_state": milestone.verification_state}}


def correct_checkpoint_milestone(shipment_id: int, checkpoint_id: int, milestone_id: int, payload: dict, user: dict, key: str) -> dict:
    base.require_permission(user, "milestone.correct")
    shipment = _shipment(shipment_id, user, "operational_shipment.read")
    milestone = db.session.scalar(select(Milestone).join(OperationalCheckpoint, Milestone.checkpoint_id == OperationalCheckpoint.id).join(RoutePlan).where(
        Milestone.id == milestone_id, Milestone.checkpoint_id == checkpoint_id,
        RoutePlan.operational_shipment_id == shipment.id,
    ).with_for_update())
    if milestone is None: raise base.OperationalError("RESOURCE_NOT_FOUND", "Checkpoint milestone was not found.", 404)
    replay, request_hash = _idempotency(shipment.organization_id, "checkpoint_milestone_correct", "milestone", milestone.id, key, payload)
    if replay:
        return {"id": milestone.id, "version": milestone.version, "verification_state": milestone.verification_state}
    if milestone.version != payload.get("expected_version"): raise base.OperationalError("STALE_MILESTONE_VERSION", "Milestone version is stale.", 409)
    if milestone.verification_state != "verified":
        raise base.OperationalError("INVALID_MILESTONE_TRANSITION", "Only a verified milestone can be corrected.", 409)
    reason = str(payload.get("reason") or "").strip()
    if not reason: raise base.OperationalError("CORRECTION_REASON_REQUIRED", "Correction reason is required.")
    previous = db.session.scalar(select(MilestoneEvent).where(
        MilestoneEvent.milestone_id == milestone.id,
        MilestoneEvent.event_type.in_(["reported", "corrected"]),
    ).order_by(MilestoneEvent.recorded_at.desc(), MilestoneEvent.id.desc()))
    if previous is None: raise base.OperationalError("INVALID_CHECKPOINT_TRANSITION", "No event exists to correct.", 409)
    occurred = base._parse_utc(payload.get("occurred_at"), "occurred_at")
    event = MilestoneEvent(organization_id=shipment.organization_id, milestone_id=milestone.id, event_type="corrected", occurred_at=occurred,
        actor_user_id=user["id"], reason=reason, supersedes_event_id=previous.id,
        idempotency_key=f"correct:{key}", request_hash=request_hash)
    checkpoint = db.session.get(OperationalCheckpoint, checkpoint_id)
    db.session.add(event); milestone.verification_state="reported"; milestone.version += 1
    checkpoint.verification_state="reported"; checkpoint.version += 1
    _invalidate_checkpoint_actual(checkpoint, milestone)
    _reserve_idempotency(shipment.organization_id, "checkpoint_milestone_correct", "milestone", milestone.id, key, request_hash, milestone.id)
    base._audit(shipment.organization_id, user["id"], "checkpoint.milestone_corrected", "Milestone", milestone.id)
    base._outbox(shipment.organization_id, "checkpoint.milestone_corrected", "Milestone", milestone.id)
    db.session.commit()
    return {"id": milestone.id, "version": milestone.version, "verification_state": milestone.verification_state}


def _aware(value):
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _topological_checkpoints(checkpoints, dependencies):
    by_id = {row.id: row for row in checkpoints}
    outgoing = {row.id: [] for row in checkpoints}
    indegree = {row.id: 0 for row in checkpoints}
    for dependency in dependencies:
        if dependency.predecessor_checkpoint_id not in by_id or dependency.successor_checkpoint_id not in by_id:
            raise base.OperationalError("INVALID_ROUTE_GRAPH", "Route dependency references an unknown checkpoint.", 409)
        outgoing[dependency.predecessor_checkpoint_id].append(dependency.successor_checkpoint_id)
        indegree[dependency.successor_checkpoint_id] += 1
    ready = [(by_id[node_id].sequence_number, node_id) for node_id, degree in indegree.items() if degree == 0]
    heapq.heapify(ready)
    ordered = []
    while ready:
        _, node_id = heapq.heappop(ready)
        ordered.append(by_id[node_id])
        for successor_id in sorted(outgoing[node_id], key=lambda item: (by_id[item].sequence_number, item)):
            indegree[successor_id] -= 1
            if indegree[successor_id] == 0:
                heapq.heappush(ready, (by_id[successor_id].sequence_number, successor_id))
    if len(ordered) != len(checkpoints):
        raise base.OperationalError("INVALID_ROUTE_GRAPH_CYCLE", "Route dependency graph contains a cycle.", 409)
    return ordered


def _timeline_summary(checkpoints):
    return [{"checkpoint_id": row.id,
             "arrival_at": row.projected_arrival_at.isoformat() if row.projected_arrival_at else None,
             "departure_at": row.projected_departure_at.isoformat() if row.projected_departure_at else None}
            for row in sorted(checkpoints, key=lambda item: (item.sequence_number, item.id))]


def recalculate_projected_timeline(shipment_id: int, user: dict, expected_version=None,
                                   idempotency_key=None, commit=True, _failure_point=None) -> dict:
    shipment = _shipment(shipment_id, user, PLAN_PERMISSIONS["replan"])
    plan = db.session.scalar(select(RoutePlan).where(
        RoutePlan.operational_shipment_id == shipment.id, RoutePlan.is_active.is_(True),
    ).with_for_update())
    if plan is None:
        raise base.OperationalError("ROUTE_PLAN_NOT_FOUND", "Active route plan was not found.", 404)
    payload = {"expected_route_plan_version": expected_version}
    replay = request_hash = None
    if idempotency_key is not None:
        replay, request_hash = _idempotency(
            shipment.organization_id, "route_timeline_reconcile", "route_plan",
            plan.id, idempotency_key, payload,
        )
        if replay is not None:
            return {"route_plan_id": plan.id, "revision": plan.revision_number,
                    "version": plan.version, "reconciled_at": plan.timeline_reconciled_at.isoformat()
                    if plan.timeline_reconciled_at else None, "updated_checkpoints": 0,
                    "actual_override_count": 0, "replayed": True}
    if expected_version is not None and plan.version != expected_version:
        raise base.OperationalError("STALE_ROUTE_PLAN_VERSION", "Route plan version is stale.", 409)
    checkpoints = db.session.scalars(select(OperationalCheckpoint).where(
        OperationalCheckpoint.route_plan_id == plan.id,
    ).with_for_update()).all()
    dependencies = db.session.scalars(select(RouteDependency).where(
        RouteDependency.route_plan_id == plan.id,
    ).order_by(RouteDependency.predecessor_checkpoint_id, RouteDependency.successor_checkpoint_id)).all()
    ordered = _topological_checkpoints(checkpoints, dependencies)
    by_id = {row.id: row for row in checkpoints}
    predecessor_map: dict[int, list[int]] = {}
    for dep in dependencies:
        predecessor_map.setdefault(dep.successor_checkpoint_id, []).append(dep.predecessor_checkpoint_id)
    previous_summary = _timeline_summary(checkpoints)
    updated = actual_overrides = 0
    changed = False
    for checkpoint_index, row in enumerate(ordered):
        planned_arrival = _aware(row.planned_arrival_at or row.planned_departure_at)
        if planned_arrival is None:
            continue
        if row.planned_arrival_at and row.planned_departure_at:
            duration = _aware(row.planned_departure_at) - _aware(row.planned_arrival_at)
            if duration < timedelta(0):
                raise base.OperationalError("INVALID_TIMELINE_DURATION", "Checkpoint duration cannot be negative.", 409)
        else:
            duration = timedelta(0)
        releases = [planned_arrival]
        for predecessor_id in predecessor_map.get(row.id, []):
            predecessor = by_id[predecessor_id]
            anchor = _aware(predecessor.actual_departure_at or predecessor.projected_departure_at
                            or predecessor.actual_arrival_at or predecessor.projected_arrival_at)
            if anchor:
                planned_predecessor = _aware(predecessor.planned_departure_at or predecessor.planned_arrival_at)
                travel = max(timedelta(0), planned_arrival - planned_predecessor) if planned_predecessor else timedelta(0)
                releases.append(anchor + travel)
        actual_arrival = _aware(row.actual_arrival_at)
        actual_departure = _aware(row.actual_departure_at)
        projected_arrival = actual_arrival or max(releases)
        projected_departure = actual_departure or max(
            [_aware(row.planned_departure_at), projected_arrival + duration]
            if row.planned_departure_at else [projected_arrival + duration]
        )
        actual_overrides += int(actual_arrival is not None) + int(actual_departure is not None)
        if _aware(row.projected_arrival_at) != projected_arrival or _aware(row.projected_departure_at) != projected_departure:
            row.projected_arrival_at=projected_arrival; row.projected_departure_at=projected_departure
            updated += 1
            changed = True
        milestones = db.session.scalars(select(Milestone).where(Milestone.checkpoint_id == row.id).with_for_update()).all()
        milestone_times = {
            "checkpoint_arrival": projected_arrival,
            "checkpoint_processing_complete": projected_departure,
            "checkpoint_departure": projected_departure,
        }
        for milestone in milestones:
            target = _aware(milestone.occurred_at) if milestone.verification_state == "verified" else milestone_times[milestone.milestone_type]
            if _aware(milestone.projected_at) != target:
                milestone.projected_at = target
                changed = True
        if checkpoint_index == 0 and _failure_point == "after_first_checkpoint":
            raise RuntimeError("injected timeline reconciliation failure")
        if checkpoint_index == len(ordered) // 2 and _failure_point == "middle_chain":
            raise RuntimeError("injected timeline reconciliation failure")
    if _failure_point == "after_milestone_sync":
        raise RuntimeError("injected timeline reconciliation failure")
    legs = db.session.scalars(select(RouteLeg).where(RouteLeg.route_plan_id == plan.id).with_for_update()).all()
    for leg in legs:
        leg_checkpoints = [row for row in checkpoints if row.route_leg_id == leg.id]
        if not leg_checkpoints or leg.status == "completed":
            continue
        starts = [_aware(row.actual_arrival_at or row.projected_arrival_at) for row in leg_checkpoints]
        ends = [_aware(row.actual_departure_at or row.projected_departure_at) for row in leg_checkpoints]
        projected_start = min(value for value in starts if value is not None)
        projected_end = max(value for value in ends if value is not None)
        if projected_end < projected_start:
            raise base.OperationalError("INVALID_TIMELINE_DURATION", "Route-leg projected end precedes its start.", 409)
        if _aware(leg.projected_departure) != projected_start or _aware(leg.projected_arrival) != projected_end:
            leg.projected_departure, leg.projected_arrival = projected_start, projected_end
            changed = True
    if _failure_point == "after_route_leg_sync":
        raise RuntimeError("injected timeline reconciliation failure")
    if changed:
        plan.version += 1
        plan.timeline_reconciled_at = utcnow()
        details = {"shipment_id": shipment.id, "route_plan_id": plan.id, "revision": plan.revision_number,
                   "reason": "delay_propagation", "affected_checkpoints": updated,
                   "previous_projected": previous_summary, "new_projected": _timeline_summary(checkpoints),
                   "actual_override_count": actual_overrides}
        if _failure_point == "before_audit":
            raise RuntimeError("injected timeline reconciliation failure")
        base._audit(shipment.organization_id, user["id"], "route_plan.timeline_reconciled", "RoutePlan", plan.id, details)
        if _failure_point == "before_outbox":
            raise RuntimeError("injected timeline reconciliation failure")
        base._outbox(shipment.organization_id, "route_plan.timeline_reconciled", "RoutePlan", plan.id, details)
    if idempotency_key is not None:
        _reserve_idempotency(shipment.organization_id, "route_timeline_reconcile", "route_plan",
                             plan.id, idempotency_key, request_hash, plan.id)
    if _failure_point == "before_commit":
        raise RuntimeError("injected timeline reconciliation failure")
    if commit:
        db.session.commit()
    return {"route_plan_id": plan.id, "revision": plan.revision_number, "version": plan.version,
            "reconciled_at": plan.timeline_reconciled_at.isoformat() if plan.timeline_reconciled_at else None,
            "updated_checkpoints": updated, "actual_override_count": actual_overrides, "replayed": False}


def reconcile_route_exceptions(
    shipment_id: int, user: dict, expected_plan_version: int | None = None,
    calculation_time: datetime | None = None, idempotency_key: str = "",
    commit: bool = True, _failure_point: str | None = None,
) -> dict:
    shipment = _shipment(shipment_id, user, "route_exception.manage")
    plan = db.session.scalar(select(RoutePlan).where(
        RoutePlan.operational_shipment_id == shipment.id, RoutePlan.is_active.is_(True),
    ).with_for_update())
    if plan is None:
        raise base.OperationalError("ROUTE_PLAN_NOT_ACTIVE", "No active route plan exists.", 409)
    payload = {
        "expected_route_plan_version": expected_plan_version,
        "calculation_time": calculation_time.isoformat() if calculation_time else None,
    }
    replay = request_hash = None
    if idempotency_key:
        replay, request_hash = _idempotency(
            shipment.organization_id, "route_exception_reconcile", "route_plan",
            plan.id, idempotency_key, payload,
        )
        if replay:
            return {
                **(replay.response_json or {}), "replayed": True,
            }
    if expected_plan_version is not None and plan.version != expected_plan_version:
        raise base.OperationalError("STALE_ROUTE_PLAN_VERSION", "Route plan version is stale.", 409)
    # Exception lifecycle intentionally consumes, but never triggers, timeline reconciliation.
    checkpoints = db.session.scalars(select(OperationalCheckpoint).where(
        OperationalCheckpoint.route_plan_id == plan.id,
    ).order_by(OperationalCheckpoint.sequence_number).with_for_update()).all()
    dependencies = db.session.scalars(select(RouteDependency).where(RouteDependency.route_plan_id == plan.id)).all()
    by_id = {row.id: row for row in checkpoints}
    now = calculation_time or utcnow()
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    conditions = {}
    for row in checkpoints:
        due = row.projected_arrival_at or row.planned_arrival_at or row.projected_departure_at or row.planned_departure_at
        if due and due.replace(tzinfo=due.tzinfo or now.tzinfo) < now and row.status not in {"completed", "cancelled"}:
            conditions[(row.id, "CHECKPOINT_OVERDUE")] = (due, "Checkpoint is overdue.", "warning")
            delay = now - due.replace(tzinfo=due.tzinfo or now.tzinfo)
            if delay >= timedelta(hours=24):
                conditions[(row.id, "REPLAN_REQUIRED")] = (due, "Projected delay exceeds the replan threshold.", "critical")
    for dep in dependencies:
        predecessor, successor = by_id[dep.predecessor_checkpoint_id], by_id[dep.successor_checkpoint_id]
        if predecessor.status not in {"departed", "completed"} and successor.status in {"approaching", "arrived", "processing", "ready_to_depart", "blocked"}:
            conditions[(successor.id, "ROUTE_DEPENDENCY_BLOCKED")] = (now, "A predecessor checkpoint is incomplete.", "critical")
            successor.status = "blocked"
    all_rows = db.session.scalars(select(OperationalWorkItem).where(
        OperationalWorkItem.organization_id == shipment.organization_id,
        OperationalWorkItem.operational_shipment_id == shipment.id,
        OperationalWorkItem.route_plan_id == plan.id,
        OperationalWorkItem.work_type.in_(["CHECKPOINT_OVERDUE", "ROUTE_DEPENDENCY_BLOCKED", "REPLAN_REQUIRED"]),
    ).order_by(OperationalWorkItem.id.desc()).with_for_update()).all()
    existing = {}
    for row in all_rows:
        existing.setdefault((row.checkpoint_id, row.work_type), row)
    opened=resolved=reopened=unchanged=0
    for scope, (due, reason, severity) in conditions.items():
        row = existing.get(scope)
        if row is None:
            row = OperationalWorkItem(organization_id=shipment.organization_id, operational_shipment_id=shipment.id,
                route_plan_id=plan.id, checkpoint_id=scope[0], milestone_id=None, work_type=scope[1],
                due_at=due, detected_at=now, last_reconciled_at=now, severity=severity, reason=reason)
            db.session.add(row); db.session.flush(); opened += 1
            base._audit(shipment.organization_id, user["id"], "route_exception.opened", "OperationalWorkItem", row.id)
            base._outbox(shipment.organization_id, "route_exception.opened", "OperationalWorkItem", row.id)
            if _failure_point == "after_exception_open": raise RuntimeError("injected exception-open failure")
        elif row.status == "resolved":
            row.status="open"; row.detected_at=now; row.resolved_at=None
            row.resolved_by_user_id=None; row.resolution_reason=None; row.resolution_source=None
            row.occurrence_count += 1; row.last_reconciled_at=now; row.version += 1; reopened += 1
            base._audit(shipment.organization_id, user["id"], "route_exception.reopened", "OperationalWorkItem", row.id)
            base._outbox(shipment.organization_id, "route_exception.reopened", "OperationalWorkItem", row.id)
        else:
            row.last_reconciled_at=now; unchanged += 1
    for scope, row in existing.items():
        if row.status == "open" and scope not in conditions:
            row.status="resolved"; row.resolved_at=now; row.resolved_by_user_id=user["id"]
            row.resolution_reason="CONDITION_CLEARED"; row.resolution_source="automatic"
            row.last_reconciled_at=now; row.version += 1; resolved += 1
            base._audit(shipment.organization_id, user["id"], "route_exception.resolved", "OperationalWorkItem", row.id)
            base._outbox(shipment.organization_id, "route_exception.resolved", "OperationalWorkItem", row.id)
            if _failure_point == "after_exception_resolve": raise RuntimeError("injected exception-resolve failure")
    result = {
        "opened": opened, "resolved": resolved, "reopened": reopened,
        "unchanged": unchanged, "work_items_created": opened + reopened,
        "work_items_closed": resolved, "plan_revision": plan.revision_number,
        "reconciliation_timestamp": now.isoformat(), "replayed": False,
    }
    if opened or resolved or reopened:
        base._audit(shipment.organization_id, user["id"], "route_exceptions.reconciled", "RoutePlan", plan.id, result)
        base._outbox(shipment.organization_id, "route_exceptions.reconciled", "RoutePlan", plan.id, result)
    if idempotency_key:
        _reserve_idempotency(
            shipment.organization_id, "route_exception_reconcile", "route_plan",
            plan.id, idempotency_key, request_hash, plan.id,
        )
        db.session.flush()
        reservation = db.session.scalar(select(OperationalIdempotency).where(
            OperationalIdempotency.organization_id == shipment.organization_id,
            OperationalIdempotency.operation == "route_exception_reconcile",
            OperationalIdempotency.command_resource_id == plan.id,
            OperationalIdempotency.idempotency_key == idempotency_key,
        ))
        reservation.response_json = result
    if _failure_point == "before_commit": raise RuntimeError("injected reconcile failure")
    if commit:
        try: db.session.commit()
        except IntegrityError as exc:
            db.session.rollback()
            raise base.OperationalError("CONCURRENT_RECONCILIATION", "Concurrent reconciliation already created this exception.", 409) from exc
    return result


def list_route_exceptions(user: dict, status="open") -> list[dict]:
    base.require_permission(user, "route_exception.read")
    org = base.organization_for_user(user["id"])
    query = select(OperationalWorkItem).where(
        OperationalWorkItem.organization_id == org,
        OperationalWorkItem.work_type.in_(["CHECKPOINT_OVERDUE", "ROUTE_DEPENDENCY_BLOCKED", "REPLAN_REQUIRED"]),
    )
    if status: query=query.where(OperationalWorkItem.status == status)
    rows=db.session.scalars(query.order_by(OperationalWorkItem.due_at)).all()
    return [{"id":r.id,"shipment_id":r.operational_shipment_id,"route_plan_id":r.route_plan_id,
        "checkpoint_id":r.checkpoint_id,"type":r.work_type,"status":r.status,"severity":r.severity,
        "due_at":r.due_at.isoformat(),"detected_at":r.detected_at.isoformat(),"reason":r.reason,
        "resolved_at":r.resolved_at.isoformat() if r.resolved_at else None,
        "resolution_source":r.resolution_source,"resolution_reason":r.resolution_reason,
        "last_reconciled_at":r.last_reconciled_at.isoformat() if r.last_reconciled_at else None,
        "occurrence_count":r.occurrence_count,"version":r.version} for r in rows]


def resolve_route_exception(item_id: int, payload: dict, user: dict) -> dict:
    return _resolve_route_exception(item_id, payload, user)


def _resolve_route_exception(
    item_id: int, payload: dict, user: dict, idempotency_key: str = "",
    commit: bool = True, _failure_point: str | None = None,
) -> dict:
    base.require_permission(user, "route_exception.manage"); org=base.organization_for_user(user["id"])
    row=db.session.scalar(select(OperationalWorkItem).where(
        OperationalWorkItem.id == item_id, OperationalWorkItem.organization_id == org,
        OperationalWorkItem.work_type.in_(["CHECKPOINT_OVERDUE","ROUTE_DEPENDENCY_BLOCKED","REPLAN_REQUIRED"]),
    ).with_for_update())
    if row is None: raise base.OperationalError("ROUTE_EXCEPTION_NOT_FOUND","Route exception was not found.",404)
    reason=str(payload.get("reason") or "").strip()
    if not reason: raise base.OperationalError("EXCEPTION_RESOLUTION_REASON_REQUIRED","Resolution reason is required.")
    replay = request_hash = None
    command_payload = {"expected_version": payload.get("expected_version"), "reason": reason}
    if idempotency_key:
        replay, request_hash = _idempotency(
            org, "route_exception_resolve", "route_exception", row.id,
            idempotency_key, command_payload,
        )
        if replay:
            return {**(replay.response_json or {}), "replayed": True}
    if row.status != "open": raise base.OperationalError("ROUTE_EXCEPTION_ALREADY_RESOLVED","Route exception is already resolved.",409)
    if row.version != payload.get("expected_version"): raise base.OperationalError("STALE_ROUTE_EXCEPTION_VERSION","Route exception version is stale.",409)
    row.status="resolved"; row.resolved_at=utcnow(); row.resolved_by_user_id=user["id"]
    row.resolution_reason=reason; row.resolution_source="manual"; row.version += 1
    if _failure_point == "after_exception_resolve":
        raise RuntimeError("injected manual-resolution failure")
    base._audit(org,user["id"],"route_exception.manually_resolved","OperationalWorkItem",row.id)
    if _failure_point == "before_outbox":
        raise RuntimeError("injected manual-resolution failure")
    base._outbox(org,"route_exception.manually_resolved","OperationalWorkItem",row.id)
    result = {"id":row.id,"status":row.status,"version":row.version,"replayed":False}
    if idempotency_key:
        _reserve_idempotency(
            org, "route_exception_resolve", "route_exception", row.id,
            idempotency_key, request_hash, row.id,
        )
        db.session.flush()
        reservation = db.session.scalar(select(OperationalIdempotency).where(
            OperationalIdempotency.organization_id == org,
            OperationalIdempotency.operation == "route_exception_resolve",
            OperationalIdempotency.command_resource_id == row.id,
            OperationalIdempotency.idempotency_key == idempotency_key,
        ))
        reservation.response_json = result
    if _failure_point == "before_commit":
        raise RuntimeError("injected manual-resolution failure")
    if commit:
        db.session.commit()
    return result


def timeline(shipment_id: int, user: dict) -> dict:
    shipment = _shipment(shipment_id, user, PLAN_PERMISSIONS["read"])
    plan = db.session.scalar(select(RoutePlan).where(RoutePlan.operational_shipment_id == shipment.id, RoutePlan.is_active.is_(True)))
    if plan is None: return {"planned": [], "projected": [], "actual": [], "delays": [], "dependencies": [], "open_exceptions": []}
    checkpoints = db.session.scalars(select(OperationalCheckpoint).where(OperationalCheckpoint.route_plan_id == plan.id).order_by(OperationalCheckpoint.sequence_number)).all()
    now = utcnow(); delays = []
    for row in checkpoints:
        baseline = row.planned_departure_at or row.planned_arrival_at
        projected = row.projected_departure_at or row.projected_arrival_at
        if baseline and projected and projected > baseline:
            delays.append({"checkpoint_id": row.id, "seconds": int((projected-baseline).total_seconds())})
        elif baseline and not row.actual_departure_at and baseline < now:
            delays.append({"checkpoint_id": row.id, "seconds": int((now-baseline).total_seconds())})
    dependencies = db.session.scalars(select(RouteDependency).where(RouteDependency.route_plan_id == plan.id)).all()
    exceptions = db.session.scalars(select(OperationalWorkItem).where(
        OperationalWorkItem.route_plan_id == plan.id, OperationalWorkItem.status == "open",
        OperationalWorkItem.work_type.in_(["CHECKPOINT_OVERDUE","ROUTE_DEPENDENCY_BLOCKED","REPLAN_REQUIRED"]),
    )).all()
    effective = []
    for checkpoint in checkpoints:
        arrival_source = "actual" if checkpoint.actual_arrival_at else "projected" if checkpoint.projected_arrival_at else "planned"
        departure_source = "actual" if checkpoint.actual_departure_at else "projected" if checkpoint.projected_departure_at else "planned"
        effective.append({"checkpoint_id": checkpoint.id,
                          "arrival_at": (_aware(checkpoint.actual_arrival_at or checkpoint.projected_arrival_at or checkpoint.planned_arrival_at).isoformat()
                                         if checkpoint.actual_arrival_at or checkpoint.projected_arrival_at or checkpoint.planned_arrival_at else None),
                          "arrival_source": arrival_source,
                          "departure_at": (_aware(checkpoint.actual_departure_at or checkpoint.projected_departure_at or checkpoint.planned_departure_at).isoformat()
                                           if checkpoint.actual_departure_at or checkpoint.projected_departure_at or checkpoint.planned_departure_at else None),
                          "departure_source": departure_source})
    return {
        "route_plan_id": plan.id, "route_plan_revision": plan.revision_number,
        "reconciliation_version": plan.version,
        "reconciled_at": plan.timeline_reconciled_at.isoformat() if plan.timeline_reconciled_at else None,
        "planned": [{"checkpoint_id": c.id, "arrival_at": c.planned_arrival_at.isoformat() if c.planned_arrival_at else None, "departure_at": c.planned_departure_at.isoformat() if c.planned_departure_at else None} for c in checkpoints],
        "projected": [{"checkpoint_id": c.id, "arrival_at": c.projected_arrival_at.isoformat() if c.projected_arrival_at else None, "departure_at": c.projected_departure_at.isoformat() if c.projected_departure_at else None} for c in checkpoints],
        "actual": [{"checkpoint_id": c.id, "arrival_at": c.actual_arrival_at.isoformat() if c.actual_arrival_at else None, "departure_at": c.actual_departure_at.isoformat() if c.actual_departure_at else None} for c in checkpoints],
        "effective": effective,
        "delays": delays,
        "dependencies": [{"predecessor_checkpoint_id": d.predecessor_checkpoint_id, "successor_checkpoint_id": d.successor_checkpoint_id, "type": d.dependency_type} for d in dependencies],
        "open_exceptions": [{"id":row.id,"checkpoint_id":row.checkpoint_id,"type":row.work_type,
            "severity":row.severity,"due_at":row.due_at.isoformat(),"reason":row.reason,"version":row.version} for row in exceptions],
    }
