"""Contract tests for the customer quote accept/decline flow."""
from datetime import date, datetime, timedelta

import pytest

from backend import create_app
from backend.extensions import db
from backend.models import (
    CustomerGamification,
    ExpertConsoleLog,
    ExpertQuote,
    ExpertUser,
    RequestCargoItem,
    ShipmentRequest,
)
from backend.services.customer_portal_auth import SESSION_CSRF, SESSION_CUSTOMER_ID, SESSION_GENERATION


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
    suffix = CustomerGamification.query.count() + 1
    customer = CustomerGamification(email=f"c{suffix}@example.com", phone=f"09121234{suffix:03d}")
    expert = ExpertUser(username=f"ex{suffix}", password_hash="x", full_name="کارشناس یک")
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
    req.tracking_code = f"SR2-Q{suffix:021d}"
    db.session.commit()
    return customer.id, req.id, quote.id, req.tracking_code


def _private_response(
    client, *, customer_id, tracking_code, response, quote_public_id=None,
    message=None, remote_addr=None,
):
    with client.application.app_context():
        request_row = ShipmentRequest.query.filter_by(tracking_code=tracking_code).one_or_none()
        if request_row is None:
            request_public_id = "11111111-1111-4111-8111-111111111111"
        else:
            request_public_id = request_row.public_id
        if quote_public_id is None and request_row is not None:
            quote = ExpertQuote.query.filter_by(shipment_request_id=request_row.id).order_by(
                ExpertQuote.created_at.desc(), ExpertQuote.id.desc()
            ).first()
            quote_public_id = quote.public_id if quote else "22222222-2222-4222-8222-222222222222"
        quote = ExpertQuote.query.filter_by(public_id=quote_public_id).one_or_none()
        expected_version = int(quote.response_version or 0) if quote else 0
    with client.session_transaction() as customer_session:
        customer_session[SESSION_CUSTOMER_ID] = customer_id
        customer_session[SESSION_GENERATION] = 0
        customer_session[SESSION_CSRF] = "quote-test-csrf"
    payload = {"response": response, "expected_response_version": expected_version}
    if message is not None:
        payload["message"] = message
    return client.post(
        f"/api/customer/requests/{request_public_id}/quotes/{quote_public_id}/response",
        headers={"X-CSRF-Token": "quote-test-csrf"}, json=payload,
        environ_base={"REMOTE_ADDR": remote_addr} if remote_addr else {},
    )


def test_customer_can_accept_quote(app, client):
    with app.app_context():
        customer_id, request_id, quote_id, tracking_code = _seed(valid_until=date.today() + timedelta(days=3))

    resp = _private_response(client, customer_id=customer_id, tracking_code=tracking_code, response="accepted")
    assert resp.status_code == 200
    assert resp.get_json()["latest_quote"]["customer_response"] == "accepted"

    with app.app_context():
        quote = db.session.get(ExpertQuote, quote_id)
        assert quote.customer_response == "accepted"
        assert quote.responded_at is not None
        request_row = db.session.get(ShipmentRequest, request_id)
        assert request_row.has_unread_for_assignee is True
        assert request_row.status == "quoted"


def test_customer_can_decline_quote(app, client):
    with app.app_context():
        customer_id, request_id, _, tracking_code = _seed()
    resp = _private_response(client, customer_id=customer_id, tracking_code=tracking_code, response="declined")
    assert resp.status_code == 200
    assert resp.get_json()["latest_quote"]["customer_response"] == "declined"
    with app.app_context():
        assert db.session.get(ShipmentRequest, request_id).status == "quoted"


def test_invalid_response_is_rejected(app, client):
    with app.app_context():
        customer_id, _request_id, _, tracking_code = _seed()
    resp = _private_response(client, customer_id=customer_id, tracking_code=tracking_code, response="maybe")
    assert resp.status_code == 400


def test_double_response_is_conflict(app, client):
    with app.app_context():
        customer_id, _request_id, _, tracking_code = _seed()
    first = _private_response(client, customer_id=customer_id, tracking_code=tracking_code, response="accepted")
    assert first.status_code == 200
    replay = _private_response(client, customer_id=customer_id, tracking_code=tracking_code, response="accepted")
    assert replay.status_code == 200
    second = _private_response(client, customer_id=customer_id, tracking_code=tracking_code, response="declined")
    assert second.status_code == 409


def test_expired_quote_cannot_be_answered(app, client):
    with app.app_context():
        customer_id, _request_id, _, tracking_code = _seed(valid_until=date.today() - timedelta(days=1))
    resp = _private_response(client, customer_id=customer_id, tracking_code=tracking_code, response="accepted")
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
        _private_response(client, customer_id=customer_id, tracking_code=tracking_code, response="accepted")

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


def test_both_legacy_public_quote_writers_are_removed(app, client):
    tracking_writer = client.post(
        "/api/customer/quote-response/SR2-REMOVED", json={"response": "accepted"}
    )
    quote_writer = client.post(
        "/api/customer/quotes/11111111-1111-4111-8111-111111111111/response",
        json={"response": "accepted"},
    )
    assert tracking_writer.status_code == quote_writer.status_code == 404
    assert tracking_writer.get_json() == quote_writer.get_json() == {
        "code": "QUOTE_NOT_FOUND", "message": "Not found"
    }


def test_private_quote_writer_requires_customer_authentication(app, client):
    response = client.post(
        "/api/customer/requests/11111111-1111-4111-8111-111111111111/quotes/"
        "22222222-2222-4222-8222-222222222222/response",
        json={"response": "accepted", "expected_response_version": 0},
    )
    assert response.status_code == 401
    assert response.get_json()["code"] == "AUTHENTICATION_REQUIRED"


def test_response_is_audited(app, client):
    with app.app_context():
        customer_id, request_id, _, tracking_code = _seed()
    response = _private_response(
        client, customer_id=customer_id, tracking_code=tracking_code,
        response="accepted", remote_addr="203.0.113.9",
    )
    assert response.status_code == 200
    with app.app_context():
        from backend.models import ExpertConsoleLog
        audit = ExpertConsoleLog.query.filter_by(
            shipment_request_id=request_id, action="customer_quote_response"
        ).one()
        assert audit.ip_address == "203.0.113.9"


def _canonical_response(
    client,
    *,
    quote_public_id,
    tracking_code,
    customer_id,
    response,
    message=None,
):
    return _private_response(
        client, quote_public_id=quote_public_id, tracking_code=tracking_code,
        customer_id=customer_id, response=response, message=message,
    )


def test_canonical_discussion_requires_and_preserves_one_bounded_message(app, client):
    with app.app_context():
        customer_id, request_id, quote_id, tracking_code = _seed()
        quote = db.session.get(ExpertQuote, quote_id)
        quote.currency = "EUR"
        quote_public_id = quote.public_id
        original_amount = quote.amount
        db.session.commit()

    missing = _canonical_response(
        client,
        quote_public_id=quote_public_id,
        tracking_code=tracking_code,
        customer_id=customer_id,
        response="discussion",
    )
    blank = _canonical_response(
        client,
        quote_public_id=quote_public_id,
        tracking_code=tracking_code,
        customer_id=customer_id,
        response="discussion",
        message="   ",
    )
    too_long = _canonical_response(
        client,
        quote_public_id=quote_public_id,
        tracking_code=tracking_code,
        customer_id=customer_id,
        response="discussion",
        message="x" * 501,
    )
    control = _canonical_response(
        client,
        quote_public_id=quote_public_id,
        tracking_code=tracking_code,
        customer_id=customer_id,
        response="discussion",
        message="line one\nline two",
    )
    assert missing.status_code == blank.status_code == too_long.status_code == control.status_code == 400
    assert missing.get_json()["code"] == "DISCUSSION_MESSAGE_REQUIRED"
    assert too_long.get_json()["code"] == control.get_json()["code"] == "DISCUSSION_MESSAGE_INVALID"

    response = _canonical_response(
        client,
        quote_public_id=quote_public_id,
        tracking_code=tracking_code,
        customer_id=customer_id,
        response="discussion",
        message="  لطفاً درباره زمان پرداخت صحبت کنیم.  ",
    )
    assert response.status_code == 200
    assert response.get_json()["code"] == "QUOTE_RESPONSE_RECORDED"
    latest = response.get_json()["latest_quote"]
    assert latest["customer_response"] == "discussion"
    assert latest["customer_response_message"] == "لطفاً درباره زمان پرداخت صحبت کنیم."
    assert latest["amount"] == original_amount
    assert latest["currency"] == "EUR"

    with app.app_context():
        quote = db.session.get(ExpertQuote, quote_id)
        assert quote.responded_by_customer_id == customer_id
        assert quote.amount == original_amount
        assert quote.currency == "EUR"
        assert ExpertQuote.query.count() == 1
        audit = ExpertConsoleLog.query.filter_by(
            shipment_request_id=request_id, action="customer_quote_response"
        ).one()
        assert "زمان پرداخت" not in (audit.note or "")


@pytest.mark.parametrize("response", ["accepted", "declined"])
def test_approve_and_reject_forbid_message_and_use_opaque_quote_identity(app, client, response):
    with app.app_context():
        customer_id, _request_id, quote_id, tracking_code = _seed()
        quote_public_id = db.session.get(ExpertQuote, quote_id).public_id

    forbidden = _canonical_response(
        client,
        quote_public_id=quote_public_id,
        tracking_code=tracking_code,
        customer_id=customer_id,
        response=response,
        message="not allowed",
    )
    assert forbidden.status_code == 400
    assert forbidden.get_json()["code"] == "DISCUSSION_MESSAGE_NOT_ALLOWED"

    recorded = _canonical_response(
        client,
        quote_public_id=quote_public_id,
        tracking_code=tracking_code,
        customer_id=customer_id,
        response=response,
    )
    assert recorded.status_code == 200
    assert recorded.get_json()["latest_quote"]["customer_response"] == response


def test_exact_discussion_replay_is_idempotent_and_changed_message_conflicts(app, client):
    with app.app_context():
        customer_id, request_id, quote_id, tracking_code = _seed()
        quote_public_id = db.session.get(ExpertQuote, quote_id).public_id

    command = dict(
        quote_public_id=quote_public_id,
        tracking_code=tracking_code,
        customer_id=customer_id,
        response="discussion",
        message="نیاز به هماهنگی زمان تحویل داریم",
    )
    first = _canonical_response(client, **command)
    replay = _canonical_response(client, **command)
    conflict = _canonical_response(client, **{**command, "message": "پیام متفاوت"})
    assert first.status_code == replay.status_code == 200
    assert replay.get_json()["code"] == "QUOTE_RESPONSE_REPLAYED"
    assert conflict.status_code == 409
    assert conflict.get_json()["code"] == "QUOTE_RESPONSE_CONFLICT"
    with app.app_context():
        assert ExpertConsoleLog.query.filter_by(
            shipment_request_id=request_id, action="customer_quote_response"
        ).count() == 1


def test_wrong_customer_foreign_and_unknown_quote_are_non_disclosing(app, client):
    with app.app_context():
        customer_id, _request_id, quote_id, tracking_code = _seed()
        other = CustomerGamification(email="other@example.com", phone="09120000001")
        db.session.add(other)
        db.session.commit()
        other_id = other.id
        quote_public_id = db.session.get(ExpertQuote, quote_id).public_id

    wrong_customer = _canonical_response(
        client,
        quote_public_id=quote_public_id,
        tracking_code=tracking_code,
        customer_id=other_id,
        response="accepted",
    )
    unknown_quote = _canonical_response(
        client,
        quote_public_id="11111111-1111-4111-8111-111111111111",
        tracking_code=tracking_code,
        customer_id=customer_id,
        response="accepted",
    )
    numeric_quote = _canonical_response(
        client,
        quote_public_id=str(quote_id),
        tracking_code=tracking_code,
        customer_id=customer_id,
        response="accepted",
    )
    assert wrong_customer.status_code == unknown_quote.status_code == numeric_quote.status_code == 404
    assert wrong_customer.get_json() == unknown_quote.get_json() == numeric_quote.get_json()


def test_removed_customer_relationship_revokes_the_response_capability(app, client):
    with app.app_context():
        customer_id, request_id, quote_id, tracking_code = _seed()
        quote_public_id = db.session.get(ExpertQuote, quote_id).public_id
        db.session.get(ShipmentRequest, request_id).gamification_customer_id = None
        db.session.commit()

    revoked = _canonical_response(
        client,
        quote_public_id=quote_public_id,
        tracking_code=tracking_code,
        customer_id=customer_id,
        response="accepted",
    )
    assert revoked.status_code == 404
    assert revoked.get_json() == {"code": "QUOTE_NOT_FOUND", "message": "Not found"}


def test_revised_quote_is_new_current_object_and_prior_discussion_stays_history(app, client):
    with app.app_context():
        customer_id, request_id, quote_id, tracking_code = _seed()
        q1 = db.session.get(ExpertQuote, quote_id)
        q1.currency = "EUR"
        q1_public_id = q1.public_id
        q1_amount = q1.amount
        db.session.commit()

    discussed = _canonical_response(
        client,
        quote_public_id=q1_public_id,
        tracking_code=tracking_code,
        customer_id=customer_id,
        response="discussion",
        message="شرایط پرداخت نیاز به گفتگو دارد",
    )
    assert discussed.status_code == 200
    with app.app_context():
        q2 = ExpertQuote(
            shipment_request_id=request_id,
            amount=q1_amount + 250,
            currency="USD",
            created_by_expert_id=db.session.get(ExpertQuote, quote_id).created_by_expert_id,
            created_at=datetime.utcnow() + timedelta(seconds=1),
        )
        db.session.add(q2)
        db.session.commit()
        q2_id = q2.id
        q2_public_id = q2.public_id

    superseded = _canonical_response(
        client,
        quote_public_id=q1_public_id,
        tracking_code=tracking_code,
        customer_id=customer_id,
        response="declined",
    )
    accepted_q2 = _canonical_response(
        client,
        quote_public_id=q2_public_id,
        tracking_code=tracking_code,
        customer_id=customer_id,
        response="accepted",
    )
    assert superseded.status_code == 409
    assert superseded.get_json()["code"] == "QUOTE_SUPERSEDED"
    assert accepted_q2.status_code == 200

    workflow = client.get(f"/api/customer/workflow/{customer_id}?request_id={request_id}")
    history = workflow.get_json()["quote_history"]
    assert [item["public_id"] for item in history] == [q2_public_id, q1_public_id]
    assert history[0]["customer_response"] == "accepted"
    assert history[1]["customer_response"] == "discussion"
    assert history[1]["customer_response_message"] == "شرایط پرداخت نیاز به گفتگو دارد"
    with app.app_context():
        q1 = db.session.get(ExpertQuote, quote_id)
        q2 = db.session.get(ExpertQuote, q2_id)
        assert (q1.amount, q1.currency) == (q1_amount, "EUR")
        assert (q2.amount, q2.currency) == (q1_amount + 250, "USD")


def test_expired_terminal_combined_zero_and_multi_cargo_contracts(app, client):
    with app.app_context():
        customer_id, request_id, quote_id, tracking_code = _seed()
        request_row = db.session.get(ShipmentRequest, request_id)
        request_row.domestic_transport_method = "COMBINED_TRANSPORT"
        db.session.add_all([
            RequestCargoItem(shipment_request_id=request_id, position=1, description="اول"),
            RequestCargoItem(shipment_request_id=request_id, position=2, description="دوم"),
        ])
        quote = db.session.get(ExpertQuote, quote_id)
        quote_public_id = quote.public_id
        db.session.commit()

    response = _canonical_response(
        client,
        quote_public_id=quote_public_id,
        tracking_code=tracking_code,
        customer_id=customer_id,
        response="discussion",
        message="بدون وابستگی به نوع حمل یا تعداد کالا",
    )
    assert response.status_code == 200
    with app.app_context():
        request_row = db.session.get(ShipmentRequest, request_id)
        assert request_row.domestic_transport_method == "COMBINED_TRANSPORT"
        assert len(request_row.request_cargo_items) == 2

    with app.app_context():
        customer2, request2, quote2, tracking2 = _seed(valid_until=date.today() - timedelta(days=1))
        quote2_public = db.session.get(ExpertQuote, quote2).public_id
    expired = _canonical_response(
        client,
        quote_public_id=quote2_public,
        tracking_code=tracking2,
        customer_id=customer2,
        response="accepted",
    )
    assert expired.status_code == 400
    assert expired.get_json()["code"] == "QUOTE_EXPIRED"

    with app.app_context():
        customer3, request3, quote3, tracking3 = _seed()
        db.session.get(ShipmentRequest, request3).status = "cancelled"
        db.session.commit()
        quote3_public = db.session.get(ExpertQuote, quote3).public_id
    terminal = _canonical_response(
        client,
        quote_public_id=quote3_public,
        tracking_code=tracking3,
        customer_id=customer3,
        response="accepted",
    )
    assert terminal.status_code == 409
    assert terminal.get_json()["code"] == "QUOTE_RESPONSE_NOT_ALLOWED"


def test_public_tracking_never_exposes_private_discussion_message(app, client):
    with app.app_context():
        customer_id, _request_id, quote_id, tracking_code = _seed()
        quote_public_id = db.session.get(ExpertQuote, quote_id).public_id
    recorded = _canonical_response(
        client,
        quote_public_id=quote_public_id,
        tracking_code=tracking_code,
        customer_id=customer_id,
        response="discussion",
        message="محرمانه تجاری مشتری",
    )
    assert recorded.status_code == 200
    public = client.get(f"/api/public/track/{tracking_code}")
    assert public.status_code == 200
    assert "latest_quote" not in public.get_json()
    assert "محرمانه تجاری مشتری" not in public.get_data(as_text=True)
