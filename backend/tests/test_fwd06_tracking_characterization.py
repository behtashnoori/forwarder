"""Pre-decision characterization, not operational/browser UAT certification."""
import json

import pytest

from backend.tests.test_multi_unit_tracking_api import tracking_api_app  # noqa: F401
from backend.tests.test_fwd05_runtime import journey  # noqa: F401


@pytest.mark.parametrize("kind", ["truck", "container", "wagon", "other"])
def test_existing_subject_accepts_valid_code_without_physical_reference(tracking_api_app, kind):  # noqa: F811
    client = tracking_api_app["app"].test_client()
    headers = {"Authorization": "Bearer " + tracking_api_app["assignee_token"]}
    base = f"/api/expert/requests/{tracking_api_app['request_public_id']}/tracking"
    assert client.post(base + "/enable", headers=headers).status_code == 200
    payload = {"unit_code": "FWD06-SYNTHETIC-01", "unit_type": kind}
    first = client.post(base + "/units", headers=headers, json=payload)
    assert first.status_code == 201
    unit = first.get_json()["unit_tracking"]["units"][0]
    assert unit["unit_code"] == payload["unit_code"]
    assert unit["vehicle_reference"] is None
    duplicate = client.post(base + "/units", headers=headers, json=payload)
    assert duplicate.status_code == 409
    reopened = client.get(base, headers=headers).get_json()["unit_tracking"]["units"]
    assert len(reopened) == 1 and reopened[0]["id"] == unit["id"]
    # Only bounded synthetic outcomes are emitted; no credential/session capture.
    print("FWD06_CHARACTERIZATION " + json.dumps({
        "kind": kind, "first_http": first.status_code,
        "retry_http": duplicate.status_code, "retry_error": duplicate.get_json()["error"],
        "reason_code": None, "field": "unit_code", "persisted_subjects": len(reopened),
    }))


def test_existing_intake_preconditions_are_preserved(tracking_api_app):  # noqa: F811
    client = tracking_api_app["app"].test_client()
    headers = {"Authorization": "Bearer " + tracking_api_app["assignee_token"]}
    base = f"/api/expert/requests/{tracking_api_app['request_public_id']}/tracking"
    missing_tracking = client.post(base + "/units", headers=headers,
        json={"unit_code": "FWD06-SYNTHETIC-01", "unit_type": "truck"})
    assert missing_tracking.status_code == 400
    assert missing_tracking.get_json()["error"] == "tracking is not enabled"
    assert client.post(base + "/enable", headers=headers).status_code == 200
    missing_code = client.post(base + "/units", headers=headers, json={"unit_type": "truck"})
    assert missing_code.status_code == 400
    assert missing_code.get_json()["error"] == "unit_code is required"
    print("FWD06_CHARACTERIZATION " + json.dumps({
        "missing_tracking_http": 400, "missing_tracking_error": "tracking is not enabled",
        "missing_code_http": 400, "missing_code_error": "unit_code is required",
        "reason_code": None,
    }))


def test_governed_quote_does_not_create_tracking_eligibility_or_shipment(journey):  # noqa: F811
    from backend.services.auth_session_service import create_session_tokens
    from backend.extensions import db
    from backend.models import ShipmentRequest
    from backend.operational_models import OperationalShipment

    root = db.session.get(ShipmentRequest, journey.root_id)
    assert root.status == "waiting_for_customer"
    token = create_session_tokens(journey.expert_id)["access_token"]
    base = f"/api/expert/requests/{root.public_id}/tracking"
    client = journey.app.test_client()
    headers = {"Authorization": "Bearer " + token}
    read = client.get(base, headers=headers)
    assert read.status_code == 200
    assert read.get_json()["eligible"] is False
    enabled = client.post(base + "/enable", headers=headers)
    assert enabled.status_code == 400
    assert enabled.get_json()["error"] == "shipment must be accepted before tracking is enabled"
    assert client.get(base, headers=headers).get_json()["enabled"] is False
    assert db.session.query(OperationalShipment).count() == 0
    print("FWD06_CHARACTERIZATION " + json.dumps({
        "engine": db.engine.dialect.name, "request_status": "waiting_for_customer", "enable_http": 400,
        "error": enabled.get_json()["error"], "reason_code": None,
        "operational_shipments_created": 0,
    }))
