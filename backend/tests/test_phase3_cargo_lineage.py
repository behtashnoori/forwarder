"""P3-02 Cargo customer/Request lineage, semantics, and authority evidence."""

from decimal import Decimal
from pathlib import Path
import re

import pytest
import yaml

from backend import create_app
from backend.cargo_models import ShipmentCargoItem
from backend.extensions import db
from backend.models import (
    CargoType,
    Customer,
    ExpertUser,
    PackagingType,
    RequestCargoItem,
    ShipmentRequest,
    UnitOfMeasure,
)
from backend.operational_models import (
    OperationalAudit,
    OperationalMembership,
    OperationalOrganization,
    OperationalShipment,
)
from backend.organization_reference_catalog_models import (
    OrganizationCargoTypeActivation,
    OrganizationPackagingTypeActivation,
    OrganizationUnitOfMeasureActivation,
)
from backend.services.auth_session_service import create_session_tokens


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def cargo_lineage_app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SECRET_KEY": "p3-02-cargo-lineage",
        },
        skip_startup=True,
    )
    with app.app_context():
        db.create_all()
        org = OperationalOrganization(name="P3-02 Org", is_active=True)
        foreign_org = OperationalOrganization(name="P3-02 Foreign", is_active=True)
        owner = ExpertUser(
            username="p3-02-owner",
            password_hash="unused",
            full_name="Owning Transport Expert",
            role="expert",
            authority="EXPERT",
            is_active=True,
        )
        peer = ExpertUser(
            username="p3-02-peer",
            password_hash="unused",
            full_name="Peer Expert",
            role="expert",
            authority="EXPERT",
            is_active=True,
        )
        admin = ExpertUser(
            username="p3-02-admin",
            password_hash="unused",
            full_name="Organization Admin",
            role="admin",
            authority="ORGANIZATION_ADMIN",
            is_active=True,
        )
        db.session.add_all([org, foreign_org, owner, peer, admin])
        db.session.flush()
        permissions = ["operational_shipment.read", "operational_shipment.create"]
        db.session.add_all(
            [
                OperationalMembership(
                    organization_id=org.id,
                    user_id=owner.id,
                    permissions=permissions,
                ),
                OperationalMembership(
                    organization_id=org.id,
                    user_id=peer.id,
                    permissions=permissions,
                ),
                OperationalMembership(
                    organization_id=org.id,
                    user_id=admin.id,
                    permissions=permissions + ["request.read"],
                ),
            ]
        )
        customer_a = Customer(
            first_name="Alpha",
            last_name="Customer",
            phone="09120000001",
            status="active",
            ownership_scope="TENANT",
            operational_organization_id=org.id,
        )
        customer_b = Customer(
            first_name="Beta",
            last_name="Customer",
            phone="09120000002",
            status="active",
            ownership_scope="TENANT",
            operational_organization_id=org.id,
        )
        foreign_customer = Customer(
            first_name="Foreign",
            last_name="Customer",
            phone="09120000003",
            status="active",
            ownership_scope="TENANT",
            operational_organization_id=foreign_org.id,
        )
        cargo_type = CargoType(
            immutable_code="P3_CARGO_GENERAL",
            fa_name="کالای عمومی",
            en_name="General cargo",
            is_active=True,
        )
        item_uom = UnitOfMeasure(
            immutable_code="P3_PALLET",
            fa_name="پالت",
            en_name="Pallet",
            symbol="plt",
            measurement_dimension="COUNT",
            is_active=True,
        )
        weight_uom = UnitOfMeasure(
            immutable_code="P3_KG",
            fa_name="کیلوگرم",
            en_name="Kilogram",
            symbol="kg",
            measurement_dimension="WEIGHT",
            is_active=True,
        )
        volume_uom = UnitOfMeasure(
            immutable_code="P3_M3",
            fa_name="متر مکعب",
            en_name="Cubic metre",
            symbol="m3",
            measurement_dimension="VOLUME",
            is_active=True,
        )
        packaging = PackagingType(
            immutable_code="P3_CRATE",
            fa_name="جعبه",
            en_name="Crate",
            is_active=True,
        )
        inactive_packaging = PackagingType(
            immutable_code="P3_INACTIVE_CRATE",
            fa_name="جعبه غیرفعال",
            en_name="Inactive crate",
            is_active=True,
        )
        db.session.add_all(
            [
                customer_a,
                customer_b,
                foreign_customer,
                cargo_type,
                item_uom,
                weight_uom,
                volume_uom,
                packaging,
                inactive_packaging,
            ]
        )
        db.session.flush()
        db.session.add_all(
            [
                OrganizationCargoTypeActivation(
                    organization_id=org.id,
                    cargo_type_id=cargo_type.id,
                    status="ACTIVE",
                    created_by=admin.id,
                    updated_by=admin.id,
                ),
                *[
                    OrganizationUnitOfMeasureActivation(
                        organization_id=org.id,
                        unit_of_measure_id=uom.id,
                        status="ACTIVE",
                        created_by=admin.id,
                        updated_by=admin.id,
                    )
                    for uom in (item_uom, weight_uom, volume_uom)
                ],
                OrganizationPackagingTypeActivation(
                    organization_id=org.id,
                    packaging_type_id=packaging.id,
                    status="ACTIVE",
                    created_by=admin.id,
                    updated_by=admin.id,
                ),
                OrganizationPackagingTypeActivation(
                    organization_id=org.id,
                    packaging_type_id=inactive_packaging.id,
                    status="INACTIVE",
                    created_by=admin.id,
                    updated_by=admin.id,
                ),
            ]
        )
        request_row = ShipmentRequest(
            contact_phone="09120000001",
            tracking_code="SR2-P302-LINEAGE",
            assigned_to=owner.id,
            customer_id=customer_a.id,
            operational_organization_id=org.id,
            ownership_scope="TENANT",
        )
        db.session.add(request_row)
        db.session.flush()
        request_cargo = RequestCargoItem(
            shipment_request_id=request_row.id,
            position=1,
            cargo_type_id=cargo_type.id,
            description="Requested pumps",
            quantity=Decimal("12"),
            uom_id=item_uom.id,
        )
        shipment = OperationalShipment(
            organization_id=org.id,
            source_type="direct",
            customer_id=customer_a.id,
            lifecycle_status="planned",
            created_by_user_id=owner.id,
            primary_responsible_expert_id=owner.id,
        )
        db.session.add_all([request_cargo, shipment])
        db.session.flush()
        legacy = ShipmentCargoItem(
            operational_shipment_id=shipment.id,
            line_number=99,
            cargo_type=cargo_type,
            quantity=Decimal("3"),
            uom=item_uom,
            display_name_snapshot="Legacy unknown quantity",
            cargo_type_code_snapshot=cargo_type.immutable_code,
            cargo_type_fa_snapshot=cargo_type.fa_name,
            cargo_type_en_snapshot=cargo_type.en_name,
            uom_code_snapshot=item_uom.immutable_code,
            uom_symbol_snapshot=item_uom.symbol,
            created_by=owner.id,
            updated_by=owner.id,
        )
        db.session.add(legacy)
        db.session.commit()
        tokens = {
            name: create_session_tokens(user.id)["access_token"]
            for name, user in (("owner", owner), ("peer", peer), ("admin", admin))
        }
        yield app, {
            "tokens": tokens,
            "shipment": shipment.public_id,
            "customers": (customer_a.id, customer_b.id),
            "foreign_customer": foreign_customer.id,
            "request": request_row.public_id,
            "request_cargo": request_cargo.public_id,
            "cargo_type": cargo_type.public_id,
            "item_uom": item_uom.public_id,
            "weight_uom": weight_uom.public_id,
            "volume_uom": volume_uom.public_id,
            "packaging": packaging.public_id,
            "inactive_packaging": inactive_packaging.public_id,
        }
        db.session.remove()
        db.drop_all()


def _base_payload(ctx, line_number, customer_id):
    return {
        "line_number": line_number,
        "display_name": f"Cargo {line_number}",
        "cargo_type_public_id": ctx["cargo_type"],
        "uom_public_id": ctx["item_uom"],
        "cargo_owner_customer_id": customer_id,
        "planned_quantity": "10",
        "quantity": "10",
    }


def test_request_and_direct_cargo_keep_customer_lineage_and_quantity_meanings(cargo_lineage_app):
    app, ctx = cargo_lineage_app
    client = app.test_client()
    owner = _headers(ctx["tokens"]["owner"])
    customer_a, customer_b = ctx["customers"]

    options = client.get(
        f"/api/internal/operational-shipments/{ctx['shipment']}/cargo-lineage-options",
        headers=owner,
    )
    assert options.status_code == 200
    assert {row["id"] for row in options.get_json()["customers"]} == {
        customer_a,
        customer_b,
    }
    assert [row["public_id"] for row in options.get_json()["requests"]] == [
        ctx["request"]
    ]

    request_payload = {
        **_base_payload(ctx, 1, customer_a),
        "source_request_public_id": ctx["request"],
        "source_request_cargo_item_public_id": ctx["request_cargo"],
        "requested_quantity": "12",
        "actual_quantity": "9",
        "packaging_type_public_id": ctx["packaging"],
        "hs_code": "8413.91",
        "description": "Progressively completed",
        "gross_weight": "850",
        "gross_weight_uom_public_id": ctx["weight_uom"],
        "volume": "4.25",
        "volume_uom_public_id": ctx["volume_uom"],
        "destination_description": "Branch A",
    }
    created_request = client.post(
        f"/api/internal/operational-shipments/{ctx['shipment']}/cargo-items",
        headers=owner,
        json=request_payload,
    )
    assert created_request.status_code == 201, created_request.get_json()
    request_item = created_request.get_json()["item"]
    assert request_item["cargo_owner"]["id"] == customer_a
    assert request_item["source_lineage"] == {
        "kind": "REQUEST",
        "request_public_id": ctx["request"],
        "request_reference": "SR2-P302-LINEAGE",
        "request_cargo_item_public_id": ctx["request_cargo"],
        "request_cargo_position": 1,
    }
    assert request_item["quantities"] == {
        "requested": "12.000000",
        "planned": "10.000000",
        "actual": "9.000000",
        "legacy": "10.000000",
        "legacy_meaning": "PLANNED_COMPATIBILITY",
    }
    assert request_item["packaging"]["code"] == "P3_CRATE"
    assert request_item["gross_weight"]["uom_code"] == "P3_KG"
    assert request_item["volume"]["uom_code"] == "P3_M3"
    assert request_item["incomplete_fields"] == []

    direct = client.post(
        f"/api/internal/operational-shipments/{ctx['shipment']}/cargo-items",
        headers=owner,
        json=_base_payload(ctx, 2, customer_b),
    )
    assert direct.status_code == 201, direct.get_json()
    direct_item = direct.get_json()["item"]
    assert direct_item["cargo_owner"]["id"] == customer_b
    assert direct_item["source_lineage"]["kind"] == "DIRECT"
    assert direct_item["source_lineage"]["request_public_id"] is None
    assert direct_item["quantities"]["requested"] is None
    assert direct_item["quantities"]["actual"] is None
    assert set(direct_item["incomplete_fields"]) == {
        "HS_CODE",
        "PACKAGING_TYPE",
        "WEIGHT",
        "VOLUME",
    }

    listed = client.get(
        f"/api/internal/operational-shipments/{ctx['shipment']}/cargo-items",
        headers=owner,
    )
    assert listed.status_code == 200
    rows = listed.get_json()["items"]
    assert {row["cargo_owner"]["id"] for row in rows if row["cargo_owner"]} == {
        customer_a,
        customer_b,
    }
    legacy = next(row for row in rows if row["line_number"] == 99)
    assert legacy["source_lineage"]["kind"] == "UNKNOWN"
    assert legacy["quantities"]["legacy"] == "3.000000"
    assert legacy["quantities"]["planned"] is None
    assert legacy["quantities"]["legacy_meaning"] == "UNKNOWN"


def test_progressive_correction_is_audited_and_authority_fails_closed(cargo_lineage_app):
    app, ctx = cargo_lineage_app
    client = app.test_client()
    owner = _headers(ctx["tokens"]["owner"])
    created = client.post(
        f"/api/internal/operational-shipments/{ctx['shipment']}/cargo-items",
        headers=owner,
        json=_base_payload(ctx, 3, ctx["customers"][1]),
    )
    item = created.get_json()["item"]
    corrected = client.patch(
        f"/api/internal/operational-shipments/{ctx['shipment']}/cargo-items/{item['public_id']}",
        headers=owner,
        json={
            "version": item["version"],
            "planned_quantity": "11",
            "actual_quantity": "10.5",
            "packaging_type_public_id": ctx["packaging"],
            "hs_code": "9999",
            "description": "Corrected without replacing history",
        },
    )
    assert corrected.status_code == 200, corrected.get_json()
    current = corrected.get_json()["item"]
    assert current["quantity"] == current["quantities"]["planned"] == "11.000000"
    assert current["quantities"]["actual"] == "10.500000"
    assert current["version"] == item["version"] + 1

    history = client.get(
        f"/api/internal/operational-shipments/{ctx['shipment']}/cargo-items/{item['public_id']}/history",
        headers=owner,
    )
    assert history.status_code == 200
    events = history.get_json()["history"]
    assert [event["action"] for event in events] == [
        "SHIPMENT_CARGO_CREATED",
        "SHIPMENT_CARGO_UPDATED",
    ]
    assert "planned_quantity" in events[-1]["changed_fields"]
    assert events[-1]["changes"]["hs_code_snapshot"] == {
        "before": "MISSING",
        "after": "SET",
    }

    mismatch = client.post(
        f"/api/internal/operational-shipments/{ctx['shipment']}/cargo-items",
        headers=owner,
        json={
            **_base_payload(ctx, 4, ctx["customers"][1]),
            "source_request_public_id": ctx["request"],
        },
    )
    assert mismatch.status_code == 422
    assert mismatch.get_json()["error"]["code"] == "SOURCE_CUSTOMER_MISMATCH"

    foreign = client.post(
        f"/api/internal/operational-shipments/{ctx['shipment']}/cargo-items",
        headers=owner,
        json=_base_payload(ctx, 5, ctx["foreign_customer"]),
    )
    assert foreign.status_code == 422

    inactive_package = client.post(
        f"/api/internal/operational-shipments/{ctx['shipment']}/cargo-items",
        headers=owner,
        json={
            **_base_payload(ctx, 6, ctx["customers"][1]),
            "packaging_type_public_id": ctx["inactive_packaging"],
        },
    )
    assert inactive_package.status_code == 409
    assert (
        inactive_package.get_json()["error"]["code"]
        == "ORGANIZATION_REFERENCE_NOT_ACTIVE"
    )

    uom_mismatch_payload = _base_payload(ctx, 7, ctx["customers"][0])
    uom_mismatch_payload.update(
        {
            "uom_public_id": ctx["weight_uom"],
            "source_request_public_id": ctx["request"],
            "source_request_cargo_item_public_id": ctx["request_cargo"],
        }
    )
    uom_mismatch = client.post(
        f"/api/internal/operational-shipments/{ctx['shipment']}/cargo-items",
        headers=owner,
        json=uom_mismatch_payload,
    )
    assert uom_mismatch.status_code == 422
    assert uom_mismatch.get_json()["error"]["code"] == "SOURCE_UOM_MISMATCH"

    stale = client.patch(
        f"/api/internal/operational-shipments/{ctx['shipment']}/cargo-items/{item['public_id']}",
        headers=owner,
        json={"version": item["version"], "actual_quantity": "10"},
    )
    assert stale.status_code == 409

    assert client.post(
        f"/api/internal/operational-shipments/{ctx['shipment']}/cargo-items",
        headers=_headers(ctx["tokens"]["admin"]),
        json=_base_payload(ctx, 8, ctx["customers"][0]),
    ).status_code == 403
    assert client.post(
        f"/api/internal/operational-shipments/{ctx['shipment']}/cargo-items",
        headers=_headers(ctx["tokens"]["peer"]),
        json=_base_payload(ctx, 9, ctx["customers"][0]),
    ).status_code == 404

    with app.app_context():
        actions = [
            row.action
            for row in OperationalAudit.query.filter_by(
                entity_type="ShipmentCargoItem"
            ).order_by(OperationalAudit.id)
        ]
        assert actions == ["SHIPMENT_CARGO_CREATED", "SHIPMENT_CARGO_UPDATED"]
        internal_cargo_rules = [
            rule.rule
            for rule in app.url_map.iter_rules()
            if "cargo-items" in rule.rule
        ]
        assert internal_cargo_rules
        assert all(not rule.startswith("/api/customer") for rule in internal_cargo_rules)


def test_p3_02_openapi_matches_runtime_routes(cargo_lineage_app):
    app, _ctx = cargo_lineage_app
    document = yaml.safe_load(
        (
            Path(__file__).resolve().parents[2]
            / "docs"
            / "openapi"
            / "openapi.yaml"
        ).read_text(encoding="utf-8")
    )
    expected = {
        "/api/internal/operational-shipments/{shipment_id}/cargo-lineage-options",
        "/api/internal/operational-shipments/{shipment_id}/cargo-items",
        "/api/internal/operational-shipments/{shipment_id}/cargo-items/{item_id}",
        "/api/internal/operational-shipments/{shipment_id}/cargo-items/{item_id}/history",
    }
    assert expected <= set(document["paths"])
    runtime = {
        re.sub(r"<(?:[^:>]+:)?([^>]+)>", r"{\1}", rule.rule)
        for rule in app.url_map.iter_rules()
    }
    assert expected <= runtime
    schema = document["components"]["schemas"]["ShipmentCargoItem"]
    assert {"quantities", "source_lineage", "packaging", "incomplete_fields"} <= set(
        schema["required"]
    )
