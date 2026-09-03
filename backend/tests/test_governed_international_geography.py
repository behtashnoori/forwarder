"""S1 permanent controls for the checked-in international geography snapshot."""

import pytest
from sqlalchemy.exc import IntegrityError

from backend import create_app
from backend.extensions import db
from backend.models import Country, InternationalCity, ShipmentRequest
from backend.seed_international_data import seed_international_data
from backend.services.international_geography_readiness import readiness_report, validate_snapshot


@pytest.fixture()
def app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"}, skip_startup=True)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def _seed(app):
    with app.app_context():
        seed_international_data(app)
        return (
            Country.query.filter_by(code="IR").one().id,
            Country.query.filter_by(code="TM").one().id,
        )


def test_snapshot_contract_and_empty_database_reconcile_to_iran_and_turkmenistan(app):
    assert validate_snapshot() == []
    iran_id, turkmenistan_id = _seed(app)
    with app.app_context():
        iran, turkmenistan = db.session.get(Country, iran_id), db.session.get(Country, turkmenistan_id)
        ashkhabad = InternationalCity.query.filter_by(country_id=turkmenistan.id, un_locode="TMASB").one()
        assert iran.code == "IR" and turkmenistan.code == "TM"
        assert ashkhabad.name_en == "Ashkhabad"
        assert ashkhabad.source_organization == "UNECE"
        report = readiness_report()
        assert report["valid"] is True
        assert {row["code"] for row in report["countries"]} == {"TM"}
        assert report["countries"][0]["selectable"] is True


def test_partial_dataset_recovers_iran_location_and_turkmenistan_without_reactivation(app):
    with app.app_context():
        iran = Country(code="IR", name_en="Iran", name_fa="ایران", is_active=False)
        unrelated = Country(code="ZZ", name_en="Unrelated", name_fa="نامرتبط")
        db.session.add_all([iran, unrelated])
        db.session.flush()
        db.session.add(InternationalCity(country_id=iran.id, name_en="Tehran", name_fa="تهران", is_active=False))
        db.session.commit()
        seed_international_data(app)
        assert Country.query.filter_by(code="IR").one().is_active is False
        assert InternationalCity.query.filter_by(country_id=iran.id, name_en="Tehran").one().is_active is False
        assert InternationalCity.query.filter_by(country_id=iran.id, name_en="Mashhad").one() is not None
        assert Country.query.filter_by(code="TM").one() is not None


def test_reconciliation_is_idempotent_and_unlocode_identity_is_duplicate_protected(app):
    _seed(app)
    with app.app_context():
        before = (Country.query.count(), InternationalCity.query.count())
        seed_international_data(app)
        assert (Country.query.count(), InternationalCity.query.count()) == before
        tm = Country.query.filter_by(code="TM").one()
        db.session.add(InternationalCity(country_id=tm.id, name_en="Duplicate", name_fa="تکراری", un_locode="TMASB"))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


def test_selector_and_canonical_request_persistence_for_turkmenistan(app):
    _iran_id, tm_id = _seed(app)
    client = app.test_client()
    countries = client.get("/api/countries").get_json()
    assert {row["code"] for row in countries}.issuperset({"IR", "TM"})
    locations = client.get(f"/api/international-cities?country_id={tm_id}").get_json()
    ashkhabad = next(row for row in locations if row["name_en"] == "Ashkhabad")
    response = client.post("/api/shipment-request", json={
        "shipping_type": "international", "contact_phone": "09123456789",
        "origin_country_id": tm_id, "origin_international_city_id": ashkhabad["id"],
        "dest_country_id": tm_id, "dest_international_city_id": ashkhabad["id"],
    })
    assert response.status_code == 201
    with app.app_context():
        row = db.session.get(ShipmentRequest, response.get_json()["id"])
        assert (row.origin_country_id, row.origin_international_city_id) == (tm_id, ashkhabad["id"])
        assert (row.dest_country_id, row.dest_international_city_id) == (tm_id, ashkhabad["id"])


def test_readiness_reports_inactive_without_treating_reference_as_missing(app):
    _seed(app)
    with app.app_context():
        tm = Country.query.filter_by(code="TM").one()
        tm.is_active = False
        db.session.commit()
        item = readiness_report()["countries"][0]
        assert item["exists"] is True and item["is_active"] is False and item["selectable"] is False
