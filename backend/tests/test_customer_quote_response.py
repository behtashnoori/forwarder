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


@pytest.mark.parametrize("identifier", ["tracking", "1", "SR-NOT-FOUND", "SR-FOREIGN-CAPABILITY"])
@pytest.mark.parametrize("response", ["accepted", "declined", "negotiation_requested", "maybe", None])
@pytest.mark.parametrize("expired", [False, True])
def test_retired_tracking_writer_denies_without_resolving_or_mutating(app, client, identifier, response, expired):
    with app.app_context():
        _, request_id, quote_id, tracking = _seed(
            valid_until=date.today() + timedelta(days=-1 if expired else 3))
        before = db.session.get(ShipmentRequest, request_id).has_unread_for_assignee
    path = tracking if identifier == "tracking" else identifier
    first = client.post(f"/api/customer/quote-response/{path}", json={"response": response})
    replay = client.post(f"/api/customer/quote-response/{path}", json={"response": response})
    assert first.status_code == replay.status_code == 403
    assert first.get_json() == replay.get_json() == {
        "message": "امکان پاسخ از این مسیر وجود ندارد", "reason": "CUSTOMER_ACTION_UNAVAILABLE"}
    with app.app_context():
        from backend.models import ExpertConsoleLog
        from backend.quote_response_models import QuoteResponseFact, QuoteResponseReceipt
        quote = db.session.get(ExpertQuote, quote_id)
        assert quote.customer_response is None and quote.responded_at is None
        assert db.session.get(ShipmentRequest, request_id).has_unread_for_assignee == before
        assert ExpertConsoleLog.query.filter_by(shipment_request_id=request_id, action="customer_quote_response").count() == 0
        assert QuoteResponseFact.query.count() == QuoteResponseReceipt.query.count() == 0


def test_workflow_preserves_historical_response_as_read_only_evidence(app, client):
    with app.app_context():
        customer_id, request_id, quote_id, _ = _seed()
        # Explicit legacy fixture; no new capability fact or invented backfill.
        quote = db.session.get(ExpertQuote, quote_id)
        quote.customer_response = "accepted"
        quote.responded_at = datetime(2026, 8, 1, 12, 0)
        db.session.commit()
    result = client.get(f"/api/customer/workflow/{customer_id}?request_id={request_id}")
    assert result.status_code == 200
    latest = result.get_json()["latest_quote"]
    assert latest["customer_response"] == "accepted"
    assert latest["responded_at"] == "2026-08-01T12:00:00"
    assert latest["money_contract"] == "legacy-unspecified" and latest["unit"] == "unknown"
    assert latest["amount"] == 1000000 and latest["currency"] == "IRR"
    assert "id" not in latest
