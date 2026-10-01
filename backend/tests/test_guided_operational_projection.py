"""Contracts for the additive guided operational read projection."""

from types import SimpleNamespace

import pytest

from backend.extensions import db
from backend.services import operational_service as service
from backend.services import operational_projection_service as projection
from backend.tests.test_operational_vertical_slice import (
    _auth,
    _auth_user,
    _direct_payload,
    _user,
    operational_app,
)
from backend.tests.test_operational_workspace import (
    _create_workspace_shipment,
    _same_org_peer,
)


def test_projection_is_authorized_rebuildable_and_actionable(operational_app):
    with operational_app.app_context():
        shipment = _create_workspace_shipment(operational_app, "guided-projection")
        shipment_id = shipment.public_id

    client = operational_app.test_client()
    assert client.get(
        f"/api/operational-shipments/{shipment_id}/operational-projection"
    ).status_code == 401

    response = client.get(
        f"/api/operational-shipments/{shipment_id}/operational-projection",
        headers=_auth(operational_app),
    )
    assert response.status_code == 200
    value = response.json["data"]
    assert value["identity"]["label"]
    assert value["identity"]["technical_id"] == shipment_id
    assert value["stage_progress"]["completed"] <= value["stage_progress"]["total"]
    assert value["recommended_action"] is not None
    assert value["recommended_action"]["href"].startswith(
        f"/operations/shipments/{shipment_id}/"
    )
    assert len([value["recommended_action"]]) == 1
    assert value["meta"]["projection_version"] == projection.PROJECTION_VERSION
    assert value["meta"]["freshness"] == "ON_REQUEST"
    assert value["meta"]["lag_seconds"] >= 0
    assert "OperationalShipment" in value["meta"]["sources"]
    assert "no backfill" in value["meta"]["rebuild"]


def test_projection_fails_closed_for_non_owner_and_has_no_false_closed_action(
    operational_app,
):
    with operational_app.app_context():
        shipment = _create_workspace_shipment(operational_app, "guided-scope")
        shipment_id = shipment.public_id
        peer_id = _same_org_peer(operational_app)
        shipment.lifecycle_status = "closed"
        recommended, secondary = projection._action(
            shipment, [], [], can_manage=True
        )
        assert recommended is None
        assert secondary == []
        db.session.rollback()

    denied = operational_app.test_client().get(
        f"/api/operational-shipments/{shipment_id}/operational-projection",
        headers=_auth_user(operational_app, peer_id),
    )
    assert denied.status_code == 404


def test_priority_list_projects_direct_shipments_without_changing_population_authority(
    operational_app,
):
    with operational_app.app_context():
        shipment, _ = service.create_direct(
            _direct_payload(operational_app),
            _user(operational_app),
            "guided-direct",
        )
        shipment_id = shipment.public_id

    response = operational_app.test_client().get(
        "/api/operational-shipments?active=true",
        headers=_auth(operational_app),
    )
    assert response.status_code == 200
    row = next(item for item in response.json["data"] if item["public_id"] == shipment_id)
    assert row["source"]["type"] == "direct"
    assert row["operational_projection"]["tasks"][0]["key"] == "route"
    assert row["operational_projection"]["tasks"][0]["status"] == "DONE"
    assert row["operational_projection"]["tasks"][0]["blocking"] is False
    assert row["operational_projection"]["meta"]["freshness"] == "ON_REQUEST"


def _matrix_stage(sequence=None, status=None, *, completed=0, total=5):
    return {
        "current": None if sequence is None else {
            "public_id": f"stage-{sequence}",
            "code": f"STAGE_{sequence}",
            "display_name_fa": f"مرحله {sequence}",
            "sequence": sequence,
            "required_for_completion": True,
            "status": status,
        },
        "completed": completed,
        "total": total,
        "configured": True,
    }


def _matrix_task(
    key,
    status="DONE",
    *,
    section=None,
    category="INFORMATIONAL",
    precedence="INFORMATIONAL",
    blocking=False,
    action_label=None,
):
    return projection._task(
        key, key, status, section or key, required=key not in {"cargo", "tracking"},
        category=category, precedence=precedence, blocking=blocking,
        action_label=action_label, reason=f"reason-{key}",
    )


def _matrix_tasks(**overrides):
    values = {
        "route": _matrix_task("route", section="route", action_label="تعریف مسیر عملیاتی"),
        "execution": _matrix_task("execution", section="route", action_label="تکمیل اجرای حمل"),
        "stages": _matrix_task("stages", section="stages", action_label="ثبت پیشرفت مرحله جاری"),
        "cargo": _matrix_task("cargo", section="cargo", action_label="تکمیل واقعیت کالای حمل‌شده"),
        "documents": _matrix_task("documents", section="documents", action_label="رفع سند اجباری"),
        "tracking": _matrix_task("tracking", section="tracking", action_label="ثبت موقعیت یا پیشرفت"),
        "delivery": _matrix_task("delivery", section="delivery", action_label="ثبت تحویل نهایی"),
        "closure": _matrix_task("closure", "BLOCKED", section="closure", action_label="بررسی و بستن پرونده"),
    }
    values.update(overrides)
    return list(values.values())


def _matrix_attention(key, category, precedence, section, action_label, *, blocking):
    return {
        "key": key, "source_code": None, "category": category, "severity": category,
        "blocking": blocking, "precedence": precedence, "label": key,
        "action_label": action_label, "reason": f"reason-{key}", "section": section,
    }


def _stage_attention(status="NOT_STARTED"):
    return _matrix_attention(
        "stage", "NEEDS_ACTION",
        "CURRENT_REQUIRED_WORK" if status == "STARTED" else "NEXT_REQUIRED_LIFECYCLE",
        "stages", "stage-action", blocking=True,
    )


ROUTE = _matrix_attention("route", "BLOCKER", "BLOCKING_PRECONDITION", "route", "تعریف مسیر عملیاتی", blocking=True)
EXECUTION = _matrix_attention("execution", "BLOCKER", "BLOCKING_PRECONDITION", "route", "تکمیل اجرای حمل", blocking=True)
DELIVERY = _matrix_attention("delivery", "BLOCKER", "CLOSURE_BLOCKER", "delivery", "ثبت تحویل نهایی", blocking=True)
DOCUMENT = _matrix_attention("documents", "BLOCKER", "CLOSURE_BLOCKER", "documents", "رفع سند اجباری", blocking=True)
ISSUE = _matrix_attention("issue", "BLOCKER", "CLOSURE_BLOCKER", "route", "رفع مشکل عملیاتی مسدودکننده", blocking=True)
CARGO_WARNING = _matrix_attention("cargo", "WARNING", "OPTIONAL_IMPROVEMENT", "cargo", "تکمیل واقعیت کالای حمل‌شده", blocking=False)
ALLOCATION_WARNING = _matrix_attention("allocation", "WARNING", "OPTIONAL_IMPROVEMENT", "cargo", "اصلاح تخصیص واقعی", blocking=False)
ETA_WARNING = _matrix_attention("eta", "WARNING", "OPTIONAL_IMPROVEMENT", "tracking", "ثبت موقعیت یا پیشرفت", blocking=False)


MATRIX_CASES = [
    ("A", "in_progress", True, _matrix_stage(1, "NOT_STARTED"), _matrix_tasks(
        route=_matrix_task("route", "NEEDS_ACTION", section="route", category="BLOCKER", precedence="BLOCKING_PRECONDITION", blocking=True, action_label="تعریف مسیر عملیاتی"),
        execution=_matrix_task("execution", "NOT_APPLICABLE", section="route"),
        stages=_matrix_task("stages", "NEEDS_ACTION", section="stages", category="NEEDS_ACTION", precedence="NEXT_REQUIRED_LIFECYCLE", blocking=True),
    ), [ROUTE, _stage_attention()], "BLOCKED_PRECONDITION", "تعریف مسیر عملیاتی", 2, 0),
    ("B", "in_progress", True, _matrix_stage(1, "NOT_STARTED"), _matrix_tasks(
        execution=_matrix_task("execution", "NEEDS_ACTION", section="route", category="BLOCKER", precedence="BLOCKING_PRECONDITION", blocking=True, action_label="تکمیل اجرای حمل"),
        stages=_matrix_task("stages", "NEEDS_ACTION", section="stages", category="NEEDS_ACTION", precedence="NEXT_REQUIRED_LIFECYCLE", blocking=True),
    ), [EXECUTION, _stage_attention()], "BLOCKED_PRECONDITION", "تکمیل اجرای حمل", 2, 0),
    ("C", "in_progress", True, _matrix_stage(1, "NOT_STARTED"), _matrix_tasks(
        stages=_matrix_task("stages", "NEEDS_ACTION", section="stages", category="NEEDS_ACTION", precedence="NEXT_REQUIRED_LIFECYCLE", blocking=True),
    ), [_stage_attention(), ALLOCATION_WARNING], "NEXT_REQUIRED_LIFECYCLE", "شروع مرحله «مرحله 1»", 1, 1),
    ("D", "in_progress", True, _matrix_stage(1, "NOT_STARTED"), _matrix_tasks(
        stages=_matrix_task("stages", "NEEDS_ACTION", section="stages", category="NEEDS_ACTION", precedence="NEXT_REQUIRED_LIFECYCLE", blocking=True),
    ), [_stage_attention()], "NEXT_REQUIRED_LIFECYCLE", "شروع مرحله «مرحله 1»", 1, 0),
    ("E", "in_progress", True, _matrix_stage(1, "STARTED"), _matrix_tasks(
        stages=_matrix_task("stages", "IN_PROGRESS", section="stages", category="NEEDS_ACTION", precedence="CURRENT_REQUIRED_WORK", blocking=True),
    ), [_stage_attention("STARTED")], "CURRENT_REQUIRED_WORK", "تکمیل مرحله «مرحله 1»", 1, 0),
    ("F", "in_progress", True, _matrix_stage(2, "NOT_STARTED", completed=1), _matrix_tasks(
        stages=_matrix_task("stages", "IN_PROGRESS", section="stages", category="NEEDS_ACTION", precedence="NEXT_REQUIRED_LIFECYCLE", blocking=True),
    ), [_stage_attention()], "NEXT_REQUIRED_LIFECYCLE", "شروع مرحله «مرحله 2»", 1, 0),
    ("G", "in_progress", True, _matrix_stage(3, "STARTED", completed=2), _matrix_tasks(
        stages=_matrix_task("stages", "IN_PROGRESS", section="stages", category="NEEDS_ACTION", precedence="CURRENT_REQUIRED_WORK", blocking=True),
    ), [_stage_attention("STARTED")], "CURRENT_REQUIRED_WORK", "تکمیل مرحله «مرحله 3»", 1, 0),
    ("H", "in_progress", True, _matrix_stage(completed=5), _matrix_tasks(
        cargo=_matrix_task("cargo", "NEEDS_ACTION", section="cargo", category="WARNING", precedence="OPTIONAL_IMPROVEMENT"),
        tracking=_matrix_task("tracking", "NEEDS_ACTION", section="tracking", category="WARNING", precedence="OPTIONAL_IMPROVEMENT"),
        delivery=_matrix_task("delivery", "NEEDS_ACTION", section="delivery", category="BLOCKER", precedence="CLOSURE_BLOCKER", blocking=True),
    ), [DELIVERY, CARGO_WARNING, ALLOCATION_WARNING, ETA_WARNING], "AWAITING_CLOSURE", "ثبت تحویل نهایی", 1, 3),
    ("I", "completed", True, _matrix_stage(completed=5), _matrix_tasks(
        cargo=_matrix_task("cargo", "NEEDS_ACTION", section="cargo", category="WARNING", precedence="OPTIONAL_IMPROVEMENT"),
        closure=_matrix_task("closure", "READY", section="closure", category="NEEDS_ACTION", precedence="NEXT_REQUIRED_LIFECYCLE", action_label="بررسی و بستن پرونده"),
    ), [CARGO_WARNING], "AWAITING_CLOSURE", "بررسی و بستن پرونده", 0, 1),
    ("J", "completed", True, _matrix_stage(completed=5), _matrix_tasks(
        closure=_matrix_task("closure", "READY", section="closure", category="NEEDS_ACTION", precedence="NEXT_REQUIRED_LIFECYCLE", action_label="بررسی و بستن پرونده"),
    ), [ALLOCATION_WARNING], "AWAITING_CLOSURE", "بررسی و بستن پرونده", 0, 1),
    ("K", "completed", True, _matrix_stage(completed=5), _matrix_tasks(
        documents=_matrix_task("documents", "NEEDS_ACTION", section="documents", category="BLOCKER", precedence="CLOSURE_BLOCKER", blocking=True),
    ), [DOCUMENT], "AWAITING_CLOSURE", "رفع سند اجباری", 1, 0),
    ("L", "completed", True, _matrix_stage(completed=5), _matrix_tasks(), [ISSUE], "AWAITING_CLOSURE", "رفع مشکل عملیاتی مسدودکننده", 1, 0),
    ("M", "completed", True, _matrix_stage(completed=5), _matrix_tasks(
        tracking=_matrix_task("tracking", "NEEDS_ACTION", section="tracking", category="WARNING", precedence="OPTIONAL_IMPROVEMENT"),
        closure=_matrix_task("closure", "READY", section="closure", category="NEEDS_ACTION", precedence="NEXT_REQUIRED_LIFECYCLE", action_label="بررسی و بستن پرونده"),
    ), [ETA_WARNING], "AWAITING_CLOSURE", "بررسی و بستن پرونده", 0, 1),
    ("N", "completed", True, _matrix_stage(completed=5), _matrix_tasks(
        closure=_matrix_task("closure", "READY", section="closure", category="NEEDS_ACTION", precedence="NEXT_REQUIRED_LIFECYCLE", action_label="بررسی و بستن پرونده"),
    ), [], "AWAITING_CLOSURE", "بررسی و بستن پرونده", 0, 0),
    ("O", "closed", True, _matrix_stage(completed=5), _matrix_tasks(
        closure=_matrix_task("closure", "DONE", section="closure"),
    ), [], "CLOSED", None, 0, 0),
    ("P", "in_progress", False, _matrix_stage(1, "STARTED"), _matrix_tasks(
        stages=_matrix_task("stages", "IN_PROGRESS", section="stages", category="NEEDS_ACTION", precedence="CURRENT_REQUIRED_WORK", blocking=True),
    ), [_stage_attention("STARTED")], "CURRENT_REQUIRED_WORK", None, 1, 0),
]


@pytest.mark.parametrize(
    "case,lifecycle,can_manage,stages,tasks,attention,process,primary,blockers,warnings",
    MATRIX_CASES,
)
def test_guidance_state_matrix_and_cross_surface_invariants(
    case, lifecycle, can_manage, stages, tasks, attention, process, primary, blockers, warnings,
):
    shipment = SimpleNamespace(public_id="shipment", lifecycle_status=lifecycle)
    result = projection._finalize_guidance(shipment, tasks, attention, can_manage, stages)

    assert shipment.lifecycle_status == lifecycle, case
    assert result["process_status"] == process, case
    assert result["readiness"]["semantic"] == "CASE_READINESS", case
    assert result["readiness"]["blocker_count"] == blockers, case
    assert result["readiness"]["warning_count"] == warnings, case
    assert (result["recommended_action"] or {}).get("label") == primary, case
    if primary:
        assert result["recommended_action"]["precedence"] != "INFORMATIONAL", case
    if blockers and primary:
        assert not (
            result["recommended_action"]["category"] == "WARNING"
            and any(item["blocking"] for item in attention)
        ), case
    for task in tasks:
        aliases = {task["key"], f"task-{task['key']}"}
        if task["key"] == "stages":
            aliases.add("stage")
        related = [item for item in attention if item["key"] in aliases]
        if related and task["category"] in {"BLOCKER", "WARNING"}:
            assert all(item["blocking"] == task["blocking"] for item in related), case


def test_current_walkthrough_warning_never_outranks_final_delivery_blocker():
    case = next(row for row in MATRIX_CASES if row[0] == "H")
    _, lifecycle, can_manage, stages, tasks, attention, *_ = case
    result = projection._finalize_guidance(
        SimpleNamespace(public_id="shipment", lifecycle_status=lifecycle),
        tasks, attention, can_manage, stages,
    )
    assert result["recommended_action"]["label"] == "ثبت تحویل نهایی"
    assert result["recommended_action"]["blocking"] is True
    assert {item["key"] for item in attention if item["category"] == "WARNING"} == {
        "cargo", "allocation", "eta",
    }
