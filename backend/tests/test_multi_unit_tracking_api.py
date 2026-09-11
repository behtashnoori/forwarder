"""Authorization, privacy, and response contracts for manual unit tracking."""
from datetime import datetime, timedelta
import logging

import pytest

from backend import create_app
from backend.extensions import db
from backend.models import ExpertUser, ShipmentRequest, ShipmentTransportUnit, ShipmentTransportUnitUpdate
from backend.services.auth_session_service import create_session_tokens
from backend.operational_models import ExecutionUnit, OperationalEvent, OperationalMembership, OperationalOrganization


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
        org_admin = ExpertUser(
            username="tracking-org-admin",
            password_hash="not-used",
            full_name="Tracking Organization Admin",
            role="admin",
            authority="ORGANIZATION_ADMIN",
            is_active=True,
        )
        organization = OperationalOrganization(name="Tracking API Organization")
        db.session.add_all([assignee, outsider, org_admin, organization])
        db.session.flush()
        db.session.add_all([
            OperationalMembership(organization_id=organization.id, user_id=assignee.id, permissions=[]),
            OperationalMembership(organization_id=organization.id, user_id=outsider.id, permissions=[]),
            OperationalMembership(
                organization_id=organization.id,
                user_id=org_admin.id,
                permissions=["tracking.read"],
            ),
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
            "request_public_id": request_row.public_id,
            "tracking_code": request_row.tracking_code,
            "assignee_token": create_session_tokens(assignee.id)["access_token"],
            "outsider_token": create_session_tokens(outsider.id)["access_token"],
            "org_admin_token": create_session_tokens(org_admin.id)["access_token"],
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


def test_tracking_management_requires_canonical_org_admin_capability(tracking_api_app):
    client = tracking_api_app["app"].test_client()
    path = f"/api/expert/requests/{tracking_api_app['request_id']}/tracking"
    assert client.get(path, headers=_headers(tracking_api_app["org_admin_token"])).status_code == 200


def test_tracking_shadow_telemetry_never_changes_canonical_decision(tracking_api_app, caplog, monkeypatch):
    shadow_logger = logging.getLogger("authorization.shadow")
    # Other suites may alter logger state.  Shadow is observational, so make
    # this test's capture boundary explicit rather than depending on globals.
    monkeypatch.setattr(shadow_logger, "disabled", False)
    monkeypatch.setattr(shadow_logger, "propagate", True)
    monkeypatch.setattr(shadow_logger, "level", logging.INFO)
    caplog.set_level(logging.INFO, logger="authorization.shadow")
    client = tracking_api_app["app"].test_client()
    path = f"/api/expert/requests/{tracking_api_app['request_id']}/tracking"
    assert client.get(path, headers=_headers(tracking_api_app["assignee_token"])).status_code == 200
    record = next(record for record in caplog.records if record.name == "authorization.shadow")
    assert "surface=expert_console.tracking" in record.message
    assert "canonical_allowed=True" in record.message
    assert "mismatch=False" in record.message


def test_tracking_management_opaque_parent_rejects_substitution(tracking_api_app):
    client = tracking_api_app["app"].test_client()
    headers = _headers(tracking_api_app["assignee_token"])
    opaque_path = f"/api/expert/requests/{tracking_api_app['request_public_id']}/tracking"
    assert client.get(opaque_path, headers=headers).status_code == 200
    assert client.get(
        opaque_path, headers=_headers(tracking_api_app["outsider_token"])
    ).status_code == 403
    assert client.get(
        "/api/expert/requests/not-a-uuid/tracking", headers=headers
    ).status_code == 404
    assert client.get(
        f"/api/expert/requests/{tracking_api_app['tracking_code']}/tracking",
        headers=headers,
    ).status_code == 404


def test_legacy_add_unit_fails_closed_without_creating_a_legacy_row(tracking_api_app):
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
    assert created.status_code == 409
    assert created.get_json() == {
        "code": "LEGACY_WRITE_MAPPING",
        "state": "NEEDS_DECISION",
        "error": "A canonical execution mapping is required.",
    }
    with tracking_api_app["app"].app_context():
        assert db.session.query(ShipmentTransportUnit).count() == 0


def test_mapped_legacy_metadata_and_update_delegate_to_canonical_models(tracking_api_app):
    client = tracking_api_app["app"].test_client()
    request_id = tracking_api_app["request_id"]
    headers = _headers(tracking_api_app["assignee_token"])
    client.post(f"/api/expert/requests/{request_id}/tracking/enable", headers=headers)
    with tracking_api_app["app"].app_context():
        request_row = db.session.get(ShipmentRequest, request_id)
        actor = db.session.scalar(db.select(ExpertUser).where(ExpertUser.username == "tracking-assignee"))
        legacy = ShipmentTransportUnit(
            tracking=request_row.shipment_tracking,
            ownership_scope="TENANT",
            operational_organization_id=request_row.operational_organization_id,
            unit_code="W-01", unit_type="wagon", created_by_user_id=actor.id,
        )
        db.session.add(legacy); db.session.flush()
        execution = ExecutionUnit(
            organization_id=request_row.operational_organization_id,
            legacy_unit_id=legacy.id, unit_code="EXEC-W-01", unit_type="wagon",
            created_by_user_id=actor.id,
        )
        db.session.add(execution); db.session.commit()
        unit_id, execution_id = legacy.id, execution.id
    updated = client.patch(
        f"/api/expert/requests/{request_id}/tracking/units/{unit_id}",
        headers=headers,
        json={"display_name": " Wagon 1 ", "vehicle_reference": "  WGN-900  "},
    )
    assert updated.status_code == 200
    occurred_at = (datetime.utcnow() - timedelta(minutes=1)).isoformat() + "Z"
    event_response = client.post(
        f"/api/expert/requests/{request_id}/tracking/units/{unit_id}/updates",
        headers=headers,
        json={"status": "in_transit", "location": "Qom", "customer_message": "On route", "occurred_at": occurred_at},
    )
    assert event_response.status_code == 201
    with tracking_api_app["app"].app_context():
        execution = db.session.get(ExecutionUnit, execution_id)
        legacy = db.session.get(ShipmentTransportUnit, unit_id)
        assert (execution.display_name, execution.vehicle_reference) == ("Wagon 1", "WGN-900")
        assert execution.lifecycle_status == "in_progress"
        assert db.session.query(OperationalEvent).filter_by(execution_unit_id=execution_id).count() == 1
        assert db.session.query(ShipmentTransportUnit).filter_by(id=unit_id).one().display_name is None
        assert db.session.query(ShipmentTransportUnitUpdate).count() == 0


def test_unmapped_historical_legacy_unit_write_paths_fail_closed(tracking_api_app):
    client = tracking_api_app["app"].test_client()
    request_id = tracking_api_app["request_id"]
    headers = _headers(tracking_api_app["assignee_token"])
    assert client.post(f"/api/expert/requests/{request_id}/tracking/enable", headers=headers).status_code == 200
    with tracking_api_app["app"].app_context():
        request_row = db.session.get(ShipmentRequest, request_id)
        actor = db.session.scalar(db.select(ExpertUser).where(ExpertUser.username == "tracking-assignee"))
        legacy = ShipmentTransportUnit(
            tracking=request_row.shipment_tracking, ownership_scope="TENANT",
            operational_organization_id=request_row.operational_organization_id,
            unit_code="HIST-01", unit_type="truck", display_name="Historical",
            created_by_user_id=actor.id,
        )
        db.session.add(legacy); db.session.commit(); unit_id = legacy.id
    historical = client.get(f"/api/expert/requests/{request_id}/tracking", headers=headers)
    assert historical.status_code == 200
    assert historical.get_json()["unit_tracking"]["units"][0]["unit_code"] == "HIST-01"
    metadata = client.patch(
        f"/api/expert/requests/{request_id}/tracking/units/{unit_id}", headers=headers,
        json={"display_name": "Must not write"},
    )
    update = client.post(
        f"/api/expert/requests/{request_id}/tracking/units/{unit_id}/updates", headers=headers,
        json={"status": "in_transit", "occurred_at": (datetime.utcnow() - timedelta(minutes=1)).isoformat() + "Z"},
    )
    expected = {"code": "LEGACY_WRITE_MAPPING", "state": "NEEDS_DECISION", "error": "A canonical execution mapping is required."}
    assert metadata.status_code == update.status_code == 409
    assert metadata.get_json() == update.get_json() == expected
    with tracking_api_app["app"].app_context():
        assert db.session.get(ShipmentTransportUnit, unit_id).display_name == "Historical"
        assert db.session.query(ShipmentTransportUnitUpdate).count() == 0


def test_cross_tenant_canonical_target_is_not_a_legacy_mapping(tracking_api_app):
    client = tracking_api_app["app"].test_client()
    request_id = tracking_api_app["request_id"]
    headers = _headers(tracking_api_app["assignee_token"])
    assert client.post(f"/api/expert/requests/{request_id}/tracking/enable", headers=headers).status_code == 200
    with tracking_api_app["app"].app_context():
        request_row = db.session.get(ShipmentRequest, request_id)
        actor = db.session.scalar(db.select(ExpertUser).where(ExpertUser.username == "tracking-assignee"))
        other_org = OperationalOrganization(name="Other tracking tenant")
        legacy = ShipmentTransportUnit(
            tracking=request_row.shipment_tracking, ownership_scope="TENANT",
            operational_organization_id=request_row.operational_organization_id,
            unit_code="OTHER-01", unit_type="truck", created_by_user_id=actor.id,
        )
        db.session.add_all([other_org, legacy]); db.session.flush()
        db.session.add(ExecutionUnit(
            organization_id=other_org.id, legacy_unit_id=legacy.id,
            unit_code="OTHER-EXEC-01", unit_type="truck", created_by_user_id=actor.id,
        ))
        db.session.commit(); unit_id = legacy.id
    response = client.patch(
        f"/api/expert/requests/{request_id}/tracking/units/{unit_id}", headers=headers,
        json={"display_name": "Cross tenant"},
    )
    assert response.status_code == 409
    assert response.get_json()["code"] == "LEGACY_WRITE_MAPPING"


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
