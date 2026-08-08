"""Contract tests for the customer quote accept/decline flow."""
from datetime import date, datetime, timedelta

import pytest

from backend import create_app
from backend.extensions import db
from backend.models import CustomerGamification, ExpertQuote, ExpertUser, ShipmentRequest


@pytest.fixture()
def app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def _seed(valid_until=None):
    customer = CustomerGamification(email="c@example.com", phone="09121234567")
    expert = ExpertUser(username="ex1", password_hash="x", full_name="کارشناس یک")
    db.session.add_all([customer, expert])
    db.session.flush()
    req = ShipmentRequest(
        shipping_type="domestic", contact_phone="09121234567",
        gamification_customer_id=customer.id, status="quoted",
    )
    db.session.add(req)
    db.session.flush()
    quote = ExpertQuote(
        shipment_request_id=req.id, amount=1000000, currency="IRR",
        created_by_expert_id=expert.id, valid_until=valid_until,
    )
    db.session.add(quote)
    db.session.commit()
    req.tracking_code = "SR-QUOTE-CAPABILITY"
    db.session.commit()
    return customer.id, req.id, quote.id, req.tracking_code


def test_customer_can_accept_quote(app, client):
    with app.app_context():
        _customer_id, request_id, quote_id, tracking_code = _seed(valid_until=date.today() + timedelta(days=3))

    resp = client.post(f"/api/customer/quote-response/{tracking_code}", json={"response": "accepted"})
    assert resp.status_code == 200
    assert resp.get_json()["latest_quote"]["customer_response"] == "accepted"

    with app.app_context():
        quote = db.session.get(ExpertQuote, quote_id)
        assert quote.customer_response == "accepted"
        assert quote.responded_at is not None
        assert db.session.get(ShipmentRequest, request_id).has_unread_for_assignee is True


def test_customer_can_decline_quote(app, client):
    with app.app_context():
        _customer_id, _request_id, _, tracking_code = _seed()
    resp = client.post(f"/api/customer/quote-response/{tracking_code}", json={"response": "declined"})
    assert resp.status_code == 200
    assert resp.get_json()["latest_quote"]["customer_response"] == "declined"


def test_invalid_response_is_rejected(app, client):
    with app.app_context():
        _customer_id, _request_id, _, tracking_code = _seed()
    resp = client.post(f"/api/customer/quote-response/{tracking_code}", json={"response": "maybe"})
    assert resp.status_code == 400


def test_double_response_is_conflict(app, client):
    with app.app_context():
        _customer_id, _request_id, _, tracking_code = _seed()
    first = client.post(f"/api/customer/quote-response/{tracking_code}", json={"response": "accepted"})
    assert first.status_code == 200
    replay = client.post(f"/api/customer/quote-response/{tracking_code}", json={"response": "accepted"})
    assert replay.status_code == 200
    second = client.post(f"/api/customer/quote-response/{tracking_code}", json={"response": "declined"})
    assert second.status_code == 409


def test_expired_quote_cannot_be_answered(app, client):
    with app.app_context():
        _customer_id, _request_id, _, tracking_code = _seed(valid_until=date.today() - timedelta(days=1))
    resp = client.post(f"/api/customer/quote-response/{tracking_code}", json={"response": "accepted"})
    assert resp.status_code == 400


def test_foreign_customer_cannot_answer(app, client):
    with app.app_context():
        _customer_id, _request_id, _, _tracking_code = _seed()
        other = CustomerGamification(email="o@example.com", phone="09120000000")
        db.session.add(other)
        db.session.commit()
        other_id = other.id
    resp = client.post(f"/api/customer/quote-response/SR-FOREIGN-CAPABILITY", json={"response": "accepted"})
    assert resp.status_code == 404


def test_workflow_payload_exposes_quote_response(app, client):
    with app.app_context():
        customer_id, request_id, _, tracking_code = _seed()
        client.post(f"/api/customer/quote-response/{tracking_code}", json={"response": "accepted"})

    resp = client.get(f"/api/customer/workflow/{customer_id}?request_id={request_id}")
    assert resp.status_code == 200
    latest_quote = resp.get_json()["latest_quote"]
    assert latest_quote["customer_response"] == "accepted"
    assert "responded_at" in latest_quote
    assert "id" not in latest_quote


def test_numeric_and_invalid_capabilities_have_same_not_found_behavior(app, client):
    with app.app_context():
        _seed()
    numeric = client.post("/api/customer/quote-response/1", json={"response": "accepted"})
    invalid = client.post("/api/customer/quote-response/SR-NOT-FOUND", json={"response": "accepted"})
    assert numeric.status_code == invalid.status_code == 404
    assert numeric.get_json() == invalid.get_json()


def test_response_is_audited(app, client):
    with app.app_context():
        _customer_id, request_id, _, tracking_code = _seed()
    response = client.post(
        f"/api/customer/quote-response/{tracking_code}",
        json={"response": "accepted"},
        environ_base={"REMOTE_ADDR": "203.0.113.9"},
    )
    assert response.status_code == 200
    with app.app_context():
        from backend.models import ExpertConsoleLog
        audit = ExpertConsoleLog.query.filter_by(
            shipment_request_id=request_id, action="customer_quote_response"
        ).one()
        assert audit.ip_address == "203.0.113.9"
