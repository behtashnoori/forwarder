"""Bounded Shipment-rooted operational follow-up Actions."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from backend.extensions import db
from backend.models import ExpertUser
from backend.operational_models import (
    OperationalAudit,
    OperationalException,
    OperationalShipment,
    OperationalWorkItem,
    utcnow,
)
from backend.services import operational_service
from backend.services.organization_sla_service import PROCESS_DEFINITIONS


def _parse_instant(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise operational_service.OperationalError(
            "VALIDATION_FAILED", f"{field} is required.", 422
        )
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise operational_service.OperationalError(
            "VALIDATION_FAILED", f"{field} must be an ISO-8601 timestamp.", 422
        ) from exc
    if parsed.tzinfo is None:
        raise operational_service.OperationalError(
            "VALIDATION_FAILED", f"{field} must include a timezone.", 422
        )
    return parsed.astimezone(timezone.utc)


def _text(value: Any, field: str, *, required: bool, maximum: int) -> str | None:
    if value is None and not required:
        return None
    if not isinstance(value, str):
        raise operational_service.OperationalError(
            "VALIDATION_FAILED", f"{field} must be text.", 422
        )
    cleaned = value.strip()
    if required and not cleaned:
        raise operational_service.OperationalError(
            "VALIDATION_FAILED", f"{field} is required.", 422
        )
    if len(cleaned) > maximum:
        raise operational_service.OperationalError(
            "VALIDATION_FAILED", f"{field} must not exceed {maximum} characters.", 422
        )
    return cleaned or None


def _shipment(public_id: str, user: dict[str, Any], *, manage: bool) -> OperationalShipment:
    shipment = operational_service.scoped_shipment(public_id, user)
    operational_service.require_permission(
        user, "work_item.manage" if manage else "work_item.read"
    )
    return shipment


def _action(shipment: OperationalShipment, public_id: str, *, lock: bool = False):
    query = select(OperationalWorkItem).where(
        OperationalWorkItem.organization_id == shipment.organization_id,
        OperationalWorkItem.operational_shipment_id == shipment.id,
        OperationalWorkItem.public_id == public_id,
        OperationalWorkItem.work_type == "FOLLOW_UP",
    )
    if lock:
        query = query.with_for_update()
    row = db.session.scalar(query)
    if row is None:
        raise operational_service.OperationalError(
            "RESOURCE_NOT_FOUND", "Operational Action was not found.", 404
        )
    return row


def _snapshot(row: OperationalWorkItem) -> dict[str, Any]:
    return {
        "public_id": row.public_id,
        "status": row.status,
        "version": row.version,
        "reason": row.reason,
        "expected_result": row.expected_result,
        "latest_follow_up": row.latest_follow_up,
        "latest_follow_up_at": row.latest_follow_up_at.isoformat() if row.latest_follow_up_at else None,
        "resolution_reason": row.resolution_reason,
        "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None,
    }


def _audit(row: OperationalWorkItem, user: dict[str, Any], action: str, metadata=None):
    db.session.add(
        OperationalAudit(
            organization_id=row.organization_id,
            actor_user_id=int(user["id"]),
            action=action,
            entity_type="OperationalWorkItem",
            entity_id=row.id,
            metadata_json=metadata or {},
        )
    )


def serialize(row: OperationalWorkItem) -> dict[str, Any]:
    exception = db.session.get(OperationalException, row.exception_id) if row.exception_id else None
    owner = db.session.get(ExpertUser, row.assignee_user_id) if row.assignee_user_id else None
    return {
        "public_id": row.public_id,
        "shipment_id": row.operational_shipment_id,
        "context": {
            "type": row.action_context_type,
            "exception_public_id": exception.public_id if exception else None,
            "process_type": row.process_type,
        },
        "what": row.reason,
        "why": row.expected_result,
        "expected_result": row.expected_result,
        "responsible": {
            "user_id": row.assignee_user_id,
            "display_name": owner.full_name if owner else None,
            "basis": "SHIPMENT_TRANSPORT_EXPERT",
        },
        "due_at": row.due_at.isoformat(),
        "status": row.status,
        "latest_follow_up": row.latest_follow_up,
        "latest_follow_up_at": row.latest_follow_up_at.isoformat() if row.latest_follow_up_at else None,
        "result": row.resolution_reason,
        "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None,
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
        "version": row.version,
    }


def list_actions(shipment_public_id: str, user: dict[str, Any]) -> list[dict[str, Any]]:
    shipment = _shipment(shipment_public_id, user, manage=False)
    rows = db.session.scalars(
        select(OperationalWorkItem)
        .where(
            OperationalWorkItem.organization_id == shipment.organization_id,
            OperationalWorkItem.operational_shipment_id == shipment.id,
            OperationalWorkItem.work_type == "FOLLOW_UP",
        )
        .order_by(OperationalWorkItem.status, OperationalWorkItem.due_at, OperationalWorkItem.id)
    ).all()
    return [serialize(row) for row in rows]


def create_action(
    shipment_public_id: str, payload: dict[str, Any], user: dict[str, Any]
) -> dict[str, Any]:
    shipment = _shipment(shipment_public_id, user, manage=True)
    what = _text(payload.get("what"), "what", required=True, maximum=1000)
    expected = _text(
        payload.get("expected_result"),
        "expected_result",
        required=False,
        maximum=2000,
    )
    due_at = _parse_instant(payload.get("due_at"), "due_at")
    context_type = str(payload.get("context_type") or "SHIPMENT").upper()
    if context_type not in {"SHIPMENT", "EXCEPTION", "PROCESS"}:
        raise operational_service.OperationalError(
            "VALIDATION_FAILED", "Unsupported Action context.", 422
        )
    exception_id = None
    process_type = None
    if context_type == "EXCEPTION":
        exception = db.session.scalar(
            select(OperationalException).where(
                OperationalException.organization_id == shipment.organization_id,
                OperationalException.operational_shipment_id == shipment.id,
                OperationalException.public_id == payload.get("exception_public_id"),
            )
        )
        if exception is None:
            raise operational_service.OperationalError(
                "RESOURCE_NOT_FOUND", "Operational Exception was not found.", 404
            )
        exception_id = exception.id
    elif context_type == "PROCESS":
        process_type = payload.get("process_type")
        if process_type not in PROCESS_DEFINITIONS:
            raise operational_service.OperationalError(
                "UNSUPPORTED_ACTION_PROCESS",
                "The requested governed process is not supported.",
                422,
            )
    now = utcnow()
    row = OperationalWorkItem(
        organization_id=shipment.organization_id,
        operational_shipment_id=shipment.id,
        exception_id=exception_id,
        action_context_type=context_type,
        process_type=process_type,
        severity="warning",
        detected_at=now,
        work_type="FOLLOW_UP",
        status="open",
        due_at=due_at,
        assignee_user_id=shipment.primary_responsible_expert_id,
        reason=what,
        expected_result=expected,
        created_by_user_id=int(user["id"]),
        created_at=now,
        updated_at=now,
    )
    db.session.add(row)
    db.session.flush()
    _audit(
        row,
        user,
        "operational_action.created",
        {"after": _snapshot(row), "context_type": context_type},
    )
    db.session.commit()
    return serialize(row)


def record_follow_up(
    shipment_public_id: str,
    action_public_id: str,
    payload: dict[str, Any],
    user: dict[str, Any],
) -> dict[str, Any]:
    shipment = _shipment(shipment_public_id, user, manage=True)
    row = _action(shipment, action_public_id, lock=True)
    expected_version = payload.get("expected_version")
    if type(expected_version) is not int or expected_version != row.version:
        raise operational_service.OperationalError(
            "STALE_AGGREGATE_VERSION",
            "Operational Action was changed by another operation.",
            409,
        )
    if row.status != "open":
        raise operational_service.OperationalError(
            "ACTION_ALREADY_RESOLVED", "Operational Action is already resolved.", 409
        )
    note = _text(payload.get("note"), "note", required=True, maximum=4000)
    before = _snapshot(row)
    now = utcnow()
    row.latest_follow_up = note
    row.latest_follow_up_at = now
    row.updated_at = now
    row.version += 1
    _audit(
        row,
        user,
        "operational_action.follow_up_recorded",
        {"before": before, "after": _snapshot(row), "note": note},
    )
    db.session.commit()
    return serialize(row)


def resolve_action(
    shipment_public_id: str,
    action_public_id: str,
    payload: dict[str, Any],
    user: dict[str, Any],
) -> dict[str, Any]:
    shipment = _shipment(shipment_public_id, user, manage=True)
    row = _action(shipment, action_public_id, lock=True)
    expected_version = payload.get("expected_version")
    if type(expected_version) is not int or expected_version != row.version:
        raise operational_service.OperationalError(
            "STALE_AGGREGATE_VERSION",
            "Operational Action was changed by another operation.",
            409,
        )
    if row.status != "open":
        raise operational_service.OperationalError(
            "ACTION_ALREADY_RESOLVED", "Operational Action is already resolved.", 409
        )
    result = _text(payload.get("result"), "result", required=True, maximum=4000)
    before = _snapshot(row)
    now = utcnow()
    row.status = "resolved"
    row.resolution_reason = result
    row.resolution_source = "manual"
    row.latest_follow_up = result
    row.latest_follow_up_at = now
    row.resolved_at = now
    row.resolved_by_user_id = int(user["id"])
    row.updated_at = now
    row.version += 1
    _audit(
        row,
        user,
        "operational_action.resolved",
        {"before": before, "after": _snapshot(row), "result": result},
    )
    db.session.commit()
    return serialize(row)


def action_history(
    shipment_public_id: str, action_public_id: str, user: dict[str, Any]
) -> list[dict[str, Any]]:
    shipment = _shipment(shipment_public_id, user, manage=False)
    row = _action(shipment, action_public_id)
    events = db.session.scalars(
        select(OperationalAudit)
        .where(
            OperationalAudit.organization_id == shipment.organization_id,
            OperationalAudit.entity_type == "OperationalWorkItem",
            OperationalAudit.entity_id == row.id,
            OperationalAudit.action.like("operational_action.%"),
        )
        .order_by(OperationalAudit.recorded_at, OperationalAudit.id)
    ).all()
    return [
        {
            "action": event.action,
            "actor_user_id": event.actor_user_id,
            "occurred_at": event.recorded_at.isoformat(),
            "details": event.metadata_json,
        }
        for event in events
    ]

