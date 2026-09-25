"""DN10 authorization, no inference, multiplicity, replay and exact-version proof."""
import io
from uuid import uuid4

import pytest

from backend.extensions import db
from backend.cargo_models import ShipmentCargoItem
from backend.customer_entitlement_models import CustomerEntitlement
from backend.models import CargoType, Customer, CustomerGamification, ShipmentRequest, UnitOfMeasure
from backend.operational_models import OperationalShipment, OperationalOrganization
from backend.tests.test_phase3_document_context import _as_customer
from backend.tests.test_shipment_document_authorization import PDF, _headers, shipment_documents_app

BASE = "/api/admin/customer-entitlements"


@pytest.fixture()
def entitlement_app(shipment_documents_app):
    app, ctx = shipment_documents_app
    with app.app_context():
        shipment = db.session.get(OperationalShipment, ctx["shipment_id"])
        a = db.session.get(Customer, shipment.customer_id)
        a.email, a.phone, a.first_name = "same@example.test", "09120000001", "Same"
        b = Customer(company_name="Other private customer", ownership_scope="TENANT",
                     operational_organization_id=shipment.organization_id)
        foreign_org = OperationalOrganization.query.filter(OperationalOrganization.id != shipment.organization_id).first()
        foreign = Customer(company_name="Foreign", ownership_scope="TENANT", operational_organization_id=foreign_org.id)
        accounts = [CustomerGamification(email=email, phone="09120000001", first_name="Same",
                    operational_organization_id=org) for email, org in (
                        ("same@example.test", shipment.organization_id), ("b@example.test", shipment.organization_id),
                        ("foreign@example.test", foreign_org.id))]
        cargo_type = CargoType(immutable_code="DN10_CARGO", fa_name="کالا", en_name="Cargo", is_active=True)
        uom = UnitOfMeasure(immutable_code="DN10_UNIT", fa_name="عدد", en_name="Item", symbol="ea", measurement_dimension="COUNT", is_active=True)
        db.session.add_all([b, foreign, cargo_type, uom, *accounts])
        db.session.flush()
        request = ShipmentRequest(contact_phone=a.phone, customer_id=a.id, gamification_customer_id=accounts[0].id,
                                  operational_organization_id=shipment.organization_id, ownership_scope="TENANT")
        db.session.add(request)
        db.session.flush()
        cargo_ids = []
        for index, owner in enumerate((a, b), 1):
            cargo = ShipmentCargoItem(operational_shipment_id=shipment.id, cargo_owner_customer_id=owner.id,
                source_shipment_request_id=request.id if index == 1 else None,
                line_number=index, cargo_type_id=cargo_type.id, quantity=100, planned_quantity=100, uom_id=uom.id,
                display_name_snapshot=f"Private Cargo {index}", cargo_type_code_snapshot="DN10_CARGO",
                cargo_type_fa_snapshot="کالا", cargo_type_en_snapshot="Cargo", uom_code_snapshot="DN10_UNIT",
                uom_symbol_snapshot="ea", created_by=ctx["owner_id"], updated_by=ctx["owner_id"])
            db.session.add(cargo)
            db.session.flush()
            cargo_ids.append(cargo.public_id)
        db.session.commit()
        ctx.update(accounts=[(a.id, a.public_id) for a in accounts], customers=[a.id, b.id, foreign.id],
                   cargo=cargo_ids, organization_id=shipment.organization_id)
    return app, ctx


def _grant(client, ctx, account=0, customer=0, key=None, actor="admin"):
    return client.post(BASE, headers={**_headers(ctx[actor]), "Idempotency-Key": key or str(uuid4())},
                       json={"portal_account_public_id": ctx["accounts"][account][1], "customer_id": ctx["customers"][customer]})


def _upload(client, ctx, index, visibility="CARGO_OWNER", replaces=None):
    data = {"title": "Private cargo evidence", "file": (io.BytesIO(PDF), f"private-{index}.pdf"),
            "context_type": "CARGO", "context_target_public_id": ctx["cargo"][index], "visibility": visibility}
    if replaces:
        data["replaces_document_public_id"] = replaces
    result = client.post(f"/api/internal/operational-shipments/{ctx['shipment']}/documents",
                         headers={**_headers(ctx["owner"]), "Idempotency-Key": str(uuid4())}, data=data)
    assert result.status_code == 201, result.get_json()
    return result.get_json()["data"]["public_id"]


def test_positive_cargo_document_current_grant_revoke_and_exact_version(entitlement_app):
    app, ctx = entitlement_app
    client = app.test_client()
    a_doc, b_doc = _upload(client, ctx, 0), _upload(client, ctx, 1)
    internal = _upload(client, ctx, 0, "INTERNAL")
    _as_customer(client, ctx["accounts"][0][0])
    # Same email/name/phone and a Request referencing both identities confer nothing.
    assert client.get("/api/customer/documents").get_json()["data"] == []
    assert client.get(f"/api/customer/documents/{a_doc}/download").status_code == 404
    granted = _grant(client, ctx, key="stable-grant-command")
    assert granted.status_code == 201
    assert granted.get_json()["item"]["granted_at"].endswith("Z")
    grant_id = granted.get_json()["item"]["public_id"]
    _as_customer(client, ctx["accounts"][0][0])
    visible = client.get("/api/customer/documents")
    assert visible.headers["Cache-Control"] == "no-store"
    assert [row["public_id"] for row in visible.get_json()["data"]] == [a_doc]
    assert client.get(f"/api/customer/documents/{a_doc}/download").data == PDF
    for doc in (b_doc, internal, str(uuid4())):
        assert client.get(f"/api/customer/documents/{doc}/download").status_code == 404
    _as_customer(client, ctx["accounts"][1][0])
    assert client.get("/api/customer/documents").get_json()["data"] == []
    assert client.get(f"/api/customer/documents/{a_doc}/download").status_code == 404
    revoked = client.post(f"{BASE}/{grant_id}/revoke", headers=_headers(ctx["admin"]))
    assert revoked.status_code == 200
    assert revoked.get_json()["item"]["revoked_by"] is not None
    assert revoked.get_json()["item"]["revoked_at"].endswith("Z")
    _as_customer(client, ctx["accounts"][0][0])
    assert client.get("/api/customer/documents").get_json()["data"] == []
    assert client.get(f"/api/customer/documents/{a_doc}/download").status_code == 404
    replay = _grant(client, ctx, key="stable-grant-command")
    assert replay.status_code == 200 and replay.get_json()["item"]["status"] == "REVOKED"
    assert _grant(client, ctx).status_code == 201
    replacement = _upload(client, ctx, 0, "INTERNAL", replaces=a_doc)
    _as_customer(client, ctx["accounts"][0][0])
    assert client.get(f"/api/customer/documents/{a_doc}/download").status_code == 404
    assert client.get(f"/api/customer/documents/{replacement}/download").status_code == 404
    with app.app_context():
        rows = CustomerEntitlement.query.order_by(CustomerEntitlement.id).all()
        assert len(rows) == 2 and rows[0].revoked_at and rows[1].revoked_at is None


def test_many_to_many_independent_revocation_and_disabled_targets(entitlement_app):
    app, ctx = entitlement_app
    client = app.test_client()
    a_doc, b_doc = _upload(client, ctx, 0), _upload(client, ctx, 1)
    a_grant = _grant(client, ctx).get_json()["item"]["public_id"]
    assert _grant(client, ctx, customer=1).status_code == 201
    assert _grant(client, ctx, account=1).status_code == 201
    _as_customer(client, ctx["accounts"][0][0])
    assert {r["public_id"] for r in client.get("/api/customer/documents").get_json()["data"]} == {a_doc, b_doc}
    assert client.post(f"{BASE}/{a_grant}/revoke", headers=_headers(ctx["admin"])).status_code == 200
    assert [r["public_id"] for r in client.get("/api/customer/documents").get_json()["data"]] == [b_doc]
    _as_customer(client, ctx["accounts"][1][0])
    assert [r["public_id"] for r in client.get("/api/customer/documents").get_json()["data"]] == [a_doc]
    with app.app_context():
        db.session.get(Customer, ctx["customers"][0]).status = "inactive"
        db.session.commit()
    assert client.get("/api/customer/documents").get_json()["data"] == []
    assert _grant(client, ctx).status_code == 404
    with app.app_context():
        db.session.get(CustomerGamification, ctx["accounts"][0][0]).account_status = "DISABLED"
        db.session.commit()
    assert _grant(client, ctx, customer=1).status_code == 404


@pytest.mark.parametrize("actor", ["owner", "peer", "foreign", "platform"])
def test_only_same_organization_admin_may_manage(entitlement_app, actor):
    app, ctx = entitlement_app
    client = app.test_client()
    grant_id = _grant(client, ctx).get_json()["item"]["public_id"]
    assert client.get(BASE, headers=_headers(ctx[actor])).status_code == 403
    assert _grant(client, ctx, actor=actor).status_code == 403
    assert client.post(f"{BASE}/{grant_id}/revoke", headers=_headers(ctx[actor])).status_code == 403
    with app.app_context():
        assert CustomerEntitlement.query.one().revoked_at is None


def test_cross_tenant_self_grant_invalid_and_replay_denials(entitlement_app):
    app, ctx = entitlement_app
    client = app.test_client()
    assert _grant(client, ctx, account=2).status_code == 404
    assert _grant(client, ctx, customer=2).status_code == 404
    _as_customer(client, ctx["accounts"][0][0])
    assert client.post(BASE, json={"customer_id": ctx["customers"][0]}).status_code == 401
    assert client.get(BASE).status_code == 401
    assert client.post(BASE, json=[], headers=_headers(ctx["admin"])).status_code == 422
    assert _grant(client, ctx, key="repeat").status_code == 201
    assert _grant(client, ctx, key="repeat", customer=1).status_code == 409
    assert _grant(client, ctx).status_code == 409
    configuration = client.get(BASE, headers=_headers(ctx["admin"])).get_json()
    assert len(configuration["accounts"]) == 2
    assert {c["id"] for c in configuration["customers"]} == set(ctx["customers"][:2])
    assert client.post(f"{BASE}/{uuid4()}/revoke", headers=_headers(ctx["admin"])).status_code == 404


def test_filtering_precedes_pagination_and_customer_commands_are_absent(entitlement_app):
    _app, ctx = entitlement_app
    client = _app.test_client()
    own = _upload(client, ctx, 0)
    for _ in range(21):
        _upload(client, ctx, 1)
    assert _grant(client, ctx).status_code == 201
    _as_customer(client, ctx["accounts"][0][0])
    assert [r["public_id"] for r in client.get("/api/customer/documents?page=1").get_json()["data"]] == [own]
    assert client.get("/api/customer/documents?page=2").get_json()["data"] == []
    path = f"/api/internal/operational-shipments/{ctx['shipment']}/documents"
    assert client.post(path).status_code == 401
    assert client.patch(f"{path}/{own}/context", json={"visibility": "EXPLICIT_SHARED"}).status_code == 401


def test_replacement_cannot_bypass_new_version_internal_policy(entitlement_app):
    app, ctx = entitlement_app
    client = app.test_client()
    own = _upload(client, ctx, 0)
    assert _grant(client, ctx).status_code == 201
    path = f"/api/internal/operational-shipments/{ctx['shipment']}/documents"
    response = client.post(path, headers={**_headers(ctx["owner"]), "Idempotency-Key": "bad-replacement"},
        data={"title": "Replacement", "file": (io.BytesIO(PDF), "new.pdf"),
              "context_type": "CARGO", "context_target_public_id": ctx["cargo"][0],
              "visibility": "CARGO_OWNER", "replaces_document_public_id": own})
    assert response.status_code == 422
    _as_customer(client, ctx["accounts"][0][0])
    assert client.get(f"/api/customer/documents/{own}/download").status_code == 200


def test_dn10_openapi_and_tenant_inventory_cover_runtime(entitlement_app):
    from pathlib import Path
    import yaml
    app, _ctx = entitlement_app
    root = Path(__file__).resolve().parents[2]
    document = yaml.safe_load((root / "docs/openapi/openapi.yaml").read_text(encoding="utf-8"))
    routes = {rule.rule.replace("<public_id>", "{public_id}"): rule.methods - {"HEAD", "OPTIONS"}
              for rule in app.url_map.iter_rules() if rule.endpoint.startswith("customer_entitlements.")}
    for path, methods in routes.items():
        assert all(method.lower() in document["paths"][path] for method in methods)
    inventory = yaml.safe_load((root / "docs/architecture/tenant-ownership-inventory.yaml").read_text(encoding="utf-8"))
    assert inventory["entities"]["CustomerEntitlement"]["tenant_key"] == "organization_id"
