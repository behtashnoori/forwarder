"""Service helpers for expert console request detail responses."""
from datetime import datetime, timedelta
from typing import Any, Optional

from backend.extensions import db
from backend.models import (
    ExpertConsoleLog,
    ExpertConsoleMessage,
    ExpertQuote,
    ExpertUser,
    ShipmentRequest,
)
from backend.services import message_service, quote_service
from backend.services.legacy_datetime import serialize_legacy_utc_datetime
from backend.services.route_payload_service import build_route_payload
from backend.services.ownership_service import tenant_organization_for_user


class ExpertRequestDetailServiceError(Exception):
    """Base service exception that maps to the current request-detail API payload."""

    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class RequestDetailNotFoundError(ExpertRequestDetailServiceError):
    """Raised when the target shipment request is missing."""

    def __init__(self):
        super().__init__("درخواست یافت نشد", 404)


class RequestDetailAccessError(ExpertRequestDetailServiceError):
    """Raised when the current user cannot access the shipment request."""

    def __init__(self):
        super().__init__("شما به این درخواست دسترسی ندارید", 403)


def get_expert_request_detail(request_id: int, user: Optional[dict[str, Any]]) -> dict[str, Any]:
    """Return the current expert request-detail response payload."""
    req = get_request_detail_target_or_none(request_id)
    if not req:
        raise RequestDetailNotFoundError()
    if not can_access_request_detail(req, user):
        raise RequestDetailAccessError()
    return build_request_detail_payload(req)


def get_request_detail_target_or_none(request_id: int) -> ShipmentRequest | None:
    """Return the target shipment request for detail display, or None."""
    return db.session.get(ShipmentRequest, request_id)


def can_access_request_detail(req: ShipmentRequest, user: Optional[dict[str, Any]]) -> bool:
    """Preserve current request-detail access behavior: admin or assigned expert only."""
    if not user:
        return False
    try:
        organization_id = tenant_organization_for_user(user)
    except ValueError:
        return False
    if req.ownership_scope != "TENANT" or req.operational_organization_id != organization_id:
        return False
    if user.get("role") == "admin":
        return True
    return req.assigned_to == user.get("id")


def build_request_detail_payload(req: ShipmentRequest) -> dict[str, Any]:
    """Build the current request-detail response payload."""
    return {
        "id": req.id,
        "public_id": req.public_id,
        "tracking_number": req.tracking_code if getattr(req, "tracking_code", None) else f"SR{req.id:06d}",
        "status": req.status,
        "priority": req.priority,
        "created_at": serialize_legacy_utc_datetime(req.created_at),
        "sla_due_at": req.sla_due_at.isoformat() if req.sla_due_at else None,
        "sla_status": build_sla_status(req),
        "assigned_to": build_assignment_detail_payload(req),
        "customer": build_customer_detail_payload(req),
        "route": build_route_detail_payload(req),
        "transport_method": req.transport_method,
        "cargo": build_cargo_detail_payload(req),
        "dates": build_dates_detail_payload(req),
        "timeline": build_timeline_payload(req.id),
        "messages": build_messages_payload(req.id),
        "has_unread": req.has_unread_for_assignee,
        "latest_quote": build_latest_quote_payload(req.id),
    }


def build_assignment_detail_payload(req: ShipmentRequest) -> dict[str, Any] | None:
    """Build the current assigned expert payload."""
    assigned_expert = db.session.get(ExpertUser, req.assigned_to) if req.assigned_to else None
    return {
        "id": assigned_expert.id,
        "name": assigned_expert.full_name,
        "username": assigned_expert.username,
    } if assigned_expert else None


def build_customer_detail_payload(req: ShipmentRequest) -> dict[str, Any]:
    """Build the current customer payload."""
    return {
        "first_name": req.customer_first_name,
        "last_name": req.customer_last_name,
        "phone": req.contact_phone,
        "full_name": f"{req.customer_first_name or ''} {req.customer_last_name or ''}".strip() or "نامشخص",
    }


def build_route_detail_payload(req: ShipmentRequest) -> dict[str, Any]:
    """Build the route payload with human-readable names for domestic and international."""
    return build_route_payload(req)


def build_cargo_detail_payload(req: ShipmentRequest) -> dict[str, Any]:
    """Build the current cargo payload."""
    return {
        "description": req.cargo_description,
        "weight": req.cargo_weight,
        "volume": req.cargo_volume,
        "value": req.cargo_value,
        "special_instructions": req.special_instructions,
    }


def build_dates_detail_payload(req: ShipmentRequest) -> dict[str, Any]:
    """Build the current date payload."""
    return {
        "pickup_date": req.pickup_date.isoformat() if req.pickup_date else None,
        "delivery_date": req.delivery_date.isoformat() if req.delivery_date else None,
    }


def build_timeline_payload(request_id: int) -> list[dict[str, Any]]:
    """Build the current expert-console timeline payload."""
    logs = db.session.query(ExpertConsoleLog).filter(
        ExpertConsoleLog.shipment_request_id == request_id
    ).order_by(ExpertConsoleLog.created_at.desc()).all()
    return [
        {
            "id": log.id,
            "action": log.action,
            "old_status": log.old_status,
            "new_status": log.new_status,
            "note": log.note,
            "created_at": log.created_at.isoformat(),
            "created_by": log.created_by_user.full_name if log.created_by_user else "سیستم",
        }
        for log in logs
    ]


def build_messages_payload(request_id: int) -> list[dict[str, Any]]:
    """Build the current messages payload for request detail."""
    messages = db.session.query(ExpertConsoleMessage).filter(
        ExpertConsoleMessage.shipment_request_id == request_id
    ).order_by(ExpertConsoleMessage.created_at.desc()).all()
    return [message_service.build_message_payload(message) for message in messages]


def build_latest_quote_payload(request_id: int) -> dict[str, Any] | None:
    """Build the current latest quote payload, preserving the safe failure behavior."""
    try:
        latest_quote_row = (
            db.session.query(ExpertQuote)
            .filter(ExpertQuote.shipment_request_id == request_id)
            .order_by(ExpertQuote.created_at.desc())
            .first()
        )
        if latest_quote_row:
            return quote_service.build_quote_payload(latest_quote_row, include_created_by=True)
    except Exception:
        pass
    return None


def build_sla_status(req: ShipmentRequest) -> str:
    """Calculate the current request-detail SLA status."""
    sla_status = "on_time"
    if req.sla_due_at:
        if datetime.utcnow() > req.sla_due_at:
            sla_status = "overdue"
        elif datetime.utcnow() + timedelta(hours=2) > req.sla_due_at:
            sla_status = "due_soon"
    return sla_status
