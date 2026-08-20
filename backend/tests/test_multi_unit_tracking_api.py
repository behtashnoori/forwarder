"""Authorization, privacy, and response contracts for manual unit tracking."""
from datetime import datetime, timedelta

import pytest

from backend import create_app
from backend.extensions import db
from backend.models import ExpertUser, ShipmentRequest
from backend.services.auth_session_service import create_session_tokens
from backend.operational_models import OperationalMembership, OperationalOrganization


@pytest.fixture()
def tracking_api_app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SECRET_KEY": "tracking-api-test",
        },
        skip_startup=True,
    )
    with app.app_context():
        db.create_all()
        assignee = ExpertUser(
            username="tracking-assignee",
            password_hash="not-used",
            full_name="Tracking Assignee",
            role="expert",
            is_active=True,
        )
        outsider = ExpertUser(
            username="tracking-outsider",
            password_hash="not-used",
            full_name="Tracking Outsider",
            role="expert",
            is_active=True,
        )
        organization = OperationalOrganization(name="Tracking API Organization")
        db.session.add_all([assignee, outsider, organization])
        db.session.flush()
        db.session.add_all([
            OperationalMembership(organization_id=organization.id, user_id=assignee.id, permissions=[]),
            OperationalMembership(organization_id=organization.id, user_id=outsider.id, permissions=[]),
        ])
        request_row = ShipmentRequest(
            ownership_scope="TENANT",
            operational_organization_id=organization.id,
            contact_phone="09120000000",
            status="won",
            status_request_status="new",
            tracking_code="SAFE-MULTI-UNIT-CODE",
            assigned_to=assignee.id,
        )
        db.session.add(request_row)
        db.session.commit()
        yield {
            "app": app,
            "request_id": request_row.id,
            "tracking_code": request_row.tracking_code,
            "assignee_token": create_session_tokens(assignee.id)["access_token"],
            "outsider_token": create_session_tokens(outsider.id)["access_token"],
        }
        db.session.remove()
        db.drop_all()


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_tracking_management_is_authenticated_and_assignment_scoped(tracking_api_app):
    client = tracking_api_app["app"].test_client()
    path = f"/api/expert/requests/{tracking_api_app['request_id']}/tracking"
    assert client.get(path).status_code == 401
    assert client.get(path, headers=_headers(tracking_api_app["outsider_token"])).status_code == 403
    response = client.get(path, headers=_headers(tracking_api_app["assignee_token"]))
    assert response.status_code == 200
    assert response.get_json()["eligible"] is True


def test_manual_tracking_flow_and_public_privacy_contract(tracking_api_app):
    client = tracking_api_app["app"].test_client()
    request_id = tracking_api_app["request_id"]
    headers = _headers(tracking_api_app["assignee_token"])

    enabled = client.post(f"/api/expert/requests/{request_id}/tracking/enable", headers=headers)
    assert enabled.status_code == 200
    created = client.post(
        f"/api/expert/requests/{request_id}/tracking/units",
        headers=headers,
        json={"unit_code": "TRUCK-01", "unit_type": "truck", "display_name": "Truck 1", "vehicle_reference": "  PLATE-77  "},
    )
    assert created.status_code == 201
    unit_id = created.get_json()["unit_tracking"]["units"][0]["id"]
    occurred_at = (datetime.utcnow() - timedelta(minutes=1)).isoformat() + "Z"
    updated = client.post(
        f"/api/expert/requests/{request_id}/tracking/units/{unit_id}/updates",
        headers=headers,
        json={
            "status": "in_transit",
            "location": "Qom",
            "customer_message": "On route",
            "internal_note": "private dispatch note",
            "is_customer_visible": True,
            "occurred_at": occurred_at,
        },
    )
    assert updated.status_code == 201
    internal_tracking = updated.get_json()["unit_tracking"]
    assert internal_tracking["enabled_at"].endswith("Z")
    assert internal_tracking["last_updated_at"].endswith("Z")
    assert internal_tracking["units"][0]["latest_event_at"].endswith("Z")

    public = client.get(f"/api/public/track/{tracking_api_app['tracking_code']}")
    assert public.status_code == 200
    unit_tracking = public.get_json()["unit_tracking"]
    assert unit_tracking["summary"]["total_units"] == 1
    assert unit_tracking["units"][0]["latest_location"] == "Qom"
    assert unit_tracking["units"][0]["vehicle_reference"] == "PLATE-77"
    assert unit_tracking["enabled_at"].endswith("Z")
    assert unit_tracking["last_updated_at"].endswith("Z")
    assert unit_tracking["units"][0]["latest_event_at"].endswith("Z")
    assert unit_tracking["units"][0]["timeline"][0]["event_at"].endswith("Z")
    assert "id" not in unit_tracking["units"][0]
    assert "created_by_user_id" not in str(unit_tracking)
    assert "private dispatch note" not in str(unit_tracking)

    legacy_numeric = client.get(f"/api/public/track/{request_id}")
    assert legacy_numeric.status_code == 200
    assert "unit_tracking" not in legacy_numeric.get_json()


def test_internal_unit_metadata_update_keeps_id_and_public_response_does_not(tracking_api_app):
    client = tracking_api_app["app"].test_client()
    request_id = tracking_api_app["request_id"]
    headers = _headers(tracking_api_app["assignee_token"])
    client.post(f"/api/expert/requests/{request_id}/tracking/enable", headers=headers)
    created = client.post(
        f"/api/expert/requests/{request_id}/tracking/units",
        headers=headers,
        json={"unit_code": "W-01", "unit_type": "wagon"},
    )
    unit_id = created.get_json()["unit_tracking"]["units"][0]["id"]
    updated = client.patch(
        f"/api/expert/requests/{request_id}/tracking/units/{unit_id}",
        headers=headers,
        json={"display_name": " Wagon 1 ", "vehicle_reference": "  WGN-900  "},
    )
    assert updated.status_code == 200
    internal = updated.get_json()["unit_tracking"]["units"][0]
    assert internal["id"] == unit_id
    assert internal["vehicle_reference"] == "WGN-900"
    too_long = client.patch(
        f"/api/expert/requests/{request_id}/tracking/units/{unit_id}",
        headers=headers,
        json={"display_name": "Wagon 1", "vehicle_reference": "x" * 101},
    )
    assert too_long.status_code == 400
    assert too_long.get_json() == {"error": "vehicle_reference must be at most 100 characters"}
    public = client.get(f"/api/public/track/{tracking_api_app['tracking_code']}").get_json()["unit_tracking"]
    assert public["units"][0]["vehicle_reference"] == "WGN-900"
    assert "id" not in public["units"][0]


def test_update_rejects_cross_shipment_unit_id(tracking_api_app):
    client = tracking_api_app["app"].test_client()
    request_id = tracking_api_app["request_id"]
    headers = _headers(tracking_api_app["assignee_token"])
    client.post(f"/api/expert/requests/{request_id}/tracking/enable", headers=headers)
    response = client.post(
        f"/api/expert/requests/{request_id}/tracking/units/999999/updates",
        headers=headers,
        json={"status": "pending", "occurred_at": datetime.utcnow().isoformat()},
    )
    assert response.status_code == 404
