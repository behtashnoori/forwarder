"""Project-scoped ExecutionUnit application service for Release 1.2.0."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
import re
from typing import Any

from sqlalchemy import and_, func, or_, select

from backend.extensions import db
from backend.models import ExpertUser
from backend.operational_models import (
    ExecutionUnit,
    OperationalEvent,
    OperationalMembership,
    OperationalShipment,
    Project,
    utcnow,
)
from backend.services.operational_service import OperationalError, organization_for_user

LIFECYCLE = {"not_started", "ready", "in_progress", "arrived", "delivered", "cancelled"}
POLICY_VERSION = os.getenv("EXECUTION_UNIT_THRESHOLD_POLICY_VERSION", "stale-v1")
STALE_HOURS = max(1, int(os.getenv("EXECUTION_UNIT_STALE_HOURS", "24")))


def _iso(value):
    if not value: return None
    if value.tzinfo is None: value=value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _as_utc(value):
    return value.replace(tzinfo=timezone.utc) if value is not None and value.tzinfo is None else value


def _parse_time(value: Any) -> datetime:
    if value is None:
        return utcnow()
    if not isinstance(value, str):
        raise OperationalError("VALIDATION_FAILED", "occurred_at must be an ISO-8601 timestamp.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise OperationalError("VALIDATION_FAILED", "occurred_at must be an ISO-8601 timestamp.") from exc
    if parsed.tzinfo is None:
        raise OperationalError("VALIDATION_FAILED", "occurred_at must include a timezone.")
    return parsed.astimezone(timezone.utc)


def _hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _organization_admin_oversight(user: dict, organization_id: int, permission: str) -> bool:
    """Project-only execution has no Expert root; admit governed tenant oversight only."""
    try:
        user_id = int(user["id"])
    except (KeyError, TypeError, ValueError):
        return False
    actor = db.session.get(ExpertUser, user_id)
    membership = db.session.scalar(
        select(OperationalMembership).where(
            OperationalMembership.organization_id == organization_id,
            OperationalMembership.user_id == user_id,
            OperationalMembership.is_active.is_(True),
        )
    )
    return bool(
        actor
        and actor.is_active
        and (actor.authority or "EXPERT").upper() == "ORGANIZATION_ADMIN"
        and membership
        and permission in set(membership.permissions or [])
    )


def scoped_project(public_id: str, user: dict, permission: str = "execution_unit.read") -> Project:
    org = organization_for_user(int(user["id"]))
    project = db.session.scalar(select(Project).where(Project.public_id == public_id, Project.organization_id == org))
    if project is None or not _organization_admin_oversight(user, org, permission):
        raise OperationalError("NOT_FOUND", "Project not found.", 404)
    return project


def scoped_unit(project: Project, public_id: str) -> ExecutionUnit:
    unit = db.session.scalar(select(ExecutionUnit).where(ExecutionUnit.public_id == public_id, ExecutionUnit.project_id == project.id))
    if unit is None:
        raise OperationalError("NOT_FOUND", "Execution unit not found.", 404)
    return unit


def _stale_expression(now: datetime):
    return and_(ExecutionUnit.lifecycle_status.in_(["ready", "in_progress", "arrived"]), or_(ExecutionUnit.last_event_at.is_(None), ExecutionUnit.last_event_at < now - timedelta(hours=STALE_HOURS)))


def _page(args: dict) -> tuple[int, int]:
    try:
        return max(1, int(args.get("page", 1))), min(50, max(1, int(args.get("per_page", 25))))
    except (TypeError, ValueError) as exc:
        raise OperationalError("VALIDATION_FAILED", "page and per_page must be integers.") from exc


def unit_projection(unit: ExecutionUnit, *, customer: bool = False, now: datetime | None = None) -> dict:
    now = now or utcnow()
    stale = unit.lifecycle_status in {"ready", "in_progress", "arrived"} and (unit.last_event_at is None or _as_utc(unit.last_event_at) < now - timedelta(hours=STALE_HOURS))
    data = {
        "public_id": unit.public_id,
        "unit_code": unit.unit_code,
        "unit_type": unit.unit_type,
        "display_name": unit.display_name,
        "vehicle_reference": unit.vehicle_reference,
        "lifecycle_status": unit.lifecycle_status,
        "is_active": unit.is_active,
        "alerts": {"attention_required": unit.attention_required, "delayed": unit.delayed, "stale": stale},
        "latest_checkpoint": unit.latest_checkpoint,
        "last_update_at": _iso(unit.last_event_at),
        "updated_at": _iso(unit.updated_at),
    }
    if not customer:
        data["version"] = unit.version
        data["operational_shipment_public_id"] = db.session.scalar(select(OperationalShipment.public_id).where(OperationalShipment.id == unit.operational_shipment_id)) if unit.operational_shipment_id else None
    return data


def list_units(project: Project, args: dict, *, customer: bool = False) -> dict:
    page, per_page = _page(args)
    query = select(ExecutionUnit).where(ExecutionUnit.project_id == project.id)
    if customer:
        query = query.where(ExecutionUnit.is_active.is_(True))
    status = str(args.get("status", "")).strip()
    if status:
        statuses = [value for value in status.split(",") if value in LIFECYCLE]
        if statuses:
            query = query.where(ExecutionUnit.lifecycle_status.in_(statuses))
    for name, column in (("delayed", ExecutionUnit.delayed), ("active", ExecutionUnit.is_active), ("attention_required", ExecutionUnit.attention_required)):
        if str(args.get(name, "")).lower() in {"true", "false"}:
            query = query.where(column.is_(str(args[name]).lower() == "true"))
    if str(args.get("stale", "")).lower() in {"true", "false"}:
        stale = _stale_expression(utcnow())
        query = query.where(stale if str(args["stale"]).lower() == "true" else ~stale)
    search = str(args.get("search", "")).strip()[:160]
    if search:
        pattern = f"%{search}%"
        query = query.where(or_(ExecutionUnit.unit_code.ilike(pattern), ExecutionUnit.vehicle_reference.ilike(pattern), ExecutionUnit.display_name.ilike(pattern)))
    total = db.session.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0
    rows = db.session.scalars(query.order_by(ExecutionUnit.unit_code).offset((page - 1) * per_page).limit(per_page)).all()
    return {"data": [unit_projection(row, customer=customer) for row in rows], "meta": {"page": page, "per_page": per_page, "total": total, "pages": (total + per_page - 1) // per_page}}


def create_unit(project: Project, payload: dict, user: dict) -> ExecutionUnit:
    unit_type = str(payload.get("unit_type", "")).strip().lower()
    if not unit_type or len(unit_type) > 32:
        raise OperationalError("VALIDATION_FAILED", "unit_type is required and must not exceed 32 characters.")
    shipment_id = payload.get("operational_shipment_public_id")
    shipment = None
    if shipment_id:
        shipment = db.session.scalar(select(OperationalShipment).where(OperationalShipment.public_id == shipment_id, OperationalShipment.project_id == project.id, OperationalShipment.organization_id == project.organization_id))
        if shipment is None:
            raise OperationalError("NOT_FOUND", "Operational shipment not found.", 404)
    db.session.execute(select(Project.id).where(Project.id == project.id).with_for_update())
    codes = db.session.scalars(select(ExecutionUnit.unit_code).where(ExecutionUnit.project_id == project.id, ExecutionUnit.unit_code.like("U-%"))).all()
    next_number = max([int(match.group(1)) for code in codes if (match := re.fullmatch(r"U-(\d+)", code))] or [0]) + 1
    unit = ExecutionUnit(
        project_id=project.id, operational_shipment_id=shipment.id if shipment else None,
        unit_code=f"U-{next_number:04d}", unit_type=unit_type,
        display_name=(str(payload.get("display_name", "")).strip() or None),
        vehicle_reference=(str(payload.get("vehicle_reference", "")).strip() or None),
        created_by_user_id=int(user["id"]),
    )
    db.session.add(unit); db.session.flush()
    return unit


def update_unit(unit: ExecutionUnit, payload: dict) -> ExecutionUnit:
    expected = payload.get("expected_version")
    if not isinstance(expected, int) or expected != unit.version:
        raise OperationalError("VERSION_CONFLICT", "expected_version does not match the current unit version.", 409)
    for field, limit in (("display_name", 160), ("vehicle_reference", 160)):
        if field in payload:
            value = str(payload[field]).strip() if payload[field] is not None else ""
            if len(value) > limit: raise OperationalError("VALIDATION_FAILED", f"{field} is too long.")
            setattr(unit, field, value or None)
    if "is_active" in payload:
        if not isinstance(payload["is_active"], bool): raise OperationalError("VALIDATION_FAILED", "is_active must be boolean.")
        unit.is_active = payload["is_active"]
    unit.version += 1; unit.updated_at = utcnow()
    return unit


def create_event(unit: ExecutionUnit, payload: dict, user: dict, idempotency_key: str) -> tuple[OperationalEvent, bool]:
    if not idempotency_key or len(idempotency_key) > 100:
        raise OperationalError("VALIDATION_FAILED", "A valid Idempotency-Key header is required.")
    request_hash = _hash(payload)
    existing = db.session.scalar(select(OperationalEvent).where(OperationalEvent.execution_unit_id == unit.id, OperationalEvent.idempotency_key == idempotency_key))
    if existing:
        if existing.request_hash != request_hash: raise OperationalError("IDEMPOTENCY_CONFLICT", "Idempotency key was already used with another payload.", 409)
        return existing, False
    expected = payload.get("expected_version")
    if not isinstance(expected, int) or expected != unit.version:
        raise OperationalError("VERSION_CONFLICT", "expected_version does not match the current unit version.", 409)
    status = payload.get("lifecycle_status")
    if status is not None and status not in LIFECYCLE: raise OperationalError("VALIDATION_FAILED", "Invalid lifecycle_status.")
    visibility = payload.get("visibility", "internal")
    if visibility not in {"internal", "customer"}: raise OperationalError("VALIDATION_FAILED", "visibility must be internal or customer.")
    customer_message = str(payload.get("customer_message", "")).strip() or None
    internal_note = str(payload.get("internal_note", "")).strip() or None
    if visibility == "customer" and not customer_message: raise OperationalError("VALIDATION_FAILED", "customer_message is required for customer visibility.")
    occurred = _parse_time(payload.get("occurred_at"))
    event = OperationalEvent(
        project_id=unit.project_id, execution_unit_id=unit.id,
        event_type=str(payload.get("event_type", "unit_updated")).strip()[:64] or "unit_updated",
        lifecycle_status=status, checkpoint_text=(str(payload.get("checkpoint_text", "")).strip()[:255] or None),
        customer_message=customer_message, internal_note=internal_note, visibility=visibility,
        attention_required=bool(payload.get("attention_required", False)), delayed=bool(payload.get("delayed", False)),
        occurred_at=occurred, actor_user_id=int(user["id"]), source="expert",
        idempotency_key=idempotency_key, request_hash=request_hash,
        correlation_id=(str(payload.get("correlation_id", "")).strip()[:100] or None), batch_id=(str(payload.get("batch_id", "")).strip()[:100] or None),
        threshold_policy_version=POLICY_VERSION,
    )
    db.session.add(event)
    if status: unit.lifecycle_status = status
    if event.checkpoint_text: unit.latest_checkpoint = event.checkpoint_text
    unit.attention_required, unit.delayed = event.attention_required, event.delayed
    unit.last_event_at = max(filter(None, [_as_utc(unit.last_event_at), occurred]))
    unit.version += 1; unit.updated_at = utcnow()
    db.session.flush()
    return event, True


def timeline(unit: ExecutionUnit, args: dict, *, customer: bool = False) -> dict:
    page,per_page=_page(args)
    query=select(OperationalEvent).where(OperationalEvent.execution_unit_id == unit.id)
    if customer: query=query.where(OperationalEvent.visibility == "customer")
    total=db.session.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows=db.session.scalars(query.order_by(OperationalEvent.occurred_at.desc(),OperationalEvent.id.desc()).offset((page-1)*per_page).limit(per_page)).all()
    data=[]
    for row in rows:
        item={"public_id":row.public_id,"event_type":row.event_type,"lifecycle_status":row.lifecycle_status,"checkpoint_text":row.checkpoint_text,"customer_message":row.customer_message,"visibility":row.visibility,"occurred_at":_iso(row.occurred_at),"recorded_at":_iso(row.recorded_at),"alerts":{"attention_required":row.attention_required,"delayed":row.delayed}}
        if not customer: item.update({"internal_note":row.internal_note,"source":row.source,"correlation_id":row.correlation_id,"batch_id":row.batch_id,"threshold_policy_version":row.threshold_policy_version})
        data.append(item)
    return {"data":data,"meta":{"page":page,"per_page":per_page,"total":total,"pages":(total+per_page-1)//per_page}}


def summary(project: Project) -> dict:
    rows=db.session.execute(select(ExecutionUnit.lifecycle_status,ExecutionUnit.delayed,ExecutionUnit.attention_required,ExecutionUnit.last_event_at).where(ExecutionUnit.project_id==project.id,ExecutionUnit.is_active.is_(True))).all()
    total=len(rows); delivered=sum(r.lifecycle_status=="delivered" for r in rows); in_progress=sum(r.lifecycle_status in {"ready","in_progress","arrived"} for r in rows)
    delayed=sum(bool(r.delayed) for r in rows); attention=sum(bool(r.attention_required) for r in rows); stale=sum(r.lifecycle_status in {"ready","in_progress","arrived"} and (r.last_event_at is None or _as_utc(r.last_event_at) < utcnow()-timedelta(hours=STALE_HOURS)) for r in rows)
    cancelled=sum(r.lifecycle_status=="cancelled" for r in rows); started=sum(r.lifecycle_status!="not_started" for r in rows)
    if total == 0 or started == 0: status="not_started"
    elif cancelled == total: status="cancelled"
    elif delivered + cancelled == total: status="completed"
    elif delivered: status="partially_delivered"
    else: status="in_progress"
    return {"project_public_id":project.public_id,"project_code":project.project_code,"status":status,"total_units":total,"delivered_units":delivered,"in_progress_units":in_progress,"delayed_units":delayed,"attention_required":attention,"units_without_recent_update":stale,"incomplete_documents":None,"progress_percentage":round(delivered*100/total) if total else 0,"last_update_at":_iso(max((_as_utc(r.last_event_at) for r in rows if r.last_event_at),default=None)),"threshold_policy":{"version":POLICY_VERSION,"stale_after_hours":STALE_HOURS}}
