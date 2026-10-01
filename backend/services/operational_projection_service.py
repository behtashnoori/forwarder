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


PROJECTION_VERSION = "guided-operational-workspace-v1"
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
    return [
        {"key": "route", "label": "مسیر عملیاتی", "status": route_status, "section": "route", "required": True},
        {"key": "execution", "label": "اجرای حمل", "status": execution_status, "section": "route", "required": True},
        {"key": "stages", "label": "مراحل فرایند", "status": stage_status, "section": "stages", "required": True},
        {"key": "cargo", "label": "مقادیر واقعی کالا", "status": _status(_criterion(assessment, "ACTUAL_QUANTITY_KNOWN")), "section": "cargo", "required": True},
        {"key": "documents", "label": "مدارک الزامی", "status": _status(_criterion(assessment, "REQUIRED_DOCUMENTS_READY")), "section": "documents", "required": True},
        {"key": "tracking", "label": "موقعیت و پیشرفت", "status": "DONE" if graph.get("latest_update") else "NEEDS_ACTION", "section": "tracking", "required": False},
        {"key": "delivery", "label": "تحویل کالا", "status": _status(_criterion(assessment, "ALL_CARGO_DELIVERED")), "section": "delivery", "required": True},
        {"key": "closure", "label": "آمادگی بستن پرونده", "status": "DONE" if closed else "READY" if assessment.get("normal_ready") else "BLOCKED", "section": "closure", "required": True},
    ]


def _attention(graph: dict, assessment: dict, permissions: set[str]) -> list[dict]:
    items: list[dict] = []
    if graph.get("overdue"):
        items.append({
            "key": "overdue-milestone", "severity": "BLOCKER", "label": "موعد عملیاتی گذشته است",
            "reason": "یک مرحله مسیر موعد گذشته و واقعیت تکمیل معتبر ندارد.", "section": "route",
        })
    if "work_item.read" in permissions and graph.get("open_work_item_count", 0):
        items.append({
            "key": "open-work", "severity": "BLOCKER", "label": "پیگیری عملیاتی باز است",
            "reason": f"{graph['open_work_item_count']} مورد کار جاری هنوز باز است.", "section": "route",
        })
    for item in assessment.get("missing", []):
        if item["code"] in {"NO_OPEN_OPERATIONAL_WORK", "NO_OPEN_FOLLOW_UPS"} and "work_item.read" not in permissions:
            continue
        if item["code"] in {"REQUIRED_DOCUMENTS_READY", "OPTIONAL_DOCUMENTS_ABSENT"} and "document_readiness.read" not in permissions:
            continue
        if item["code"] in {"NO_OPEN_OPERATIONAL_WORK", "NO_OPEN_FOLLOW_UPS"} and graph.get("open_work_item_count"):
            continue
        items.append({
            "key": f"closure-{item['code'].lower()}",
            "severity": "BLOCKER" if item.get("mandatory") else "WARNING",
            "label": item["label"],
            "reason": "این واقعیت برای آمادگی پرونده هنوز کامل یا قطعی نیست.",
            "section": {
                "REQUIRED_DOCUMENTS_READY": "documents",
                "ACTUAL_QUANTITY_KNOWN": "cargo",
                "ALL_CARGO_DELIVERED": "delivery",
                "FINAL_DELIVERY_EXISTS": "delivery",
                "REQUIRED_OPERATIONAL_STAGES_COMPLETE": "stages",
                "ETA_UNAVAILABLE": "tracking",
            }.get(item["code"], "closure"),
        })
    unique = {item["key"]: item for item in items}
    order = {"BLOCKER": 0, "WARNING": 1, "INFO": 2}
    return sorted(unique.values(), key=lambda item: (order[item["severity"]], item["key"]))


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


def _attention_rank(section: str) -> int:
    return {
        "route": 5,
        "stages": 30,
        "cargo": 40,
        "documents": 50,
        "tracking": 60,
        "delivery": 70,
        "closure": 75,
    }.get(section, 75)


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
    candidates: list[tuple[int, str, str, str, str]] = []
    if task_by_key["route"]["status"] != "DONE":
        candidates.append((10, "route", f"/operations/shipments/{shipment.public_id}/route", "تعریف مسیر عملیاتی", "برای شروع اجرا، مسیر فعال لازم است."))
    elif task_by_key["execution"]["status"] != "DONE":
        candidates.append((20, "route", f"/operations/shipments/{shipment.public_id}/route", "تکمیل اجرای حمل", "وسیله یا اجرای حمل برای مسیر فعال کامل نشده است."))
    if task_by_key["stages"]["status"] not in {"DONE", "UNKNOWN"}:
        stage_action = _stage_action(shipment, stages or {})
        if stage_action:
            rank, href, label, reason = stage_action
            candidates.append((rank, "stages", href, label, reason))
        else:
            candidates.append((30, "stages", f"/operations/shipments/{shipment.public_id}/stages", "ثبت پیشرفت مرحله جاری", "مرحله جاری فرایند هنوز کامل نشده است."))
    if task_by_key["cargo"]["status"] != "DONE":
        candidates.append((40, "cargo", f"/operations/shipments/{shipment.public_id}/cargo", "تکمیل واقعیت کالای حمل‌شده", "مقدار واقعی یک یا چند قلم هنوز قطعی نیست."))
    if task_by_key["documents"]["status"] != "DONE":
        candidates.append((50, "documents", f"/operations/shipments/{shipment.public_id}/documents", "تکمیل مدارک الزامی", "آمادگی یک یا چند سند الزامی کامل نیست."))
    if task_by_key["tracking"]["status"] != "DONE":
        candidates.append((60, "tracking", f"/operations/shipments/{shipment.public_id}/tracking", "ثبت موقعیت یا پیشرفت", "آخرین موقعیت یا پیشرفت عملیاتی ثبت نشده است."))
    if task_by_key["delivery"]["status"] != "DONE":
        candidates.append((70, "delivery", f"/operations/shipments/{shipment.public_id}/delivery", "ثبت تحویل کالا", "تحویل کامل کالا هنوز با واقعیت‌های ثبت‌شده اثبات نشده است."))
    if task_by_key["closure"]["status"] == "READY":
        candidates.append((80, "closure", f"/operations/shipments/{shipment.public_id}/closure", "بررسی و بستن پرونده", "همه الزامات بستن عادی آماده‌اند."))
    if attention and attention[0]["severity"] == "BLOCKER":
        blocker = attention[0]
        section = blocker["section"]
        candidates.append((_attention_rank(section), section, f"/operations/shipments/{shipment.public_id}/{section}", blocker["label"], blocker["reason"]))
    candidates.sort(key=lambda row: (row[0], row[1]))
    actions = [{
        "rank": rank, "section": section, "label": label, "reason": reason,
        "href": href,
    } for rank, section, href, label, reason in candidates]
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
    attention = _attention(graph, assessment, permissions)
    can_manage = authorize_document_management(user, shipment).allowed
    recommended, secondary = _action(shipment, tasks, attention, can_manage, stages)
    completed = sum(1 for task in tasks if task["status"] in {"DONE", "NOT_APPLICABLE"})
    now = utcnow()
    updated = _aware(shipment.updated_at)
    return {
        "identity": _identity(shipment, graph),
        "overall_state": shipment.lifecycle_status,
        "operational_route": graph.get("route_summary"),
        "stage_progress": stages,
        "tasks": tasks,
        "attention": attention,
        "recommended_action": recommended,
        "secondary_actions": secondary,
        "readiness": {
            "completed": completed,
            "total": len(tasks),
            "percent": round(completed * 100 / len(tasks)) if tasks else 0,
            "blocker_count": sum(1 for item in attention if item["severity"] == "BLOCKER"),
            "warning_count": sum(1 for item in attention if item["severity"] == "WARNING"),
            "closure_ready": bool(assessment.get("normal_ready")),
        },
        "current_operation": _current_operation(shipment, user, cargo_rows, graph) if include_current_operation else {
            "latest_position": None,
            "eta": {"available": False, "reason": "NOT_CALCULATED_IN_COMPACT_VIEW", "message": "در نمای خلاصه محاسبه نشده است.", "earliest": None, "latest": None},
            "latest_update": graph.get("latest_update"),
        },
        "priority": {
            "band": "BLOCKED" if attention and attention[0]["severity"] == "BLOCKER" else "WARNING" if attention else "NORMAL",
            "score": (100 if any(item["severity"] == "BLOCKER" for item in attention) else 50 if attention else 0) + min(graph.get("open_work_item_count", 0), 20),
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
            ],
        },
    }


def read(shipment_public_id: str, user: dict) -> dict:
    shipment = operational_service.scoped_shipment(shipment_public_id, user)
    return build(shipment, user)
