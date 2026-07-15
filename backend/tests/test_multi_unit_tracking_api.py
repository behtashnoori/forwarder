"""Authorization, privacy, and response contracts for manual unit tracking."""
from datetime import datetime, timedelta

import pytest

from backend import create_app
from backend.extensions import db
from backend.models import ExpertUser, ShipmentRequest
from backend.security import security


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
        db.session.add_all([assignee, outsider])
        db.session.flush()
        request_row = ShipmentRequest(
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
            "assignee_token": security.generate_token(assignee.id, "access"),
            "outsider_token": security.generate_token(outsider.id, "access"),
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
        json={"unit_code": "TRUCK-01", "unit_type": "truck", "display_name": "Truck 1"},
    )
    assert created.status_code == 201
    unit_id = created.get_json()["unit_tracking"]["units"][0]["id"]
    occurred_at = (datetime.utcnow() - timedelta(minutes=1)).isoformat()
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

    public = client.get(f"/api/public/track/{tracking_api_app['tracking_code']}")
    assert public.status_code == 200
    unit_tracking = public.get_json()["unit_tracking"]
    assert unit_tracking["unit_count"] == 1
    assert unit_tracking["units"][0]["latest_location"] == "Qom"
    assert "private dispatch note" not in str(unit_tracking)

    legacy_numeric = client.get(f"/api/public/track/{request_id}")
    assert legacy_numeric.status_code == 200
    assert "unit_tracking" not in legacy_numeric.get_json()


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
