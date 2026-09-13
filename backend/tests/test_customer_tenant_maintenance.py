"""Tenant customer maintenance and direct-shipment boundary contracts."""
from datetime import datetime, timedelta, timezone

import pytest

from backend import create_app
from backend.extensions import db
from backend.models import Customer, ExpertUser, Province
from backend.operational_models import OperationalMembership, OperationalOrganization, OperationalShipment
from backend.services import operational_service
from backend.services.auth_session_service import create_session_tokens


@pytest.fixture()
def customer_app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "SECRET_KEY": "tenant-customer"}, skip_startup=True)
    with app.app_context():
        db.create_all()
        org_a, org_b = OperationalOrganization(name="Tenant A"), OperationalOrganization(name="Tenant B")
        manager_a = ExpertUser(username="customer-manager-a", password_hash="x", full_name="Manager A", role="expert", authority="ORGANIZATION_ADMIN", is_active=True)
        manager_b = ExpertUser(username="customer-manager-b", password_hash="x", full_name="Manager B", role="expert", authority="ORGANIZATION_ADMIN", is_active=True)
        platform = ExpertUser(username="customer-platform", password_hash="x", full_name="Platform", role="admin", authority="PLATFORM_ADMIN", is_active=True)
        ordinary = ExpertUser(username="customer-ordinary", password_hash="x", full_name="Ordinary", role="expert", authority="EXPERT", is_active=True)
        no_membership = ExpertUser(username="customer-no-membership", password_hash="x", full_name="No Membership", role="expert", authority="ORGANIZATION_ADMIN", is_active=True)
        multiple_memberships = ExpertUser(username="customer-multiple-memberships", password_hash="x", full_name="Multiple Memberships", role="expert", authority="ORGANIZATION_ADMIN", is_active=True)
        origin, destination = Province(name_fa="مبدأ مشتری", code="CTM-O"), Province(name_fa="مقصد مشتری", code="CTM-D")
        db.session.add_all([org_a, org_b, manager_a, manager_b, platform, ordinary, no_membership, multiple_memberships, origin, destination]); db.session.flush()
        permissions = ["operational_shipment.create_direct"]
        db.session.add_all([
            OperationalMembership(organization_id=org_a.id, user_id=manager_a.id, permissions=permissions),
            OperationalMembership(organization_id=org_b.id, user_id=manager_b.id, permissions=permissions),
            OperationalMembership(organization_id=org_a.id, user_id=ordinary.id, permissions=permissions),
            OperationalMembership(organization_id=org_a.id, user_id=platform.id, permissions=permissions),
            OperationalMembership(organization_id=org_a.id, user_id=multiple_memberships.id, permissions=[]),
            OperationalMembership(organization_id=org_b.id, user_id=multiple_memberships.id, permissions=[]),
        ])
        foreign = Customer(ownership_scope="TENANT", operational_organization_id=org_b.id, company_name="Foreign Iran Khodro", first_name="Foreign", last_name="Owner", status="active")
        db.session.add(foreign); db.session.commit()
        tokens = {name: create_session_tokens(user.id)["access_token"] for name, user in {"a": manager_a, "b": manager_b, "platform": platform, "ordinary": ordinary, "no_membership": no_membership, "multiple": multiple_memberships}.items()}
        yield {"app": app, "a": manager_a.id, "ordinary": ordinary.id, "org_a": org_a.id, "foreign": foreign.id, "origin": origin.id, "destination": destination.id, "tokens": tokens}
        db.session.remove(); db.drop_all()


def headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_tenant_customer_create_list_search_selector_and_direct_roundtrip(customer_app):
    client = customer_app["app"].test_client()
    created = client.post("/api/crm/customers", headers=headers(customer_app["tokens"]["a"]), json={"company_name": "ایران خودرو", "country": "Iran"})
    assert created.status_code == 201
    customer_id = created.get_json()["customer_id"]
    with customer_app["app"].app_context():
        legal_customer = db.session.get(Customer, customer_id)
        assert legal_customer.first_name is None and legal_customer.last_name is None
    own = client.get("/api/crm/customers?search=ایران", headers=headers(customer_app["tokens"]["a"]))
    assert own.status_code == 200 and [row["id"] for row in own.get_json()["customers"]] == [customer_id]
    foreign = client.get("/api/crm/customers?search=ایران", headers=headers(customer_app["tokens"]["b"]))
    assert foreign.status_code == 200 and customer_id not in [row["id"] for row in foreign.get_json()["customers"]]
    selector = client.get("/api/operations/selectors/customers?q=ایران خودرو", headers=headers(customer_app["tokens"]["ordinary"]))
    assert selector.status_code == 200 and selector.get_json()["items"] == [{"id": customer_id, "label": "ایران خودرو"}]
    with customer_app["app"].app_context():
        departure = datetime.now(timezone.utc) + timedelta(hours=1)
        shipment, created_flag = operational_service.create_direct({"source_type": "direct", "customer_id": customer_id, "origin": {"source_type": "province", "source_id": customer_app["origin"]}, "destination": {"source_type": "province", "source_id": customer_app["destination"]}, "transport_mode": "road", "planned_departure": departure.isoformat(), "planned_arrival": (departure + timedelta(hours=2)).isoformat()}, {"id": customer_app["ordinary"], "role": "expert"}, "tenant-customer-roundtrip")
        assert created_flag and shipment.customer_id == customer_id


def test_customer_maintenance_rejects_platform_and_ordinary_users(customer_app):
    client = customer_app["app"].test_client()
    payload = {"company_name": "Blocked", "first_name": "Blocked", "last_name": "Customer"}
    assert client.post("/api/crm/customers", headers=headers(customer_app["tokens"]["platform"]), json=payload).status_code == 403
    assert client.post("/api/crm/customers", headers=headers(customer_app["tokens"]["ordinary"]), json=payload).status_code == 403
    assert client.get("/api/crm/customers", headers=headers(customer_app["tokens"]["platform"])).status_code == 403
    assert client.get("/api/crm/customers", headers=headers(customer_app["tokens"]["ordinary"])).status_code == 403


def test_customer_maintenance_fails_closed_without_exactly_one_membership(customer_app):
    client = customer_app["app"].test_client()
    payload = {"company_name": "Blocked", "first_name": "Blocked", "last_name": "Customer"}
    assert client.post("/api/crm/customers", headers=headers(customer_app["tokens"]["no_membership"]), json=payload).status_code == 403
    assert client.post("/api/crm/customers", headers=headers(customer_app["tokens"]["multiple"]), json=payload).status_code == 403


def test_direct_shipment_foreign_customer_is_hidden_and_creates_nothing(customer_app):
    with customer_app["app"].app_context():
        departure = datetime.now(timezone.utc) + timedelta(hours=1)
        before = OperationalShipment.query.count()
        with pytest.raises(operational_service.OperationalError) as denied:
            operational_service.create_direct({"source_type": "direct", "customer_id": customer_app["foreign"], "origin": {"source_type": "province", "source_id": customer_app["origin"]}, "destination": {"source_type": "province", "source_id": customer_app["destination"]}, "transport_mode": "road", "planned_departure": departure.isoformat(), "planned_arrival": (departure + timedelta(hours=2)).isoformat()}, {"id": customer_app["a"], "role": "admin"}, "tenant-customer-foreign")
        assert denied.value.code == "RESOURCE_NOT_FOUND"
        assert OperationalShipment.query.count() == before
