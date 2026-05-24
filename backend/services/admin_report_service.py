"""Service helpers for admin report payloads."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import and_, case, func

from backend.extensions import db
from backend.models import AssignmentLog, ExpertConsoleLog, ExpertUser, ShipmentRequest


def get_assignment_summary_payload() -> dict[str, Any]:
    """Return the current admin assignment summary report payload."""
    return build_assignment_summary_response_payload()


def build_assignment_summary_response_payload() -> dict[str, Any]:
    """Build the assignment summary payload with the existing report calculations."""
    assignments_per_expert, total_assignments, total_won = build_assignments_per_expert()

    return {
        "assignments_per_expert": assignments_per_expert,
        "overall_stats": build_overall_assignment_stats(total_assignments, total_won),
        "generated_at": datetime.utcnow().isoformat(),
    }


def build_assignments_per_expert() -> tuple[list[dict[str, Any]], int, int]:
    """Return per-expert assignment rows and the aggregate totals used by the report."""
    experts_with_assignments = (
        db.session.query(
            ExpertUser.id,
            ExpertUser.full_name,
            ExpertUser.username,
            ExpertUser.role,
            func.count(ShipmentRequest.id).label("total_assignments"),
            func.sum(case((ShipmentRequest.status == "won", 1), else_=0)).label("won_count"),
            func.sum(case((ShipmentRequest.status == "lost", 1), else_=0)).label("lost_count"),
            func.sum(
                case((ShipmentRequest.status.in_(["assigned", "in_progress"]), 1), else_=0)
            ).label("active_count"),
        )
        .join(
            ShipmentRequest,
            ShipmentRequest.assigned_to == ExpertUser.id,
        )
        .filter(ExpertUser.is_active == True)
        .group_by(ExpertUser.id, ExpertUser.full_name, ExpertUser.username, ExpertUser.role)
        .all()
    )

    assignments_per_expert = []
    total_won = 0
    total_assignments = 0

    for expert_stat in experts_with_assignments:
        total = expert_stat.total_assignments or 0
        won = expert_stat.won_count or 0
        lost = expert_stat.lost_count or 0
        active = expert_stat.active_count or 0
        avg_response_time = None

        assignments_per_expert.append(
            {
                "expert_id": expert_stat.id,
                "expert_name": expert_stat.full_name,
                "username": expert_stat.username,
                "role": expert_stat.role,
                "total_assignments": total,
                "won_count": won,
                "lost_count": lost,
                "active_count": active,
                "conversion_rate": round(calculate_conversion_rate(won, total), 2),
                "avg_response_time_hours": (
                    round(avg_response_time, 2) if avg_response_time else None
                ),
            }
        )

        total_won += won
        total_assignments += total

    return assignments_per_expert, total_assignments, total_won


def build_overall_assignment_stats(total_assignments: int, total_won: int) -> dict[str, Any]:
    """Return the existing overall assignment summary fields."""
    avg_response_time = calculate_avg_response_time_hours()

    return {
        "total_assignments": total_assignments,
        "total_won": total_won,
        "overall_conversion_rate": round(
            calculate_conversion_rate(total_won, total_assignments),
            2,
        ),
        "avg_response_time_hours": round(avg_response_time, 2) if avg_response_time else None,
        "sla_violations": calculate_sla_violations(),
    }


def calculate_avg_response_time_hours() -> float | None:
    """Calculate response time in Python to keep the report SQLite-compatible."""
    response_time_rows = (
        db.session.query(
            AssignmentLog.created_at.label("assignment_created_at"),
            ExpertConsoleLog.created_at.label("action_created_at"),
        )
        .join(
            AssignmentLog,
            ExpertConsoleLog.shipment_request_id == AssignmentLog.shipment_request_id,
        )
        .filter(
            and_(
                ExpertConsoleLog.action.notin_(["status_change", "assigned"]),
                ExpertConsoleLog.created_at > AssignmentLog.created_at,
            )
        )
        .all()
    )

    response_time_hours = [
        (row.action_created_at - row.assignment_created_at).total_seconds() / 3600
        for row in response_time_rows
        if row.action_created_at and row.assignment_created_at
    ]

    if not response_time_hours:
        return None

    return sum(response_time_hours) / len(response_time_hours)


def calculate_conversion_rate(won_count: int, total_count: int) -> float:
    """Return the current percentage calculation used by assignment reports."""
    return (won_count / total_count * 100) if total_count > 0 else 0


def calculate_sla_violations() -> int:
    """Return active assigned requests that are past their SLA due date."""
    return (
        db.session.query(func.count(ShipmentRequest.id))
        .filter(
            and_(
                ShipmentRequest.sla_due_at.isnot(None),
                ShipmentRequest.sla_due_at < datetime.utcnow(),
                ShipmentRequest.status.in_(
                    ["assigned", "in_progress", "waiting_for_customer"]
                ),
            )
        )
        .scalar()
        or 0
    )
