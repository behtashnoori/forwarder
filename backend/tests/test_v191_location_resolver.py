"""Slice 3 canonical location resolver and request contracts."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend import create_app
from backend.extensions import db
from backend.models import (
    City, Country, County, CustomsOffice, ExpertQuote, ExpertUser,
    InternationalCity, IranPort, PortLocation, Province, ShipmentRequest,
)
from backend.operational_models import (
    OperationalMembership, OperationalOrganization, RouteLeg,
)
from backend.services import operational_service
from backend.services.location_resolver import LocationResolutionError, resolve_location
from backend.services.route_payload_service import build_route_payload


@pytest.fixture()
def app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "SECRET_KEY": "slice3"}, skip_startup=True)
    with app.app_context():
        db.create_all()
        iran = Country(code="IR", name_en="Iran", name_fa="Iran")
        de = Country(code="DE", name_en="Germany", name_fa="Germany")
        db.session.add_all([iran, de])
        db.session.flush()
        province = Province(code="THR", name_fa="Tehran", country_id=iran.id)
        other = Province(code="HRM", name_fa="Hormozgan", country_id=iran.id)
        db.session.add_all([province, other])
        db.session.flush()
        county = County(code="THR", name_fa="Tehran County", province_id=province.id)
        other_county = County(code="BND", name_fa="Bandar County", province_id=other.id)
        db.session.add_all([county, other_county])
        db.session.flush()
        city = City(code="THR", name_fa="Duplicate", county_id=county.id, province_id=province.id)
        duplicate = City(code="BND", name_fa="Duplicate", county_id=other_county.id, province_id=other.id)
        inactive = City(code="OFF", name_fa="Inactive", county_id=county.id, province_id=province.id, is_active=False)
        hamburg = InternationalCity(name_en="Hamburg", name_fa="Hamburg", country_id=de.id)
        port = IranPort(code="BND", name_en="Bandar", name_fa="Bandar", port_type="sea", province_id=other.id, country_id=iran.id)
        customs = CustomsOffice(code="BZG", name_en="Border", name_fa="Duplicate", customs_type="road_border", country_id=iran.id, province_id=province.id, county_id=county.id, city_id=city.id)
        incomplete = CustomsOffice(code="BAD", name_en="Bad", name_fa="Bad", customs_type="road_border", country_id=iran.id)
        db.session.add_all([city, duplicate, inactive, hamburg, port, customs, incomplete])
        db.session.flush()
        db.session.add(PortLocation(port_id=port.id, country_id=iran.id, province_id=other.id, location_status="confirmed", is_active=True))
        db.session.commit()
        app.config["geo"] = {
            "IR": iran.id, "DE": de.id, "province": province.id,
            "other_province": other.id, "city": city.id,
            "duplicate_city": duplicate.id, "inactive": inactive.id,
            "port": port.id, "customs": customs.id,
            "incomplete": incomplete.id, "hamburg": hamburg.id,
        }
    yield app


def test_resolver_covers_supported_types_and_ancestry(app):
    with app.app_context():
        ids = app.config["geo"]
        assert resolve_location({"source_type": "city", "source_id": ids["city"]}).province_id == ids["province"]
        assert resolve_location({"source_type": "international_city", "source_id": ids["hamburg"]}).country_code == "DE"
        assert resolve_location({"source_type": "iran_port", "source_id": ids["port"]}).location_type == "port"
        assert resolve_location({"source_type": "customs_office", "source_id": ids["customs"]}).county_name == "Tehran County"
        with pytest.raises(LocationResolutionError, match="supported") as unsupported:
            resolve_location({"source_type": "warehouse", "source_id": 1})
        assert unsupported.value.code == "LOCATION_MAPPING_REQUIRED"
        with pytest.raises(LocationResolutionError) as missing:
            resolve_location({"source_type": "city", "source_id": 99999})
        assert missing.value.code == "RESOURCE_NOT_FOUND"
        with pytest.raises(LocationResolutionError) as inactive:
            resolve_location({"source_type": "city", "source_id": ids["inactive"]})
        assert inactive.value.code == "LOCATION_MAPPING_REQUIRED"
        with pytest.raises(LocationResolutionError) as mismatch:
            resolve_location({"source_type": "international_city", "source_id": ids["hamburg"]}, expected_country_id=ids["IR"])
        assert mismatch.value.code == "LOCATION_ANCESTRY_MISMATCH"


def test_iran_projection_is_eligible_typed_and_disambiguated(app):
    response = app.test_client().get("/api/locations/iran-destinations?q=Duplicate")
    assert response.status_code == 200
    rows = response.json["data"]
    assert {(row["identity"]["type"], row["identity"]["id"]) for row in rows} == {
        ("city", app.config["geo"]["city"]),
        ("city", app.config["geo"]["duplicate_city"]),
        ("customs", app.config["geo"]["customs"]),
    }
    assert all("—" in row["label"] and row["province"]["id"] for row in rows)
    excluded = app.test_client().get("/api/locations/iran-destinations?q=Bad")
    assert excluded.json["data"] == []
    port = app.test_client().get("/api/locations/iran-destinations?type=port")
    assert [(row["identity"]["type"], row["identity"]["id"]) for row in port.json["data"]] == [
        ("port", app.config["geo"]["port"]),
    ]


def _payload(app, **changes):
    ids = app.config["geo"]
    payload = {
        "shipping_type": "international", "contact_phone": "09123456789",
        "origin_country_id": ids["DE"], "origin_international_city_id": ids["hamburg"],
        "dest_country_id": ids["IR"],
        "iran_destination": {"type": "city", "id": ids["city"]},
    }
    payload.update(changes)
    return payload


def test_request_round_trip_uses_ids_derives_iran_province_and_keeps_legacy_reads(app):
    response = app.test_client().post("/api/shipment-request", json=_payload(app))
    assert response.status_code == 201
    with app.app_context():
        row = db.session.get(ShipmentRequest, response.json["id"])
        assert (row.origin_country_id, row.origin_international_city_id) == (app.config["geo"]["DE"], app.config["geo"]["hamburg"])
        assert row.dest_country_id == app.config["geo"]["IR"] and row.dest_international_city_id is None
        assert row.iran_dest_city_id == app.config["geo"]["city"] and row.iran_entry_province_id == app.config["geo"]["province"]
        assert build_route_payload(row)["location_state"] == "canonical"
        legacy = ShipmentRequest(shipping_type="international", contact_phone="09111111111", origin_country="Old", origin_city_international="Text", dest_country="Old", dest_city_international="Text")
        db.session.add(legacy)
        db.session.commit()
        projected = build_route_payload(legacy)
        assert projected["location_state"] == "legacy_ambiguous"
        assert all(value is None for value in projected["canonical_ids"].values())

    non_iran = app.test_client().post("/api/shipment-request", json=_payload(
        app,
        dest_country_id=app.config["geo"]["DE"],
        dest_international_city_id=app.config["geo"]["hamburg"],
        iran_destination=None,
        contact_phone="09123456780",
    ))
    assert non_iran.status_code == 201
    with app.app_context():
        row = db.session.get(ShipmentRequest, non_iran.json["id"])
        assert (row.dest_country_id, row.dest_international_city_id, row.dest_country, row.dest_city_international) == (
            app.config["geo"]["DE"], app.config["geo"]["hamburg"], "Germany", "Hamburg",
        )


def test_iran_origin_requires_province_and_rejects_lower_mismatch(app):
    ids = app.config["geo"]
    base = _payload(app, origin_country_id=ids["IR"], origin_international_city_id=None)
    missing = app.test_client().post("/api/shipment-request", json=base)
    assert missing.status_code == 400 and missing.json["error"]["code"] == "LOCATION_MAPPING_REQUIRED"
    valid = app.test_client().post("/api/shipment-request", json={**base, "origin_province_id": ids["province"], "origin_location": {"type": "city", "id": ids["city"]}})
    assert valid.status_code == 201
    mismatch = app.test_client().post("/api/shipment-request", json={**base, "origin_province_id": ids["province"], "origin_location": {"type": "city", "id": ids["duplicate_city"]}, "contact_phone": "09123456788"})
    assert mismatch.status_code == 422 and mismatch.json["error"]["code"] == "LOCATION_ANCESTRY_MISMATCH"
    redundant = app.test_client().post("/api/shipment-request", json={**_payload(app), "iran_entry_province_id": ids["province"], "contact_phone": "09123456787"})
    assert redundant.status_code == 400 and redundant.json["error"]["code"] == "VALIDATION_FAILED"


def test_quote_conversion_uses_shared_resolver_and_enriched_snapshot(app):
    with app.app_context():
        ids = app.config["geo"]
        org = OperationalOrganization(name="Ops")
        user = ExpertUser(username="slice3", password_hash="x", full_name="Slice 3", role="expert", is_active=True)
        request = ShipmentRequest(contact_phone="09120000000", status="waiting_for_customer", status_request_status="new")
        db.session.add_all([org, user, request])
        db.session.flush()
        db.session.add(OperationalMembership(organization_id=org.id, user_id=user.id, permissions=["operational_shipment.create"]))
        quote = ExpertQuote(shipment_request_id=request.id, amount=1, currency="IRR", created_by_expert_id=user.id, created_at=datetime.now(timezone.utc), customer_response="accepted", responded_at=datetime.now(timezone.utc), operational_organization_id=org.id)
        db.session.add(quote)
        db.session.commit()
        payload = {"accepted_quote_id": quote.id, "origin": {"source_type": "international_city", "source_id": ids["hamburg"]}, "destination": {"source_type": "customs_office", "source_id": ids["customs"]}, "transport_mode": "road", "planned_departure": "2026-08-10T10:00:00Z", "planned_arrival": "2026-08-10T12:00:00Z"}
        shipment, created = operational_service.create_from_accepted_quote(payload, {"id": user.id}, "slice3")
        leg = RouteLeg.query.one()
        assert created and shipment.source_type == "accepted_quote"
        assert leg.destination_snapshot["province"] == {"id": ids["province"], "name": "Tehran"}
        assert leg.destination_snapshot["canonical_reference"] == {"source_type": "customs_office", "source_id": ids["customs"]}
