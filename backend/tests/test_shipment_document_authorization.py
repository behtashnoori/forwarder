from __future__ import annotations

import io
from uuid import uuid4

import pytest

from backend import create_app
from backend.auth import auth_manager
from backend.extensions import db
from backend.models import CaseDocumentFile, Customer, ExpertUser
from backend.operational_models import OperationalMembership, OperationalOrganization, OperationalShipment


PDF = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF"


@pytest.fixture()
def shipment_documents_app(tmp_path):
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "DOCUMENT_STORAGE_ROOT": str(tmp_path / "private"),
    })
    with app.app_context():
        owner = ExpertUser(username="shipment-doc-owner", password_hash="x", full_name="Owner", role="expert", authority="EXPERT", is_active=True)
        peer = ExpertUser(username="shipment-doc-peer", password_hash="x", full_name="Peer", role="expert", authority="EXPERT", is_active=True)
        admin = ExpertUser(username="shipment-doc-admin", password_hash="x", full_name="Admin", role="admin", authority="ORGANIZATION_ADMIN", is_active=True)
        platform = ExpertUser(username="shipment-doc-platform", password_hash="x", full_name="Platform", role="admin", authority="PLATFORM_ADMIN", is_active=True)
        foreign = ExpertUser(username="shipment-doc-foreign", password_hash="x", full_name="Foreign", role="expert", authority="EXPERT", is_active=True)
        organization = OperationalOrganization(name="Shipment Documents")
        foreign_organization = OperationalOrganization(name="Foreign Shipment Documents")
        db.session.add_all([owner, peer, admin, platform, foreign, organization, foreign_organization])
        db.session.flush()
        db.session.add_all([
            OperationalMembership(organization_id=organization.id, user_id=owner.id, permissions=[]),
            OperationalMembership(organization_id=organization.id, user_id=peer.id, permissions=[]),
            OperationalMembership(organization_id=organization.id, user_id=admin.id, permissions=["operational_shipment.read", "operational_shipment.create"]),
            OperationalMembership(organization_id=organization.id, user_id=platform.id, permissions=["operational_shipment.read", "operational_shipment.create"]),
            OperationalMembership(organization_id=foreign_organization.id, user_id=foreign.id, permissions=["operational_shipment.read", "operational_shipment.create"]),
        ])
        customer = Customer(
            company_name="Shipment customer", ownership_scope="TENANT",
            operational_organization_id=organization.id,
        )
        db.session.add(customer)
        db.session.flush()
        shipment = OperationalShipment(
            public_id=str(uuid4()), organization_id=organization.id,
            source_type="direct", customer_id=customer.id, lifecycle_status="planned",
            created_by_user_id=owner.id, primary_responsible_expert_id=owner.id,
        )
        db.session.add(shipment)
        db.session.commit()
        state = {
            "shipment": shipment.public_id,
            "shipment_id": shipment.id,
            "owner_id": owner.id,
            "root": tmp_path / "private",
            **{
                name: auth_manager.generate_tokens(user.id)["access_token"]
                for name, user in {
                    "owner": owner, "peer": peer, "admin": admin,
                    "platform": platform, "foreign": foreign,
                }.items()
            },
        }
    return app, state


def _headers(token: str):
    return {"Authorization": f"Bearer {token}"}


def _state(app, root):
    with app.app_context():
        rows = [(row.id, row.status, row.storage_key) for row in CaseDocumentFile.query.order_by(CaseDocumentFile.id)]
    files = sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file())
    return rows, files


def test_shipment_owner_can_append_while_admin_read_is_preserved(shipment_documents_app):
    app, state = shipment_documents_app
    client = app.test_client()
    path = f"/api/internal/operational-shipments/{state['shipment']}/documents"
    uploaded = client.post(path, headers={
        **_headers(state["owner"]), "Idempotency-Key": "shipment-doc-owner-1",
    }, data={"title": "بارنامه", "file": (io.BytesIO(PDF), "بارنامه.pdf")})
    assert uploaded.status_code == 201
    assert uploaded.get_json()["data"]["filename"] == "بارنامه.pdf"

    owner_read = client.get(path, headers=_headers(state["owner"])).get_json()
    admin_read = client.get(path, headers=_headers(state["admin"])).get_json()
    assert owner_read["can_manage_documents"] is True
    assert admin_read["can_manage_documents"] is False
    assert admin_read["data"][0]["public_id"] == uploaded.get_json()["data"]["public_id"]


@pytest.mark.parametrize("actor", ["admin", "platform", "peer", "foreign"])
def test_shipment_non_owner_mutation_is_denied_without_side_effect(shipment_documents_app, actor):
    app, state = shipment_documents_app
    client = app.test_client()
    path = f"/api/internal/operational-shipments/{state['shipment']}/documents"
    before = _state(app, state["root"])
    response = client.post(path, headers={
        **_headers(state[actor]), "Idempotency-Key": f"forbidden-{actor}",
    }, data={"title": "Forbidden", "file": (io.BytesIO(PDF), "forbidden.pdf")})
    assert response.status_code == 404
    assert _state(app, state["root"]) == before


def test_new_shipment_owner_cannot_be_cleared(shipment_documents_app):
    app, state = shipment_documents_app
    with app.app_context():
        db.session.get(OperationalShipment, state["shipment_id"]).primary_responsible_expert_id = None
        with pytest.raises(ValueError, match="responsible Expert is immutable"):
            db.session.commit()
        db.session.rollback()
        assert db.session.get(
            OperationalShipment, state["shipment_id"]
        ).primary_responsible_expert_id == state["owner_id"]
