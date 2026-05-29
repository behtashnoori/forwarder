"""Characterization tests for public shipment request endpoints."""
from __future__ import annotations

import pytest
from datetime import datetime, timedelta

from backend import create_app
from backend.extensions import db
from backend.models import ShipmentRequest, ShipmentRequestLog, TransportMethod


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
        "pickup_date": "2099-06-01",
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


def test_create_domestic_shipment_request_preserves_response_defaults_and_commit(shipment_app, client):
    """Domestic POST /api/shipment-request keeps response, normalization, defaults, and log creation."""
    response = client.post("/api/shipment-request", json=_domestic_payload())

    assert response.status_code == 201
    data = response.get_json()
    assert set(data.keys()) == {"message", "id", "tracking_code"}
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
        assert shipment_request.pickup_date.isoformat() == "2099-06-01"
        assert shipment_request.delivery_date is None
        assert shipment_request.status_request_status == "new"
        assert shipment_request.status == "new"
        assert shipment_request.assigned_to is None
        assert shipment_request.has_unread_for_assignee is True
        assert shipment_request.priority == "normal"
        assert shipment_request.sla_due_at is None
        assert shipment_request.tracking_code == data["tracking_code"]

        log_entry = ShipmentRequestLog.query.filter_by(shipment_request_id=data["id"]).one()
        assert log_entry.note == "ثبت اولیه درخواست"


def test_public_shipment_request_sla_defaults_contract(shipment_app, client):
    """Public shipment creation keeps current SLA/priority defaults without persisted sla_status."""
    response = client.post("/api/shipment-request", json=_domestic_payload())

    assert response.status_code == 201
    request_id = response.get_json()["id"]

    with shipment_app.app_context():
        shipment_request = db.session.get(ShipmentRequest, request_id)
        assert shipment_request.priority == "normal"
        assert shipment_request.sla_due_at is None
        assert shipment_request.status == "new"
        assert shipment_request.status_request_status == "new"
        assert "sla_status" not in ShipmentRequest.__table__.columns.keys()


def test_public_shipment_request_without_pickup_date_keeps_normal_priority_contract(shipment_app, client):
    """No-date public shipment creation keeps normal priority and response shape."""
    response = client.post("/api/shipment-request", json=_domestic_payload(pickup_date=None))

    assert response.status_code == 201
    assert set(response.get_json().keys()) == {"message", "id", "tracking_code"}

    with shipment_app.app_context():
        shipment_request = db.session.get(ShipmentRequest, response.get_json()["id"])
        assert shipment_request.pickup_date is None
        assert shipment_request.priority == "normal"


def test_public_shipment_request_near_pickup_date_sets_automatic_priority_contract(shipment_app, client):
    """Public shipment creation assigns initial priority from pickup date urgency."""
    urgent_date = datetime.utcnow().date().isoformat()
    high_date = (datetime.utcnow() + timedelta(hours=48)).date().isoformat()

    urgent_response = client.post("/api/shipment-request", json=_domestic_payload(pickup_date=urgent_date))
    high_response = client.post("/api/shipment-request", json=_domestic_payload(pickup_date=high_date))

    assert urgent_response.status_code == 201
    assert high_response.status_code == 201
    assert set(urgent_response.get_json().keys()) == {"message", "id", "tracking_code"}
    assert set(high_response.get_json().keys()) == {"message", "id", "tracking_code"}

    with shipment_app.app_context():
        urgent_request = db.session.get(ShipmentRequest, urgent_response.get_json()["id"])
        high_request = db.session.get(ShipmentRequest, high_response.get_json()["id"])
        assert urgent_request.priority == "urgent"
        assert high_request.priority == "high"


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
    assert set(data.keys()) == {"message", "id", "tracking_code"}

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
