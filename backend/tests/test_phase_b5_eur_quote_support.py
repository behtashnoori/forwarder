"""Phase B5 contract tests for EUR in the existing Golden quote workflow."""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from backend import create_app
from backend.extensions import db
from backend.models import (
    CustomerGamification,
    ExpertConsoleLog,
    ExpertQuote,
    ExpertUser,
    ShipmentRequest,
)
from backend.operational_models import OperationalMembership, OperationalOrganization
from backend.services.auth_session_service import create_session_tokens
from backend.services.quote_currency import (
    DEFAULT_QUOTE_CURRENCY,
    QUOTE_CURRENCIES,
    SUPPORTED_QUOTE_CURRENCIES,
)
from backend.services.customer_portal_auth import SESSION_CSRF, SESSION_CUSTOMER_ID, SESSION_GENERATION


@pytest.fixture()
def eur_quote_state():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SECRET_KEY": "phase-b5-test-secret",
        },
        skip_startup=True,
    )
    with app.app_context():
        db.create_all()
        organization = OperationalOrganization(name="Phase B5 Organization")
        foreign_organization = OperationalOrganization(name="Phase B5 Foreign")
        expert = ExpertUser(
            username="phase_b5_expert",
            password_hash="synthetic-unusable",
            full_name="Phase B5 Expert",
            role="expert",
            is_active=True,
        )
        outsider = ExpertUser(
            username="phase_b5_outsider",
            password_hash="synthetic-unusable",
            full_name="Phase B5 Outsider",
            role="expert",
            is_active=True,
        )
        customer = CustomerGamification(email="phase-b5@example.test", phone="09120000000")
        db.session.add_all([organization, foreign_organization, expert, outsider, customer])
        db.session.flush()
        db.session.add_all(
            [
                OperationalMembership(
                    organization_id=organization.id,
                    user_id=expert.id,
                    is_active=True,
                ),
                OperationalMembership(
                    organization_id=foreign_organization.id,
                    user_id=outsider.id,
                    is_active=True,
                ),
            ]
        )
        request_row = ShipmentRequest(
            ownership_scope="TENANT",
            operational_organization_id=organization.id,
            tracking_code="SR-PHASE-B5-EUR",
            shipping_type="domestic",
            contact_phone=customer.phone,
            gamification_customer_id=customer.id,
            status="in_progress",
            status_request_status="in_progress",
            assigned_to=expert.id,
        )
        db.session.add(request_row)
        db.session.commit()
        state = {
            "app": app,
            "request_id": request_row.id,
            "tracking_code": request_row.tracking_code,
            "customer_id": customer.id,
            "request_public_id": request_row.public_id,
            "expert_token": create_session_tokens(expert.id)["access_token"],
            "outsider_token": create_session_tokens(outsider.id)["access_token"],
        }
        db.session.commit()
        yield state
        db.session.remove()
        db.drop_all()


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _customer_session(client, state):
    with client.session_transaction() as customer_session:
        customer_session[SESSION_CUSTOMER_ID] = state["customer_id"]
        customer_session[SESSION_GENERATION] = 0
        customer_session[SESSION_CSRF] = "phase-b5-csrf"
    return {"X-CSRF-Token": "phase-b5-csrf"}


def _customer_quote_endpoint(state):
    with state["app"].app_context():
        quote = ExpertQuote.query.filter_by(shipment_request_id=state["request_id"]).order_by(ExpertQuote.id.desc()).first()
        return f"/api/customer/requests/{state['request_public_id']}/quotes/{quote.public_id}/response"


def _publish(client, state, *, currency="EUR", valid_until=None):
    return client.post(
        f"/api/expert/requests/{state['request_id']}/quote",
        headers=_headers(state["expert_token"]),
        json={
            "amount": 1234567,
            "currency": currency,
            "note": "Phase B5 EUR quote",
            "valid_until": (valid_until or date.today() + timedelta(days=3)).isoformat(),
        },
    )


def test_quote_currency_contract_has_one_bounded_authoritative_set():
    assert DEFAULT_QUOTE_CURRENCY == "IRR"
    assert tuple(item["code"] for item in QUOTE_CURRENCIES) == ("IRR", "USD", "EUR")
    assert SUPPORTED_QUOTE_CURRENCIES == {"IRR", "USD", "EUR"}


def test_eur_validation_persistence_expert_and_customer_reads(eur_quote_state):
    client = eur_quote_state["app"].test_client()
    created = _publish(client, eur_quote_state)
    assert created.status_code == 200
    assert created.get_json()["quote"]["amount"] == 1234567
    assert created.get_json()["quote"]["currency"] == "EUR"
    assert created.get_json()["request"]["status"] == "waiting_for_customer"

    with eur_quote_state["app"].app_context():
        stored = ExpertQuote.query.filter_by(
            shipment_request_id=eur_quote_state["request_id"]
        ).one()
        assert stored.amount == 1234567
        assert stored.currency == "EUR"

    expert_read = client.get(
        f"/api/expert/requests/{eur_quote_state['request_id']}/quote/latest",
        headers=_headers(eur_quote_state["expert_token"]),
    )
    assert expert_read.status_code == 200
    assert expert_read.get_json()["quote"]["currency"] == "EUR"
    assert expert_read.get_json()["quote"]["amount"] == 1234567

    _customer_session(client, eur_quote_state)
    customer_read = client.get(f"/api/customer/requests/{eur_quote_state['request_public_id']}")
    assert customer_read.status_code == 200
    assert customer_read.get_json()["latest_quote"]["currency"] == "EUR"
    assert customer_read.get_json()["latest_quote"]["amount"] == 1234567

    refreshed = client.get(
        f"/api/expert/requests/{eur_quote_state['request_id']}/quote/latest",
        headers=_headers(eur_quote_state["expert_token"]),
    )
    assert refreshed.get_json()["quote"]["currency"] == "EUR"


def test_unsupported_quote_currency_remains_rejected(eur_quote_state):
    client = eur_quote_state["app"].test_client()
    response = _publish(client, eur_quote_state, currency="JPY")
    assert response.status_code == 400
    assert response.get_json() == {"error": "ارز پشتیبانی نمی‌شود"}
    with eur_quote_state["app"].app_context():
        assert ExpertQuote.query.count() == 0


@pytest.mark.parametrize(
    ("decision", "conflict"),
    (("accepted", "declined"), ("declined", "accepted")),
)
def test_eur_customer_response_preserves_golden_semantics(
    eur_quote_state, decision, conflict
):
    client = eur_quote_state["app"].test_client()
    assert _publish(client, eur_quote_state).status_code == 200

    headers = _customer_session(client, eur_quote_state)
    endpoint = _customer_quote_endpoint(eur_quote_state)
    response = client.post(endpoint, headers=headers, json={"response": decision, "expected_response_version": 0})
    assert response.status_code == 200
    assert response.get_json()["latest_quote"]["currency"] == "EUR"
    assert response.get_json()["latest_quote"]["customer_response"] == decision

    replay = client.post(endpoint, headers=headers, json={"response": decision, "expected_response_version": 1})
    assert replay.status_code == 200
    assert replay.get_json()["latest_quote"]["customer_response"] == decision
    assert client.post(endpoint, headers=headers, json={"response": conflict, "expected_response_version": 1}).status_code == 409

    with eur_quote_state["app"].app_context():
        request_row = db.session.get(ShipmentRequest, eur_quote_state["request_id"])
        quote = ExpertQuote.query.filter_by(shipment_request_id=request_row.id).one()
        assert quote.currency == "EUR"
        assert quote.customer_response == decision
        assert quote.responded_at is not None
        assert request_row.status == "waiting_for_customer"
        assert request_row.has_unread_for_assignee is True
        assert ExpertConsoleLog.query.filter_by(
            shipment_request_id=request_row.id,
            action="customer_quote_response",
        ).count() == 1


def test_eur_expiry_and_authorization_boundaries_are_unchanged(eur_quote_state):
    client = eur_quote_state["app"].test_client()
    forbidden = client.post(
        f"/api/expert/requests/{eur_quote_state['request_id']}/quote",
        headers=_headers(eur_quote_state["outsider_token"]),
        json={"amount": 1234567, "currency": "EUR"},
    )
    assert forbidden.status_code == 403
    assert _publish(
        client,
        eur_quote_state,
        valid_until=date.today() - timedelta(days=1),
    ).status_code == 200

    outsider_read = client.get(
        f"/api/expert/requests/{eur_quote_state['request_id']}/quote/latest",
        headers=_headers(eur_quote_state["outsider_token"]),
    )
    assert outsider_read.status_code == 403
    headers = _customer_session(client, eur_quote_state)
    expired = client.post(_customer_quote_endpoint(eur_quote_state), headers=headers, json={"response": "accepted", "expected_response_version": 0})
    assert expired.status_code == 400
    unrelated = client.post(
        "/api/customer/quote-response/SR-PHASE-B5-UNRELATED",
        json={"response": "accepted"},
    )
    assert unrelated.status_code == 404
