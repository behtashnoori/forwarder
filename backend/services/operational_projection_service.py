"""Guided operational projection assembled from existing domain authorities.

This module owns no operational truth and performs no writes.  It is rebuilt
on request after the Shipment has been scoped by the existing authorization
boundary.  The UI may use its ranking and recommendations as navigation help;
domain services remain authoritative for every fact and command.
"""

from __future__ import annotations

from datetime import timezone

from sqlalchemy import select

from backend.cargo_models import ShipmentCargoItem
from backend.extensions import db
from backend.models import City, ShipmentRequest
from backend.operational_models import (
    OperationalShipment,
    Project,
    RoutePlan,
    RouteStageExecution,
    utcnow,
)
from backend.services import closure_service, eta_service, operational_read_service
from backend.services import operational_service, reported_fact_service
from backend.services import shipment_stage_service
from backend.services.assigned_work_authorization import authorize_document_management


PROJECTION_VERSION = "guided-operational-workspace-v2"
PRECEDENCE_ORDER = {
    "BLOCKING_PRECONDITION": 10,
    "CURRENT_REQUIRED_WORK": 20,
    "NEXT_REQUIRED_LIFECYCLE": 30,
    "CLOSURE_BLOCKER": 40,
    "OPTIONAL_IMPROVEMENT": 50,
    "INFORMATIONAL": 60,
}
ATTENTION_ORDER = {
    "FINAL_DELIVERY_EXISTS": 10,
    "REQUIRED_DOCUMENTS_READY": 20,
    "NO_BLOCKING_OPERATIONAL_ISSUE": 30,
    "REQUIRED_OPERATIONAL_STAGES_COMPLETE": 40,
    "ACTUAL_CARGO_UNKNOWN": 10,
    "ACTUAL_ALLOCATION_DIFFERS_FROM_PLANNED": 20,
    "DELIVERED_DIFFERS_FROM_PLANNED": 30,
    "OPTIONAL_DOCUMENTS_ABSENT": 40,
    "ETA_UNAVAILABLE": 50,
    "NON_BLOCKING_OPERATIONAL_WARNINGS": 60,
}
SOURCE_TYPES = [
    "OperationalShipment",
    "Project",
    "ShipmentRequest",
    "RoutePlan",
    "RouteLeg",
    "RouteStageExecution",
    "ShipmentOperationalStageEvent",
    "ShipmentCargoItem",
    "OperationalDocumentRequirement",
    "OperationalEvent",
    "CargoEta",
    "Delivery",
    "OperationalException",
    "OperationalWorkItem",
    "ClosurePolicy",
]


def _aware(value):
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _request_route(request_row: ShipmentRequest | None) -> dict | None:
    if request_row is None:
        return None
    origin_city = db.session.get(City, request_row.origin_city_id) if request_row.origin_city_id else None
    destination_city = db.session.get(City, request_row.dest_city_id) if request_row.dest_city_id else None
    origin = request_row.origin_city_international or (origin_city.name_fa if origin_city else None)
    destination = request_row.dest_city_international or (destination_city.name_fa if destination_city else None)
    if not origin and not destination:
        return None
    return {
        "origin": origin,
        "destination": destination,
        "shipping_type": request_row.shipping_type,
    }


def _identity(shipment: OperationalShipment, graph: dict) -> dict:
    project = db.session.get(Project, shipment.project_id) if shipment.project_id else None
    request_row = db.session.get(ShipmentRequest, shipment.shipment_request_id) if shipment.shipment_request_id else None
    customer = graph.get("customer")
    customer_name = customer.get("display_name") if isinstance(customer, dict) else customer
    if project:
        label, source = project.project_code, "PROJECT_CODE"
    elif request_row and request_row.tracking_code:
        label, source = request_row.tracking_code, "REQUEST_TRACKING_CODE"
    elif customer_name:
        label, source = f"عملیات حمل {customer_name}", "CUSTOMER_CONTEXT"
    else:
        label, source = "عملیات حمل مستقیم", "DIRECT_OPERATION"
    return {
        "label": label,
        "source": source,
        "technical_id": shipment.public_id,
        "requested_route": _request_route(request_row),
    }


def _stage_projection(shipment: OperationalShipment, user: dict) -> dict:
    stage_view = shipment_stage_service.read(shipment.public_id, user)
    stages = stage_view.get("stages", [])
    completed = sum(1 for row in stages if row["status"] == "COMPLETED")
    current = next((row for row in stages if row["status"] != "COMPLETED"), None)
    return {
        "completed": completed,
        "total": len(stages),
        "current": current,
        "items": stages,
        "can_record": bool(stage_view.get("can_record")),
        "configured": stage_view.get("configuration") is not None,
    }


def _criterion(assessment: dict, code: str) -> dict | None:
    return next((item for item in assessment.get("items", []) if item["code"] == code), None)


def _status(item: dict | None, *, empty: str = "UNKNOWN") -> str:
    if item is None:
        return empty
    return "DONE" if item["state"] == "PASS" else "UNKNOWN" if item["state"] == "UNKNOWN" else "NEEDS_ACTION"


def _task(
    key: str,
    label: str,
    status: str,
    section: str,
    *,
    required: bool,
    category: str = "INFORMATIONAL",
    precedence: str = "INFORMATIONAL",
    blocking: bool = False,
    source_code: str | None = None,
    action_label: str | None = None,
    reason: str | None = None,
) -> dict:
    return {
        "key": key,
        "label": label,
        "status": status,
        "section": section,
        "required": required,
        "category": category,
        "precedence": precedence,
        "blocking": blocking,
        "source_code": source_code,
        "action_label": action_label,
        "reason": reason,
    }


def _tasks(shipment: OperationalShipment, graph: dict, stages: dict, assessment: dict) -> list[dict]:
    plan = db.session.scalar(select(RoutePlan).where(
        RoutePlan.operational_shipment_id == shipment.id,
        RoutePlan.is_active.is_(True),
    ))
    legs = graph.get("route_legs") or []
    execution_count = db.session.scalar(select(RouteStageExecution.id).where(
        RouteStageExecution.operational_shipment_id == shipment.id,
    ).limit(1))
    route_status = "DONE" if plan else "NEEDS_ACTION"
    execution_status = (
        "NOT_APPLICABLE" if not plan else
        "DONE" if legs and execution_count else
        "NEEDS_ACTION"
    )
    stage_status = (
        "UNKNOWN" if not stages["configured"] else
        "DONE" if stages["total"] and stages["completed"] == stages["total"] else
        "IN_PROGRESS" if stages["completed"] else
        "NEEDS_ACTION"
    )
    closed = shipment.lifecycle_status == "closed"
    cargo = _criterion(assessment, "ACTUAL_CARGO_UNKNOWN")
    documents = _criterion(assessment, "REQUIRED_DOCUMENTS_READY")
    tracking = _criterion(assessment, "ETA_UNAVAILABLE")
    delivery = _criterion(assessment, "FINAL_DELIVERY_EXISTS")

    def assessed_task(
        key: str,
        label: str,
        section: str,
        item: dict | None,
        *,
        required: bool,
        warning: bool = False,
        action_label: str,
        reason: str,
    ) -> dict:
        status = _status(item)
        incomplete = status != "DONE"
        return _task(
            key, label, status, section, required=required,
            category="WARNING" if warning and incomplete else "BLOCKER" if incomplete else "INFORMATIONAL",
            precedence="OPTIONAL_IMPROVEMENT" if warning and incomplete else "CLOSURE_BLOCKER" if incomplete else "INFORMATIONAL",
            blocking=bool(incomplete and not warning),
            source_code=item.get("code") if item else None,
            action_label=action_label,
            reason=reason,
        )

    route_task = _task(
        "route", "مسیر عملیاتی", route_status, "route", required=True,
        category="BLOCKER" if route_status != "DONE" else "INFORMATIONAL",
        precedence="BLOCKING_PRECONDITION" if route_status != "DONE" else "INFORMATIONAL",
        blocking=route_status != "DONE",
        action_label="تعریف مسیر عملیاتی",
        reason="برای شروع اجرا، مسیر فعال لازم است.",
    )
    execution_task = _task(
        "execution", "اجرای حمل", execution_status, "route", required=True,
        category="BLOCKER" if execution_status == "NEEDS_ACTION" else "INFORMATIONAL",
        precedence="BLOCKING_PRECONDITION" if execution_status == "NEEDS_ACTION" else "INFORMATIONAL",
        blocking=execution_status == "NEEDS_ACTION",
        action_label="تکمیل اجرای حمل",
        reason="وسیله یا اجرای حمل برای مسیر فعال کامل نشده است.",
    )
    stage_action = _stage_action(shipment, stages)
    stage_incomplete = stage_status not in {"DONE", "UNKNOWN"}
    stage_task = _task(
        "stages", "مراحل فرایند", stage_status, "stages", required=True,
        category="NEEDS_ACTION" if stage_incomplete else "BLOCKER" if stage_status == "UNKNOWN" else "INFORMATIONAL",
        precedence=(
            "CURRENT_REQUIRED_WORK"
            if (stages.get("current") or {}).get("status") == "STARTED"
            else "NEXT_REQUIRED_LIFECYCLE"
            if stage_incomplete
            else "BLOCKING_PRECONDITION"
            if stage_status == "UNKNOWN"
            else "INFORMATIONAL"
        ),
        blocking=stage_status != "DONE",
        source_code="REQUIRED_OPERATIONAL_STAGES_COMPLETE",
        action_label=stage_action[2] if stage_action else "ثبت پیشرفت مرحله جاری",
        reason=stage_action[3] if stage_action else "وضعیت مراحل عملیاتی برای ادامه باید روشن باشد.",
    )
    closure_status = "DONE" if closed else "READY" if assessment.get("normal_ready") else "BLOCKED"
    tasks = [
        route_task,
        execution_task,
        stage_task,
        assessed_task(
            "cargo", "واقعیت کالای حمل‌شده", "cargo", cargo, required=False, warning=True,
            action_label="تکمیل واقعیت کالای حمل‌شده",
            reason="مقدار واقعی یک یا چند قلم هنوز قطعی نیست؛ این مورد هشدار است و مانع چرخه نیست.",
        ),
        assessed_task(
            "documents", "مدارک الزامی", "documents", documents, required=True,
            action_label="رفع سند اجباری",
            reason="آمادگی یک یا چند سند الزامی کامل نیست.",
        ),
        assessed_task(
            "tracking", "موقعیت و زمان رسیدن", "tracking", tracking, required=False, warning=True,
            action_label="ثبت موقعیت یا پیشرفت",
            reason="زمان رسیدن در دسترس نیست؛ این مورد هشدار است و مانع چرخه نیست.",
        ),
        assessed_task(
            "delivery", "تحویل نهایی", "delivery", delivery, required=True,
            action_label="ثبت تحویل نهایی",
            reason="تحویل نهایی محموله هنوز به‌صراحت ثبت نشده است.",
        ),
        _task(
            "closure", "آمادگی بستن پرونده", closure_status, "closure", required=True,
            category="NEEDS_ACTION" if closure_status == "READY" else "INFORMATIONAL",
            precedence="NEXT_REQUIRED_LIFECYCLE" if closure_status == "READY" else "INFORMATIONAL",
            blocking=False,
            action_label="بررسی و بستن پرونده",
            reason="همه الزامات بستن عادی آماده‌اند.",
        ),
    ]
    if closed:
        return [{
            **task,
            "category": "INFORMATIONAL",
            "precedence": "INFORMATIONAL",
            "blocking": False,
            "action_label": None,
        } for task in tasks]
    return tasks


def _attention(
    graph: dict,
    assessment: dict,
    permissions: set[str],
    tasks: list[dict],
    *,
    closed: bool = False,
) -> list[dict]:
    items: list[dict] = []
    for task in tasks:
        if task["status"] in {"DONE", "NOT_APPLICABLE", "READY"} or task["category"] == "INFORMATIONAL":
            continue
        items.append({
            "key": f"task-{task['key']}",
            "source_code": task.get("source_code"),
            "category": task["category"],
            "severity": task["category"],
            "blocking": task["blocking"],
            "precedence": task["precedence"],
            "label": task["label"],
            "action_label": task.get("action_label"),
            "reason": task.get("reason") or "این کار برای ادامه نیازمند توجه است.",
            "section": task["section"],
        })
    if graph.get("overdue"):
        items.append({
            "key": "overdue-milestone", "source_code": None,
            "category": "NEEDS_ACTION", "severity": "NEEDS_ACTION", "blocking": False,
            "precedence": "OPTIONAL_IMPROVEMENT", "label": "موعد عملیاتی گذشته است",
            "action_label": "بررسی تأخیر عملیاتی",
            "reason": "یک مرحله مسیر موعد گذشته و واقعیت تکمیل معتبر ندارد.", "section": "route",
        })
    represented_codes = {item.get("source_code") for item in items}
    for item in assessment.get("missing", []):
        if item["code"] in represented_codes:
            continue
        if item["code"] in {"NO_OPEN_OPERATIONAL_WORK", "NO_OPEN_FOLLOW_UPS"} and "work_item.read" not in permissions:
            continue
        if item["code"] in {"REQUIRED_DOCUMENTS_READY", "OPTIONAL_DOCUMENTS_ABSENT"} and "document_readiness.read" not in permissions:
            continue
        if item["code"] in {"NO_OPEN_OPERATIONAL_WORK", "NO_OPEN_FOLLOW_UPS"} and graph.get("open_work_item_count"):
            continue
        mandatory = bool(item.get("mandatory"))
        section = {
            "REQUIRED_DOCUMENTS_READY": "documents",
            "ACTUAL_CARGO_UNKNOWN": "cargo",
            "ACTUAL_ALLOCATION_DIFFERS_FROM_PLANNED": "cargo",
            "DELIVERED_DIFFERS_FROM_PLANNED": "delivery",
            "OPTIONAL_DOCUMENTS_ABSENT": "documents",
            "ALL_CARGO_DELIVERED": "delivery",
            "FINAL_DELIVERY_EXISTS": "delivery",
            "REQUIRED_OPERATIONAL_STAGES_COMPLETE": "stages",
            "ETA_UNAVAILABLE": "tracking",
            "NO_BLOCKING_OPERATIONAL_ISSUE": "route",
            "NON_BLOCKING_OPERATIONAL_WARNINGS": "route",
            "MODE_UNDEFINED": "route",
        }.get(item["code"], "closure")
        action_labels = {
            "REQUIRED_DOCUMENTS_READY": "رفع سند اجباری",
            "ACTUAL_CARGO_UNKNOWN": "تکمیل واقعیت کالای حمل‌شده",
            "ACTUAL_ALLOCATION_DIFFERS_FROM_PLANNED": "اصلاح تخصیص واقعی",
            "DELIVERED_DIFFERS_FROM_PLANNED": "بررسی مقدار تحویل‌شده",
            "OPTIONAL_DOCUMENTS_ABSENT": "تکمیل سند اختیاری",
            "FINAL_DELIVERY_EXISTS": "ثبت تحویل نهایی",
            "REQUIRED_OPERATIONAL_STAGES_COMPLETE": "تکمیل مراحل عملیاتی",
            "ETA_UNAVAILABLE": "ثبت موقعیت یا پیشرفت",
            "NO_BLOCKING_OPERATIONAL_ISSUE": "رفع مشکل عملیاتی مسدودکننده",
            "NON_BLOCKING_OPERATIONAL_WARNINGS": "بررسی هشدارهای عملیاتی",
            "MODE_UNDEFINED": "تکمیل روش حمل مسیر",
        }
        items.append({
            "key": f"closure-{item['code'].lower()}",
            "source_code": item["code"],
            "category": "BLOCKER" if mandatory else "WARNING",
            "severity": "BLOCKER" if mandatory else "WARNING",
            "blocking": mandatory,
            "precedence": "CLOSURE_BLOCKER" if mandatory else "OPTIONAL_IMPROVEMENT",
            "label": item["label"],
            "action_label": action_labels.get(item["code"], "بررسی آمادگی پرونده"),
            "reason": "این واقعیت برای آمادگی پرونده هنوز کامل یا قطعی نیست.",
            "section": section,
        })
    unique = {item["key"]: item for item in items}
    if closed:
        unique = {key: {
            **item,
            "category": "INFORMATIONAL",
            "severity": "INFORMATIONAL",
            "blocking": False,
            "precedence": "INFORMATIONAL",
            "action_label": None,
            "reason": f"{item['reason']} پرونده بسته است و این مورد فقط سابقه اطلاعاتی است.",
        } for key, item in unique.items()}
    category_order = {"BLOCKER": 0, "NEEDS_ACTION": 1, "WARNING": 2, "INFORMATIONAL": 3}
    return sorted(unique.values(), key=lambda item: (
        PRECEDENCE_ORDER[item["precedence"]],
        category_order[item["category"]],
        ATTENTION_ORDER.get(item.get("source_code"), 100),
        item["key"],
    ))


def _stage_action(shipment: OperationalShipment, stages: dict) -> tuple[int, str, str, str] | None:
    current = stages.get("current") if stages else None
    if not current or not current.get("required_for_completion"):
        return None
    name = current.get("display_name_fa") or "جاری"
    public_id = current.get("public_id")
    fragment = f"#shipment-operational-stage-{public_id}" if public_id else ""
    href = f"/operations/shipments/{shipment.public_id}/stages{fragment}"
    if current.get("status") == "STARTED":
        return (
            30,
            href,
            f"تکمیل مرحله «{name}»",
            "مرحله الزامی جاری شروع شده اما هنوز کامل نشده است.",
        )
    if current.get("status") == "NOT_STARTED":
        return (
            30,
            href,
            f"شروع مرحله «{name}»",
            "مرحله الزامی بعدی آماده شروع است.",
        )
    return None


def _action(
    shipment: OperationalShipment,
    tasks: list[dict],
    attention: list[dict],
    can_manage: bool,
    stages: dict | None = None,
) -> tuple[dict | None, list[dict]]:
    if shipment.lifecycle_status == "closed" or not can_manage:
        return None, []
    task_by_key = {task["key"]: task for task in tasks}
    candidates = [item for item in attention if item.get("action_label")]
    if task_by_key.get("closure", {}).get("status") == "READY":
        candidates.append({
            "key": "task-closure", "category": "NEEDS_ACTION", "blocking": False,
            "precedence": "NEXT_REQUIRED_LIFECYCLE", "section": "closure",
            "action_label": "بررسی و بستن پرونده", "reason": "همه الزامات بستن عادی آماده‌اند.",
        })
    candidates.sort(key=lambda item: (
        PRECEDENCE_ORDER[item["precedence"]],
        ATTENTION_ORDER.get(item.get("source_code"), 100),
        item["section"],
        item["key"],
    ))
    stage_action = _stage_action(shipment, stages or {})
    actions = []
    seen = set()
    for item in candidates:
        identity = (item["section"], item["action_label"])
        if identity in seen:
            continue
        seen.add(identity)
        href = f"/operations/shipments/{shipment.public_id}/{item['section']}"
        label = item["action_label"]
        reason = item["reason"]
        if item["section"] == "stages" and stage_action:
            _, href, label, reason = stage_action
        actions.append({
            "rank": PRECEDENCE_ORDER[item["precedence"]],
            "precedence": item["precedence"],
            "category": item["category"],
            "blocking": item["blocking"],
            "section": item["section"],
            "label": label,
            "reason": reason,
            "href": href,
        })
    return (actions[0] if actions else None), actions[1:4]


def _eta(shipment: OperationalShipment, cargo_rows: list[ShipmentCargoItem]) -> dict:
    if not cargo_rows:
        return {"available": False, "reason": "CARGO_UNDEFINED", "message": "برای محاسبه زمان رسیدن، قلم کالای عملیاتی لازم است.", "earliest": None, "latest": None}
    values = [eta_service.calculate(shipment, cargo)[2]["final"] for cargo in cargo_rows]
    unavailable = [value for value in values if not value.get("available")]
    if unavailable:
        first = unavailable[0]
        return {
            "available": False,
            "reason": first.get("reason"),
            "message": first.get("message") or "زمان رسیدن برای یک یا چند قلم در دسترس نیست.",
            "earliest": None,
            "latest": None,
        }
    return {
        "available": True,
        "reason": None,
        "message": None,
        "earliest": min(value["earliest"] for value in values),
        "latest": max(value["latest"] for value in values),
    }


def _process_status(shipment: OperationalShipment, tasks: list[dict], stages: dict) -> str:
    if shipment.lifecycle_status == "closed":
        return "CLOSED"
    task_by_key = {task["key"]: task for task in tasks}
    if task_by_key["route"]["status"] != "DONE" or task_by_key["execution"]["status"] == "NEEDS_ACTION":
        return "BLOCKED_PRECONDITION"
    current = stages.get("current") or {}
    if current.get("status") == "STARTED":
        return "CURRENT_REQUIRED_WORK"
    if current.get("status") == "NOT_STARTED":
        return "NEXT_REQUIRED_LIFECYCLE"
    if stages.get("configured") and stages.get("total") == stages.get("completed"):
        return "AWAITING_CLOSURE"
    return "UNKNOWN"


def _finalize_guidance(
    shipment: OperationalShipment,
    tasks: list[dict],
    attention: list[dict],
    can_manage: bool,
    stages: dict,
) -> dict:
    """Assemble every decision surface from the same classified conditions."""
    recommended, secondary = _action(shipment, tasks, attention, can_manage, stages)
    completed = sum(1 for task in tasks if task["status"] in {"DONE", "NOT_APPLICABLE"})
    return {
        "process_status": _process_status(shipment, tasks, stages),
        "recommended_action": recommended,
        "secondary_actions": secondary,
        "readiness": {
            "semantic": "CASE_READINESS",
            "completed": completed,
            "total": len(tasks),
            "percent": round(completed * 100 / len(tasks)) if tasks else 0,
            "blocker_count": sum(1 for item in attention if item["blocking"]),
            "warning_count": sum(1 for item in attention if item["category"] == "WARNING"),
            "closure_ready": any(task["key"] == "closure" and task["status"] == "READY" for task in tasks),
        },
    }


def _current_operation(shipment: OperationalShipment, user: dict, cargo_rows: list[ShipmentCargoItem], graph: dict) -> dict:
    reported = reported_fact_service.listing(shipment.public_id, user)
    latest = (reported.get("reported_locations") or [None])[0]
    return {
        "latest_position": ({
            "label": latest.get("location") or latest.get("scope_label"),
            "scope": latest.get("scope"),
            "reported_at": latest.get("occurred_at"),
            "recorded_at": latest.get("recorded_at"),
            "route_progress": latest.get("route_progress"),
        } if latest else None),
        "eta": _eta(shipment, cargo_rows),
        "latest_update": graph.get("latest_update"),
    }


def build(shipment: OperationalShipment, user: dict, *, graph: dict | None = None, include_current_operation: bool = True) -> dict:
    """Build a pure projection for an already server-scoped Shipment."""
    graph = graph or operational_service.shipment_graph(shipment)
    permissions = set(operational_service.operational_context(user)["permissions"])
    stages = _stage_projection(shipment, user)
    assessment = closure_service.assess(shipment)
    cargo_rows = db.session.scalars(select(ShipmentCargoItem).where(
        ShipmentCargoItem.operational_shipment_id == shipment.id,
    ).order_by(ShipmentCargoItem.line_number)).all()
    tasks = _tasks(shipment, graph, stages, assessment)
    attention = _attention(
        graph, assessment, permissions, tasks,
        closed=shipment.lifecycle_status == "closed",
    )
    can_manage = authorize_document_management(user, shipment).allowed
    guidance = _finalize_guidance(shipment, tasks, attention, can_manage, stages)
    now = utcnow()
    updated = _aware(shipment.updated_at)
    return {
        "identity": _identity(shipment, graph),
        "overall_state": shipment.lifecycle_status,
        "process_status": guidance["process_status"],
        "operational_route": graph.get("route_summary"),
        "stage_progress": {**stages, "semantic": "OPERATIONAL_PROGRESS"},
        "tasks": tasks,
        "attention": attention,
        "recommended_action": guidance["recommended_action"],
        "secondary_actions": guidance["secondary_actions"],
        "readiness": guidance["readiness"],
        "current_operation": _current_operation(shipment, user, cargo_rows, graph) if include_current_operation else {
            "latest_position": None,
            "eta": {"available": False, "reason": "NOT_CALCULATED_IN_COMPACT_VIEW", "message": "در نمای خلاصه محاسبه نشده است.", "earliest": None, "latest": None},
            "latest_update": graph.get("latest_update"),
        },
        "priority": {
            "band": "BLOCKED" if any(item["blocking"] for item in attention) else "WARNING" if attention else "NORMAL",
            "score": (100 if any(item["blocking"] for item in attention) else 50 if attention else 0) + min(graph.get("open_work_item_count", 0), 20),
        },
        "meta": {
            "projection_version": PROJECTION_VERSION,
            "calculated_at": operational_read_service.iso(now),
            "source_updated_at": operational_read_service.iso(shipment.updated_at),
            "lag_seconds": max(0, int((now - updated).total_seconds())) if updated else None,
            "freshness": "ON_REQUEST",
            "rebuild": "Recompute from current authorized source facts; no backfill or projection persistence is required.",
            "sources": SOURCE_TYPES,
            "limitations": [
                "Recommendations are deterministic navigation guidance, not workflow authority.",
                "Missing facts remain unknown and never imply success.",
                "Every command is re-authorized by its owning domain service.",
                "Named semantic precedence, not section order, controls guidance ranking.",
            ],
        },
    }


def read(shipment_public_id: str, user: dict) -> dict:
    shipment = operational_service.scoped_shipment(shipment_public_id, user)
    return build(shipment, user)
