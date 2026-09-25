"""P3-06 exact-version, explicit-audience, and denial contract."""
from __future__ import annotations

import io
from uuid import uuid4

from backend.extensions import db
from backend.models import CaseDocumentFile, CustomerGamification
from backend.document_context_models import OperationalDocumentContextEvent
from backend.operational_models import OperationalShipment
from backend.services.customer_portal_auth import SESSION_CUSTOMER_ID, SESSION_GENERATION
from backend.tests.test_shipment_document_authorization import (
    PDF, _headers, shipment_documents_app,
)


def _portal(app, state):
    with app.app_context():
        a = CustomerGamification(
            email=f"a-{uuid4()}@example.test", phone="09120000001",
            operational_organization_id=db.session.get(OperationalShipment, state["shipment_id"]).organization_id,
        )
        b = CustomerGamification(
            email=f"b-{uuid4()}@example.test", phone="09120000002",
            operational_organization_id=a.operational_organization_id,
        )
        db.session.add_all([a, b])
        db.session.commit()
        return (a.id, a.public_id), (b.id, b.public_id)


def _as_customer(client, customer_id):
    with client.session_transaction() as session:
        session[SESSION_CUSTOMER_ID] = customer_id
        session[SESSION_GENERATION] = 0


def test_explicit_sharing_is_version_bound_and_revocable(shipment_documents_app):
    app, state = shipment_documents_app
    a, b = _portal(app, state)
    client = app.test_client()
    parent = f"/api/internal/operational-shipments/{state['shipment']}/documents"
    created = client.post(parent, headers={
        **_headers(state["owner"]), "Idempotency-Key": f"p306-internal-{uuid4()}",
    }, data={"title": "بارنامه", "file": (io.BytesIO(PDF), "private.pdf")})
    assert created.status_code == 201
    v1 = created.get_json()["data"]
    assert v1["context"]["type"] == "SHIPMENT"
    assert v1["context"]["visibility"] == "INTERNAL"

    _as_customer(client, a[0])
    assert client.get("/api/customer/documents").get_json()["data"] == []
    assert client.get(f"/api/customer/documents/{v1['public_id']}/download").status_code == 404

    changed = client.patch(f"{parent}/{v1['public_id']}/context", headers=_headers(state["owner"]),
        json={"expected_version": 1, "visibility": "EXPLICIT_SHARED", "audience_public_ids": [a[1]]})
    assert changed.status_code == 200
    assert changed.get_json()["data"]["visibility"] == "EXPLICIT_SHARED"
    assert client.get(f"{parent}/{v1['public_id']}/context-history",
        headers=_headers(state["owner"])).get_json()["data"][-1]["action"] == "VISIBILITY_CHANGED"
    _as_customer(client, a[0])
    visible = client.get("/api/customer/documents").get_json()["data"]
    assert [item["public_id"] for item in visible] == [v1["public_id"]]
    assert visible[0]["filename"] == "document-v1.pdf"
    assert client.get(f"/api/customer/documents/{v1['public_id']}/download").data == PDF

    _as_customer(client, b[0])
    assert client.get("/api/customer/documents").get_json()["data"] == []
    assert client.get(f"/api/customer/documents/{v1['public_id']}/download").status_code == 404

    replaced = client.post(parent, headers={
        **_headers(state["owner"]), "Idempotency-Key": f"p306-replace-{uuid4()}",
    }, data={"title": "بارنامه", "file": (io.BytesIO(PDF), "replacement.pdf"),
             "replaces_document_public_id": v1["public_id"]})
    assert replaced.status_code == 201
    v2 = replaced.get_json()["data"]
    assert v2["version"] == 2
    assert v2["context"]["visibility"] == "INTERNAL"
    _as_customer(client, a[0])
    assert client.get("/api/customer/documents").get_json()["data"] == []
    assert client.get(f"/api/customer/documents/{v1['public_id']}/download").status_code == 404
    assert client.get(f"/api/customer/documents/{v2['public_id']}/download").status_code == 404

    with app.app_context():
        rows = CaseDocumentFile.query.order_by(CaseDocumentFile.id).all()
        assert [row.status for row in rows] == ["superseded", "active"]
        assert OperationalDocumentContextEvent.query.count() == 3


def test_context_change_requires_owner_current_version_and_real_target(shipment_documents_app):
    app, state = shipment_documents_app
    client = app.test_client()
    parent = f"/api/internal/operational-shipments/{state['shipment']}/documents"
    created = client.post(parent, headers={
        **_headers(state["owner"]), "Idempotency-Key": f"p306-context-{uuid4()}",
    }, data={"title": "سند", "file": (io.BytesIO(PDF), "context.pdf")})
    assert created.status_code == 201
    doc_id = created.get_json()["data"]["public_id"]
    change = f"{parent}/{doc_id}/context"
    assert client.patch(change, headers=_headers(state["admin"]),
        json={"expected_version": 1, "visibility": "INTERNAL"}).status_code in (403, 404)
    assert client.patch(change, headers=_headers(state["owner"]),
        json={"expected_version": 1, "context_type": "CARGO",
              "context_target_public_id": str(uuid4())}).status_code == 404
    assert client.patch(change, headers=_headers(state["owner"]),
        json={"expected_version": 0, "visibility": "INTERNAL"}).status_code == 409
    assert client.get(f"{parent}/{doc_id}/context-history",
        headers=_headers(state["owner"])).get_json()["data"][0]["action"] == "ATTACHED"


def test_customer_list_count_cache_revocation_and_admin_boundaries(shipment_documents_app):
    app, state = shipment_documents_app
    a, b = _portal(app, state)
    client = app.test_client()
    parent = f"/api/internal/operational-shipments/{state['shipment']}/documents"
    created = client.post(parent, headers={
        **_headers(state["owner"]), "Idempotency-Key": f"p306-matrix-{uuid4()}",
    }, data={"title": "محدود", "file": (io.BytesIO(PDF), "shared.pdf"),
             "visibility": "EXPLICIT_SHARED", "audience_public_ids": a[1]})
    assert created.status_code == 201
    doc_id = created.get_json()["data"]["public_id"]
    download = f"/api/customer/documents/{doc_id}/download"

    _as_customer(client, a[0])
    assert len(client.get("/api/customer/documents?page=1").get_json()["data"]) == 1
    assert client.get(download).status_code == 200
    _as_customer(client, b[0])
    assert client.get("/api/customer/documents?page=1").get_json()["data"] == []
    assert client.get("/api/customer/documents?page=2").get_json()["data"] == []
    assert client.get(download).status_code == 404
    assert client.get("/api/customer/documents/guessed-version/download").status_code == 404

    assert client.get(f"{parent}/{doc_id}/download", headers=_headers(state["admin"])).status_code == 200
    assert client.get(f"{parent}/{doc_id}/download", headers=_headers(state["platform"])).status_code == 404
    assert client.patch(f"{parent}/{doc_id}/context", headers=_headers(state["admin"]),
        json={"expected_version": 1, "visibility": "INTERNAL"}).status_code in (403, 404)

    revoked = client.patch(f"{parent}/{doc_id}/context", headers=_headers(state["owner"]),
        json={"expected_version": 1, "visibility": "INTERNAL"})
    assert revoked.status_code == 200
    _as_customer(client, a[0])
    assert client.get("/api/customer/documents").get_json()["data"] == []
    assert client.get(download).status_code == 404
    with app.app_context():
        account = db.session.get(CustomerGamification, a[0])
        account.account_status = "DISABLED"
        db.session.commit()
    assert client.get("/api/customer/documents").status_code == 401
