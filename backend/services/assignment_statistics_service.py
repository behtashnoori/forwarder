"""Service helpers for user-management assignment statistics endpoint."""
from __future__ import annotations

from typing import Any


def normalize_assignment_statistics(raw_stats: dict[str, Any]) -> dict[str, Any]:
    """Keep the current assignment engine statistics payload unchanged."""
    return raw_stats


def build_assignment_statistics_response_payload(raw_stats: dict[str, Any]) -> dict[str, Any]:
    """Build the current assignment statistics response payload."""
    return normalize_assignment_statistics(raw_stats)


def get_assignment_statistics_payload(context=None) -> dict[str, Any]:
    """Fetch assignment statistics from the current assignment engine."""
    if context is not None:
        from backend.extensions import db
        from backend.models import ExpertUser
        from backend.operational_models import OperationalMembership
        from backend.services.expert_workload_service import organization_workloads
        experts = (
            db.session.query(ExpertUser)
            .join(OperationalMembership, OperationalMembership.user_id == ExpertUser.id)
            .filter(
                OperationalMembership.organization_id == context.organization_id,
                OperationalMembership.is_active.is_(True),
                ExpertUser.is_active.is_(True),
                ExpertUser.role.in_(["expert", "business_expert"]),
            )
            .order_by(ExpertUser.full_name)
            .all()
        )
        counts = organization_workloads(context.organization_id, [item.id for item in experts])
        return {
            "expert_workloads": [
                {"expert_id": item.id, "expert_name": item.full_name, "workload": counts.get(item.id, 0)}
                for item in experts
            ],
            "displayed_workload_statuses": ["assigned", "in_progress"],
            "assignment_strategy_note": "Workload is informational unless a least_workload referral strategy is selected.",
        }
    from backend.assignment_engine import assignment_engine

    raw_stats = assignment_engine.get_assignment_statistics()
    return build_assignment_statistics_response_payload(raw_stats)
