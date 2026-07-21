"""Contract tests for the structured Iran destination point."""
import pytest

from backend import create_app
from backend.extensions import db
from backend.models import (
    City,
    Country,
    County,
    CustomsOffice,
    IranPort,
    Province,
    ShipmentRequest,
)


@pytest.fixture()
def app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def _geography():
    country = Country(code="IR", name_en="Iran", name_fa="ایران")
    province = Province(code="WAZ", name_fa="آذربایجان غربی")
    db.session.add_all([country, province])
    db.session.flush()
    county = County(name_fa="ماکو", province_id=province.id)
    db.session.add(county)
    db.session.flush()
    city = City(name_fa="ماکو", province_id=province.id, county_id=county.id)
    port = IranPort(name_fa="بندرعباس", name_en="Bandar Abbas", port_type="sea", province_id=province.id)
    customs = CustomsOffice(
        code="IRBZG", name_fa="گمرک بازرگان", name_en="Bazargan",
        customs_type="road_border", country_id=country.id, province_id=province.id,
    )
    db.session.add_all([city, port, customs])
    db.session.commit()
    return province, county, city, port, customs


def _base_payload(**overrides):
    payload = {
        "shipping_type": "international",
        "origin_country": "Germany",
        "origin_city_international": "Hamburg",
        "dest_country": "ایران",
        "dest_city_international": "Tehran",
        "contact_phone": "09121234567",
        "international_transport_method": "sea",
    }
    payload.update(overrides)
    return payload


def test_border_customs_endpoint_returns_only_border_offices(app, client):
    with app.app_context():
        _geography()
        # An inland office must not appear among border destinations.
        country = Country.query.filter_by(code="IR").first()
        db.session.add(CustomsOffice(
            code="IRINL", name_fa="گمرک داخلی", name_en="Inland",
            customs_type="inland", country_id=country.id,
        ))
        db.session.commit()

    response = client.get("/api/border-customs")
    assert response.status_code == 200
    data = response.get_json()
    codes = {row["name_en"] for row in data}
    assert "Bazargan" in codes
    assert "Inland" not in codes
    bazargan = next(row for row in data if row["name_en"] == "Bazargan")
    assert bazargan["province_name"] == "آذربایجان غربی"


def test_city_destination_persists_structured_fields(app, client):
    with app.app_context():
        province, county, city, _port, _customs = _geography()
        province_id, city_id = province.id, city.id

    response = client.post("/api/shipment-request", json=_base_payload(
        iran_dest_type="city",
        iran_dest_city_id=city_id,
        iran_entry_province_id=province_id,
    ))
    assert response.status_code == 201
    with app.app_context():
        req = ShipmentRequest.query.first()
        assert req.iran_dest_type == "city"
        assert req.iran_dest_city_id == city_id
        assert req.iran_entry_province_id == province_id


def test_customs_destination_persists_structured_fields(app, client):
    with app.app_context():
        province, _county, _city, _port, customs = _geography()
        province_id, customs_id = province.id, customs.id

    response = client.post("/api/shipment-request", json=_base_payload(
        iran_dest_type="customs",
        iran_dest_customs_office_id=customs_id,
        iran_entry_province_id=province_id,
    ))
    assert response.status_code == 201
    with app.app_context():
        req = ShipmentRequest.query.first()
        assert req.iran_dest_type == "customs"
        assert req.iran_dest_customs_office_id == customs_id


def test_port_destination_persists_structured_fields(app, client):
    with app.app_context():
        province, _county, _city, port, _customs = _geography()
        province_id, port_id = province.id, port.id

    response = client.post("/api/shipment-request", json=_base_payload(
        iran_dest_type="port",
        iran_entry_port_id=port_id,
        iran_entry_province_id=province_id,
    ))
    assert response.status_code == 201
    with app.app_context():
        req = ShipmentRequest.query.first()
        assert req.iran_dest_type == "port"
        assert req.iran_entry_port_id == port_id


def test_missing_reference_for_declared_type_is_rejected(app, client):
    with app.app_context():
        province, _county, _city, _port, _customs = _geography()
        province_id = province.id

    response = client.post("/api/shipment-request", json=_base_payload(
        iran_dest_type="city",
        iran_entry_province_id=province_id,
    ))
    assert response.status_code == 400


def test_route_payload_surfaces_international_and_iran_destination(app):
    """Regression: expert/admin route payload must not show international as «نامشخص»."""
    from backend.models import ShipmentRequest
    from backend.services.route_payload_service import build_route_payload

    with app.app_context():
        province, _county, _city, _port, customs = _geography()
        req = ShipmentRequest(
            shipping_type="international",
            origin_country="آلمان",
            origin_city_international="هامبورگ",
            dest_country="ایران",
            dest_city_international="تهران",
            contact_phone="09121234567",
            iran_dest_type="customs",
            iran_dest_customs_office_id=customs.id,
            iran_entry_province_id=province.id,
        )
        db.session.add(req)
        db.session.commit()

        route = build_route_payload(req)
        assert route["shipping_type"] == "international"
        assert route["origin"]["country"] == "آلمان"
        assert route["origin"]["international_city"] == "هامبورگ"
        assert route["destination"]["country"] == "ایران"
        # Domestic slots stay empty for an international shipment (never «نامشخص» in country slot).
        assert route["origin"]["province"] is None
        assert route["iran_destination"] == {
            "type": "customs",
            "label": "گمرک بازرگان",
            "province": "آذربایجان غربی",
        }


def test_legacy_international_without_dest_type_still_succeeds(app, client):
    """Payloads that never declare iran_dest_type keep working unchanged."""
    with app.app_context():
        _geography()

    response = client.post("/api/shipment-request", json=_base_payload())
    assert response.status_code == 201
    with app.app_context():
        req = ShipmentRequest.query.first()
        assert req.iran_dest_type is None
