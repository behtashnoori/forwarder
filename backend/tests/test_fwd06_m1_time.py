"""M1 command and provenance checks against real Flask routes and ORM writes."""

from datetime import datetime, timezone

import pytest

from backend.extensions import db
from backend.models import ShipmentTransportUnitUpdate
from backend.services.multi_unit_tracking_service import add_update, TrackingValidationError
from backend.services.tracking_time import TrackingTimeError, manual, offset
from backend.services import tracking_time
from backend.tests.test_multi_unit_tracking_api import tracking_api_app  # noqa: F401


def test_tehran_wall_is_independent_of_browser_zone():
    expected = datetime(2026, 7, 15, 8, 30, tzinfo=timezone.utc)
    assert manual("2026-07-15T12:00", "tracking.manual-iran.v1")[0] == expected
    assert offset("2026-07-15T12:00:00+03:30")[0] == expected
    precise = manual("2026-07-15T12:00:00.123456", "tracking.manual-iran.v1")
    assert precise[0] == expected.replace(microsecond=123456)
    assert precise[1] == "2026-07-15T12:00:00.123456"
    for policy in (None, "tracking.manual-iran.v2", "Asia/Tehran"):
        with pytest.raises(TrackingTimeError):
            manual("2026-07-15T12:00", policy)
    for bad in ("2026-02-30T12:00", "2026-07-15T12:00+03:30", "2026-07-15T25:00", "2026-07-15T12:00:00.1234567"):
        with pytest.raises(TrackingTimeError):
            manual(bad, "tracking.manual-iran.v1")
    with pytest.raises(TrackingTimeError, match="ambiguous or nonexistent"):
        manual("2022-03-22T00:30", "tracking.manual-iran.v1")
    with pytest.raises(TrackingTimeError):
        offset("2026-07-15T12:00:00")


def test_manual_route_persists_all_five_and_replays_authorized_snapshot(tracking_api_app, monkeypatch):  # noqa: F811
    app = tracking_api_app["app"]
    client = app.test_client()
    headers = {"Authorization": "Bearer " + tracking_api_app["assignee_token"]}
    base = f"/api/expert/requests/{tracking_api_app['request_public_id']}/tracking"
    assert client.post(base + "/enable", headers=headers).status_code == 200
    created = client.post(base + "/units", headers={**headers, "Idempotency-Key": "subject-1"},
                          json={"unit_code": "M1-TRUCK", "unit_type": "truck"})
    assert created.status_code == 201
    unit = created.get_json()["unit_tracking"]["units"][0]
    assert client.post(base + "/units", headers={**headers, "Idempotency-Key": "subject-1"},
                       json={"unit_code": "M1-TRUCK", "unit_type": "truck"}).status_code == 200
    assert client.post(base + "/units", headers={**headers, "Idempotency-Key": "subject-1"},
                       json={"unit_code": "OTHER", "unit_type": "truck"}).status_code == 409
    path = f"{base}/units/{unit['id']}/updates"
    payload = {"status": "in_transit", "time_input_wall": "2026-07-15T12:00",
               "time_input_policy": "tracking.manual-iran.v1", "location_text": "Tehran"}
    keyed = {**headers, "Idempotency-Key": "event-1"}
    first = client.post(path, headers=keyed, json=payload)
    assert first.status_code == 201
    monkeypatch.setattr(tracking_time, "POLICY", "tracking.manual-iran.v2")
    assert client.post(path, headers=keyed, json=payload).status_code == 200
    assert client.post(path, headers=keyed, json={**payload, "status": "delayed"}).status_code == 409
    timeline = client.get(base, headers=headers).get_json()["unit_tracking"]["units"][0]["timeline"]
    assert len(timeline) == 1
    assert timeline[0]["event_at"] == "2026-07-15T08:30:00Z"
    assert timeline[0]["recorded_at"] != timeline[0]["event_at"]
    public = client.get(f"/api/public/track/{tracking_api_app['tracking_code']}").get_json()["unit_tracking"]
    assert public["units"][0]["timeline"][0]["event_at"] == "2026-07-15T08:30:00Z"
    assert all(key not in str(public) for key in ("time_input_policy", "time_input_basis", "time_input_source", "internal_note", "operational_organization_id"))
    with app.app_context():
        row = db.session.query(ShipmentTransportUnitUpdate).one()
        assert row.time_input_wall == "2026-07-15T12:00"
        assert row.time_input_basis == "Asia/Tehran"
        assert row.time_input_source == "manual"
        assert row.time_input_policy == "tracking.manual-iran.v1"
        assert row.occurred_at == datetime(2026, 7, 15, 8, 30)
        assert row.occurred_at_utc.replace(tzinfo=timezone.utc) == datetime(2026, 7, 15, 8, 30, tzinfo=timezone.utc)
        row.unit.tracking.is_enabled = False
        db.session.commit()
    assert client.post(path, headers=keyed, json=payload).status_code == 400
    assert client.post(base + "/units", headers={**headers, "Idempotency-Key": "subject-1"},
                       json={"unit_code": "M1-TRUCK", "unit_type": "truck"}).status_code == 400


def test_untrusted_source_and_invalid_time_fail_closed(tracking_api_app):  # noqa: F811
    client = tracking_api_app["app"].test_client()
    headers = {"Authorization": "Bearer " + tracking_api_app["assignee_token"]}
    base = f"/api/expert/requests/{tracking_api_app['request_public_id']}/tracking"
    client.post(base + "/enable", headers=headers)
    unit = client.post(base + "/units", headers=headers, json={"unit_code": "M1", "unit_type": "other"}).get_json()["unit_tracking"]["units"][0]
    path = f"{base}/units/{unit['id']}/updates"
    for payload in (
        {"status": "in_transit", "time_input_wall": "2026-07-15T12:00"},
        {"status": "in_transit", "time_input_wall": "2026-07-15T12:00", "time_input_policy": "tracking.manual-iran.v1", "occurred_at": "2026-07-15T08:30:00Z"},
        {"status": "in_transit", "occurred_at": "2026-07-15T12:00:00"},
        {"status": "in_transit", "occurred_at": "2026-07-15T12:00:00Z", "source": "machine"},
    ):
        assert client.post(path, headers=headers, json=payload).status_code in (400, 403)
    assert client.get(base, headers=headers).get_json()["unit_tracking"]["units"][0]["timeline"] == []


def test_offset_contract_and_historical_unknown_are_distinct(tracking_api_app):  # noqa: F811
    app = tracking_api_app["app"]
    client = app.test_client()
    headers = {"Authorization": "Bearer " + tracking_api_app["assignee_token"]}
    base = f"/api/expert/requests/{tracking_api_app['request_public_id']}/tracking"
    client.post(base + "/enable", headers=headers)
    unit = client.post(base + "/units", headers=headers, json={"unit_code": "OFFSET", "unit_type": "wagon"}).get_json()["unit_tracking"]["units"][0]
    path = f"{base}/units/{unit['id']}/updates"
    response = client.post(path, headers=headers, json={"status": "in_transit", "occurred_at": "2026-07-15T12:00:00+04:00"})
    assert response.status_code == 201
    with app.app_context():
        row = db.session.query(ShipmentTransportUnitUpdate).one()
        assert row.time_input_source == "offset"
        assert row.time_input_wall == "2026-07-15T12:00:00"
        assert row.time_input_basis == "+04:00"
        assert row.time_input_policy is None
        assert row.occurred_at == datetime(2026, 7, 15, 8, 0)
        with pytest.raises(TrackingValidationError, match="inconsistent"):
            add_update(row.unit, row.created_by_user_id,
                       status="loading", occurred_at=datetime(2026, 7, 15, 8, tzinfo=timezone.utc),
                       time_snapshot=(datetime(2026, 7, 15, 8, tzinfo=timezone.utc),
                                      "2026-07-15T12:00:00", "+03:30", "offset", None))
        legacy = ShipmentTransportUnitUpdate(
            unit_id=unit["id"], operational_organization_id=row.operational_organization_id,
            ownership_scope="TENANT", status="loading", occurred_at=datetime(2026, 7, 16, 8, 0),
            created_at=datetime(2026, 7, 14, 8, 1), is_customer_visible=True,
        )
        db.session.add(legacy)
        db.session.commit()
    history = client.get(base, headers=headers).get_json()["unit_tracking"]["units"][0]["timeline"]
    assert history[1]["event_at"] is None
    assert history[1]["recorded_at"].endswith("Z")
    public = client.get(f"/api/public/track/{tracking_api_app['tracking_code']}").get_json()["unit_tracking"]
    assert public["units"][0]["timeline"][1]["event_at"] is None


def test_visible_last_recorded_and_late_event_scope(tracking_api_app):  # noqa: F811
    client = tracking_api_app["app"].test_client()
    headers = {"Authorization": "Bearer " + tracking_api_app["assignee_token"]}
    base = f"/api/expert/requests/{tracking_api_app['request_public_id']}/tracking"
    client.post(base + "/enable", headers=headers)
    unit = client.post(base + "/units", headers=headers, json={"unit_code": "VISIBLE", "unit_type": "container"}).get_json()["unit_tracking"]["units"][0]
    path = f"{base}/units/{unit['id']}/updates"
    assert client.post(path, headers=headers, json={"status": "in_transit", "occurred_at": "2026-07-15T12:00:00Z"}).status_code == 201
    public_path = f"/api/public/track/{tracking_api_app['tracking_code']}"
    first = client.get(public_path).get_json()["unit_tracking"]
    first_recorded = first["last_recorded_at"]
    assert first["summary"]["in_transit"] == 1
    assert client.post(path, headers=headers, json={"status": "delayed", "occurred_at": "2026-07-15T13:00:00Z", "is_customer_visible": False, "internal_note": "private"}).status_code == 201
    hidden = client.get(public_path).get_json()["unit_tracking"]
    assert hidden["last_recorded_at"] == first_recorded
    assert len(hidden["units"][0]["timeline"]) == 1
    assert "private" not in str(hidden)
    assert client.post(path, headers=headers, json={"status": "delivered", "occurred_at": "2026-07-14T12:00:00Z"}).status_code == 201
    late = client.get(public_path).get_json()["unit_tracking"]
    assert late["units"][0]["latest_status"] == "in_transit"
    assert late["last_updated_at"] == "2026-07-15T12:00:00Z"
    assert late["last_recorded_at"] >= first_recorded
    assert len(late["units"][0]["timeline"]) == 2
