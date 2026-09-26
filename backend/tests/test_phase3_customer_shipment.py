"""Customer authorization precedes every list, count, page and fact projection."""
import io
import json
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select
from backend.extensions import db
from backend.cargo_models import ShipmentCargoItem as Cargo
from backend.models import Customer, CustomerGamification, CaseDocumentFile
from backend.operational_models import OperationalOrganization, OperationalShipment, RouteCargoDestination, RouteLeg, RouteStageExecution
from backend.services import customer_entitlement_service as grants, customer_shipment_service as service
from backend.services import reported_fact_service as reports, delivery_service as deliveries
from backend.tests.test_operational_vertical_slice import _auth, _user, operational_app
from backend.tests.test_phase3_cargo_delivery import setup, payload as delivery_payload, record as delivery_record
from backend.tests.test_phase3_cargo_allocation import _set
from backend.tests.test_phase3_document_context import _as_customer
from backend.tests.test_shipment_document_authorization import PDF


def new_cargo(template, shipment, customer, name):
    row = Cargo(operational_shipment_id=shipment.id, line_number=1,
        cargo_owner_customer_id=customer, quantity=25, planned_quantity=25, actual_quantity=25,
        display_name_snapshot=name, **{key: getattr(template, key) for key in (
            "cargo_type_id", "uom_id", "cargo_type_code_snapshot", "cargo_type_fa_snapshot", "cargo_type_en_snapshot",
            "uom_code_snapshot", "uom_symbol_snapshot", "created_by", "updated_by")})
    db.session.add(row)
    return row


def account(app, ctx, index=0):
    return db.session.get(CustomerGamification, ctx["accounts"][index])


def report(app, ctx, cargo, text, **extra):
    row, _ = reports.create(ctx["shipment"], _user(app), {
        "scope": "CARGO", "target_public_id": cargo, "kind": "LOCATION", "source": "CARRIER_REPORT",
        "occurred_at": "2026-09-21T08:00:00Z", "location": {"location_text": text},
        "customer_message": text, "internal_note": "PRIVATE-INTERNAL-NOTE", "impacted_cargo_public_ids": [cargo], **extra}, str(uuid4()))
    db.session.commit()
    return row


def document(app, ctx, target, context="CARGO", visibility="CARGO_OWNER", **extra):
    response = app.test_client().post(f"/api/internal/operational-shipments/{ctx['shipment']}/documents",
        headers={**_auth(app), "Idempotency-Key": str(uuid4())}, data={"file": (io.BytesIO(PDF), "PRIVATE-FILENAME.pdf"),
            "title": "PRIVATE-TITLE", "context_type": context, "context_target_public_id": target,
            "visibility": visibility, **extra})
    assert response.status_code == 201, response.get_json()
    return response.get_json()["data"]["public_id"]


def revoke(app, customer_account, customer_id=None):
    ids = app.config["phase1a"]
    for row in grants.configuration(ids["org"], ids["verifier"])["grants"]:
        if row["portal_account_public_id"] == customer_account.public_id and row["status"] == "ACTIVE" and (customer_id is None or row["customer_id"] == customer_id):
            grants.revoke(ids["org"], ids["verifier"], row["public_id"])
    db.session.commit()


def test_a_b_same_shipment_separate_quantity_delivery_documents_and_safe_timeline(operational_app, tmp_path):
    app = operational_app; app.config["DOCUMENT_STORAGE_ROOT"] = str(tmp_path)
    with app.app_context():
        ctx = setup(app)
        own_delivery, _ = delivery_record(app, ctx, delivery_payload(ctx, quantity="100", reason="PRIVATE-REASON"))
        delivery_record(app, ctx, delivery_payload(ctx, cargo_public_id=ctx["cargo_b"], quantity="5", destination_text="PRIVATE-B-DESTINATION"))
        report(app, ctx, ctx["cargo"], "گزارش مشتری اول")
        report(app, ctx, ctx["cargo_b"], "PRIVATE-B-REPORT")
        delivery_id = own_delivery.public_id
    doc_a = document(app, ctx, delivery_id, "DELIVERY")
    doc_b = document(app, ctx, ctx["cargo_b"])
    client = app.test_client(); _as_customer(client, ctx["accounts"][0])
    response = client.get(f"/api/customer/shipments/{ctx['shipment']}")
    assert response.status_code == 200 and "no-store" in response.headers["Cache-Control"]
    value = response.get_json()
    assert set(value) == {"authorization_revision", "public_id", "created_at", "status", "shared_transport", "cargo", "routes", "documents", "deliveries", "timeline", "reported_locations"}
    assert value["public_id"] == ctx["shipment"] and value["shared_transport"]
    assert [c["public_id"] for c in value["cargo"]] == [ctx["cargo"]]
    assert value["cargo"][0]["requested"] is None
    assert Decimal(value["cargo"][0]["delivered"]) == 100 and Decimal(value["cargo"][0]["remaining"]) == 0
    assert {x["public_id"] for x in value["documents"]["items"]} == {doc_a}
    assert value["deliveries"]["items"][0]["evidence"][0]["public_id"] == doc_a
    assert "PRIVATE" not in json.dumps(value, ensure_ascii=False)
    assert all(not {"actor_label", "internal_note", "reason", "target_public_id", "actor_user_id"}.intersection(row) for row in value["timeline"]["items"] + value["deliveries"]["items"])
    assert client.get(f"/api/customer/documents/{doc_a}/download").data == PDF
    assert client.get(f"/api/customer/documents/{doc_b}/download").status_code == 404
    _as_customer(client, ctx["accounts"][1])
    b = client.get(f"/api/customer/shipments/{ctx['shipment']}").get_json()
    assert [c["public_id"] for c in b["cargo"]] == [ctx["cargo_b"]]
    assert Decimal(b["cargo"][0]["delivered"]) == 5 and Decimal(b["cargo"][0]["remaining"]) == 20
    assert {x["public_id"] for x in b["documents"]["items"]} == {doc_b}
    assert client.get(f"/api/customer/documents/{doc_a}/download").status_code == 404
    with app.app_context(): assert OperationalShipment.query.count() == 1


def test_union_partial_revoke_and_unentitled_c_are_live(operational_app, tmp_path):
    app = operational_app; app.config["DOCUMENT_STORAGE_ROOT"] = str(tmp_path)
    with app.app_context():
        ctx = setup(app); a = account(app, ctx); ids = app.config["phase1a"]
        b = Cargo.query.filter_by(public_id=ctx["cargo_b"]).one()
        third = Customer(company_name="PRIVATE-CUSTOMER-C", ownership_scope="TENANT", operational_organization_id=ids["org"], status="active")
        c = CustomerGamification(email="unentitled@example.test", phone="09000000003", operational_organization_id=ids["org"])
        db.session.add_all([third, c]); db.session.flush()
        row = new_cargo(b, db.session.get(OperationalShipment, ctx["shipment_id"]), third.id, "PRIVATE-CARGO-C"); row.line_number = 3
        grants.grant(ids["org"], ids["verifier"], {"portal_account_public_id": a.public_id, "customer_id": b.cargo_owner_customer_id}, str(uuid4()))
        db.session.commit(); c_id = c.id
        union = service.detail(a, ctx["shipment"])
        assert {r["public_id"] for r in union["cargo"]} == {ctx["cargo"], ctx["cargo_b"]}
        assert "PRIVATE-CARGO-C" not in json.dumps(union)
        assert service.listing(a)["pagination"]["total"] == 1
    doc_a = document(app, ctx, ctx["cargo"]); doc_b = document(app, ctx, ctx["cargo_b"])
    client = app.test_client(); _as_customer(client, c_id)
    assert client.get("/api/customer/shipments").get_json()["pagination"]["total"] == 0
    assert client.get(f"/api/customer/shipments/{ctx['shipment']}").status_code == 404
    with app.app_context(): revoke(app, account(app, ctx), ids["customer"])
    _as_customer(client, ctx["accounts"][0])
    assert [r["public_id"] for r in client.get(f"/api/customer/shipments/{ctx['shipment']}").get_json()["cargo"]] == [ctx["cargo_b"]]
    assert client.get(f"/api/customer/documents/{doc_a}/download").status_code == 404
    assert client.get(f"/api/customer/documents/{doc_b}/download").data == PDF
    with app.app_context(): revoke(app, account(app, ctx))
    assert client.get("/api/customer/shipments").get_json()["items"] == []
    denied = client.get(f"/api/customer/shipments/{ctx['shipment']}")
    assert denied.status_code == 404 and denied.get_json() == client.get(f"/api/customer/shipments/{uuid4()}").get_json()
    _as_customer(client, ctx["accounts"][1])
    assert client.get(f"/api/customer/shipments/{ctx['shipment']}").status_code == 200


def test_authorization_before_search_count_sort_pagination_and_foreign_lookup(operational_app):
    app = operational_app
    with app.app_context():
        ctx = setup(app); ids = app.config["phase1a"]
        template = Cargo.query.filter_by(public_id=ctx["cargo"]).one()
        b = Cargo.query.filter_by(public_id=ctx["cargo_b"]).one()
        for i in range(50):
            owner = ids["customer"] if i % 2 else b.cargo_owner_customer_id
            row = OperationalShipment(organization_id=ids["org"], source_type="direct", customer_id=owner,
                created_by_user_id=ids["user"], primary_responsible_expert_id=ids["user"])
            db.session.add(row); db.session.flush(); new_cargo(template, row, owner, "A-ONLY" if i % 2 else "B-ONLY")
        foreign = OperationalShipment(organization_id=ids["other_org"], source_type="direct", customer_id=ids["customer"],
            created_by_user_id=ids["outsider"], primary_responsible_expert_id=ids["outsider"])
        db.session.add(foreign); db.session.flush(); new_cargo(template, foreign, ids["customer"], "FOREIGN-PRIVATE")
        db.session.commit(); foreign_id = foreign.public_id
    client = app.test_client(); _as_customer(client, ctx["accounts"][0])
    first = client.get("/api/customer/shipments").get_json(); second = client.get("/api/customer/shipments?page=2").get_json()
    assert first["pagination"]["total"] == second["pagination"]["total"] == 26
    assert len(first["items"]) == 20 and len(second["items"]) == 6
    assert not {x["public_id"] for x in first["items"]}.intersection(x["public_id"] for x in second["items"])
    assert client.get("/api/customer/shipments?q=B-ONLY").get_json()["pagination"]["total"] == 0
    assert client.get("/api/customer/shipments?q=A-ONLY").get_json()["pagination"]["total"] == 25
    assert client.get("/api/customer/shipments?q=%25").get_json()["items"] == []
    assert client.get("/api/customer/shipments?page=3").get_json()["items"] == []
    assert client.get(f"/api/customer/shipments/{foreign_id}").status_code == 404
    for bad in ("bad", "0", "100001"):
        assert client.get(f"/api/customer/shipments?page={bad}").status_code == 422


@pytest.mark.parametrize("change", ["disabled", "generation", "crm", "organization"])
def test_current_session_account_crm_and_organization_revocation(operational_app, change):
    app = operational_app
    with app.app_context(): ctx = setup(app)
    client = app.test_client(); _as_customer(client, ctx["accounts"][0])
    assert client.get(f"/api/customer/shipments/{ctx['shipment']}").status_code == 200
    with app.app_context():
        a = account(app, ctx)
        if change == "disabled": a.account_status = "DISABLED"
        elif change == "generation": a.session_generation += 1
        elif change == "crm": db.session.get(Customer, app.config["phase1a"]["customer"]).status = "inactive"
        else: db.session.get(OperationalOrganization, app.config["phase1a"]["org"]).is_active = False
        db.session.commit()
    response = client.get(f"/api/customer/shipments/{ctx['shipment']}")
    assert response.status_code == (401 if change in {"disabled", "generation"} else 404)
    assert "no-store" in response.headers["Cache-Control"]


def test_route_ancestry_unknown_quantities_and_private_snapshots(operational_app):
    app = operational_app
    with app.app_context():
        ctx = setup(app); a = account(app, ctx)
        cargo = Cargo.query.filter_by(public_id=ctx["cargo"]).one(); cargo.actual_quantity = None; cargo.planned_quantity = None
        first = db.session.get(RouteLeg, ctx["leg"])
        branch = RouteLeg(route_plan_id=ctx["plan"], sequence_number=3, parent_route_leg_id=first.id,
            origin_location_id=first.destination_location_id, destination_location_id=first.origin_location_id,
            origin_snapshot={"display_name": "PRIVATE-B-ORIGIN"}, destination_snapshot={"display_name": "PRIVATE-B-DESTINATION"}, branch_label="PRIVATE-B-BRANCH", carrier_reference="PRIVATE-CARRIER")
        db.session.add(branch); db.session.flush()
        b = Cargo.query.filter_by(public_id=ctx["cargo_b"]).one()
        db.session.add(RouteCargoDestination(route_plan_id=ctx["plan"], operational_shipment_id=ctx["shipment_id"],
            shipment_cargo_item_id=b.id, destination_route_leg_id=branch.id, created_by_user_id=app.config["phase1a"]["user"]))
        first.origin_snapshot = {"display_name": "PRIVATE-SHARED-FACILITY"}; db.session.commit()
        value = service.detail(a, ctx["shipment"])
        assert len(value["routes"]) == 1 and len(value["routes"][0]["legs"]) == 2
        assert "PRIVATE" not in json.dumps(value)
        assert value["cargo"][0]["requested"] is value["cargo"][0]["planned"] is value["cargo"][0]["known_actual"] is value["cargo"][0]["remaining"] is None
        RouteCargoDestination.query.filter_by(shipment_cargo_item_id=cargo.id).delete(); db.session.commit()
        assert service.detail(a, ctx["shipment"])["routes"][0]["legs"] == []


def test_latest_location_per_own_unit_correction_and_independent_timeline_pages(operational_app):
    app = operational_app
    with app.app_context():
        ctx = setup(app)
        for name in ("first", "second"): _set(app, ctx, ctx[name], "ACTUAL", 50, 0, name)
        db.session.commit()
        units = [RouteStageExecution.query.filter_by(public_id=ctx[name]).one().execution_unit.public_id for name in ("first", "second")]
        old = report(app, ctx, ctx["cargo"], "Old first", scope="EXECUTION_UNIT", target_public_id=units[0])
        report(app, ctx, ctx["cargo"], "Second independent", scope="EXECUTION_UNIT", target_public_id=units[1])
        corrected = report(app, ctx, ctx["cargo"], "Corrected first", scope="EXECUTION_UNIT", target_public_id=units[0],
            occurred_at="2026-09-20T07:00:00Z", corrects_public_id=old.event.public_id, reason="PRIVATE-CORRECTION")
        for i in range(22): report(app, ctx, ctx["cargo_b"], f"PRIVATE-B-{i}", occurred_at="2026-09-22T08:00:00Z")
        for i in range(21): report(app, ctx, ctx["cargo"], f"Progress {i}", kind="PROGRESS", location=None)
        value = service.detail(account(app, ctx), ctx["shipment"])
        assert len(value["timeline"]["items"]) == 20 and value["timeline"]["has_next"]
        expected = {"Corrected first", "Second independent"}
        assert {x["reported_location"] for x in value["reported_locations"]} == expected
        second = service.detail(account(app, ctx), ctx["shipment"], timeline_page=2)
        assert len(second["timeline"]["items"]) == 4 and not second["timeline"]["has_next"]
        assert {x["reported_location"] for x in second["reported_locations"]} == expected
        old_row = next(x for x in second["timeline"]["items"] if x["public_id"] == old.event.public_id)
        assert old_row["status"] == "SUPERSEDED" and "PRIVATE" not in json.dumps(second)
        assert next(x for x in second["timeline"]["items"] if x["public_id"] == corrected.event.public_id)["is_correction"]


def test_documents_and_deliveries_filter_before_pagination_and_replacement(operational_app, tmp_path):
    app = operational_app; app.config["DOCUMENT_STORAGE_ROOT"] = str(tmp_path)
    with app.app_context():
        ctx = setup(app)
        for i in range(22): delivery_record(app, ctx, delivery_payload(ctx, quantity="1", cargo_public_id=ctx["cargo_b"]))
        for i in range(21): delivery_record(app, ctx, delivery_payload(ctx, quantity="1"))
    own = document(app, ctx, ctx["cargo"])
    for i in range(21): document(app, ctx, ctx["cargo_b"])
    client = app.test_client(); _as_customer(client, ctx["accounts"][0])
    value = client.get(f"/api/customer/shipments/{ctx['shipment']}").get_json()
    assert len(value["deliveries"]["items"]) == 20 and value["deliveries"]["has_next"]
    assert [d["public_id"] for d in value["documents"]["items"]] == [own] and not value["documents"]["has_next"]
    assert len(client.get(f"/api/customer/shipments/{ctx['shipment']}?deliveries_page=2").get_json()["deliveries"]["items"]) == 1
    replaced = document(app, ctx, ctx["cargo"], visibility="INTERNAL", replaces_document_public_id=own)
    assert client.get(f"/api/customer/shipments/{ctx['shipment']}").get_json()["documents"]["items"] == []
    for identity in (own, replaced): assert client.get(f"/api/customer/documents/{identity}/download").status_code == 404


def test_latest_location_limit_follows_location_permission_not_just_safe_effect(operational_app):
    app = operational_app
    with app.app_context():
        ctx = setup(app)
        report(app, ctx, ctx["cargo"], "Own earlier location")
        unit = RouteStageExecution.query.filter_by(public_id=ctx["second"]).one().execution_unit
        report(app, ctx, ctx["cargo_b"], "PRIVATE-B-LOCATION", scope="EXECUTION_UNIT",
            target_public_id=unit.public_id, customer_message="Safe operational effect",
            impacted_cargo_public_ids=[ctx["cargo"]], occurred_at="2026-09-22T08:00:00Z")
        shipment = db.session.get(OperationalShipment, ctx["shipment_id"])
        latest = reports.customer_timeline(shipment, account(app, ctx), limit=1, latest_locations=True)
        assert [r["reported_location"] for r in latest] == ["Own earlier location"]
        history = reports.customer_timeline(shipment, account(app, ctx), limit=1)
        assert history[0]["message"] == "Safe operational effect" and history[0]["reported_location"] is None


def test_anonymous_expert_uuid_and_write_do_not_grant_customer_authority(operational_app):
    app = operational_app
    with app.app_context(): ctx = setup(app)
    client = app.test_client()
    for path in ("/api/customer/shipments", f"/api/customer/shipments/{ctx['shipment']}"):
        assert client.get(path).status_code == 401
        assert client.get(path, headers=_auth(app)).status_code == 401
    _as_customer(client, ctx["accounts"][0])
    assert client.post(f"/api/customer/shipments/{ctx['shipment']}", json={}).status_code == 405
    assert client.get(f"/api/public/track/{ctx['shipment']}").status_code == 404


def test_authorization_receipt_changes_on_partial_revoke_without_exposing_identities(operational_app):
    app = operational_app
    with app.app_context():
        ctx = setup(app); a = account(app, ctx); ids = app.config["phase1a"]
        b = Cargo.query.filter_by(public_id=ctx["cargo_b"]).one()
        grants.grant(ids["org"], ids["verifier"], {"portal_account_public_id": a.public_id,
            "customer_id": b.cargo_owner_customer_id}, str(uuid4()))
        db.session.commit()
    client = app.test_client(); _as_customer(client, ctx["accounts"][0])
    before = client.get(f"/api/customer/shipments/{ctx['shipment']}").get_json()
    receipt = client.get("/api/customer/shipments/authorization")
    assert set(receipt.get_json()) == {"authorization_revision"}
    assert receipt.get_json()["authorization_revision"] == before["authorization_revision"]
    assert "no-store" in receipt.headers["Cache-Control"]
    with app.app_context(): revoke(app, account(app, ctx), ids["customer"])
    after = client.get("/api/customer/shipments/authorization").get_json()
    assert after["authorization_revision"] != before["authorization_revision"]
    assert [c["public_id"] for c in client.get(f"/api/customer/shipments/{ctx['shipment']}").get_json()["cargo"]] == [ctx["cargo_b"]]


@pytest.mark.parametrize("change", ["entitlement", "generation"])
def test_revoke_during_projection_never_returns_pre_revoke_body(operational_app, monkeypatch, change):
    app = operational_app
    with app.app_context(): ctx = setup(app)
    original = service.detail
    def delayed(account, *args, **kwargs):
        value = original(account, *args, **kwargs)
        if change == "entitlement": revoke(app, account)
        else:
            account.session_generation += 1
            db.session.commit()
        return value
    monkeypatch.setattr(service, "detail", delayed)
    client = app.test_client(); _as_customer(client, ctx["accounts"][0])
    response = client.get(f"/api/customer/shipments/{ctx['shipment']}")
    assert response.status_code == (409 if change == "entitlement" else 401)
    assert "cargo" not in response.get_json()


def test_customer_shipment_openapi_exact_route_and_allowlist_contract(operational_app):
    from pathlib import Path
    import yaml
    app = operational_app
    document = yaml.safe_load((Path(__file__).resolve().parents[2] / "docs/openapi/openapi.yaml").read_text(encoding="utf-8"))
    actual = {(rule.rule.replace("<shipment_id>", "{shipment_id}"), method.lower())
        for rule in app.url_map.iter_rules() if rule.rule.startswith("/api/customer/shipments")
        for method in rule.methods - {"HEAD", "OPTIONS"}}
    declared = {(path, method) for path, value in document["paths"].items()
        if path.startswith("/api/customer/shipments") for method in value if method in {"get", "post", "put", "patch", "delete"}}
    assert actual == declared
    def assert_allowlist(value, schema):
        if "$ref" in schema:
            schema = document["components"]["schemas"][schema["$ref"].split("/")[-1]]
        if isinstance(value, dict):
            assert schema["additionalProperties"] is False
            assert set(schema["required"]) <= set(value) <= set(schema["properties"])
            for key, item in value.items(): assert_allowlist(item, schema["properties"][key])
        elif isinstance(value, list):
            for item in value: assert_allowlist(item, schema["items"])
        elif value is None:
            assert schema.get("nullable") is True
        elif "enum" in schema:
            assert value in schema["enum"]
    with app.app_context(): ctx = setup(app)
    client = app.test_client(); _as_customer(client, ctx["accounts"][0])
    for path, schema in (("/api/customer/shipments", "CustomerShipmentList"),
                         (f"/api/customer/shipments/{ctx['shipment']}", "CustomerShipmentDetail")):
        assert_allowlist(client.get(path).get_json(), document["components"]["schemas"][schema])
