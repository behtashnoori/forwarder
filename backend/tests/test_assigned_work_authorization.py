from backend.extensions import db
import pytest

from backend import create_app
from backend.models import Customer, ExpertUser, ShipmentRequest
from backend.operational_models import OperationalMembership, OperationalOrganization, OperationalShipment
from backend.services.assigned_work_authorization import authorize_work_action


def _user(username, authority="EXPERT", role="expert"):
    row = ExpertUser(username=username, password_hash="x", full_name=username, authority=authority, role=role, is_active=True)
    db.session.add(row); db.session.flush(); return row


def _member(user, org, permissions=()):
    db.session.add(OperationalMembership(user_id=user.id, organization_id=org.id, is_active=True, permissions=list(permissions)))


@pytest.fixture()
def assigned_work_app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "SECRET_KEY": "assigned-work"}, skip_startup=True)
    with app.app_context():
        db.create_all()
    yield app


def test_request_assignment_is_current_and_tenant_fenced(assigned_work_app):
    with assigned_work_app.app_context():
        org = OperationalOrganization(name="one", is_active=True); other = OperationalOrganization(name="two", is_active=True); db.session.add_all([org, other]); db.session.flush()
        a = _user("assigned"); b = _user("other"); _member(a, org); _member(b, org); db.session.flush()
        request = ShipmentRequest(operational_organization_id=org.id, ownership_scope="TENANT", assigned_to=a.id, contact_phone="09110000001"); db.session.add(request); db.session.commit()
        assert authorize_work_action({"id": a.id}, request, "request.read").allowed
        assert not authorize_work_action({"id": b.id}, request, "request.read").allowed
        request.assigned_to = b.id; db.session.commit()
        assert not authorize_work_action({"id": a.id}, request, "request.read").allowed
        assert authorize_work_action({"id": b.id}, request, "request.read").allowed


def test_direct_shipment_requires_current_responsibility(assigned_work_app):
    with assigned_work_app.app_context():
        db.create_all(); org = OperationalOrganization(name="one", is_active=True); db.session.add(org); db.session.flush()
        a = _user("direct-a"); b = _user("direct-b"); _member(a, org); _member(b, org); db.session.flush()
        customer = Customer(first_name="Direct", last_name="Customer", phone="09110000000", status="active"); db.session.add(customer); db.session.flush()
        shipment = OperationalShipment(organization_id=org.id, source_type="direct", customer_id=customer.id, lifecycle_status="planned", created_by_user_id=a.id, primary_responsible_expert_id=a.id); db.session.add(shipment); db.session.commit()
        assert authorize_work_action({"id": a.id}, shipment, "shipment.read").allowed
        assert not authorize_work_action({"id": b.id}, shipment, "shipment.read").allowed
        shipment.primary_responsible_expert_id = b.id; db.session.commit()
        assert not authorize_work_action({"id": a.id}, shipment, "shipment.read").allowed
        assert authorize_work_action({"id": b.id}, shipment, "shipment.read").allowed
