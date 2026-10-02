"""HW_GEO_009 Customer Request location contract regression proof."""
from __future__ import annotations

import pytest

from backend import create_app
from backend.extensions import db
from backend.geonames_geography_catalog import DATASET_ID
from backend.models import City, Country, InternationalCity, Province, ShipmentRequest
from backend.operational_models import CanonicalLocation
from backend.services.logistics_network_service import canonical_cities
from backend.services.route_payload_service import build_route_payload
from backend.services.shipment_service import ShipmentValidationError, normalize_shipment_payload


@pytest.fixture()
def location_app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "SECRET_KEY": "geo-009"}, skip_startup=True)
    with app.app_context():
        db.create_all()
        iran = Country(code="IR", name_en="Iran", name_fa="ایران", is_active=True)
        china = Country(code="CN", name_en="China", name_fa="چین", is_active=True)
        brazil = Country(code="BR", name_en="Brazil", name_fa="برزیل", is_active=True)
        db.session.add_all([iran, china, brazil]); db.session.flush()
        tehran = Province(code="26", name_fa="تهران", name_en="Tehran", geoname_id=110791, country_id=iran.id, dataset_id=DATASET_ID, is_active=True)
        esfahan = Province(code="04", name_fa="اصفهان", name_en="Isfahan", geoname_id=418862, country_id=iran.id, dataset_id=DATASET_ID, is_active=True)
        hormozgan = Province(code="11", name_fa="هرمزگان", name_en="Hormozgan", geoname_id=131222, country_id=iran.id, dataset_id=DATASET_ID, is_active=True)
        beijing = Province(code="22", name_fa="پکن", name_en="Beijing", geoname_id=2038349, country_id=china.id, dataset_id=DATASET_ID, is_active=True)
        db.session.add_all([tehran, esfahan, hormozgan, beijing]); db.session.flush()
        cities = [
            City(code="112931", name_fa="تهران", name_en="Tehran", geoname_id=112931, country_id=iran.id, province_id=tehran.id, dataset_id=DATASET_ID, is_active=True, aliases=["Teheran"]),
            City(code="418863", name_fa="اصفهان", name_en="Isfahan", geoname_id=418863, country_id=iran.id, province_id=esfahan.id, dataset_id=DATASET_ID, is_active=True, aliases=["Esfahan", "اصفهان"]),
            City(code="141681", name_fa="بندرعباس", name_en="Bandar Abbas", geoname_id=141681, country_id=iran.id, province_id=hormozgan.id, dataset_id=DATASET_ID, is_active=True),
            City(code="999001", name_fa="اصفهانک", name_en="Esfahanak", geoname_id=999001, country_id=iran.id, province_id=esfahan.id, dataset_id=DATASET_ID, is_active=True),
            City(code="1816670", name_fa="پکن", name_en="Beijing", geoname_id=1816670, country_id=china.id, province_id=beijing.id, dataset_id=DATASET_ID, is_active=True),
        ]
        db.session.add_all(cities); db.session.flush()
        legacy = [
            InternationalCity(name_en="Bandar Abbas", name_fa="بندرعباس", country_id=iran.id, city_type="city", un_locode="IRBND", is_active=True),
            InternationalCity(name_en="Tehran", name_fa="تهران", country_id=iran.id, city_type="city", un_locode="IRTHR", is_active=True),
            InternationalCity(name_en="Imam Khomeini Airport", name_fa="فرودگاه امام خمینی", country_id=iran.id, city_type="airport", un_locode="IRIKA", is_active=True),
        ]
        db.session.add_all(legacy); db.session.commit()
        ids = {
            "ir": iran.id, "cn": china.id, "br": brazil.id,
            "tehran": cities[0].id, "isfahan": cities[1].id,
            "bandar": cities[2].id, "beijing": cities[4].id,
            "legacy_tehran": legacy[1].id, "airport": legacy[2].id,
        }
        yield app, ids
        db.session.remove(); db.drop_all()


def _payload(ids, origin, destination, *, origin_country=None, dest_country=None):
    return {
        "shipping_type": "international",
        "contact_phone": "09123456789",
        "transport_method_preference": "forwarder_suggestion",
        "origin_country_id": origin_country or ids["cn"],
        "dest_country_id": dest_country or ids["ir"],
        "origin_location": origin,
        "destination_location": destination,
    }


def test_canonical_city_and_declared_place_normalize_without_materializing_location(location_app):
    app, ids = location_app
    with app.app_context():
        before = CanonicalLocation.query.count()
        normalized = normalize_shipment_payload(_payload(
            ids,
            {"kind": "canonical_city", "source_id": ids["beijing"]},
            {"kind": "declared", "description": "  انبار مشتری در سائوپائولو  "},
            dest_country=ids["br"],
        ))
        assert normalized["origin_city_id"] == ids["beijing"]
        assert normalized["origin_international_city_id"] is None
        assert normalized["dest_city_id"] is None
        assert normalized["dest_international_city_id"] is None
        assert normalized["dest_city_international"] == "انبار مشتری در سائوپائولو"
        assert CanonicalLocation.query.count() == before


def test_typed_physical_reference_is_distinct_from_canonical_city(location_app):
    app, ids = location_app
    with app.app_context():
        normalized = normalize_shipment_payload(_payload(
            ids,
            {"kind": "canonical_city", "source_id": ids["beijing"]},
            {"kind": "physical_reference", "source_id": ids["airport"]},
        ))
        assert normalized["dest_city_id"] is None
        assert normalized["dest_international_city_id"] == ids["airport"]


@pytest.mark.parametrize("destination,code", [
    ({"kind": "declared", "description": "   "}, "DECLARED_PLACE_REQUIRED"),
    ({"kind": "canonical_city", "source_id": 999999}, "LOCATION_COUNTRY_MISMATCH"),
])
def test_invalid_declared_or_unknown_city_is_rejected(location_app, destination, code):
    app, ids = location_app
    with app.app_context(), pytest.raises(ShipmentValidationError) as exc:
        normalize_shipment_payload(_payload(ids, {"kind": "canonical_city", "source_id": ids["beijing"]}, destination))
    assert exc.value.code == code


def test_cross_country_city_and_legacy_city_type_are_rejected(location_app):
    app, ids = location_app
    with app.app_context():
        with pytest.raises(ShipmentValidationError) as cross:
            normalize_shipment_payload(_payload(ids, {"kind": "canonical_city", "source_id": ids["tehran"]}, {"kind": "canonical_city", "source_id": ids["isfahan"]}))
        assert cross.value.code == "LOCATION_COUNTRY_MISMATCH"
        with pytest.raises(ShipmentValidationError) as wrong_type:
            normalize_shipment_payload(_payload(ids, {"kind": "canonical_city", "source_id": ids["beijing"]}, {"kind": "physical_reference", "source_id": ids["legacy_tehran"]}))
        assert wrong_type.value.code == "LOCATION_TYPE_MISMATCH"


def test_country_city_search_pages_and_prioritizes_exact_normalized_match(location_app):
    app, _ = location_app
    with app.app_context():
        first = canonical_cities({"country_code": "IR", "q": "اصفهان", "limit": 1, "offset": 0})
        second = canonical_cities({"country_code": "IR", "q": "اصفهان", "limit": 1, "offset": 1})
        alternate = canonical_cities({"country_code": "IR", "q": "Esfahan", "limit": 20, "offset": 0})
        assert first["items"][0]["name_en"] == "Isfahan"
        assert first["has_more"] is True
        assert second["items"][0]["name_en"] == "Esfahanak"
        assert alternate["items"][0]["name_en"] == "Isfahan"


def test_read_projection_distinguishes_reference_declared_and_historical(location_app):
    app, ids = location_app
    with app.app_context():
        canonical = ShipmentRequest(shipping_type="international", contact_phone="09123456789", origin_country_id=ids["cn"], origin_city_id=ids["beijing"], origin_city_international="پکن", dest_country_id=ids["ir"], dest_city_id=ids["bandar"], dest_city_international="بندرعباس")
        declared = ShipmentRequest(shipping_type="international", contact_phone="09123456789", origin_country_id=ids["cn"], origin_city_id=ids["beijing"], origin_city_international="پکن", dest_country_id=ids["br"], dest_city_international="Santos customer yard")
        historical = ShipmentRequest(shipping_type="international", contact_phone="09123456789", origin_country_id=ids["ir"], origin_international_city_id=ids["legacy_tehran"], origin_city_international="تهران", dest_country_id=ids["ir"], dest_international_city_id=ids["airport"], dest_city_international="فرودگاه امام خمینی")
        db.session.add_all([canonical, declared, historical]); db.session.flush()
        canonical_route = build_route_payload(canonical)
        declared_route = build_route_payload(declared)
        historical_route = build_route_payload(historical)
        assert canonical_route["origin"]["selection_kind"] == "canonical_city"
        assert canonical_route["location_state"] == "canonical"
        assert declared_route["destination"]["resolution_state"] == "requires_expert_review"
        assert declared_route["location_state"] == "customer_declared"
        assert historical_route["origin"]["selection_kind"] == "legacy_reference"
        assert historical_route["destination"]["selection_kind"] == "physical_reference"


def test_public_submission_persists_declared_place_without_creating_operations(location_app):
    app, ids = location_app
    response = app.test_client().post("/api/shipment-request", json=_payload(
        ids,
        {"kind": "canonical_city", "source_id": ids["beijing"]},
        {"kind": "declared", "description": "Santos customer warehouse"},
        dest_country=ids["br"],
    ))
    assert response.status_code == 201
    with app.app_context():
        row = db.session.get(ShipmentRequest, response.get_json()["id"])
        assert row.origin_city_id == ids["beijing"]
        assert row.dest_city_id is None and row.dest_international_city_id is None
        assert row.dest_city_international == "Santos customer warehouse"
        assert build_route_payload(row)["destination"]["selection_label"] == "محل اعلام‌شده مشتری؛ هنوز به مکان مرجع متصل نیست"
        from backend.operational_models import OperationalShipment
        assert OperationalShipment.query.count() == 0

