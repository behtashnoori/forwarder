"""Service helpers for admin referral rule workflows."""
import json
from datetime import datetime
from typing import Any, Optional

from backend.extensions import db
from backend.models import ReferralRule, ReferralRuleState
from backend.referral_engine import referral_engine


class ReferralServiceError(Exception):
    """Base service exception that maps to the current referral API error payload."""

    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class ReferralValidationError(ReferralServiceError):
    """Raised for current referral validation failures."""

    def __init__(self, message: str):
        super().__init__(message, 400)


class ReferralUnauthorizedError(ReferralServiceError):
    """Raised when the current referral action has no authenticated actor."""

    def __init__(self, message: str = "احراز هویت نشده"):
        super().__init__(message, 401)


class ReferralNotFoundError(ReferralServiceError):
    """Raised when a referral rule is missing."""

    def __init__(self, message: str = "قانون ارجاع یافت نشد"):
        super().__init__(message, 404)


def list_referral_rules(filters: Optional[dict[str, Any]] = None, context=None) -> dict[str, Any]:
    """Return the current referral-rules list response payload."""
    _ = filters
    query = db.session.query(ReferralRule)
    if context is not None:
        query = query.filter(ReferralRule.operational_organization_id == context.organization_id)
    rules = query.order_by(
        ReferralRule.priority.asc(), ReferralRule.name
    ).all()
    return {"referral_rules": [build_referral_rule_payload(rule) for rule in rules]}


def build_referral_rule_payload(rule: ReferralRule) -> dict[str, Any]:
    """Build the current referral-rule JSON payload."""
    try:
        conditions = json.loads(rule.conditions) if rule.conditions else {}
    except Exception:
        conditions = {}
    try:
        action = json.loads(rule.action) if rule.action else {}
    except Exception:
        action = {}

    action_type = action.get("type", "")
    expert_ids = (action.get("expert_ids") or []) if action_type == "pool_assign" else []
    return {
        "id": rule.id,
        "name": rule.name,
        "is_active": rule.is_active,
        "priority": rule.priority,
        "conditions": conditions,
        "action": action,
        "stop_on_match": getattr(rule, "stop_on_match", True),
        "created_by": rule.creator.id if rule.creator else None,
        "created_at": rule.created_at.isoformat() if rule.created_at else None,
        "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
        "action_type": action_type,
        "pool_expert_count": len(expert_ids) if action_type == "pool_assign" else 0,
        "strategy": action.get("strategy") if action_type == "pool_assign" else None,
    }


def create_referral_rule(payload: dict[str, Any], actor: Optional[dict[str, Any]], context=None) -> dict[str, Any]:
    """Create a referral rule and return the current success payload."""
    if not actor:
        raise ReferralUnauthorizedError()
    normalized = normalize_referral_payload(payload, require_name=True)
    validate_referral_experts(normalized["action"], context)
    rule = ReferralRule(
        name=normalized["name"],
        is_active=payload.get("is_active", True),
        priority=int(payload.get("priority", 1)),
        conditions=json.dumps(normalized["conditions"]),
        action=json.dumps(normalized["action"]),
        stop_on_match=payload.get("stop_on_match", True),
        created_by=actor.get("id"),
        operational_organization_id=context.organization_id if context else None,
    )
    db.session.add(rule)
    db.session.commit()
    return {"message": "قانون ارجاع با موفقیت ایجاد شد", "rule_id": rule.id}


def update_referral_rule(rule_id: int, payload: dict[str, Any], context=None) -> dict[str, Any]:
    """Update a referral rule and return the current success payload."""
    query = db.session.query(ReferralRule).filter(ReferralRule.id == rule_id)
    if context is not None: query = query.filter(ReferralRule.operational_organization_id == context.organization_id)
    rule = query.one_or_none()
    if not rule:
        raise ReferralNotFoundError()

    if "name" in payload and payload["name"]:
        rule.name = payload["name"].strip()
    if "is_active" in payload:
        rule.is_active = bool(payload["is_active"])
    if "priority" in payload:
        rule.priority = int(payload["priority"])
    if "stop_on_match" in payload:
        rule.stop_on_match = bool(payload["stop_on_match"])
    if "conditions" in payload:
        rule.conditions = json.dumps(payload["conditions"])
    if "action" in payload:
        action = payload["action"]
        validate_referral_action_for_update(action)
        validate_referral_experts(action, context)
        rule.action = json.dumps(action)
    rule.updated_at = datetime.utcnow()
    db.session.commit()
    return {"message": "قانون ارجاع به‌روزرسانی شد"}


def delete_referral_rule(rule_id: int, context=None) -> dict[str, Any]:
    """Delete a referral rule and its state while preserving audit logs."""
    query = db.session.query(ReferralRule).filter(ReferralRule.id == rule_id)
    if context is not None: query = query.filter(ReferralRule.operational_organization_id == context.organization_id)
    rule = query.one_or_none()
    if not rule:
        raise ReferralNotFoundError()
    db.session.query(ReferralRuleState).filter(ReferralRuleState.rule_id == rule_id).delete()
    db.session.delete(rule)
    db.session.commit()
    return {"message": "قانون ارجاع حذف شد"}


def preview_referral_assignment(payload: dict[str, Any], context=None) -> dict[str, Any]:
    """Run the current dry-run referral preview behavior."""
    request_id = payload.get("request_id")
    if request_id is None:
        raise ReferralValidationError("request_id الزامی است")
    if context is not None:
        from backend.models import ShipmentRequest
        visible = db.session.query(ShipmentRequest.id).filter(ShipmentRequest.id == int(request_id), ShipmentRequest.operational_organization_id == context.organization_id, ShipmentRequest.ownership_scope == "TENANT").first()
        if not visible: raise ReferralNotFoundError("Request not found")
    result = referral_engine.preview_assignment(int(request_id))
    return build_referral_preview_payload(result)


def build_referral_preview_payload(result: dict[str, Any]) -> dict[str, Any]:
    """Return the current preview payload unchanged."""
    return result


def run_referral_auto_assignment(payload: Optional[dict[str, Any]] = None, actor: Optional[dict[str, Any]] = None) -> Any:
    """Run current referral auto-assignment behavior for a request id payload."""
    _ = actor
    payload = payload or {}
    request_id = payload.get("request_id")
    if request_id is None:
        raise ReferralValidationError("request_id الزامی است")
    return referral_engine.auto_assign_request(int(request_id))


def build_referral_assignment_payload(result: Any) -> dict[str, Any]:
    """Build a minimal referral assignment payload for future route extraction."""
    return {"assigned_expert_id": result}


def create_referral_log_if_needed(*args: Any, **kwargs: Any) -> None:
    """Referral logs are currently created by the referral engine."""
    _ = args, kwargs
    return None


def validate_referral_experts(action: dict[str, Any], context=None) -> None:
    if context is None:
        return
    from backend.operational_models import OperationalMembership
    values = [action.get("expert_id")] if action.get("type") == "direct_assign" else list(action.get("expert_ids") or [])
    expert_ids = {int(value) for value in values if value is not None}
    matched = db.session.query(OperationalMembership.user_id).filter(
        OperationalMembership.organization_id == context.organization_id,
        OperationalMembership.user_id.in_(expert_ids),
        OperationalMembership.is_active.is_(True),
    ).distinct().count()
    if matched != len(expert_ids):
        raise ReferralValidationError("All referral experts must belong to the same organization.")


def normalize_referral_payload(payload: dict[str, Any], require_name: bool = False) -> dict[str, Any]:
    """Validate referral create payload while preserving current error text."""
    name = payload.get("name")
    if require_name and (not name or not name.strip()):
        raise ReferralValidationError("نام قانون الزامی است")

    conditions = payload.get("conditions")
    if conditions is None:
        conditions = {}
    action = payload.get("action")
    validate_referral_action_for_create(action)

    return {
        "name": name.strip() if name else name,
        "conditions": conditions,
        "action": action,
    }


def validate_referral_action_for_create(action: Any) -> None:
    """Validate create action using the current route error messages."""
    if not action or action.get("type") not in ("direct_assign", "pool_assign"):
        raise ReferralValidationError("action باید نوع direct_assign یا pool_assign داشته باشد")
    if action.get("type") == "direct_assign" and action.get("expert_id") is None:
        raise ReferralValidationError("برای direct_assign مقدار expert_id الزامی است")
    if action.get("type") == "pool_assign":
        if not action.get("expert_ids"):
            raise ReferralValidationError("برای pool_assign لیست expert_ids الزامی است")
        if action.get("strategy") not in ("round_robin", "least_workload"):
            raise ReferralValidationError("برای pool_assign strategy باید round_robin یا least_workload باشد")


def validate_referral_action_for_update(action: Any) -> None:
    """Validate update action using the current route error messages."""
    if action.get("type") not in ("direct_assign", "pool_assign"):
        raise ReferralValidationError("action.type باید direct_assign یا pool_assign باشد")
    if action.get("type") == "pool_assign" and action.get("strategy") not in ("round_robin", "least_workload"):
        raise ReferralValidationError("strategy باید round_robin یا least_workload باشد")
