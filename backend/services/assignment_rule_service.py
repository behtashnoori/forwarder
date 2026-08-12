"""Service helpers for user-management assignment rule endpoints."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import desc

from backend.extensions import db
from backend.models import AssignmentRule


def parse_conditions(value: str) -> Any:
    """Parse stored assignment rule conditions for response payloads."""
    return json.loads(value)


def serialize_conditions(value: Any) -> str:
    """Serialize request conditions using the existing JSON storage behavior."""
    return json.dumps(value if value is not None else {})


def normalize_assignment_rule_payload(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    """Keep the route's current payload semantics while centralizing the handoff."""
    return payload


def build_assignment_rule_payload(rule: AssignmentRule) -> dict[str, Any]:
    """Build the current assignment rule response item shape."""
    return {
        "id": rule.id,
        "name": rule.name,
        "description": rule.description,
        "rule_type": rule.rule_type,
        "conditions": parse_conditions(rule.conditions),
        "priority": rule.priority,
        "is_active": rule.is_active,
        "created_by": {
            "id": rule.creator.id,
            "name": rule.creator.full_name,
        },
        "created_at": rule.created_at.isoformat(),
        "updated_at": rule.updated_at.isoformat(),
    }


def list_assignment_rules(context=None) -> list[dict[str, Any]]:
    """List assignment rules in the existing priority/name order."""
    query = db.session.query(AssignmentRule)
    if context is not None: query = query.filter(AssignmentRule.operational_organization_id == context.organization_id)
    rules = query.order_by(
        desc(AssignmentRule.priority),
        AssignmentRule.name,
    ).all()
    return [build_assignment_rule_payload(rule) for rule in rules]


def get_assignment_rule_or_none(rule_id: int, context=None) -> AssignmentRule | None:
    """Return an assignment rule by id, preserving the existing lookup behavior."""
    query = db.session.query(AssignmentRule).filter(AssignmentRule.id == rule_id)
    if context is not None: query = query.filter(AssignmentRule.operational_organization_id == context.organization_id)
    return query.one_or_none()


def create_assignment_rule(payload: dict[str, Any] | None, created_by_user_id: int, context=None) -> AssignmentRule:
    """Create and commit an assignment rule using the existing field defaults."""
    data = normalize_assignment_rule_payload(payload)
    rule = AssignmentRule(
        name=data.get("name"),
        description=data.get("description"),
        rule_type=data.get("rule_type"),
        conditions=serialize_conditions(data.get("conditions", {})),
        priority=data.get("priority", 1),
        is_active=data.get("is_active", True),
        created_by=created_by_user_id,
        operational_organization_id=context.organization_id if context else None,
    )

    db.session.add(rule)
    db.session.commit()
    return rule


def update_assignment_rule(rule_id: int, payload: dict[str, Any] | None, context=None) -> AssignmentRule | None:
    """Update and commit an assignment rule, returning None for current not-found behavior."""
    rule = get_assignment_rule_or_none(rule_id, context)
    if not rule:
        return None

    data = normalize_assignment_rule_payload(payload)
    updatable_fields = ["name", "description", "rule_type", "priority", "is_active"]
    for field in updatable_fields:
        if field in data:
            setattr(rule, field, data[field])

    if "conditions" in data:
        rule.conditions = serialize_conditions(data["conditions"])

    rule.updated_at = datetime.utcnow()
    db.session.commit()
    return rule
