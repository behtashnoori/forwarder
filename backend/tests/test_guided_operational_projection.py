"""Contracts for the additive guided operational read projection."""

from types import SimpleNamespace

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
    assert row["operational_projection"]["tasks"][0] == {
        "key": "route",
        "label": "مسیر عملیاتی",
        "required": True,
        "section": "route",
        "status": "DONE",
    }
    assert row["operational_projection"]["meta"]["freshness"] == "ON_REQUEST"


def _ranking_tasks(*, stages="DONE", delivery="DONE", closure="BLOCKED"):
    values = {
        "route": "DONE",
        "execution": "DONE",
        "stages": stages,
        "cargo": "DONE",
        "documents": "DONE",
        "tracking": "DONE",
        "delivery": delivery,
        "closure": closure,
    }
    return [
        {"key": key, "status": status, "section": key, "label": key, "required": True}
        for key, status in values.items()
    ]


def _ranking_stage(sequence, status):
    return {
        "current": {
            "public_id": f"stage-{sequence}",
            "code": f"STAGE_{sequence}",
            "display_name_fa": f"مرحله {sequence}",
            "sequence": sequence,
            "required_for_completion": True,
            "status": status,
        }
    }


def _final_delivery_attention():
    return [{
        "key": "closure-final_delivery_exists",
        "severity": "BLOCKER",
        "label": "تحویل نهایی محموله به‌صراحت ثبت شده باشد",
        "reason": "این واقعیت برای آمادگی پرونده هنوز کامل یا قطعی نیست.",
        "section": "delivery",
    }]


def test_next_action_ranking_cases_1_to_4_prioritize_authoritative_stage_state():
    shipment = SimpleNamespace(public_id="shipment", lifecycle_status="in_progress")

    case_1, _ = projection._action(
        shipment, _ranking_tasks(stages="NEEDS_ACTION"), _final_delivery_attention(), True,
        _ranking_stage(1, "NOT_STARTED"),
    )
    assert case_1["label"] == "شروع مرحله «مرحله 1»"
    assert case_1["href"].endswith("/stages#shipment-operational-stage-stage-1")

    case_2, _ = projection._action(
        shipment, _ranking_tasks(stages="NEEDS_ACTION"), _final_delivery_attention(), True,
        _ranking_stage(1, "STARTED"),
    )
    assert case_2["label"] == "تکمیل مرحله «مرحله 1»"

    case_3, _ = projection._action(
        shipment, _ranking_tasks(stages="IN_PROGRESS"), _final_delivery_attention(), True,
        _ranking_stage(2, "NOT_STARTED"),
    )
    assert case_3["label"] == "شروع مرحله «مرحله 2»"

    case_4, _ = projection._action(
        shipment, _ranking_tasks(stages="IN_PROGRESS"), _final_delivery_attention(), True,
        _ranking_stage(3, "STARTED"),
    )
    assert case_4["label"] == "تکمیل مرحله «مرحله 3»"
    assert case_4["section"] == "stages"


def test_next_action_ranking_cases_5_to_8_preserve_delivery_closure_and_authorization():
    shipment = SimpleNamespace(public_id="shipment", lifecycle_status="in_progress")

    case_5, _ = projection._action(
        shipment, _ranking_tasks(), _final_delivery_attention(), True,
        {"current": None},
    )
    assert case_5["label"] == "تحویل نهایی محموله به‌صراحت ثبت شده باشد"
    assert case_5["section"] == "delivery"

    case_6, _ = projection._action(
        shipment, _ranking_tasks(closure="READY"), [], True, {"current": None},
    )
    assert case_6["label"] == "بررسی و بستن پرونده"
    assert case_6["section"] == "closure"

    closed = SimpleNamespace(public_id="shipment", lifecycle_status="closed")
    case_7, secondary_7 = projection._action(
        closed, _ranking_tasks(closure="DONE"), [], True, {"current": None},
    )
    assert case_7 is None
    assert secondary_7 == []

    case_8, secondary_8 = projection._action(
        shipment, _ranking_tasks(stages="NEEDS_ACTION"), _final_delivery_attention(), False,
        _ranking_stage(1, "STARTED"),
    )
    assert case_8 is None
    assert secondary_8 == []
