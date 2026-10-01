"""Partial delivery truth, corrections, authorization and exact-version evidence."""
from decimal import Decimal
from uuid import uuid4
import io
import json

import pytest
from sqlalchemy import select
from backend.extensions import db
from backend.cargo_models import ShipmentCargoItem
from backend.delivery_models import CargoDelivery, CargoDeliveryEvidence
from backend.logistics_network_models import LogisticsPoint, LogisticsPointType
from backend.models import City, Country, Customer, CustomerGamification, ExpertUser, Province
from backend.operational_models import OperationalShipment, OperationalWorkItem, ExecutionUnit, OperationalMembership
from backend.services import delivery_service as deliveries, customer_entitlement_service as entitlements
from backend.services import unified_shipment_history as unified_history
from backend.services.operational_service import OperationalError
from backend.tests.test_operational_vertical_slice import _auth, _user, operational_app
from backend.tests.test_phase3_cargo_allocation import _fixture
from backend.tests.test_phase3_document_context import _as_customer
from backend.tests.test_shipment_document_authorization import PDF


def setup(app):
    ctx = _fixture(app, second_stage=True)
    ids = app.config["phase1a"]
    a = db.session.scalar(select(ShipmentCargoItem).where(ShipmentCargoItem.public_id == ctx["cargo"]))
    a.actual_quantity = Decimal("100")
    owner = Customer(company_name="PRIVATE-CUSTOMER-B", ownership_scope="TENANT",
                     operational_organization_id=ids["org"], status="active")
    accounts = [CustomerGamification(email=f"delivery-{i}@example.test", phone=f"0900800000{i}", operational_organization_id=ids["org"]) for i in range(2)]
    db.session.add_all([owner, *accounts]); db.session.flush()
    b = ShipmentCargoItem(operational_shipment_id=ctx["shipment_id"], line_number=2,
        cargo_owner_customer_id=owner.id, cargo_type_id=a.cargo_type_id, uom_id=a.uom_id,
        quantity=25, planned_quantity=25, actual_quantity=25, display_name_snapshot="PRIVATE-CARGO-B",
        cargo_type_code_snapshot=a.cargo_type_code_snapshot, cargo_type_fa_snapshot=a.cargo_type_fa_snapshot,
        cargo_type_en_snapshot=a.cargo_type_en_snapshot, uom_code_snapshot=a.uom_code_snapshot,
        uom_symbol_snapshot=a.uom_symbol_snapshot, created_by=ids["user"], updated_by=ids["user"])
    db.session.add(b); db.session.flush()
    for account, customer in zip(accounts, [ids["customer"], owner.id]):
        entitlements.grant(ids["org"], ids["verifier"], {"portal_account_public_id": account.public_id,
            "customer_id": customer}, str(uuid4()))
    db.session.commit()
    ctx.update(cargo_b=b.public_id, accounts=[x.id for x in accounts], uom=a.uom.public_id)
    return ctx


def payload(ctx, **changes):
    return {"cargo_public_id": ctx["cargo"], "quantity": "60", "uom_public_id": ctx["uom"],
            "destination_text": "انبار مشتری A", "occurred_at": "2026-09-21T10:00:00+03:30",
            "expected_version": 0, **changes}


def record(app, ctx, data=None, key=None):
    result = deliveries.create(ctx["shipment"], _user(app), data or payload(ctx), key or str(uuid4()))
    db.session.commit()
    return result


def test_partial_second_correction_excess_and_no_upstream_side_effects(operational_app):
    app = operational_app
    with app.app_context():
        ctx = setup(app)
        shipment = db.session.get(OperationalShipment, ctx["shipment_id"])
        cargo = ShipmentCargoItem.query.filter_by(public_id=ctx["cargo"]).one()
        before = (shipment.lifecycle_status, shipment.version, cargo.quantity, cargo.planned_quantity,
                  cargo.actual_quantity, cargo.version, OperationalWorkItem.query.count(), ExecutionUnit.query.count())
        first, _ = record(app, ctx, key="delivery-one")
        record(app, ctx, payload(ctx, quantity="35"))
        result = deliveries.listing(ctx["shipment"], _user(app))
        assert Decimal(result["cargo"][0]["delivered"]) == 95
        assert Decimal(result["cargo"][0]["remaining"]) == 5
        assert not result["cargo"][1]["has_delivery"] and Decimal(result["cargo"][1]["delivered"]) == 0
        corrected, _ = record(app, ctx, payload(ctx, quantity="58", expected_version=1,
            corrects_public_id=first.public_id, reason="PRIVATE-RECOUNT"))
        result = deliveries.listing(ctx["shipment"], _user(app))
        assert Decimal(result["cargo"][0]["delivered"]) == 93
        assert Decimal(result["cargo"][0]["remaining"]) == 7
        rows = {r["public_id"]: r for r in result["items"]}
        assert rows[first.public_id]["status"] == "SUPERSEDED" and Decimal(rows[first.public_id]["quantity"]) == 60
        assert rows[corrected.public_id]["reason"] == "PRIVATE-RECOUNT"
        assert rows[corrected.public_id]["corrects_public_id"] == first.public_id
        assert rows[first.public_id]["occurred_at"] == "2026-09-21T06:30:00Z"
        assert rows[first.public_id]["recorded_at"].endswith("Z") and rows[first.public_id]["actor_label"]
        replay, created = record(app, ctx, key="delivery-one")
        assert replay.id == first.id and not created
        record(app, ctx, payload(ctx, quantity="9"))
        result = deliveries.listing(ctx["shipment"], _user(app))
        assert Decimal(result["cargo"][0]["delivered"]) == 102 and Decimal(result["cargo"][0]["excess"]) == 2
        assert Decimal(result["cargo"][1]["remaining"]) == 25
        db.session.refresh(shipment); db.session.refresh(cargo)
        assert before == (shipment.lifecycle_status, shipment.version, cargo.quantity, cargo.planned_quantity,
                          cargo.actual_quantity, cargo.version, OperationalWorkItem.query.count(), ExecutionUnit.query.count())
        first.quantity = 1
        with pytest.raises(ValueError, match="immutable"): db.session.flush()
        db.session.rollback()


def test_legacy_status_unknown_actual_and_unknown_customer_are_not_inferred(operational_app):
    app = operational_app
    with app.app_context():
        ctx = setup(app)
        shipment = db.session.get(OperationalShipment, ctx["shipment_id"])
        shipment.lifecycle_status = "completed"
        for unit in ExecutionUnit.query.all(): unit.lifecycle_status = "delivered"
        cargo = ShipmentCargoItem.query.filter_by(public_id=ctx["cargo"]).one()
        cargo.actual_quantity = None
        db.session.commit()
        assert CargoDelivery.query.count() == 0
        assert not deliveries.listing(ctx["shipment"], _user(app))["cargo"][0]["has_delivery"]
        record(app, ctx)
        summary = deliveries.listing(ctx["shipment"], _user(app))["cargo"][0]
        assert summary["known_actual"] is summary["remaining"] is summary["excess"] is None
        cargo.cargo_owner_customer_id = None
        db.session.commit()
        with pytest.raises(OperationalError) as caught: record(app, ctx)
        assert caught.value.code == "DELIVERY_CUSTOMER_UNKNOWN"
        db.session.rollback()
        assert CargoDelivery.query.count() == 1


def test_structured_destination_is_exact_and_legacy_free_text_remains_unbound(operational_app):
    app = operational_app
    with app.app_context():
        ctx = setup(app)
        legacy, _ = record(app, ctx, payload(ctx, quantity="5", destination_text="بندرعباس"))
        country = Country(code="IR", name_fa="ایران", name_en="Iran", is_active=True)
        db.session.add(country); db.session.flush()
        province = Province(code="DEL-HRZ", name_fa="هرمزگان", name_en="Hormozgan",
                            geoname_id=131222, country_id=country.id,
                            dataset_id="GEONAMES_ADMIN1_CITY_V1", is_active=True)
        db.session.add(province); db.session.flush()
        city = City(code="141679", name_fa="بندرعباس", name_en="Bandar Abbas",
                    geoname_id=141679, country_id=country.id, province_id=province.id,
                    county_id=None, dataset_id="GEONAMES_ADMIN1_CITY_V1", is_active=True)
        db.session.add(city); db.session.commit()

        structured, _ = record(app, ctx, payload(ctx, quantity="7", destination_text=None,
            destination_reference={"country_id": country.id, "source_type": "city", "source_id": city.id},
            destination_note="تحویل در دروازه شرقی"))
        projected = {item["public_id"]: item for item in deliveries.listing(ctx["shipment"], _user(app))["items"]}
        assert projected[legacy.public_id]["destination_text"] == "بندرعباس"
        assert projected[legacy.public_id]["destination"] is None
        assert projected[legacy.public_id]["destination_reference"] is None
        current = projected[structured.public_id]
        assert current["destination"]["canonical_reference"] == {"source_type": "city", "source_id": city.id}
        assert current["destination_reference"] == {"country_id": country.id, "source_type": "city", "source_id": city.id}
        assert current["destination_text"] == "تحویل در دروازه شرقی"

        history = unified_history.history(db.session.get(OperationalShipment, ctx["shipment_id"]), per_page=100)
        delivery_items = [item for item in history["items"] if item["category"] == "DELIVERY"]
        assert {item["source_entity_id"] for item in delivery_items}.issuperset({legacy.public_id, structured.public_id})
        assert all(item["business_label"] == "تحویل کالا ثبت شد" for item in delivery_items)

        row = db.session.get(CargoDelivery, structured.id)
        row.destination_snapshot = {**row.destination_snapshot, "display_name": "بازنویسی ممنوع"}
        with pytest.raises(ValueError, match="immutable"):
            db.session.flush()
        db.session.rollback()


def _without_destination(data):
    return {key: value for key, value in data.items()
            if key not in {"destination_text", "destination_reference", "destination_note"}}


def test_historical_free_text_final_and_quantity_corrections_preserve_destination(operational_app):
    """Cases 1-2: non-destination corrections inherit free-text identity exactly."""
    app = operational_app
    with app.app_context():
        ctx = setup(app)
        original, _ = record(app, ctx, payload(ctx, quantity="95", destination_text="بندرعباس"))
        final_command = _without_destination(payload(ctx, quantity="95", expected_version=1,
            corrects_public_id=original.public_id, is_final=True))
        corrected, _ = record(app, ctx, final_command)

        assert corrected.quantity == original.quantity == Decimal("95")
        assert corrected.occurred_at == original.occurred_at
        assert corrected.destination_text == original.destination_text == "بندرعباس"
        assert corrected.destination_location_id is original.destination_location_id is None
        assert corrected.destination_logistics_point_id is original.destination_logistics_point_id is None
        assert corrected.destination_snapshot is original.destination_snapshot is None
        assert corrected.is_final and not original.is_final
        assert corrected.supersedes_delivery_id == original.id and corrected.revision == 2

        quantity_original, _ = record(app, ctx, payload(ctx, cargo_public_id=ctx["cargo_b"],
            quantity="5", destination_text="مقصد تاریخی"))
        quantity_command = _without_destination(payload(ctx, cargo_public_id=ctx["cargo_b"],
            quantity="6", expected_version=1, corrects_public_id=quantity_original.public_id))
        quantity_correction, _ = record(app, ctx, quantity_command)
        assert quantity_correction.quantity == Decimal("6")
        assert quantity_correction.destination_text == "مقصد تاریخی"
        assert quantity_correction.destination_location_id is None
        assert quantity_correction.destination_snapshot is None


def test_destination_replacement_requires_structure_and_structured_identity_is_inherited(operational_app):
    """Cases 3 and 5: replacement is structured; omission preserves exact identity."""
    app = operational_app
    with app.app_context():
        ctx = setup(app)
        historical, _ = record(app, ctx, payload(ctx, quantity="5", destination_text="بندرعباس"))

        changed_text = _without_destination(payload(ctx, quantity="5", expected_version=1,
            corrects_public_id=historical.public_id))
        changed_text["destination_text"] = "مقصد آزاد جدید"
        with pytest.raises(OperationalError) as caught:
            record(app, ctx, changed_text)
        assert caught.value.code == "DELIVERY_STRUCTURED_DESTINATION_REQUIRED"
        db.session.rollback()

        country = Country(code="HC", name_fa="کشور آزمون اصلاح", name_en="Historical Correction", is_active=True)
        db.session.add(country); db.session.flush()
        province = Province(code="HC-P", name_fa="استان آزمون اصلاح", name_en="Correction Province",
                            geoname_id=910001, country_id=country.id,
                            dataset_id="GEONAMES_ADMIN1_CITY_V1", is_active=True)
        db.session.add(province); db.session.flush()
        city = City(code="910002", name_fa="شهر ساخت‌یافته", name_en="Structured City",
                    geoname_id=910002, country_id=country.id, province_id=province.id,
                    county_id=None, dataset_id="GEONAMES_ADMIN1_CITY_V1", is_active=True)
        db.session.add(city); db.session.commit()

        replacement = _without_destination(payload(ctx, quantity="5", expected_version=1,
            corrects_public_id=historical.public_id))
        replacement.update(destination_reference={"country_id": country.id, "source_type": "city", "source_id": city.id},
                           destination_note="مقصد جایگزین‌شده")
        structured, _ = record(app, ctx, replacement)
        assert structured.destination_text == "مقصد جایگزین‌شده"
        assert structured.destination_location_id is not None
        assert structured.destination_snapshot["canonical_reference"] == {"source_type": "city", "source_id": city.id}

        inherited_command = _without_destination(payload(ctx, quantity="7", expected_version=2,
            corrects_public_id=structured.public_id))
        inherited, _ = record(app, ctx, inherited_command)
        assert inherited.destination_text == structured.destination_text
        assert inherited.destination_location_id == structured.destination_location_id
        assert inherited.destination_logistics_point_id == structured.destination_logistics_point_id
        assert inherited.destination_snapshot == structured.destination_snapshot


def test_cross_tenant_destination_replacement_is_refused(operational_app):
    """Case 6: correction inheritance never weakens endpoint tenant isolation."""
    app = operational_app
    with app.app_context():
        ctx = setup(app)
        original, _ = record(app, ctx, payload(ctx, quantity="5", destination_text="مقصد تاریخی"))
        ids = app.config["phase1a"]
        country = Country(code="XT", name_fa="کشور مرزی", name_en="Cross Tenant", is_active=True)
        point_type = LogisticsPointType(immutable_code="XT-WAREHOUSE", fa_name="انبار مرزی",
            en_name="Cross Tenant Warehouse", created_by=ids["user"], updated_by=ids["user"])
        db.session.add_all([country, point_type]); db.session.flush()
        foreign = LogisticsPoint(organization_id=ids["other_org"], immutable_code="FOREIGN-DELIVERY",
            logistics_point_type_id=point_type.id, fa_name="مقصد سازمان دیگر", en_name="Foreign Destination",
            normalized_name="foreign destination", country_id=country.id, geography_key=f"country:{country.id}",
            is_active=True, created_by=ids["user"], updated_by=ids["user"])
        db.session.add(foreign); db.session.commit()

        command = _without_destination(payload(ctx, quantity="5", expected_version=1,
            corrects_public_id=original.public_id))
        command["destination_reference"] = {"country_id": country.id, "source_type": "logistics_point", "source_id": foreign.public_id}
        with pytest.raises(OperationalError) as caught:
            record(app, ctx, command)
        assert caught.value.code == "RESOURCE_NOT_FOUND" and caught.value.status == 404
        db.session.rollback()
        assert CargoDelivery.query.count() == 1


@pytest.mark.parametrize("changes", [
    {"quantity": "-1"}, {"quantity": "0"}, {"quantity": "NaN"}, {"quantity": "Infinity"},
    {"quantity": "1.0000001"}, {"quantity": True}, {"quantity": "1000000000000"},
    {"uom_public_id": str(uuid4())}, {"cargo_public_id": "bad"}, {"cargo_public_id": str(uuid4())},
    {"occurred_at": "2026-09-21T10:00:00"}, {"destination_text": " "}, {"expected_version": True},
    {"evidence_document_public_ids": [str(uuid4())]}, {"customer_id": 1},
])
def test_invalid_commands_leave_no_delivery(operational_app, changes):
    with operational_app.app_context():
        ctx = setup(operational_app)
        with pytest.raises(OperationalError): record(operational_app, ctx, payload(ctx, **changes))
        db.session.rollback()
        assert CargoDelivery.query.count() == CargoDeliveryEvidence.query.count() == 0


def test_http_permissions_replay_correction_conflict_and_reload(operational_app):
    app = operational_app
    with app.app_context(): ctx = setup(app)
    client = app.test_client()
    url = f"/api/operational-shipments/{ctx['shipment']}/deliveries"
    headers = {**_auth(app), "Idempotency-Key": "delivery-http"}
    first = client.post(url, json=payload(ctx), headers=headers)
    assert first.status_code == 201, first.get_json()
    assert client.post(url, json=payload(ctx), headers=headers).status_code == 200
    assert client.post(url, json=payload(ctx, quantity="61"), headers=headers).status_code == 409
    correction = payload(ctx, quantity="58", expected_version=1, corrects_public_id=first.get_json()["public_id"])
    assert client.post(url, json=correction, headers={**_auth(app), "Idempotency-Key": "correction"}).status_code == 201
    assert client.post(url, json=correction, headers={**_auth(app), "Idempotency-Key": "stale-correction"}).status_code == 409
    for key in ("verifier", "outsider"):
        assert client.post(url, json=payload(ctx), headers={**_auth(app, key), "Idempotency-Key": key}).status_code in (403, 404)
    assert client.post(url, json=payload(ctx)).status_code == 401
    read = client.get(url, headers=_auth(app))
    assert read.status_code == 200 and "no-store" in read.headers["Cache-Control"]
    assert read.get_json()["data"]["total"] == 2
    assert not client.get(url, headers=_auth(app, "verifier")).get_json()["data"]["can_manage"]
    assert client.get(url, headers=_auth(app, "outsider")).status_code in (403, 404)
    with app.app_context():
        ids = app.config["phase1a"]
        peer = ExpertUser(username="delivery-peer", password_hash="unused", full_name="Peer", role="expert", is_active=True)
        platform = ExpertUser(username="delivery-platform", password_hash="unused", full_name="Platform", role="manager", authority="PLATFORM_ADMIN", is_active=True)
        db.session.add_all([peer, platform]); db.session.flush()
        for account in (peer, platform):
            db.session.add(OperationalMembership(organization_id=ids["org"], user_id=account.id,
                permissions=["operational_shipment.read", "operational_shipment.create"]))
        ids.update(delivery_peer=peer.id, delivery_platform=platform.id)
        db.session.commit()
    for key in ("delivery_peer", "delivery_platform"):
        assert client.post(url, json=payload(ctx), headers={**_auth(app, key), "Idempotency-Key": key}).status_code in (403, 404)
    with app.app_context():
        owner = db.session.get(ExpertUser, app.config["phase1a"]["user"])
        owner.is_active = False; db.session.commit()
    assert client.post(url, json=payload(ctx), headers={**headers, "Idempotency-Key": "inactive"}).status_code in (401, 403, 404)


def test_customer_projection_filters_before_limit_and_rechecks_entitlement(operational_app):
    app = operational_app
    with app.app_context():
        ctx = setup(app)
        own, _ = record(app, ctx, payload(ctx, reason="PRIVATE-INTERNAL"))
        for i in range(3):
            record(app, ctx, payload(ctx, cargo_public_id=ctx["cargo_b"], quantity="1",
                destination_text="PRIVATE-B-DESTINATION", occurred_at=f"2026-09-22T0{i}:00:00Z"))
        shipment = db.session.get(OperationalShipment, ctx["shipment_id"])
        a, b = [db.session.get(CustomerGamification, i) for i in ctx["accounts"]]
        result = deliveries.customer_data(shipment, a, limit=1)
        assert [x["public_id"] for x in result["items"]] == [own.public_id]
        assert len(result["cargo"]) == 1 and "PRIVATE" not in json.dumps(result)
        assert "actor_label" not in result["items"][0] and "reason" not in result["items"][0]
        assert len(deliveries.customer_data(shipment, b)["items"]) == 3
        ids = app.config["phase1a"]
        grant = next(g for g in entitlements.configuration(ids["org"], ids["verifier"])["grants"] if g["portal_account_public_id"] == a.public_id)
        entitlements.revoke(ids["org"], ids["verifier"], grant["public_id"]); db.session.commit()
        assert deliveries.customer_data(shipment, a) == {"cargo": [], "items": []}


def test_delivery_document_exact_version_replacement_and_customer_download(operational_app, tmp_path):
    app = operational_app
    app.config["DOCUMENT_STORAGE_ROOT"] = str(tmp_path / "private")
    with app.app_context():
        ctx = setup(app)
        row, _ = record(app, ctx)
        delivery_public_id, delivery_id = row.public_id, row.id
    client = app.test_client()
    parent = f"/api/internal/operational-shipments/{ctx['shipment']}/documents"
    def upload(key, **changes):
        return client.post(parent, headers={**_auth(app), "Idempotency-Key": key}, data={
            "title": "مدرک تحویل", "file": (io.BytesIO(PDF), "PRIVATE-INTERNAL-NAME.pdf"),
            "context_type": "DELIVERY", "context_target_public_id": delivery_public_id,
            "visibility": "CARGO_OWNER", **changes})
    created = upload("delivery-evidence")
    assert created.status_code == 201, created.get_json()
    v1 = created.get_json()["data"]
    _as_customer(client, ctx["accounts"][0])
    allowed = client.get(f"/api/customer/documents/{v1['public_id']}/download")
    assert allowed.status_code == 200 and allowed.data == PDF
    assert "PRIVATE" not in allowed.headers["Content-Disposition"]
    _as_customer(client, ctx["accounts"][1])
    assert client.get(f"/api/customer/documents/{v1['public_id']}/download").status_code == 404
    replaced = upload("delivery-evidence-replace", replaces_document_public_id=v1["public_id"], visibility="INTERNAL")
    assert replaced.status_code == 201, replaced.get_json()
    v2 = replaced.get_json()["data"]
    _as_customer(client, ctx["accounts"][0])
    for version in (v1, v2):
        assert client.get(f"/api/customer/documents/{version['public_id']}/download").status_code == 404
    with app.app_context():
        row = db.session.get(CargoDelivery, delivery_id)
        assert [(d["version"], d["status"]) for d in deliveries.evidence_projection(row)] == [(1, "superseded"), (2, "active")]
        assert CargoDeliveryEvidence.query.count() == 2
    published = client.patch(f"{parent}/{v2['public_id']}/context", headers=_auth(app),
        json={"expected_version": 1, "visibility": "CARGO_OWNER"})
    assert published.status_code == 200, published.get_json()
    _as_customer(client, ctx["accounts"][0])
    assert client.get(f"/api/customer/documents/{v2['public_id']}/download").data == PDF
    with app.app_context():
        row = db.session.get(CargoDelivery, delivery_id)
        account = db.session.get(CustomerGamification, ctx["accounts"][0])
        projected = deliveries.evidence_projection(row, account)
        assert [(d["public_id"], d["filename"]) for d in projected] == [(v2["public_id"], "document-v2.pdf")]
        ids = app.config["phase1a"]
        grant = next(g for g in entitlements.configuration(ids["org"], ids["verifier"])["grants"] if g["portal_account_public_id"] == account.public_id)
        entitlements.revoke(ids["org"], ids["verifier"], grant["public_id"]); db.session.commit()
    assert client.get(f"/api/customer/documents/{v2['public_id']}/download").status_code == 404
    assert upload("bad-delivery-target", context_target_public_id=str(uuid4())).status_code == 404


def test_full_delivery_of_one_customer_does_not_complete_shared_shipment(operational_app):
    with operational_app.app_context():
        ctx = setup(operational_app)
        shipment = db.session.get(OperationalShipment, ctx["shipment_id"])
        before = (shipment.lifecycle_status, shipment.version)
        record(operational_app, ctx, payload(ctx, quantity="100"))
        result = deliveries.listing(ctx["shipment"], _user(operational_app))
        assert Decimal(result["cargo"][0]["remaining"]) == 0 and Decimal(result["cargo"][0]["excess"]) == 0
        assert Decimal(result["cargo"][1]["remaining"]) == 25 and not result["cargo"][1]["has_delivery"]
        db.session.refresh(shipment)
        assert (shipment.lifecycle_status, shipment.version) == before


def test_explicit_existing_evidence_must_be_current_and_same_cargo(operational_app, tmp_path):
    app = operational_app
    app.config["DOCUMENT_STORAGE_ROOT"] = str(tmp_path / "private")
    with app.app_context(): ctx = setup(app)
    client = app.test_client()
    parent = f"/api/internal/operational-shipments/{ctx['shipment']}/documents"
    documents = []
    for cargo in (ctx["cargo"], ctx["cargo_b"]):
        response = client.post(parent, headers={**_auth(app), "Idempotency-Key": str(uuid4())}, data={
            "title": "رسید", "file": (io.BytesIO(PDF), "receipt.pdf"), "context_type": "CARGO",
            "context_target_public_id": cargo, "visibility": "INTERNAL"})
        assert response.status_code == 201
        documents.append(response.get_json()["data"]["public_id"])
    with app.app_context():
        original, _ = record(app, ctx, payload(ctx, evidence_document_public_ids=[documents[0]]))
        corrected, _ = record(app, ctx, payload(ctx, quantity="58", expected_version=1,
            corrects_public_id=original.public_id, evidence_document_public_ids=[documents[0]]))
        assert deliveries.evidence_projection(original)[0]["public_id"] == documents[0]
        assert deliveries.evidence_projection(corrected)[0]["public_id"] == documents[0]
        with pytest.raises(OperationalError) as denied:
            record(app, ctx, payload(ctx, evidence_document_public_ids=[documents[1]]))
        assert denied.value.status == 404
        db.session.rollback()
        assert CargoDelivery.query.count() == CargoDeliveryEvidence.query.count() == 2
