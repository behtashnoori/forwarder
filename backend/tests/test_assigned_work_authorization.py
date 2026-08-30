from backend.extensions import db
import pytest
from sqlalchemy import select, update

from backend import create_app
from backend.models import Customer, ExpertQuote, ExpertUser, ShipmentRequest
from backend.operational_models import OperationalMembership, OperationalOrganization, OperationalShipment
from backend.services.assigned_work_authorization import (
    assigned_shipment_scope,
    authorize_work_action,
)


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


def test_reassignment_reloads_persisted_root_for_stale_actor_and_child_ids(assigned_work_app):
    """A committed reassignment revokes a stale actor before its next operation."""
    with assigned_work_app.app_context():
        org = OperationalOrganization(name="one", is_active=True); other = OperationalOrganization(name="two", is_active=True)
        db.session.add_all([org, other]); db.session.flush()
        a = _user("reassign-a"); b = _user("reassign-b"); outsider = _user("reassign-outsider")
        _member(a, org, permissions=("operational_shipment.read",))
        _member(b, org, permissions=("operational_shipment.read",))
        _member(outsider, other, permissions=("operational_shipment.read",))
        request = ShipmentRequest(operational_organization_id=org.id, ownership_scope="TENANT", assigned_to=a.id, contact_phone="09110000002")
        db.session.add(request); db.session.flush()
        quote = ExpertQuote(shipment_request_id=request.id, amount=1, created_by_expert_id=a.id, operational_organization_id=org.id)
        db.session.add(quote); db.session.flush()
        child = OperationalShipment(organization_id=org.id, source_type="accepted_quote", shipment_request_id=request.id, accepted_quote_id=quote.id, lifecycle_status="planned", created_by_user_id=a.id)
        db.session.add(child); db.session.commit()

        # Keep these exact objects/IDs as a browser or client would after its
        # initial allow.  They must not carry the old decision forward.
        stale_request, stale_child = request, child
        assert authorize_work_action({"id": a.id}, stale_request, "request.read").allowed
        assert authorize_work_action({"id": a.id}, stale_child, "shipment.read").allowed

        db.session.execute(update(ShipmentRequest).where(ShipmentRequest.id == request.id).values(assigned_to=b.id))
        db.session.commit()

        assert not authorize_work_action({"id": a.id}, stale_request, "request.read").allowed
        assert not authorize_work_action({"id": a.id}, stale_child, "shipment.read").allowed
        assert authorize_work_action({"id": b.id}, stale_request, "request.read").allowed
        assert authorize_work_action({"id": b.id}, stale_child, "shipment.read").allowed
        assert not authorize_work_action({"id": outsider.id}, stale_child, "shipment.read").allowed
        assert db.session.scalars(select(OperationalShipment).where(assigned_shipment_scope({"id": a.id}))).all() == []
        assert [row.id for row in db.session.scalars(select(OperationalShipment).where(assigned_shipment_scope({"id": b.id}))).all()] == [child.id]


def test_capability_history_and_forged_assignee_never_replace_current_tenant_root(assigned_work_app):
    with assigned_work_app.app_context():
        org = OperationalOrganization(name="one", is_active=True); other = OperationalOrganization(name="two", is_active=True)
        db.session.add_all([org, other]); db.session.flush()
        a = _user("history-a"); b = _user("current-b"); foreign = _user("foreign-b")
        _member(a, org, permissions=("request.read", "operational_shipment.read"))
        _member(b, org, permissions=("request.read", "operational_shipment.read"))
        _member(foreign, other, permissions=("request.read", "operational_shipment.read"))
        request = ShipmentRequest(operational_organization_id=org.id, ownership_scope="TENANT", assigned_to=b.id, contact_phone="09110000003")
        db.session.add(request); db.session.commit()

        # A's capability and prior knowledge of this root are insufficient.
        assert not authorize_work_action({"id": a.id}, request, "request.read").allowed
        assert authorize_work_action({"id": b.id}, request, "request.read").allowed

        # A forged cross-tenant assignee produces an unusable root: neither
        # tenant can turn the malformed persisted relationship into an allow.
        request.assigned_to = foreign.id; db.session.commit()
        assert not authorize_work_action({"id": a.id}, request, "request.read").allowed
        assert not authorize_work_action({"id": b.id}, request, "request.read").allowed
        assert not authorize_work_action({"id": foreign.id}, request, "request.read").allowed
