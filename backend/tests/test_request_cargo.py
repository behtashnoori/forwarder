"""Optional multi-item Request Cargo acceptance contracts."""
from __future__ import annotations

from decimal import Decimal

import pytest

from backend import create_app
from backend.extensions import db
from backend.models import (
    CargoType,
    CustomerGamification,
    RequestCargoItem,
    ShipmentRequest,
    UnitOfMeasure,
)


CARGO_TYPE_ID = "11111111-1111-4111-8111-111111111111"
UOM_ID = "22222222-2222-4222-8222-222222222222"
INACTIVE_CARGO_TYPE_ID = "33333333-3333-4333-8333-333333333333"


@pytest.fixture()
def cargo_app():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "request-cargo-test",
    }, skip_startup=True)
    with app.app_context():
        db.create_all()
        db.session.add_all([
            CargoType(
                public_id=CARGO_TYPE_ID,
                immutable_code="GENERAL_GOODS",
                fa_name="کالای عمومی",
                en_name="General goods",
                display_order=1,
                is_active=True,
            ),
            CargoType(
                public_id=INACTIVE_CARGO_TYPE_ID,
                immutable_code="INACTIVE_TYPE",
                fa_name="غیرفعال",
                en_name="Inactive",
                display_order=2,
                is_active=False,
            ),
            UnitOfMeasure(
                public_id=UOM_ID,
                immutable_code="KG",
                fa_name="کیلوگرم",
                en_name="Kilogram",
                symbol="kg",
                measurement_dimension="WEIGHT",
                display_order=1,
                is_active=True,
            ),
        ])
        db.session.commit()
    yield app


def _payload(**overrides):
    payload = {
        "shipping_type": "domestic",
        "origin_province_id": 1,
        "dest_province_id": 2,
        "contact_phone": "09123456789",
        "transport_method_preference": "forwarder_suggestion",
    }
    payload.update(overrides)
    return payload


def test_zero_cargo_omitted_and_empty_are_both_valid(cargo_app):
    client = cargo_app.test_client()
    omitted = client.post("/api/shipment-request", json=_payload())
    empty = client.post("/api/shipment-request", json=_payload(cargo_items=[]))

    assert omitted.status_code == empty.status_code == 201
    assert omitted.get_json()["cargo_items"] == []
    assert empty.get_json()["cargo_items"] == []
    with cargo_app.app_context():
        assert ShipmentRequest.query.count() == 2
        assert RequestCargoItem.query.count() == 0


def test_one_and_multiple_items_round_trip_identity_order_and_exact_quantity(cargo_app):
    client = cargo_app.test_client()
    one = client.post("/api/shipment-request", json=_payload(cargo_items=[
        {"description": " Medical devices "},
    ]))
    assert one.status_code == 201
    assert one.get_json()["cargo_items"][0]["description"] == "Medical devices"

    multiple = client.post("/api/shipment-request", json=_payload(cargo_items=[
        {"description": "Two boxed pumps"},
        {"cargo_type_public_id": CARGO_TYPE_ID},
        {"quantity": "3.250000", "uom_public_id": UOM_ID},
    ]))
    assert multiple.status_code == 201
    items = multiple.get_json()["cargo_items"]
    assert [item["position"] for item in items] == [1, 2, 3]
    assert len({item["public_id"] for item in items}) == 3
    assert items[0]["description"] == "Two boxed pumps"
    assert items[1]["cargo_type"]["code"] == "GENERAL_GOODS"
    assert items[2]["quantity"] == "3.250000"
    assert items[2]["uom"]["symbol"] == "kg"

    with cargo_app.app_context():
        request_row = db.session.get(ShipmentRequest, multiple.get_json()["id"])
        assert [item.public_id for item in request_row.request_cargo_items] == [
            item["public_id"] for item in items
        ]
        assert request_row.request_cargo_items[2].quantity == Decimal("3.250000")


@pytest.mark.parametrize(
    ("cargo_items", "field", "code"),
    [
        (None, "cargo_items", "INVALID_TYPE"),
        ({}, "cargo_items", "INVALID_TYPE"),
        ([{}], "cargo_items[0]", "ITEM_EMPTY"),
        ([{"public_id": "client"}], "cargo_items[0].public_id", "UNKNOWN_FIELD"),
        ([{"quantity": 1, "uom_public_id": UOM_ID}], "cargo_items[0].quantity", "INVALID_TYPE"),
        ([{"quantity": "1"}], "cargo_items[0].uom_public_id", "QUANTITY_UOM_PAIR_REQUIRED"),
        ([{"uom_public_id": UOM_ID}], "cargo_items[0].quantity", "QUANTITY_UOM_PAIR_REQUIRED"),
        ([{"quantity": "1.0000001", "uom_public_id": UOM_ID}], "cargo_items[0].quantity", "DECIMAL_SCALE_EXCEEDED"),
        ([{"quantity": "1234567890123", "uom_public_id": UOM_ID}], "cargo_items[0].quantity", "DECIMAL_PRECISION_EXCEEDED"),
        ([{"quantity": "1e3", "uom_public_id": UOM_ID}], "cargo_items[0].quantity", "DECIMAL_FORMAT_INVALID"),
        ([{"quantity": "0", "uom_public_id": UOM_ID}], "cargo_items[0].quantity", "MUST_BE_POSITIVE"),
        ([{"cargo_type_public_id": "not-found"}], "cargo_items[0].cargo_type_public_id", "REFERENCE_NOT_FOUND"),
        ([{"cargo_type_public_id": INACTIVE_CARGO_TYPE_ID}], "cargo_items[0].cargo_type_public_id", "REFERENCE_INACTIVE"),
    ],
)
def test_invalid_voluntary_item_returns_indexed_422_and_is_atomic(
    cargo_app, cargo_items, field, code
):
    response = cargo_app.test_client().post(
        "/api/shipment-request", json=_payload(cargo_items=cargo_items)
    )
    assert response.status_code == 422
    body = response.get_json()
    assert body["error"]["code"] == "REQUEST_CARGO_VALIDATION_FAILED"
    assert any(error["field"] == field and error["code"] == code for error in body["error"]["fields"])
    with cargo_app.app_context():
        assert ShipmentRequest.query.count() == 0
        assert RequestCargoItem.query.count() == 0


def test_legacy_and_structured_cargo_are_preserved_independently(cargo_app):
    response = cargo_app.test_client().post("/api/shipment-request", json=_payload(
        cargo_description="Legacy scalar",
        cargo_weight="12.5",
        cargo_items=[{"description": "Structured item"}],
    ))
    assert response.status_code == 201
    with cargo_app.app_context():
        row = db.session.get(ShipmentRequest, response.get_json()["id"])
        assert row.cargo_description == "Legacy scalar"
        assert row.cargo_weight == 12.5
        assert [item.description for item in row.request_cargo_items] == ["Structured item"]


def test_reference_options_are_active_safe_and_deterministic(cargo_app):
    response = cargo_app.test_client().get("/api/request-cargo-options")
    assert response.status_code == 200
    body = response.get_json()
    assert body == {
        "cargo_types": [{
            "public_id": CARGO_TYPE_ID,
            "code": "GENERAL_GOODS",
            "fa_name": "کالای عمومی",
            "en_name": "General goods",
        }],
        "uoms": [{
            "public_id": UOM_ID,
            "code": "KG",
            "fa_name": "کیلوگرم",
            "en_name": "Kilogram",
            "symbol": "kg",
            "measurement_dimension": "WEIGHT",
        }],
    }
    assert "id" not in body["cargo_types"][0]
    assert "catalog" not in str(body).lower()


def test_customer_parent_ownership_fences_cargo_read(cargo_app):
    with cargo_app.app_context():
        owner = CustomerGamification(email="owner@example.test", phone="09120000001")
        other = CustomerGamification(email="other@example.test", phone="09120000002")
        db.session.add_all([owner, other])
        db.session.commit()
        owner_id, other_id = owner.id, other.id

    created = cargo_app.test_client().post("/api/shipment-request", json=_payload(
        gamification_customer_id=owner_id,
        cargo_items=[{"description": "Owned cargo"}],
    ))
    request_id = created.get_json()["id"]
    owner_read = cargo_app.test_client().get(
        f"/api/customer/workflow/{owner_id}?request_id={request_id}"
    )
    other_read = cargo_app.test_client().get(
        f"/api/customer/workflow/{other_id}?request_id={request_id}"
    )
    assert owner_read.status_code == 200
    assert owner_read.get_json()["cargo_items"][0]["description"] == "Owned cargo"
    assert other_read.status_code == 404
    assert cargo_app.test_client().get(
        f"/api/request-cargo-item/{created.get_json()['cargo_items'][0]['public_id']}"
    ).status_code == 404


def test_public_tracking_does_not_gain_structured_cargo(cargo_app):
    created = cargo_app.test_client().post("/api/shipment-request", json=_payload(
        cargo_items=[{"description": "Private structured cargo"}],
    )).get_json()
    tracked = cargo_app.test_client().get(f"/api/public/track/{created['tracking_code']}")
    assert tracked.status_code == 200
    assert "cargo_items" not in tracked.get_json()
