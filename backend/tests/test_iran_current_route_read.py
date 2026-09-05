"""Current Iran geography and historical destination read compatibility."""
import pytest

from backend.tests.test_governed_international_geography import app, _seed
from backend.tests.test_iran_destination_point import _geography
from backend.extensions import db
from backend.models import Country, InternationalCity, ShipmentRequest
from backend.services.route_payload_service import build_route_payload


def references(app):
    iran, other = _seed(app)
    city = InternationalCity.query.filter_by(country_id=iran, un_locode="IRTHR").one()
    other_city = InternationalCity.query.filter_by(country_id=other).first()
    return iran, city.id, other, other_city.id


@pytest.mark.parametrize("iran_origin,iran_destination", [(False, True), (True, True), (True, False), (False, False)])
def test_current_write_read(app, iran_origin, iran_destination):
    iran, city, other, other_city = references(app)
    response = app.test_client().post("/api/shipment-request", json={
        "shipping_type": "international", "contact_phone": "09123456789",
        "origin_country_id": iran if iran_origin else other,
        "origin_international_city_id": city if iran_origin else other_city,
        "dest_country_id": iran if iran_destination else other,
        "dest_international_city_id": city if iran_destination else other_city,
    })
    assert response.status_code == 201, response.json
    row = ShipmentRequest.query.one()
    route = build_route_payload(row)
    assert route["location_state"] == "canonical"
    assert route["iran_destination"] is None
    assert route["canonical_ids"]["dest_international_city_id"] == (city if iran_destination else other_city)
    assert route["destination"]["international_city"] != "نامشخص"


@pytest.mark.parametrize("invalid", ["missing", "inactive", "mismatched"])
def test_current_iran_invalid_city_rejected(app, invalid):
    iran, city, other, other_city = references(app)
    if invalid == "inactive":
        db.session.get(InternationalCity, city).is_active = False
        db.session.commit()
    destination = {"missing": 999999, "inactive": city, "mismatched": other_city}[invalid]
    response = app.test_client().post("/api/shipment-request", json={
        "shipping_type": "international", "contact_phone": "09123456789",
        "origin_country_id": other, "origin_international_city_id": other_city,
        "dest_country_id": iran, "dest_international_city_id": destination,
    })
    assert response.status_code in (400, 404, 422)
    assert ShipmentRequest.query.count() == 0


@pytest.mark.parametrize("city_kind", ["missing", "mismatched"])
def test_read_does_not_mark_invalid_current_iran_identity_complete(app, city_kind):
    iran, city, other, other_city = references(app)
    row = ShipmentRequest(shipping_type="international", origin_country_id=other,
                          origin_international_city_id=other_city, dest_country_id=iran,
                          dest_international_city_id=999999 if city_kind == "missing" else other_city)
    assert build_route_payload(row)["location_state"] == "legacy_incomplete"


def test_deactivation_does_not_erase_historical_current_identity(app):
    iran, city, other, other_city = references(app)
    db.session.get(InternationalCity, city).is_active = False
    row = ShipmentRequest(shipping_type="international", origin_country_id=other,
                          origin_international_city_id=other_city, dest_country_id=iran,
                          dest_international_city_id=city)
    route = build_route_payload(row)
    assert route["location_state"] == "canonical"
    assert route["destination"]["international_city"] == "تهران"


@pytest.mark.parametrize("kind", ["city", "port", "customs"])
def test_legacy_typed_iran_read_preserves_destination(app, kind):
    province, county, city, port, customs = _geography()
    iran = Country.query.filter_by(code="IR").one()
    other = Country(code="TR", name_en="Turkey", name_fa="ترکیه")
    db.session.add(other)
    db.session.flush()
    other_city = InternationalCity(country_id=other.id, name_en="Istanbul", name_fa="استانبول")
    db.session.add(other_city)
    db.session.flush()
    selected = {"city": city, "port": port, "customs": customs}[kind]
    field = {"city": "iran_dest_city_id", "port": "iran_entry_port_id", "customs": "iran_dest_customs_office_id"}[kind]
    row = ShipmentRequest(shipping_type="international", origin_country_id=other.id,
                          origin_international_city_id=other_city.id, dest_country_id=iran.id,
                          iran_dest_type=kind, iran_entry_province_id=province.id,
                          **{field: selected.id})
    route = build_route_payload(row)
    assert route["location_state"] == "canonical"
    assert route["iran_destination"] == {"type": kind, "label": selected.name_fa, "province": province.name_fa}
