"""Adversarial local certification for the second MT-1 ownership slice."""
from __future__ import annotations

import pytest

from backend import create_app
from backend.extensions import db
from backend.models import (
    Activity,
    Customer,
    DocumentAuditEvent,
    ExpertUser,
    Opportunity,
    ShipmentRequest,
)
from backend.operational_models import OperationalMembership, OperationalOrganization
from backend.services.auth_session_service import create_session_tokens


@pytest.fixture()
def ownership_app():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "mt1-slice2-test",
    }, skip_startup=True)
    with app.app_context():
        db.create_all()
        org_a = OperationalOrganization(name="Organization A")
        org_b = OperationalOrganization(name="Organization B")
        user_a = ExpertUser(username="tenant-a", password_hash="x", full_name="Tenant A", role="business_expert", is_active=True)
        user_b = ExpertUser(username="tenant-b", password_hash="x", full_name="Tenant B", role="business_expert", is_active=True)
        db.session.add_all([org_a, org_b, user_a, user_b])
        db.session.flush()
        db.session.add_all([
            OperationalMembership(organization_id=org_a.id, user_id=user_a.id, permissions=[]),
            OperationalMembership(organization_id=org_b.id, user_id=user_b.id, permissions=[]),
        ])
        customer_a = Customer(ownership_scope="TENANT", operational_organization_id=org_a.id, first_name="A", last_name="Customer")
        customer_b = Customer(ownership_scope="TENANT", operational_organization_id=org_b.id, first_name="B", last_name="Customer")
        intake = ShipmentRequest(ownership_scope="INTAKE", contact_phone="09000000000")
        db.session.add_all([customer_a, customer_b, intake])
        db.session.flush()
        opportunity_b = Opportunity(operational_organization_id=org_b.id, customer_id=customer_b.id, title="B opportunity", stage="lead")
        db.session.add(opportunity_b)
        db.session.commit()
        yield {
            "app": app,
            "org_a": org_a.id,
            "org_b": org_b.id,
            "user_a": user_a.id,
            "user_b": user_b.id,
            "token_a": create_session_tokens(user_a.id)["access_token"],
            "token_b": create_session_tokens(user_b.id)["access_token"],
            "customer_a": customer_a.id,
            "customer_b": customer_b.id,
            "opportunity_b": opportunity_b.id,
            "intake": intake.id,
        }
        db.session.remove()
        db.drop_all()


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_crm_get_and_list_do_not_leak_cross_tenant_or_quarantined_rows(ownership_app):
    client = ownership_app["app"].test_client()
    response = client.get("/api/crm/customers", headers=_headers(ownership_app["token_a"]))
    assert response.status_code == 200
    assert [row["id"] for row in response.get_json()["customers"]] == [ownership_app["customer_a"]]
    assert client.get(
        f"/api/crm/customers/{ownership_app['customer_b']}",
        headers=_headers(ownership_app["token_a"]),
    ).status_code == 404


def test_activity_rejects_mixed_tenant_parents_even_when_actor_is_valid(ownership_app):
    with ownership_app["app"].app_context():
        db.session.add(Activity(
            ownership_scope="TENANT",
            operational_organization_id=ownership_app["org_a"],
            customer_id=ownership_app["customer_a"],
            opportunity_id=ownership_app["opportunity_b"],
            expert_user_id=ownership_app["user_a"],
            activity_type="call",
            subject="cross tenant",
        ))
        with pytest.raises(ValueError, match="parents must belong"):
            db.session.commit()
        db.session.rollback()


def test_intake_acceptance_is_authorized_audited_idempotent_and_cannot_retenant(ownership_app):
    client = ownership_app["app"].test_client()
    path = f"/api/expert/requests/{ownership_app['intake']}/accept-intake"
    assert client.post(path).status_code == 401
    first = client.post(path, headers=_headers(ownership_app["token_a"]))
    assert first.status_code == 200
    assert first.get_json()["operational_organization_id"] == ownership_app["org_a"]
    assert client.post(path, headers=_headers(ownership_app["token_a"])).status_code == 200
    assert client.post(path, headers=_headers(ownership_app["token_b"])).status_code == 409
    with ownership_app["app"].app_context():
        assert DocumentAuditEvent.query.filter_by(
            shipment_request_id=ownership_app["intake"], event_type="shipment_intake_accepted"
        ).count() == 1
