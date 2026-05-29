"""Service helpers for admin-managed SLA policies."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, Iterable, Optional

from backend.extensions import db
from backend.models import ShipmentRequest, SlaPolicy


ALLOWED_PRIORITY_SCOPES = {"low", "normal", "high", "urgent", "all"}
ALLOWED_SHIPPING_TYPE_SCOPES = {"domestic", "international", "all"}
DEFAULT_REQUEST_STATUS_SCOPE = ["assigned", "in_progress"]
LEGACY_RESPONSE_TIME_MINUTES = 120
LEGACY_NEAR_DEADLINE_THRESHOLD_MINUTES = 120
EXPERT_ACTIVE_SLA_STATUSES = {"assigned", "in_progress"}


class SlaPolicyServiceError(Exception):
    """Base service exception that maps to SLA policy API error payloads."""

    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class SlaPolicyValidationError(SlaPolicyServiceError):
    """Raised when an SLA policy payload is invalid."""

    def __init__(self, message: str):
        super().__init__(message, 400)


class SlaPolicyNotFoundError(SlaPolicyServiceError):
    """Raised when an SLA policy cannot be found."""

    def __init__(self, message: str = "SLA policy not found"):
        super().__init__(message, 404)


def list_sla_policies() -> dict[str, Any]:
    """Return SLA policies in deterministic admin-list order."""
    policies = db.session.query(SlaPolicy).order_by(
        SlaPolicy.sort_order.asc(),
        SlaPolicy.name.asc(),
        SlaPolicy.id.asc(),
    ).all()
    return {"sla_policies": [build_sla_policy_payload(policy) for policy in policies]}


def create_sla_policy(payload: dict[str, Any]) -> dict[str, Any]:
    """Create an SLA policy and return the admin response payload."""
    normalized = normalize_sla_policy_payload(payload, require_name=True)
    now = datetime.utcnow()
    policy = SlaPolicy(
        name=normalized["name"],
        priority_scope=normalized["priority_scope"],
        request_status_scope=json.dumps(normalized["request_status_scope"]),
        transport_method_scope=normalized["transport_method_scope"],
        shipping_type_scope=normalized["shipping_type_scope"],
        response_time_minutes=normalized["response_time_minutes"],
        near_deadline_threshold_minutes=normalized["near_deadline_threshold_minutes"],
        is_active=normalized["is_active"],
        sort_order=normalized["sort_order"],
        created_at=now,
        updated_at=now,
    )
    db.session.add(policy)
    db.session.commit()
    return {"message": "SLA policy created", "sla_policy": build_sla_policy_payload(policy)}


def update_sla_policy(policy_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    """Update an SLA policy and return the admin response payload."""
    policy = db.session.get(SlaPolicy, policy_id)
    if not policy:
        raise SlaPolicyNotFoundError()

    normalized = normalize_sla_policy_payload(payload, require_name=False, existing_policy=policy)
    policy.name = normalized["name"]
    policy.priority_scope = normalized["priority_scope"]
    policy.request_status_scope = json.dumps(normalized["request_status_scope"])
    policy.transport_method_scope = normalized["transport_method_scope"]
    policy.shipping_type_scope = normalized["shipping_type_scope"]
    policy.response_time_minutes = normalized["response_time_minutes"]
    policy.near_deadline_threshold_minutes = normalized["near_deadline_threshold_minutes"]
    policy.is_active = normalized["is_active"]
    policy.sort_order = normalized["sort_order"]
    policy.updated_at = datetime.utcnow()
    db.session.commit()
    return {"message": "SLA policy updated", "sla_policy": build_sla_policy_payload(policy)}


def set_sla_policy_active(policy_id: int, is_active: bool) -> dict[str, Any]:
    """Enable or disable an SLA policy idempotently."""
    policy = db.session.get(SlaPolicy, policy_id)
    if not policy:
        raise SlaPolicyNotFoundError()
    policy.is_active = is_active
    policy.updated_at = datetime.utcnow()
    db.session.commit()
    return {"message": "SLA policy updated", "sla_policy": build_sla_policy_payload(policy)}


def resolve_sla_policy(
    request_or_priority: ShipmentRequest | str | None = None,
    status: Optional[str] = None,
    transport_method: Optional[str] = None,
    shipping_type: Optional[str] = None,
) -> SlaPolicy | None:
    """Return the first active SLA policy matching the context, or None for legacy fallback."""
    if isinstance(request_or_priority, ShipmentRequest):
        priority = request_or_priority.priority or "normal"
        request_status = status or request_or_priority.status or request_or_priority.status_request_status
        request_transport_method = (
            transport_method
            or request_or_priority.domestic_transport_method
            or request_or_priority.international_transport_method
            or request_or_priority.transport_method
        )
        request_shipping_type = shipping_type or request_or_priority.shipping_type
    else:
        priority = request_or_priority or "normal"
        request_status = status
        request_transport_method = transport_method
        request_shipping_type = shipping_type

    policies = db.session.query(SlaPolicy).filter(SlaPolicy.is_active == True).order_by(
        SlaPolicy.sort_order.asc(),
        SlaPolicy.name.asc(),
        SlaPolicy.id.asc(),
    ).all()

    for policy in policies:
        if not policy_matches_context(
            policy,
            priority=str(priority),
            status=request_status,
            transport_method=request_transport_method,
            shipping_type=request_shipping_type,
        ):
            continue
        return policy
    return None


def calculate_due_at(start_time: datetime, policy: SlaPolicy | None = None) -> datetime:
    """Calculate SLA due date using a policy or current legacy fallback."""
    minutes = policy.response_time_minutes if policy else LEGACY_RESPONSE_TIME_MINUTES
    return start_time + timedelta(minutes=minutes)


def calculate_due_at_for_request(
    request_row: ShipmentRequest,
    start_time: datetime,
    target_status: str = "assigned",
) -> datetime:
    """Calculate an SLA due date for a request/status context."""
    policy = resolve_sla_policy(request_row, status=target_status)
    return calculate_due_at(start_time, policy)


def assign_sla_due_at_if_needed(
    request_row: ShipmentRequest,
    start_time: datetime | None = None,
    target_status: str = "assigned",
) -> bool:
    """Set request SLA due date only when it is currently empty."""
    if request_row.sla_due_at:
        return False
    request_row.sla_due_at = calculate_due_at_for_request(
        request_row,
        start_time or datetime.utcnow(),
        target_status=target_status,
    )
    return True


def calculate_sla_status(
    sla_due_at: datetime | None,
    policy: SlaPolicy | None = None,
    now: datetime | None = None,
) -> str:
    """Calculate current SLA status using a policy threshold or legacy fallback."""
    if not sla_due_at:
        return "on_time"

    current_time = now or datetime.utcnow()
    if current_time > sla_due_at:
        return "overdue"

    threshold = (
        policy.near_deadline_threshold_minutes
        if policy
        else LEGACY_NEAR_DEADLINE_THRESHOLD_MINUTES
    )
    if current_time + timedelta(minutes=threshold) > sla_due_at:
        return "due_soon"
    return "on_time"


def calculate_request_sla_status(
    request_row: ShipmentRequest,
    status: str | None = None,
    now: datetime | None = None,
) -> str:
    """Calculate request SLA status using the matching active policy or legacy fallback."""
    policy = resolve_sla_policy(request_row, status=status or request_row.status)
    return calculate_sla_status(request_row.sla_due_at, policy=policy, now=now)


def request_has_active_sla_status(
    request_row: ShipmentRequest,
    active_statuses: set[str] | None = None,
) -> bool:
    """Return whether either current status field is active for SLA counting."""
    statuses = active_statuses or EXPERT_ACTIVE_SLA_STATUSES
    return request_row.status in statuses or request_row.status_request_status in statuses


def policy_matches_context(
    policy: SlaPolicy,
    priority: str = "normal",
    status: Optional[str] = None,
    transport_method: Optional[str] = None,
    shipping_type: Optional[str] = None,
) -> bool:
    """Return whether a policy applies to a request/status context."""
    if policy.priority_scope != "all" and policy.priority_scope != priority:
        return False

    status_scope = parse_request_status_scope(policy.request_status_scope)
    if status and status not in status_scope:
        return False

    if policy.transport_method_scope and transport_method:
        if policy.transport_method_scope != transport_method:
            return False
    elif policy.transport_method_scope and not transport_method:
        return False

    if policy.shipping_type_scope and policy.shipping_type_scope != "all":
        if shipping_type != policy.shipping_type_scope:
            return False

    return True


def build_sla_policy_payload(policy: SlaPolicy) -> dict[str, Any]:
    """Build the stable admin SLA policy response payload."""
    return {
        "id": policy.id,
        "name": policy.name,
        "priority_scope": policy.priority_scope,
        "request_status_scope": parse_request_status_scope(policy.request_status_scope),
        "transport_method_scope": policy.transport_method_scope,
        "shipping_type_scope": policy.shipping_type_scope,
        "response_time_minutes": policy.response_time_minutes,
        "near_deadline_threshold_minutes": policy.near_deadline_threshold_minutes,
        "is_active": policy.is_active,
        "sort_order": policy.sort_order,
        "created_at": policy.created_at.isoformat() if policy.created_at else None,
        "updated_at": policy.updated_at.isoformat() if policy.updated_at else None,
    }


def normalize_sla_policy_payload(
    payload: dict[str, Any],
    require_name: bool,
    existing_policy: SlaPolicy | None = None,
) -> dict[str, Any]:
    """Validate and normalize create/update payloads."""
    name = payload.get("name", existing_policy.name if existing_policy else None)
    if require_name and not is_non_empty_string(name):
        raise SlaPolicyValidationError("name is required")
    if name is not None and not is_non_empty_string(name):
        raise SlaPolicyValidationError("name is required")

    priority_scope = payload.get(
        "priority_scope",
        existing_policy.priority_scope if existing_policy else "all",
    )
    if priority_scope not in ALLOWED_PRIORITY_SCOPES:
        raise SlaPolicyValidationError("priority_scope is invalid")

    request_status_scope = payload.get(
        "request_status_scope",
        parse_request_status_scope(existing_policy.request_status_scope)
        if existing_policy
        else DEFAULT_REQUEST_STATUS_SCOPE,
    )
    request_status_scope = normalize_status_scope(request_status_scope)

    response_time_minutes = normalize_positive_int(
        payload.get(
            "response_time_minutes",
            existing_policy.response_time_minutes if existing_policy else None,
        ),
        "response_time_minutes",
    )
    near_deadline_threshold_minutes = normalize_positive_int(
        payload.get(
            "near_deadline_threshold_minutes",
            existing_policy.near_deadline_threshold_minutes if existing_policy else None,
        ),
        "near_deadline_threshold_minutes",
    )
    if near_deadline_threshold_minutes > response_time_minutes:
        raise SlaPolicyValidationError(
            "near_deadline_threshold_minutes cannot exceed response_time_minutes"
        )

    shipping_type_scope = payload.get(
        "shipping_type_scope",
        existing_policy.shipping_type_scope if existing_policy else None,
    )
    if shipping_type_scope == "":
        shipping_type_scope = None
    if shipping_type_scope is not None and shipping_type_scope not in ALLOWED_SHIPPING_TYPE_SCOPES:
        raise SlaPolicyValidationError("shipping_type_scope is invalid")

    transport_method_scope = payload.get(
        "transport_method_scope",
        existing_policy.transport_method_scope if existing_policy else None,
    )
    if transport_method_scope == "":
        transport_method_scope = None
    if transport_method_scope is not None and not is_non_empty_string(transport_method_scope):
        raise SlaPolicyValidationError("transport_method_scope is invalid")

    sort_order = normalize_int(
        payload.get("sort_order", existing_policy.sort_order if existing_policy else 100),
        "sort_order",
    )

    is_active = payload.get("is_active", existing_policy.is_active if existing_policy else True)
    if not isinstance(is_active, bool):
        raise SlaPolicyValidationError("is_active must be boolean")

    return {
        "name": name.strip(),
        "priority_scope": priority_scope,
        "request_status_scope": request_status_scope,
        "transport_method_scope": transport_method_scope.strip() if transport_method_scope else None,
        "shipping_type_scope": shipping_type_scope,
        "response_time_minutes": response_time_minutes,
        "near_deadline_threshold_minutes": near_deadline_threshold_minutes,
        "is_active": is_active,
        "sort_order": sort_order,
    }


def normalize_status_scope(value: Any) -> list[str]:
    """Normalize request_status_scope to a non-empty list of strings."""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            value = [value]

    if not isinstance(value, list) or not value:
        raise SlaPolicyValidationError("request_status_scope must be a non-empty list")

    statuses = []
    for item in value:
        if not is_non_empty_string(item):
            raise SlaPolicyValidationError("request_status_scope must contain strings")
        statuses.append(item.strip())
    return statuses


def parse_request_status_scope(value: str | Iterable[str] | None) -> list[str]:
    """Parse stored request status scope safely."""
    if value is None:
        return list(DEFAULT_REQUEST_STATUS_SCOPE)
    if isinstance(value, list):
        return [str(item) for item in value]
    try:
        parsed = json.loads(value)
    except Exception:
        return list(DEFAULT_REQUEST_STATUS_SCOPE)
    if not isinstance(parsed, list) or not parsed:
        return list(DEFAULT_REQUEST_STATUS_SCOPE)
    return [str(item) for item in parsed]


def normalize_positive_int(value: Any, field_name: str) -> int:
    """Normalize positive integer payload fields."""
    normalized = normalize_int(value, field_name)
    if normalized <= 0:
        raise SlaPolicyValidationError(f"{field_name} must be positive")
    return normalized


def normalize_int(value: Any, field_name: str) -> int:
    """Normalize integer payload fields."""
    if isinstance(value, bool) or value is None:
        raise SlaPolicyValidationError(f"{field_name} must be integer")
    try:
        return int(value)
    except (TypeError, ValueError):
        raise SlaPolicyValidationError(f"{field_name} must be integer")


def is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())
