"""FWD-02 official-input, identity, lifecycle and compatibility proof."""
import pytest

from backend import create_app
from backend.extensions import db
from backend.international_geography_catalog import CATALOG_SHA256, apply_catalog, load_catalog, plan_catalog
from backend.models import Country, InternationalCity, ShipmentRequest
from backend.seed_international_data import seed_international_data


@pytest.fixture()
def app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"}, skip_startup=True)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def apply():
    return apply_catalog(expected_checksum=CATALOG_SHA256, executed_by="FWD-02 qualification",
                         approval_reference="FWD-02 owner authorization of global standards", environment="qualification")


def test_official_coverage_idempotency_preserves_v1_and_inactive_history(app):
    from backend.services.international_geography_readiness import approved_snapshot
    for record in approved_snapshot()["records"]:
        country = Country(**record["country"])
        db.session.add(country)
        db.session.flush()
        for item in record["locations"]:
            db.session.add(InternationalCity(country_id=country.id, **item))
    db.session.commit()
    tehran = InternationalCity.query.filter_by(un_locode="IRTHR").one()
    prior = (tehran.id, tehran.name_fa, tehran.dataset_id)
    tehran.is_active = False
    db.session.commit()
    plan, run = apply()
    assert not plan["conflicts"] and run.status == "succeeded"
    assert (tehran.id, tehran.name_fa, tehran.dataset_id) == prior and not tehran.is_active
    assert len(load_catalog()["records"]) == 249
    counts = {code: InternationalCity.query.join(Country).filter(Country.code == code).count() for code in ("IR", "IT", "NO")}
    assert counts == {"IR": 154, "IT": 5799, "NO": 1142}
    plan2, run2 = apply()
    assert plan2["creates"] == [] and run2.created_count == 0
    assert not plan_catalog()["conflicts"]
    assert InternationalCity.query.count() == 115208
    assert len(app.test_client().get("/api/countries").get_json()) == 249
    client = app.test_client()
    usa = Country.query.filter_by(code="US").one()
    base = f"/api/international-cities?country_id={usa.id}&paged=1"
    first = client.get(base).get_json()
    second = client.get(base + "&offset=50").get_json()
    assert len(first["items"]) == len(second["items"]) == 50 and first["has_more"]
    assert not {x["id"] for x in first["items"]} & {x["id"] for x in second["items"]}
    target = InternationalCity.query.filter_by(country_id=usa.id, un_locode="USNYC").one()
    assert client.get(base + "&q=USNYC").get_json()["items"][0]["id"] == target.id
    assert client.get(base + "&q=%25").get_json()["items"] == []
    assert client.get(base + "&offset=-1").status_code == 400
    assert client.get(base + "&limit=101").status_code == 400
    assert client.get(base + "&q=" + "x" * 161).status_code == 400


def test_same_name_is_not_identity_and_apply_is_refused_without_writes(app):
    iran = Country(code="IR", name_en="Iran", name_fa="ایران")
    db.session.add(iran)
    db.session.flush()
    db.session.add(InternationalCity(country_id=iran.id, name_en="Tehran", name_fa="تهران", city_type="city"))
    db.session.commit()
    plan, run = apply()
    assert "IRTHR" in plan["conflicts"] and run.status == "refused"
    assert Country.query.count() == 1 and InternationalCity.query.count() == 1


def test_countries_locations_roundtrip_country_fence_and_read_old_select_new(app):
    apply()
    client = app.test_client()
    countries = {x["code"]: x for x in client.get("/api/countries").get_json()}
    assert {"IT", "NO", "IR"}.issubset(countries)
    places = {code: client.get(f"/api/international-cities?country_id={countries[code]['id']}").get_json()
              for code in ("IT", "NO", "IR")}
    assert len(places["IR"]) > 3
    for origin in ("IT", "NO"):
        payload = {"shipping_type": "international", "contact_phone": "09123456789", "cargo_description": "Synthetic cargo",
                   "origin_country_id": countries[origin]["id"], "origin_international_city_id": places[origin][0]["id"],
                   "dest_country_id": countries["IR"]["id"], "dest_international_city_id": places["IR"][0]["id"]}
        response = client.post("/api/shipment-request", json=payload)
        assert response.status_code == 201, response.get_json()
        db.session.expire_all()
        saved = db.session.get(ShipmentRequest, response.get_json()["id"])
        assert saved.origin_country_id == countries[origin]["id"]
        assert saved.dest_international_city_id == places["IR"][0]["id"]
        assert saved.origin_city_international == places[origin][0]["name"]
        assert saved.dest_city_international == places["IR"][0]["name"]
        bad = {**payload, "origin_international_city_id": places["IR"][0]["id"]}
        assert client.post("/api/shipment-request", json=bad).status_code == 422
    iran = db.session.get(Country, countries["IR"]["id"])
    iran.is_active = False
    db.session.commit()
    assert client.get(f"/api/international-cities?country_id={iran.id}").get_json() == []
    assert client.post("/api/shipment-request", json=payload).status_code == 422
    db.session.expire_all()
    historical = db.session.get(ShipmentRequest, saved.id)
    assert historical.dest_city_international == places["IR"][0]["name"]


def test_checksum_and_input_type_provenance(app):
    with pytest.raises(ValueError, match="checksum"):
        apply_catalog(expected_checksum="wrong", executed_by="test", approval_reference="test", environment="qualification")
    for country in load_catalog()["records"]:
        for location in country["locations"]:
            assert location["un_locode"].startswith(country["country"]["code"])
            if "source_function" in location:
                assert location["city_type"] == {"1-------": "port", "---4----": "airport"}.get(location["source_function"], "city")
                assert not location["is_major_port"] and not location["is_major_airport"]


def test_worldwide_input_has_no_country_or_function_shortlist():
    catalog = load_catalog()
    records = {row["country"]["code"]: row["locations"] for row in catalog["records"]}
    assert all(records.values()) and len(records) == 249
    assert {code: len(records[code]) for code in ("US", "DE", "CN", "BR", "ZA", "AU")} == {
        "US": 20856, "DE": 10021, "CN": 1666, "BR": 5635, "ZA": 793, "AU": 2583}
    assert any(item.get("source_function", "").count("-") < 6 for item in records["US"])
    assert any(item.get("source_function") == "--3-----" for item in records["DE"])
    assert all(item.get("source_status", "AA") in {"AA", "AC", "AF", "AI", "AS", "AM", "AQ", "RN", "RL"}
               for items in records.values() for item in items)


def test_unbound_historical_seed_requires_explicit_identity_review(app):
    seed_international_data(app)
    before = [(row.id, row.un_locode, row.name_en) for row in InternationalCity.query.all()]
    plan, run = apply()
    assert plan["conflicts"] and run.status == "refused"
    assert [(row.id, row.un_locode, row.name_en) for row in InternationalCity.query.all()] == before
