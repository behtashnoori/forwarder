"""Service helpers for expert console message workflows."""
from datetime import datetime
from typing import Any, Optional

from backend.extensions import db
from backend.models import ExpertConsoleLog, ExpertConsoleMessage, ExpertUser, ShipmentRequest


class MessageServiceError(Exception):
    """Base service exception that maps to the current message API error payload."""

    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class MessageValidationError(MessageServiceError):
    """Raised for current message validation failures."""

    def __init__(self, message: str):
        super().__init__(message, 400)


class MessageNotFoundError(MessageServiceError):
    """Raised when the target request or expert is missing."""


class MessageAccessError(MessageServiceError):
    """Raised when the current user cannot access the message target request."""


def create_message_for_request(
    request_id: int,
    payload: dict[str, Any],
    user: dict[str, Any],
    remote_addr: Optional[str] = None,
) -> dict[str, Any]:
    """Create a request message and return the current POST message response payload."""
    normalized = normalize_message_payload(payload)
    expert_id = user["id"]

    req = get_message_target_request_or_none(request_id)
    if not req:
        raise MessageNotFoundError("درخواست یافت نشد", 404)
    if not can_access_message_request(req, user):
        raise MessageAccessError("شما به این درخواست دسترسی ندارید", 403)

    expert = db.session.get(ExpertUser, expert_id)
    if not expert:
        raise MessageNotFoundError("کارشناس یافت نشد", 404)

    message = ExpertConsoleMessage(
        shipment_request_id=request_id,
        expert_user_id=expert_id,
        message_type=normalized["message_type"],
        subject=normalized["subject"],
        content=normalized["content"],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.session.add(message)

    log = ExpertConsoleLog(
        shipment_request_id=request_id,
        expert_user_id=expert_id,
        action="message_added",
        note=f"پیام {normalized['message_type']} اضافه شد",
        ip_address=remote_addr,
        created_at=datetime.utcnow(),
    )
    db.session.add(log)

    if normalized["message_type"] == "customer_message":
        req.status = "waiting_for_customer"
        req.last_customer_touch_at = datetime.utcnow()
        req.has_unread_for_assignee = True

    db.session.commit()

    return build_create_message_response_payload(message)


def normalize_message_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize message payload while preserving current defaults."""
    message_type = payload.get("type") or "internal_note"
    subject = payload.get("subject", "")
    content = payload.get("content")

    if not content:
        raise MessageValidationError("محتوای پیام الزامی است")

    return {
        "message_type": message_type,
        "subject": subject,
        "content": content,
    }


def build_create_message_response_payload(message: ExpertConsoleMessage) -> dict[str, Any]:
    """Build the current successful POST message response payload."""
    return {
        "message": "پیام با موفقیت اضافه شد",
        "message_id": message.id,
    }


def build_message_payload(message: ExpertConsoleMessage) -> dict[str, Any]:
    """Build the request-detail message payload shape used by current expert responses."""
    return {
        "id": message.id,
        "type": message.message_type,
        "subject": message.subject,
        "content": message.content,
        "is_read_by_customer": message.is_read_by_customer,
        "customer_response": message.customer_response,
        "created_at": message.created_at.isoformat(),
        "created_by": message.created_by_user.full_name if message.created_by_user else "سیستم",
    }


def get_message_target_request_or_none(request_id: int) -> ShipmentRequest | None:
    """Return the target shipment request for message operations, or None."""
    return db.session.get(ShipmentRequest, request_id)


def can_access_message_request(req: ShipmentRequest, user: dict[str, Any] | None) -> bool:
    """Preserve current message access behavior: admin or assigned expert only."""
    if not user:
        return False
    if user.get("role") == "admin":
        return True
    return req.assigned_to == user.get("id")
