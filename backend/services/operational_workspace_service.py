"""Authorized Operational Workspace Phase 2 read projection.

The Workspace owns no operational truth. It composes the current authorized
Shipment population with domain-owned Exception, Action, SLA commitment and
OIP Attention facts, preserving source permissions and projection freshness.
"""

from __future__ import annotations

import hashlib
from datetime import timezone

from sqlalchemy import case, func, select

from backend.extensions import db
from backend.oip_models import (
    OipAttentionProjection,
    OipFactReference,
    OipSituation,
    OipSituationEvidence,
)
from backend.operational_models import (
    DelayReason,
    ExceptionReason,
    Milestone,
    MilestoneEvent,
    OperationalDelay,
    OperationalException,
    OperationalShipment,
    OperationalSlaCommitment,
    OperationalWorkItem,
    utcnow,
)
from backend.services import operational_read_service
from backend.services import operational_service
from backend.services import oip_service
from backend.services.attention_truth_contract import build_attention_truth_contract
from backend.services.organization_sla_service import shipment_status
from backend.services.shipment_population_service import operational_shipment_population


PROJECTION_VERSION = "operational-workspace-phase-2-v1"
ACTIVE_STATUSES = ("planned", "in_progress")
WORK_ITEM_LABELS = {
    "OVERDUE_MILESTONE": "موعد یک مرحله عملیاتی گذشته است",
    "CHECKPOINT_OVERDUE": "موعد یک نقطه مسیر گذشته است",
    "ROUTE_DEPENDENCY_BLOCKED": "وابستگی مسیر مانع ادامه عملیات است",
    "REPLAN_REQUIRED": "مسیر به بازبینی برنامه نیاز دارد",
    "FOLLOW_UP": "اقدام عملیاتی نیاز به پیگیری دارد",
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


def _shipment_card(
    graph: dict, *, include_follow_up_count: bool, sla: dict | None = None
) -> dict:
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
        "sla": sla,
        "updated_at": graph.get("updated_at"),
    }


def _aware(value):
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _work_item_identity(item: OperationalWorkItem, shipment: OperationalShipment) -> str:
    if item.public_id:
        return item.public_id[:24]
    subject = item.milestone_id or item.checkpoint_id or item.route_plan_id or item.id
    logical = f"{shipment.organization_id}:{shipment.public_id}:{subject}:{item.work_type}"
    return hashlib.sha256(logical.encode("utf-8")).hexdigest()[:24]


def _work_item_attention(item, shipment, card):
    return {
        "identity": _work_item_identity(item, shipment),
        "shipment": card(shipment),
        "kind": item.work_type,
        "label": WORK_ITEM_LABELS.get(item.work_type, "پیگیری عملیاتی باز است"),
        "why": item.reason,
        "time_effect": f"موعد مرتبط: {operational_read_service.iso(item.due_at)}",
        "next_action": (
            item.expected_result
            if item.work_type == "FOLLOW_UP"
            else "پیگیری عملیاتی ثبت‌شده را بررسی کنید."
        ),
        "severity": item.severity,
        "priority": "high" if item.severity == "critical" else "medium",
        "detected_at": operational_read_service.iso(item.detected_at),
        "due_at": operational_read_service.iso(item.due_at),
        "source": {
            "type": "OperationalWorkItem",
            "version": item.version,
            "status": item.status,
        },
        "freshness": {
            "status": "DIRECT_SOURCE",
            "calculated_at": operational_read_service.iso(utcnow()),
            "source_watermark": f"work-item:{item.id}:{item.version}",
        },
        "source_path": f"/operations/shipments/{shipment.public_id}",
    }


def _projection_health(organization_id: int) -> dict:
    health=oip_service.projection_health_for_organization(organization_id)
    return {
        "state":health["health_state"],"trustworthy":health["trustworthy"],
        "calculated_at":health["calculated_at"],"checked_at":health["checked_at"],
        "last_success_at":health["last_evaluation_success_at"],
        "last_attempt_at":health["last_evaluation_attempt_at"],
        "next_evaluation_due_at":health["next_evaluation_due_at"],
        "reason_code":health["reason_code"],"reason":health["reason"],
        "source_watermark":health["source_watermark"],
        "processed_watermark":health["processed_watermark"],"last_run":health["last_run"],
    }


def _situation_fact(situation_id: int):
    return db.session.execute(
        select(OipFactReference)
        .join(
            OipSituationEvidence,
            OipSituationEvidence.fact_reference_id == OipFactReference.id,
        )
        .where(
            OipSituationEvidence.situation_id == situation_id,
            OipSituationEvidence.is_current.is_(True),
        )
        .order_by(OipFactReference.id.desc())
        .limit(1)
    ).scalar_one_or_none()


def _attention_view(
    situation: OipSituation,
    shipment: OperationalShipment,
    permissions: set[str],
    card,
) -> dict | None:
    fact = _situation_fact(situation.id)
    projection = db.session.get(OipAttentionProjection, situation.id)
    item = (
        db.session.get(OperationalWorkItem, projection.operational_work_item_id)
        if projection and projection.operational_work_item_id
        else None
    )
    label = "موضوع عملیاتی نیازمند توجه است"
    why = "یک واقعیت جاری و قابل ردیابی نیاز به بررسی دارد."
    next_action = None
    source_type = fact.source_type if fact else situation.situation_type
    source_public_id = fact.source_public_id if fact else None
    source_version = fact.source_version if fact else situation.policy_version
    time_effect = (
        f"موعد مرتبط: {operational_read_service.iso(situation.due_at)}"
        if situation.due_at
        else "این موضوع موعد ثبت‌شده مستقلی ندارد."
    )

    if situation.situation_type == "ACTION_FOLLOW_UP":
        if "work_item.read" not in permissions or item is None:
            return None
        label = WORK_ITEM_LABELS["FOLLOW_UP"]
        why = item.reason
        next_action = item.expected_result or "آخرین پیگیری یا نتیجه اقدام را ثبت کنید."
        source_type = "OperationalWorkItem"
        source_public_id = item.public_id
        source_version = item.version
    elif situation.situation_type == "SLA_COMMITMENT_RISK":
        commitment_id = (situation.identity_dimensions or {}).get("commitment_public_id")
        commitment = db.session.scalar(
            select(OperationalSlaCommitment).where(
                OperationalSlaCommitment.public_id == commitment_id,
                OperationalSlaCommitment.organization_id == shipment.organization_id,
                OperationalSlaCommitment.operational_shipment_id == shipment.id,
            )
        )
        if commitment is None:
            return None
        if commitment.source_type == "OperationalException" and "operational_execution.read" not in permissions:
            return None
        if commitment.source_type == "OperationalWorkItem" and "work_item.read" not in permissions:
            return None
        label = "SLA نقض شده است" if commitment.evaluation_status == "BREACHED" else "SLA به مرز هشدار نزدیک شده است"
        why = (
            f"{commitment.explanation.get('process_label')} بر اساس قاعده «"
            f"{commitment.rule_snapshot.get('name')}» در وضعیت "
            f"{commitment.evaluation_status} قرار دارد."
        )
        next_action = "منبع فرایند و پیگیری مرتبط را بررسی کنید."
        source_type = "OperationalSlaCommitment"
        source_public_id = commitment.public_id
        source_version = commitment.version
        time_effect = (
            f"شروع: {commitment.started_at.isoformat()}؛ موعد: {commitment.due_at.isoformat()}؛ "
            f"ارزیابی: {commitment.evaluated_at.isoformat()}"
        )
    elif situation.situation_type == "ACTIVE_DELAY_OR_EXCEPTION":
        if "operational_execution.read" not in permissions or fact is None:
            return None
        if fact.source_type == "OperationalException":
            row = db.session.scalar(
                select(OperationalException).where(
                    OperationalException.organization_id == shipment.organization_id,
                    OperationalException.operational_shipment_id == shipment.id,
                    OperationalException.public_id == fact.source_public_id,
                )
            )
            if row is None:
                return None
            reason = db.session.get(ExceptionReason, row.reason_id)
            label = "استثنای عملیاتی باز است"
            why = " · ".join(
                value
                for value in (
                    reason.fa_name if reason else None,
                    row.impact_summary,
                    row.note,
                )
                if value
            ) or label
            next_action = "استثنا و اقدام پیگیری مرتبط را بررسی کنید."
        else:
            row = db.session.scalar(
                select(OperationalDelay).where(
                    OperationalDelay.organization_id == shipment.organization_id,
                    OperationalDelay.operational_shipment_id == shipment.id,
                    OperationalDelay.public_id == fact.source_public_id,
                )
            )
            if row is None:
                return None
            reason = db.session.get(DelayReason, row.reason_id)
            label = "تأخیر عملیاتی فعال است"
            why = reason.fa_name if reason else label
            next_action = "تأخیر و واقعیت‌های مسیر را بررسی کنید."
    elif item is not None:
        if "work_item.read" not in permissions:
            return None
        label = WORK_ITEM_LABELS.get(item.work_type, label)
        why = item.reason
        next_action = "پیگیری عملیاتی ثبت‌شده را بررسی کنید."
        source_type = "OperationalWorkItem"
        source_public_id = item.public_id
        source_version = item.version
    elif situation.situation_type == "DOCUMENT_READINESS_BLOCKED":
        if "document_readiness.read" not in permissions:
            return None
        label = "آمادگی سند مانع ادامه عملیات است"
        why = "یک الزام سند معتبر هنوز برای گذار بعدی آماده نیست."
        next_action = "آمادگی و ارزیابی سند را بررسی کنید."
    else:
        return None

    truth = build_attention_truth_contract(
        shipment_public_id=shipment.public_id,
        situation_identity_key=situation.identity_key,
        policy_id=situation.policy_id,
        policy_version=situation.policy_version,
        source_watermark=situation.source_watermark,
        calculated_at=operational_read_service.iso(situation.calculated_at),
        urgency=situation.urgency,
        severity=situation.severity,
        priority=situation.priority,
    )
    return {
        "identity": situation.identity_key[:24],
        "situation_public_id": situation.public_id,
        "shipment": card(shipment),
        "kind": situation.situation_type,
        "label": label,
        "why": why,
        "time_effect": time_effect,
        "next_action": next_action,
        "severity": situation.severity.lower(),
        "priority": situation.priority.lower(),
        "detected_at": operational_read_service.iso(situation.first_detected_at),
        "due_at": operational_read_service.iso(situation.due_at),
        "source": {
            "type": source_type,
            "public_id": source_public_id,
            "version": source_version,
        },
        "freshness": {
            "status": situation.freshness_status,
            "calculated_at": operational_read_service.iso(situation.calculated_at),
            "source_watermark": situation.source_watermark,
        },
        "truth": truth,
        "source_path": f"/operations/shipments/{shipment.public_id}",
    }


def snapshot(user: dict, limit=8) -> dict:
    """Return one bounded Workspace snapshot with authorization applied first."""
    operational_service.require_permission(user, "operational_shipment.read")
    context = operational_service.operational_context(user)
    permissions = set(context["permissions"])
    attention_available = bool(
        permissions.intersection(
            {"work_item.read", "operational_execution.read", "document_readiness.read"}
        )
    )
    limit = _bounded_limit(limit)

    active = (
        operational_shipment_population(user)
        .order_by(None)
        .where(OperationalShipment.lifecycle_status.in_(ACTIVE_STATUSES))
    )
    active_ids = active.with_only_columns(OperationalShipment.id).order_by(None)
    active_public_ids = active.with_only_columns(OperationalShipment.public_id).order_by(None)
    active_count = db.session.scalar(
        select(func.count()).select_from(active.order_by(None).subquery())
    ) or 0
    active_rows = db.session.scalars(
        active.order_by(
            OperationalShipment.updated_at.desc(),
            OperationalShipment.public_id.asc(),
        ).limit(limit)
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
    sla_cache: dict[int, dict] = {}
    allowed_sla_sources = set()
    if "operational_execution.read" in permissions:
        allowed_sla_sources.add("OperationalException")
    if "work_item.read" in permissions:
        allowed_sla_sources.add("OperationalWorkItem")

    def graph(shipment: OperationalShipment) -> dict:
        if shipment.id not in graph_cache:
            graph_cache[shipment.id] = operational_service.shipment_graph(shipment)
        return graph_cache[shipment.id]

    def card(shipment: OperationalShipment) -> dict:
        if shipment.id not in sla_cache:
            sla_cache[shipment.id] = shipment_status(
                shipment, allowed_source_types=allowed_sla_sources
            )
        return _shipment_card(
            graph(shipment),
            include_follow_up_count="work_item.read" in permissions,
            sla=sla_cache[shipment.id],
        )

    shipments = [card(row) for row in active_rows]
    attention = []
    included_work_item_ids = set()
    if attention_available:
        situations = db.session.scalars(
            select(OipSituation)
            .where(
                OipSituation.organization_id == context["organization_id"],
                OipSituation.subject_type == "SHIPMENT",
                OipSituation.subject_public_id.in_(active_public_ids),
                OipSituation.status.in_(("OPEN", "ACKNOWLEDGED", "IN_PROGRESS", "SNOOZED")),
                OipSituation.freshness_status == "FRESH",
            )
            .order_by(
                case(
                    (OipSituation.priority == "CRITICAL", 0),
                    (OipSituation.priority == "HIGH", 1),
                    (OipSituation.priority == "MEDIUM", 2),
                    else_=3,
                ),
                OipSituation.due_at.asc().nullslast(),
                OipSituation.public_id,
            )
        ).all()
        shipments_by_public = {
            row.public_id: row
            for row in db.session.scalars(
                select(OperationalShipment).where(OperationalShipment.id.in_(active_ids))
            ).all()
        }
        now = utcnow()
        for situation in situations:
            if situation.status == "SNOOZED" and situation.snoozed_until and _aware(situation.snoozed_until) > _aware(now):
                continue
            shipment = shipments_by_public.get(situation.subject_public_id)
            if shipment is None:
                continue
            view = _attention_view(situation, shipment, permissions, card)
            if view is not None:
                attention.append(view)
                projection = db.session.get(OipAttentionProjection, situation.id)
                if projection and projection.operational_work_item_id:
                    included_work_item_ids.add(projection.operational_work_item_id)

    if "work_item.read" in permissions:
        direct_rows = db.session.execute(
            select(OperationalWorkItem, OperationalShipment)
            .join(
                OperationalShipment,
                OperationalShipment.id == OperationalWorkItem.operational_shipment_id,
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
        ).all()
        for item, shipment in direct_rows:
            if item.id not in included_work_item_ids:
                attention.append(_work_item_attention(item, shipment, card))

    attention.sort(
        key=lambda row: (
            0 if row["priority"] in {"critical", "high"} else 1,
            row.get("due_at") or "9999",
            row["identity"],
        )
    )
    attention_count = len(attention) if attention_available else None
    attention = attention[:limit]

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
            "attention_projection": _projection_health(context["organization_id"]),
            "calculated_at": operational_read_service.iso(utcnow()),
            "projection_version": PROJECTION_VERSION,
            "sources": [
                "OperationalShipment",
                "OperationalException",
                "OperationalWorkItem",
                "OrganizationSlaRule",
                "OperationalSlaCommitment",
                "OipSituation",
                "MilestoneEvent",
            ],
            "limitations": [
                "SLA is evaluated only for explicitly configured supported processes.",
                "Missing SLA configuration is reported as SLA تعریف نشده.",
                "Attention is deterministic and advisory; it never changes operational truth.",
                "No prediction, AI score, or autonomous operational decision is applied.",
            ],
        },
    }
