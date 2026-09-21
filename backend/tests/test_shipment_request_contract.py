"""Characterization tests for public shipment request endpoints."""
from __future__ import annotations

from uuid import UUID

import pytest

from backend import create_app
from backend.extensions import db
from backend.models import ShipmentRequest, ShipmentRequestLog, TransportMethod
from backend.operational_models import RoutePlan
from backend.request_transport_catalog import COMBINED_TRANSPORT_CODE


@pytest.fixture
def shipment_app():
    """App with isolated test DB for shipment request contracts."""
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "test-secret",
    }, skip_startup=True)
    with app.app_context():
        db.create_all()
    return app


@pytest.fixture
def client(shipment_app):
    return shipment_app.test_client()


def _domestic_payload(**overrides):
    payload = {
        "shipping_type": "domestic",
        "origin_province_id": "1",
        "origin_county_id": "2",
        "origin_city_id": "3",
        "dest_province_id": "4",
        "dest_county_id": "5",
        "dest_city_id": "6",
        "contact_phone": "09123456789",
        "customer_first_name": " Ali ",
        "customer_last_name": " Rahimi ",
        "shipment_mode": " Road Transport ",
        "domestic_transport_method": "road",
        "transport_method_preference": "invalid-preference",
        "cargo_description": " Test cargo ",
        "cargo_weight": "12.5",
        "cargo_volume": "bad-volume",
        "cargo_value": "5000",
        "special_instructions": " Keep dry ",
        "pickup_date": "2026-06-01",
        "delivery_date": "bad-date",
    }
    payload.update(overrides)
    return payload


def _international_payload(**overrides):
    payload = {
        "shipping_type": "international",
        "origin_country": " Germany ",
        "origin_city_international": " Hamburg ",
        "origin_address_international": " Origin address ",
        "dest_country": " Iran ",
        "dest_city_international": " Tehran ",
        "dest_address_international": " Destination address ",
        "contact_phone": "09123456789",
        "transport_method": " Sea Freight ",
        "international_transport_method": "sea",
        "transport_method_preference": "forwarder_suggestion",
    }
    payload.update(overrides)
    return payload


def test_transport_methods_contract_and_grouping(shipment_app):
    """GET /api/transport-methods keeps current grouped response shape."""
    with shipment_app.app_context():
        db.session.add_all([
            TransportMethod(name="Sea Freight", name_fa="حمل دریایی", description="دریایی", is_active=True),
            TransportMethod(name="Road Transport", name_fa="حمل جاده‌ای", description="جاده‌ای", is_active=True),
            TransportMethod(name="Custom Method", name_fa="روش سفارشی", description="سفارشی", is_active=True),
            TransportMethod(name="Inactive Method", name_fa="غیرفعال", description="نباید برگردد", is_active=False),
        ])
        db.session.commit()

    response = shipment_app.test_client().get("/api/transport-methods")

    assert response.status_code == 200
    data = response.get_json()
    assert set(data.keys()) == {"international_methods", "domestic_methods", "preference_options"}
    assert data["preference_options"] == [
        {"value": "customer_choice", "label": "انتخاب مشتری", "description": "مشتری روش حمل را انتخاب می‌کند"},
        {"value": "forwarder_suggestion", "label": "پیشنهاد فورواردر", "description": "فورواردر بهترین روش را پیشنهاد می‌دهد"},
    ]
    assert {method["name"] for method in data["international_methods"]} == {"Sea Freight", "Custom Method"}
    assert {method["name"] for method in data["domestic_methods"]} == {"Road Transport", "Custom Method"}


def test_combined_transport_catalog_is_one_deterministic_choice_for_both_scopes(shipment_app):
    with shipment_app.app_context():
        db.session.add_all([
            TransportMethod(name=COMBINED_TRANSPORT_CODE, name_fa="حمل ترکیبی", description="canonical", is_active=True),
            TransportMethod(name=COMBINED_TRANSPORT_CODE, name_fa="برچسب تکراری", description="duplicate", is_active=True),
            TransportMethod(name="Rail Transport", name_fa="حمل ریلی", description="rail", is_active=True),
            TransportMethod(name="Rail Transport", name_fa="ریل تکراری", description="duplicate", is_active=True),
        ])
        db.session.commit()

    data = shipment_app.test_client().get("/api/transport-methods").get_json()
    for scope in ("domestic_methods", "international_methods"):
        names = [method["name"] for method in data[scope]]
        assert names.count(COMBINED_TRANSPORT_CODE) == 1
        assert names.count("Rail Transport") == 1
        combined = next(method for method in data[scope] if method["name"] == COMBINED_TRANSPORT_CODE)
        assert combined["name_fa"] == "حمل ترکیبی"


def test_combined_transport_round_trips_with_zero_and_multiple_optional_cargo(shipment_app, client):
    with shipment_app.app_context():
        db.session.add(TransportMethod(
            name=COMBINED_TRANSPORT_CODE,
            name_fa="حمل ترکیبی",
            description="Customer intent only",
            is_active=True,
        ))
        db.session.commit()

    zero = client.post(
        "/api/shipment-request",
        json=_domestic_payload(
            shipment_mode="",
            domestic_transport_method=COMBINED_TRANSPORT_CODE,
            cargo_items=[],
        ),
    )
    multiple = client.post(
        "/api/shipment-request",
        json=_domestic_payload(
            shipment_mode="",
            domestic_transport_method=COMBINED_TRANSPORT_CODE,
            cargo_items=[
                {"description": "Medical devices"},
                {"description": "Precision cargo"},
            ],
        ),
    )

    assert zero.status_code == 201
    assert multiple.status_code == 201
    assert zero.get_json()["request_transport_intent"] == COMBINED_TRANSPORT_CODE
    assert multiple.get_json()["request_transport_intent"] == COMBINED_TRANSPORT_CODE
    assert zero.get_json()["cargo_items"] == []
    assert [item["description"] for item in multiple.get_json()["cargo_items"]] == [
        "Medical devices",
        "Precision cargo",
    ]

    with shipment_app.app_context():
        rows = ShipmentRequest.query.order_by(ShipmentRequest.id).all()
        assert [row.domestic_transport_method for row in rows] == [
            COMBINED_TRANSPORT_CODE,
            COMBINED_TRANSPORT_CODE,
        ]
        assert RoutePlan.query.count() == 0


def test_request_transport_rejects_unsupported_or_inactive_values(shipment_app, client):
    with shipment_app.app_context():
        db.session.add(TransportMethod(
            name="Inactive Method",
            name_fa="غیرفعال",
            is_active=False,
        ))
        db.session.commit()

    for value in ("arbitrary-unsupported", "Inactive Method", "combined_transport"):
        response = client.post(
            "/api/shipment-request",
            json=_domestic_payload(shipment_mode="", domestic_transport_method=value),
        )
        assert response.status_code == 400
        assert response.get_json()["error"] == {
            "code": "REQUEST_TRANSPORT_INVALID",
            "message": "روش حمل انتخاب‌شده پشتیبانی نمی‌شود.",
            "fields": [{
                "field": "domestic_transport_method",
                "code": "UNSUPPORTED_VALUE",
                "message": "Transport method is not supported.",
            }],
        }


def test_create_domestic_shipment_request_preserves_response_defaults_and_commit(shipment_app, client):
    """Domestic POST /api/shipment-request keeps response, normalization, defaults, and log creation."""
    response = client.post("/api/shipment-request", json=_domestic_payload())

    assert response.status_code == 201
    data = response.get_json()
    assert set(data.keys()) == {"message", "id", "tracking_code", "request_transport_intent", "cargo_items"}
    assert data["request_transport_intent"] == "road"
    assert data["cargo_items"] == []
    assert "public_id" not in data
    assert data["message"] == "درخواست شما ثبت شد. کارشناسان ما ظرف دو ساعت با شما تماس خواهند گرفت."
    assert data["tracking_code"].startswith("SR")

    with shipment_app.app_context():
        shipment_request = db.session.get(ShipmentRequest, data["id"])
        assert shipment_request is not None
        assert shipment_request.shipping_type == "domestic"
        assert shipment_request.origin_province_id == 1
        assert shipment_request.dest_city_id == 6
        assert shipment_request.contact_phone == "09123456789"
        assert shipment_request.customer_first_name == "Ali"
        assert shipment_request.customer_last_name == "Rahimi"
        assert shipment_request.transport_method == "road transport"
        assert shipment_request.domestic_transport_method == "road"
        assert shipment_request.international_transport_method is None
        assert shipment_request.transport_method_preference == "customer_choice"
        assert shipment_request.cargo_description == "Test cargo"
        assert shipment_request.cargo_weight == 12.5
        assert shipment_request.cargo_volume is None
        assert shipment_request.cargo_value == 5000.0
        assert shipment_request.special_instructions == "Keep dry"
        assert shipment_request.pickup_date.isoformat() == "2026-06-01"
        assert shipment_request.delivery_date is None
        assert shipment_request.status == "new"
        # Legacy compatibility field remains creation-only and is not operational lifecycle state.
        assert shipment_request.status_request_status == "new"
        assert shipment_request.assigned_to is None
        assert shipment_request.has_unread_for_assignee is True
        assert shipment_request.priority == "normal"
        assert shipment_request.tracking_code == data["tracking_code"]
        assert UUID(shipment_request.public_id).version == 4
        assert shipment_request.public_id == str(UUID(shipment_request.public_id))

        log_entry = ShipmentRequestLog.query.filter_by(shipment_request_id=data["id"]).one()
        assert log_entry.note == "ثبت اولیه درخواست"


def test_public_create_cannot_choose_shipment_request_public_id(shipment_app, client):
    supplied = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    response = client.post(
        "/api/shipment-request",
        json=_domestic_payload(public_id=supplied),
    )
    assert response.status_code == 201
    data = response.get_json()
    assert "public_id" not in data
    with shipment_app.app_context():
        row = db.session.get(ShipmentRequest, data["id"])
        assert row.public_id != supplied
        assert UUID(row.public_id).version == 4


def test_create_domestic_shipment_request_accepts_province_only_locations(shipment_app, client):
    """Domestic POST /api/shipment-request accepts province-only origin and destination."""
    response = client.post(
        "/api/shipment-request",
        json=_domestic_payload(
            origin_county_id=None,
            origin_city_id=None,
            dest_county_id="",
            dest_city_id="",
        ),
    )

    assert response.status_code == 201
    data = response.get_json()
    assert set(data.keys()) == {"message", "id", "tracking_code", "request_transport_intent", "cargo_items"}
    assert data["request_transport_intent"] == "road"
    assert data["cargo_items"] == []

    with shipment_app.app_context():
        shipment_request = db.session.get(ShipmentRequest, data["id"])
        assert shipment_request.origin_province_id == 1
        assert shipment_request.origin_county_id is None
        assert shipment_request.origin_city_id is None
        assert shipment_request.dest_province_id == 4
        assert shipment_request.dest_county_id is None
        assert shipment_request.dest_city_id is None


def test_create_international_shipment_request_preserves_location_and_transport_behavior(shipment_app, client):
    """International POST /api/shipment-request keeps location trimming and transport behavior."""
    response = client.post("/api/shipment-request", json=_international_payload())

    assert response.status_code == 201
    data = response.get_json()

    with shipment_app.app_context():
        shipment_request = db.session.get(ShipmentRequest, data["id"])
        assert shipment_request.shipping_type == "international"
        assert shipment_request.origin_country == "Germany"
        assert shipment_request.origin_city_international == "Hamburg"
        assert shipment_request.origin_address_international == "Origin address"
        assert shipment_request.dest_country == "Iran"
        assert shipment_request.dest_city_international == "Tehran"
        assert shipment_request.dest_address_international == "Destination address"
        assert shipment_request.origin_province_id is None
        assert shipment_request.dest_city_id is None
        assert shipment_request.transport_method == "sea freight"
        assert shipment_request.international_transport_method == "sea"
        assert shipment_request.transport_method_preference == "forwarder_suggestion"


def test_create_shipment_request_preserves_validation_errors(client):
    """POST /api/shipment-request keeps current validation status codes and error formats."""
    invalid_shipping_type = client.post("/api/shipment-request", json={"shipping_type": "space"})
    assert invalid_shipping_type.status_code == 400
    assert invalid_shipping_type.get_json() == {"message": "نوع ارسال نامعتبر است."}

    invalid_domestic_location = client.post(
        "/api/shipment-request",
        json=_domestic_payload(origin_city_id="not-an-int"),
    )
    assert invalid_domestic_location.status_code == 400
    assert invalid_domestic_location.get_json() == {"message": "اطلاعات مبدا و مقصد داخلی نامعتبر است."}

    invalid_international_location = client.post(
        "/api/shipment-request",
        json=_international_payload(origin_country="   "),
    )
    assert invalid_international_location.status_code == 400
    assert invalid_international_location.get_json() == {"message": "اطلاعات مبدا و مقصد بین‌المللی نامعتبر است."}

    invalid_phone = client.post(
        "/api/shipment-request",
        json=_domestic_payload(contact_phone="123"),
    )
    assert invalid_phone.status_code == 400
    assert invalid_phone.get_json() == {
        "message": "شماره تماس نامعتبر است. لطفاً شماره‌ای با پیش‌شماره 09 و ۱۱ رقم وارد کنید."
    }
