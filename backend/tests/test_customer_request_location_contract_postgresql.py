"""Owned PostgreSQL 18 qualification for HW_GEO_009."""
from __future__ import annotations

import os

from alembic import command
import pytest
import sqlalchemy as sa
from sqlalchemy.engine import make_url

from backend import create_app
from backend.extensions import db
from backend.geonames_geography_catalog import DATASET_ID
from backend.migration_runtime import alembic_config
from backend.models import City, Country, InternationalCity, Province, ShipmentRequest
from backend.operational_models import CanonicalLocation, OperationalShipment
from backend.services.route_payload_service import build_route_payload
from scripts.uat.canonical_geography_fixture import ensure_canonical_geography


URL = os.environ.get("CUSTOMER_LOCATION_POSTGRES_URL", "")
pytestmark = pytest.mark.skipif(not URL, reason="requires owned CUSTOMER_LOCATION_POSTGRES_URL")


def test_postgresql18_complete_city_contract_persistence_and_legacy_fixture():
    parsed = make_url(URL)
    assert parsed.get_backend_name() == "postgresql" and parsed.host == "127.0.0.1"
    assert (parsed.database or "").startswith("forwarder_customer_location_")
    engine = sa.create_engine(URL)
    with engine.connect() as connection:
        assert 180000 <= int(connection.execute(sa.text("SHOW server_version_num")).scalar_one()) < 190000

    command.upgrade(alembic_config(URL), "head")
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": URL, "SECRET_KEY": "geo-009-postgres-secret-key-32", "JWT_SECRET_KEY": "geo-009-postgres-jwt-secret-key-32"}, skip_startup=True)
    with app.app_context():
        ensure_canonical_geography()
        iran = db.session.scalar(sa.select(Country).where(Country.code == "IR"))
        brazil = db.session.scalar(sa.select(Country).where(Country.code == "BR"))
        province = db.session.scalar(sa.select(Province).where(Province.country_id == iran.id, Province.dataset_id == DATASET_ID).limit(1))
        if db.session.scalar(sa.select(sa.func.count()).select_from(City).where(City.country_id == iran.id, City.dataset_id == DATASET_ID)) < 3:
            db.session.add_all([
                City(code=f"GEO009-{index}", name_fa=name, name_en=en, geoname_id=9900000 + index, country_id=iran.id, province_id=province.id, dataset_id=DATASET_ID, is_active=True, aliases=aliases)
                for index, (name, en, aliases) in enumerate([
                    ("اصفهان", "Isfahan", ["Esfahan"]),
                    ("تهران", "Tehran", ["Teheran"]),
                    ("بندرعباس", "Bandar Abbas", []),
                ], 1)
            ])
        db.session.query(InternationalCity).delete()
        db.session.add_all([
            InternationalCity(country_id=iran.id, name_fa="بندرعباس", name_en="Bandar Abbas", city_type="city", un_locode="IRBND", is_active=True),
            InternationalCity(country_id=iran.id, name_fa="تهران", name_en="Tehran", city_type="city", un_locode="IRTHR", is_active=True),
            InternationalCity(country_id=iran.id, name_fa="فرودگاه امام خمینی", name_en="Imam Khomeini Airport", city_type="airport", un_locode="IRIKA", is_active=True),
        ])
        db.session.commit()
        expected = [row.id for row in db.session.scalars(sa.select(City).join(Province, City.province_id == Province.id).where(City.country_id == iran.id, City.dataset_id == DATASET_ID, City.is_active.is_(True), Province.is_active.is_(True)).order_by(City.name_fa, City.geoname_id)).all()]
        canonical_before = db.session.scalar(sa.select(sa.func.count()).select_from(CanonicalLocation))
        iran_id, brazil_id = iran.id, brazil.id

    actual: list[int] = []
    offset = 0
    with app.test_client() as client:
        while True:
            page = client.get(f"/api/geography/cities?country_code=IR&offset={offset}&limit=2")
            assert page.status_code == 200
            body = page.get_json()
            actual.extend(item["source_id"] for item in body["items"])
            if not body["has_more"]:
                break
            offset += body["limit"]
        exact = client.get("/api/geography/cities?country_code=IR&q=اصفهان&limit=20").get_json()["items"]
        assert exact and exact[0]["name_en"] == "Isfahan"
        city_id = actual[0]
        response = client.post("/api/shipment-request", json={
            "shipping_type": "international", "contact_phone": "09123456789", "transport_method_preference": "forwarder_suggestion",
            "origin_country_id": iran_id, "origin_location": {"kind": "canonical_city", "source_id": city_id},
            "dest_country_id": brazil_id, "destination_location": {"kind": "declared", "description": "Santos customer warehouse"},
        })
        assert response.status_code == 201

    assert actual == expected
    with app.app_context():
        assert InternationalCity.query.count() == 3
        row = db.session.get(ShipmentRequest, response.get_json()["id"])
        assert row.origin_city_id == city_id and row.origin_international_city_id is None
        assert row.dest_city_id is None and row.dest_international_city_id is None
        assert row.dest_city_international == "Santos customer warehouse"
        assert build_route_payload(row)["location_state"] == "customer_declared"
        assert db.session.scalar(sa.select(sa.func.count()).select_from(CanonicalLocation)) == canonical_before
        assert OperationalShipment.query.count() == 0
        heads = db.session.execute(sa.text("select version_num from alembic_version")).scalars().all()
        assert heads == ["20261017_document_type_ownership"]
