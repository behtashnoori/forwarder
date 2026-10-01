"""Contracts for the additive guided operational read projection."""

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
