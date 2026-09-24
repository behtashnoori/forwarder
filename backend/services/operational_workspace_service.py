"""Read-only Operational Workspace Phase 1 projection.

The Workspace composes existing authorized Shipment, WorkItem, and event facts.
It stores no state and introduces no attention, SLA, or task lifecycle.
"""

from __future__ import annotations

import hashlib

from sqlalchemy import case, func, select

from backend.extensions import db
from backend.operational_models import (
    Milestone,
    MilestoneEvent,
    OperationalShipment,
    OperationalWorkItem,
    utcnow,
)
from backend.services import operational_read_service
from backend.services import operational_service
from backend.services.shipment_population_service import operational_shipment_population


PROJECTION_VERSION = "operational-workspace-phase-1-v1"
ACTIVE_STATUSES = ("planned", "in_progress")
WORK_ITEM_LABELS = {
    "OVERDUE_MILESTONE": "موعد یک مرحله عملیاتی گذشته است",
    "CHECKPOINT_OVERDUE": "موعد یک نقطه مسیر گذشته است",
    "ROUTE_DEPENDENCY_BLOCKED": "وابستگی مسیر مانع ادامه عملیات است",
    "REPLAN_REQUIRED": "مسیر به بازبینی برنامه نیاز دارد",
}


def _bounded_limit(value) -> int:
    try:
        limit = int(value or 8)
    except (TypeError, ValueError) as exc:
        raise operational_service.OperationalError(
            "VALIDATION_FAILED", "limit must be an integer.", 422
        ) from exc
    if limit < 1 or limit > 20:
        raise operational_service.OperationalError(
            "VALIDATION_FAILED", "limit must be between 1 and 20.", 422
        )
    return limit


def _shipment_card(graph: dict, *, include_follow_up_count: bool) -> dict:
    customer = graph.get("customer")
    if isinstance(customer, dict):
        customer = {"display_name": customer.get("display_name")}
    return {
        "public_id": graph["public_id"],
        "status": graph["status"],
        "customer": customer,
        "responsible_expert": graph.get("responsible_expert"),
        "route_summary": graph.get("route_summary"),
        "current_milestone": graph.get("current_milestone"),
        "latest_update": graph.get("latest_update"),
        "overdue": graph.get("overdue", False),
        "overdue_since": graph.get("overdue_since"),
        "open_work_item_count": (
            graph.get("open_work_item_count", 0) if include_follow_up_count else None
        ),
        "updated_at": graph.get("updated_at"),
    }


def _attention_identity(item: OperationalWorkItem, shipment: OperationalShipment) -> str:
    if item.milestone_id is not None:
        subject = f"milestone:{item.milestone_id}"
    elif item.checkpoint_id is not None:
        subject = f"checkpoint:{item.checkpoint_id}"
    else:
        subject = f"route-plan:{item.route_plan_id}"
    logical_identity = (
        f"{shipment.organization_id}:{shipment.public_id}:{subject}:{item.work_type}"
    )
    return hashlib.sha256(logical_identity.encode("utf-8")).hexdigest()[:24]


def snapshot(user: dict, limit=8) -> dict:
    """Return one bounded Workspace snapshot with authorization applied first."""
    operational_service.require_permission(user, "operational_shipment.read")
    permissions = set(operational_service.operational_context(user)["permissions"])
    attention_available = "work_item.read" in permissions
    limit = _bounded_limit(limit)

    active = (
        operational_shipment_population(user)
        .order_by(None)
        .where(OperationalShipment.lifecycle_status.in_(ACTIVE_STATUSES))
    )
    active_ids = active.with_only_columns(OperationalShipment.id).order_by(None)
    active_count = db.session.scalar(
        select(func.count()).select_from(active.order_by(None).subquery())
    ) or 0
    active_rows = db.session.scalars(
        active.order_by(
            OperationalShipment.updated_at.desc(),
            OperationalShipment.public_id.asc(),
        ).limit(limit)
    ).all()

    attention_count = None
    attention_rows = []
    if attention_available:
        attention_count = db.session.scalar(
            select(func.count())
            .select_from(OperationalWorkItem)
            .where(
                OperationalWorkItem.operational_shipment_id.in_(active_ids),
                OperationalWorkItem.status == "open",
            )
        ) or 0
        attention_rows = db.session.execute(
            select(OperationalWorkItem, OperationalShipment)
            .join(
                OperationalShipment,
                OperationalShipment.id
                == OperationalWorkItem.operational_shipment_id,
            )
            .where(
                OperationalShipment.id.in_(active_ids),
                OperationalWorkItem.status == "open",
            )
            .order_by(
                case((OperationalWorkItem.severity == "critical", 0), else_=1),
                OperationalWorkItem.due_at.asc(),
                OperationalWorkItem.id.asc(),
            )
            .limit(limit)
        ).all()

    recent_rows = db.session.execute(
        select(MilestoneEvent, Milestone, OperationalShipment)
        .join(Milestone, Milestone.id == MilestoneEvent.milestone_id)
        .join(
            OperationalShipment,
            OperationalShipment.id == Milestone.operational_shipment_id,
        )
        .where(
            OperationalShipment.id.in_(active_ids),
            Milestone.organization_id == OperationalShipment.organization_id,
            MilestoneEvent.organization_id == OperationalShipment.organization_id,
        )
        .order_by(MilestoneEvent.recorded_at.desc(), MilestoneEvent.id.desc())
        .limit(limit)
    ).all()

    graph_cache: dict[int, dict] = {}

    def graph(shipment: OperationalShipment) -> dict:
        if shipment.id not in graph_cache:
            graph_cache[shipment.id] = operational_service.shipment_graph(shipment)
        return graph_cache[shipment.id]

    def card(shipment: OperationalShipment) -> dict:
        return _shipment_card(
            graph(shipment), include_follow_up_count=attention_available
        )

    shipments = [card(row) for row in active_rows]
    attention = []
    for item, shipment in attention_rows:
        attention.append(
            {
                "identity": _attention_identity(item, shipment),
                "shipment": card(shipment),
                "kind": item.work_type,
                "label": WORK_ITEM_LABELS.get(
                    item.work_type, "پیگیری عملیاتی باز است"
                ),
                "severity": item.severity,
                "detected_at": operational_read_service.iso(item.detected_at),
                "due_at": operational_read_service.iso(item.due_at),
                "source": {
                    "type": "OperationalWorkItem",
                    "version": item.version,
                    "status": item.status,
                },
                "source_path": f"/operations/shipments/{shipment.public_id}",
            }
        )

    recent_updates = []
    for event, milestone, shipment in recent_rows:
        event_view = operational_read_service.event_view(event, shipment)
        recent_updates.append(
            {
                "event_public_id": event_view["public_id"],
                "shipment_public_id": shipment.public_id,
                "customer": card(shipment)["customer"],
                "label": event_view["business_label"],
                "milestone_type": milestone.milestone_type,
                "occurred_at": event_view["occurred_at"],
                "recorded_at": event_view["recorded_at"],
                "source": event_view["source_channel"],
            }
        )

    return {
        "data": {
            "active_shipments": shipments,
            "attention_items": attention,
            "recent_updates": recent_updates,
        },
        "meta": {
            "active_shipment_count": active_count,
            "open_follow_up_count": attention_count,
            "attention_available": attention_available,
            "calculated_at": operational_read_service.iso(utcnow()),
            "projection_version": PROJECTION_VERSION,
            "sources": [
                "OperationalShipment",
                "OperationalWorkItem",
                "MilestoneEvent",
            ],
            "limitations": [
                "Only existing open operational follow-ups are attention signals.",
                "Follow-up details require the existing work_item.read capability.",
                "No SLA threshold, prediction, or AI prioritization is applied.",
            ],
        },
    }
