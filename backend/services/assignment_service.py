"""Service helpers for expert assignment workflows."""
from datetime import datetime
from typing import Any, Optional

from backend.extensions import db
from backend.models import ExpertConsoleLog, ExpertConsoleNotification, ExpertUser, ShipmentRequest
from backend.services.expert_scope_service import can_handle_request
from backend.services.sla_service import set_initial_assignment_sla
from backend.services.ownership_service import tenant_organization_for_user


class AssignmentServiceError(Exception):
    """Base service exception that maps to the current assignment API error payload."""

    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class AssignmentValidationError(AssignmentServiceError):
    """Raised for current assignment validation failures."""

    def __init__(self, message: str):
        super().__init__(message, 400)


class AssignmentNotFoundError(AssignmentServiceError):
    """Raised when the target request or expert is missing."""


class AssignmentAccessError(AssignmentServiceError):
    """Raised when the current actor cannot assign the target request."""


def assign_request_to_expert(
    request_id: int,
    expert_id: Any = None,
    actor: Optional[dict[str, Any]] = None,
    payload: Optional[dict[str, Any]] = None,
    remote_addr: Optional[str] = None,
    organization_context=None,
) -> dict[str, Any]:
    """Assign a shipment request to an expert and return the current response payload."""
    target_expert_id = expert_id
    if payload is not None:
        target_expert_id = normalize_assignment_payload(payload)["expert_id"]
    elif not target_expert_id:
        raise AssignmentValidationError("شناسه کارشناس الزامی است")

    req = get_assignment_target_request_or_none(request_id)
    if not req:
        raise AssignmentNotFoundError("درخواست یافت نشد", 404)
    if not can_assign_request(req, actor):
        raise AssignmentAccessError("شما به این درخواست دسترسی ندارید", 403)

    expert = get_assignment_target_expert_or_none(target_expert_id)
    if not expert:
        raise AssignmentNotFoundError("کارشناس یافت نشد", 404)
    if not expert.is_active:
        raise AssignmentValidationError("کارشناس غیرفعال است")

    if organization_context is not None:
        from backend.operational_models import OperationalMembership
        if req.ownership_scope != "TENANT" or req.operational_organization_id != organization_context.organization_id:
            raise AssignmentNotFoundError("Request not found", 404)
        memberships = db.session.query(OperationalMembership).filter(OperationalMembership.user_id == expert.id, OperationalMembership.is_active.is_(True)).all()
        if len(memberships) != 1 or memberships[0].organization_id != organization_context.organization_id:
            raise AssignmentNotFoundError("Expert not found", 404)

    if not can_handle_request(expert, req):
        raise AssignmentValidationError("حوزه فعالیت کارشناس با نوع درخواست سازگار نیست")

    old_status = req.status
    req.assigned_to = target_expert_id
    req.status = "assigned"
    req.has_unread_for_assignee = True
    set_initial_assignment_sla(req, expert)

    create_assignment_log(request_id, target_expert_id, old_status, expert.full_name, remote_addr)
    create_assignment_notification_if_needed(request_id, target_expert_id)

    db.session.commit()

    return build_assignment_response_payload(expert)


def manual_assign_request(
    payload: dict[str, Any],
    actor: Optional[dict[str, Any]] = None,
    remote_addr: Optional[str] = None,
    organization_context=None,
) -> dict[str, Any]:
    """Validate the user-management manual assignment payload and use the shared assignment path."""
    normalized = normalize_manual_assignment_payload(payload)
    return assign_request_to_expert(
        normalized["request_id"],
        expert_id=normalized["expert_id"],
        actor=actor,
        remote_addr=remote_addr,
        organization_context=organization_context,
    )


def assign_request_to_current_user(
    request_id: int, actor: Optional[dict[str, Any]], remote_addr: Optional[str] = None
) -> dict[str, Any]:
    """Assign an unassigned tenant request using only the trusted session identity."""
    if not actor or actor.get("id") is None:
        raise AssignmentAccessError("احراز هویت نشده", 401)
    req = get_assignment_target_request_or_none(request_id)
    if not req:
        raise AssignmentNotFoundError("درخواست یافت نشد", 404)
    try:
        organization_id = tenant_organization_for_user(actor)
    except ValueError as exc:
        raise AssignmentAccessError("عضویت سازمانی معتبر الزامی است", 403) from exc
    if req.ownership_scope != "TENANT" or req.operational_organization_id != organization_id:
        raise AssignmentNotFoundError("درخواست یافت نشد", 404)
    if req.assigned_to not in (None, int(actor["id"])):
        raise AssignmentAccessError("درخواست قبلاً تخصیص یافته است", 409)
    expert = db.session.get(ExpertUser, int(actor["id"]))
    if not expert or not can_handle_request(expert, req):
        raise AssignmentValidationError("کاربر فعلی کارشناس واجد شرایط این درخواست نیست")
    if req.assigned_to == expert.id:
        return build_assignment_response_payload(expert)
    old_status = req.status
    req.assigned_to = expert.id
    req.status = "assigned"
    req.has_unread_for_assignee = True
    set_initial_assignment_sla(req, expert)
    create_assignment_log(req.id, expert.id, old_status, expert.full_name, remote_addr)
    create_assignment_notification_if_needed(req.id, expert.id)
    db.session.commit()
    return build_assignment_response_payload(expert)


def normalize_manual_assignment_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize the manual assignment payload."""
    request_id = payload.get("request_id")
    if not request_id:
        raise AssignmentValidationError("شناسه درخواست الزامی است")

    expert_id = payload.get("expert_id")
    if not expert_id:
        raise AssignmentValidationError("شناسه کارشناس الزامی است")

    return {"request_id": request_id, "expert_id": expert_id}


def normalize_assignment_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize the current assignment payload."""
    expert_id = payload.get("expert_id")
    if not expert_id:
        raise AssignmentValidationError("شناسه کارشناس الزامی است")
    return {"expert_id": expert_id}


def get_assignment_target_request_or_none(request_id: int) -> ShipmentRequest | None:
    """Return the target shipment request for assignment operations, or None."""
    return db.session.get(ShipmentRequest, request_id)


def get_assignment_target_expert_or_none(expert_id: Any) -> ExpertUser | None:
    """Return the target expert for assignment operations, or None."""
    return db.session.get(ExpertUser, expert_id)


def can_assign_request(req: ShipmentRequest, actor: dict[str, Any] | None) -> bool:
    """Preserve current assignment access behavior: admin or assigned expert only."""
    if not actor:
        return False
    if actor.get("role") == "admin" or actor.get("authority") in {"PLATFORM_ADMIN", "ORGANIZATION_ADMIN"}:
        return True
    return req.assigned_to == actor.get("id")


def create_assignment_log(
    request_id: int,
    expert_id: Any,
    old_status: str | None,
    expert_full_name: str,
    remote_addr: Optional[str] = None,
) -> ExpertConsoleLog:
    """Create the current expert-console assignment log entry."""
    log = ExpertConsoleLog(
        shipment_request_id=request_id,
        expert_user_id=expert_id,
        action="assignment",
        old_status=old_status,
        new_status="assigned",
        note=f"ارجاع به کارشناس: {expert_full_name}",
        ip_address=remote_addr,
        created_at=datetime.utcnow(),
    )
    db.session.add(log)
    return log


def create_assignment_notification_if_needed(request_id: int, expert_id: Any) -> ExpertConsoleNotification:
    """Create the current expert-console assignment notification."""
    notification = ExpertConsoleNotification(
        expert_user_id=expert_id,
        shipment_request_id=request_id,
        notification_type="assignment",
        title="ارجاع درخواست جدید",
        message=f"درخواست {request_id} به شما ارجاع داده شد",
        is_read=False,
        created_at=datetime.utcnow(),
    )
    db.session.add(notification)
    return notification


def build_assignment_response_payload(expert: ExpertUser) -> dict[str, Any]:
    """Build the current successful assignment response payload."""
    return {
        "message": "درخواست با موفقیت ارجاع داده شد",
        "assigned_to": {
            "id": expert.id,
            "name": expert.full_name,
        },
    }


def preserve_manual_assignment_failure() -> None:
    """Preserve the currently documented manual-assignment 500 behavior."""
    raise RuntimeError("manual assignment currently fails before processing payload")
