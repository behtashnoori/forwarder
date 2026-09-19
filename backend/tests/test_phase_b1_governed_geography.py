"""Phase B1 governed worldwide geography, identity, and lookup contracts."""
from __future__ import annotations

import pytest

from backend import create_app
from backend.extensions import db
from backend.international_geography_catalog import (
    CATALOG_CHECKSUM,
    CATALOG_DATASET_ID,
    EXPECTED_TYPE_COUNTS,
    GeographyCatalog,
    apply_catalog,
    load_catalog,
    plan_catalog,
)
from backend.models import Country, InternationalCity, ReferenceDataSeedRun, ShipmentRequest
from backend.services.admin_shipment_request_service import (
    build_admin_request_detail_payload,
)
from backend.services.international_geography_readiness import approved_snapshot


@pytest.fixture(scope="module")
def catalog():
    return load_catalog()


@pytest.fixture()
def app():
    application = create_app(
        {"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"},
        skip_startup=True,
    )
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


def _install_golden_v1() -> None:
    for record in approved_snapshot()["records"]:
        country = Country(**record["country"], dataset_id="forwarder-international-geography-v1")
        db.session.add(country)
        db.session.flush()
        for item in record["locations"]:
            db.session.add(
                InternationalCity(
                    country_id=country.id,
                    dataset_id="forwarder-international-geography-v1",
                    **item,
                )
            )
    db.session.commit()


def _apply(catalog):
    return apply_catalog(
        catalog=catalog,
        expected_checksum=CATALOG_CHECKSUM,
        executed_by="Phase B1 qualification",
        approval_reference="Approved Golden Phase B Slice 1",
        environment="qualification",
    )


def _bounded_rehearsal_catalog(catalog: GeographyCatalog) -> GeographyCatalog:
    """Use real approved records while keeping routine suite memory bounded.

    Exact full-catalog identity/count validation is covered above; release
    qualification separately rehearses all 115,208 rows twice.
    """
    source = {row["country"]["code"]: row for row in catalog.payload["records"]}
    records = []
    for code, limit, required in (
        ("IR", 154, ()),
        ("IT", 101, ("ITGOA",)),
        ("NO", 101, ("NOOSL",)),
    ):
        locations = list(source[code]["locations"][:limit])
        by_code = {item["un_locode"] for item in locations}
        for locode in required:
            if locode not in by_code:
                locations.append(
                    next(item for item in source[code]["locations"] if item["un_locode"] == locode)
                )
        records.append({"country": source[code]["country"], "locations": locations})
    type_counts = {kind: 0 for kind in EXPECTED_TYPE_COUNTS}
    for record in records:
        for item in record["locations"]:
            type_counts[item["city_type"]] += 1
    payload = {**catalog.payload, "records": records}
    return GeographyCatalog(
        payload=payload,
        checksum=catalog.checksum,
        country_count=len(records),
        location_count=sum(len(record["locations"]) for record in records),
        iran_location_count=len(records[0]["locations"]),
        location_type_counts=type_counts,
        duplicate_count=0,
        invalid_record_count=0,
    )


def test_catalog_provenance_coverage_uniqueness_and_label_policy(catalog):
    assert catalog.dataset_id == CATALOG_DATASET_ID
    assert catalog.snapshot_version == "2025-1"
    assert catalog.checksum == CATALOG_CHECKSUM
    assert catalog.country_count == 249
    assert catalog.location_count == 115_208
    assert catalog.iran_location_count == 154
    assert catalog.location_type_counts == EXPECTED_TYPE_COUNTS
    assert catalog.duplicate_count == 0
    assert catalog.invalid_record_count == 0
    records = {row["country"]["code"]: row for row in catalog.payload["records"]}
    assert {"IR", "IT", "NO"}.issubset(records)
    assert len(records["IT"]["locations"]) == 5_799
    assert len(records["NO"]["locations"]) == 1_142
    verified = next(item for item in records["IR"]["locations"] if item["un_locode"] == "IRTHR")
    fallback = next(item for item in records["IR"]["locations"] if item["un_locode"] == "IRABD")
    assert verified["name_fa"] == "تهران" and verified["name_fa"] != verified["name_en"]
    assert fallback["name_fa"] == fallback["name_en"] == "Abadan"
    assert "untranslated fallback" in catalog.payload["label_policy"]


def test_additive_apply_is_idempotent_bounded_and_round_trips_stable_ids(app, catalog):
    catalog = _bounded_rehearsal_catalog(catalog)
    _install_golden_v1()
    tehran = InternationalCity.query.filter_by(un_locode="IRTHR").one()
    tehran.is_active = False
    golden_identity = (tehran.id, tehran.country_id, tehran.name_en, tehran.name_fa, tehran.dataset_id)
    db.session.commit()

    initial_plan = plan_catalog(catalog)
    assert initial_plan.conflicts == []
    assert initial_plan.created_country_count == 2
    assert initial_plan.created_location_count == catalog.location_count - 3
    first_plan, first_run = _apply(catalog)
    assert first_run.status == "succeeded"
    assert first_run.updated_count == 0
    assert first_run.created_count == first_plan.created_count == catalog.location_count - 1
    assert first_plan.unchanged_count == 4
    db.session.expire_all()
    preserved = InternationalCity.query.filter_by(un_locode="IRTHR").one()
    assert (preserved.id, preserved.country_id, preserved.name_en, preserved.name_fa, preserved.dataset_id) == golden_identity
    assert preserved.is_active is False
    assert Country.query.count() == 4
    assert InternationalCity.query.count() == catalog.location_count + 1

    second_plan, second_run = _apply(catalog)
    assert second_run.status == "succeeded"
    assert second_plan.created_count == second_run.created_count == 0
    assert second_plan.unchanged_count == catalog.location_count + 3
    assert second_plan.skipped_count == 0
    assert ReferenceDataSeedRun.query.count() == 2
    assert InternationalCity.query.filter_by(un_locode="IRTHR").one().is_active is False

    client = app.test_client()
    countries = {item["code"]: item for item in client.get("/api/countries").get_json()}
    assert {"IT", "NO", "IR"}.issubset(countries)
    italy_page = client.get(
        f"/api/international-cities?country_id={countries['IT']['id']}&paged=1&limit=50"
    ).get_json()
    assert len(italy_page["items"]) == 50 and italy_page["has_more"] is True
    assert italy_page["limit"] == 50 and italy_page["offset"] == 0
    italy_second = client.get(
        f"/api/international-cities?country_id={countries['IT']['id']}&paged=1&limit=50&offset=50"
    ).get_json()
    assert not {item["id"] for item in italy_page["items"]} & {
        item["id"] for item in italy_second["items"]
    }
    genoa = client.get(
        f"/api/international-cities?country_id={countries['IT']['id']}&paged=1&q=ITGOA"
    ).get_json()["items"]
    oslo = client.get(
        f"/api/international-cities?country_id={countries['NO']['id']}&paged=1&q=NOOSL"
    ).get_json()["items"]
    assert [item["un_locode"] for item in genoa] == ["ITGOA"]
    assert [item["un_locode"] for item in oslo] == ["NOOSL"]
    iran = client.get(
        f"/api/international-cities?country_id={countries['IR']['id']}&paged=1&limit=100"
    ).get_json()
    assert len(iran["items"]) == 100 and iran["has_more"] is True
    assert client.get(
        f"/api/international-cities?country_id={countries['IR']['id']}&paged=1&type=port"
    ).status_code == 200
    assert client.get(
        f"/api/international-cities?country_id={countries['IT']['id']}&paged=1&q=%25"
    ).get_json()["items"] == []
    assert client.get(
        f"/api/international-cities?country_id={countries['IT']['id']}&paged=1&limit=101"
    ).status_code == 400
    assert client.get(
        f"/api/international-cities?country_id={countries['IT']['id']}&paged=1&offset=-1"
    ).status_code == 400
    assert client.get(
        f"/api/international-cities?country_id={countries['IT']['id']}&paged=1&type=warehouse"
    ).status_code == 400

    abadan = client.get(
        f"/api/international-cities?country_id={countries['IR']['id']}&paged=1&q=IRABD"
    ).get_json()["items"][0]
    assert abadan["name_fa_is_fallback"] is True
    assert abadan["label_source"] == "source_name_fallback"
    inactive_tehran = client.get(
        f"/api/international-cities?country_id={countries['IR']['id']}&paged=1&q=IRTHR"
    ).get_json()["items"]
    assert inactive_tehran == []

    payload = {
        "shipping_type": "international",
        "contact_phone": "09123456789",
        "origin_country_id": countries["NO"]["id"],
        "origin_international_city_id": oslo[0]["id"],
        "dest_country_id": countries["IT"]["id"],
        "dest_international_city_id": genoa[0]["id"],
    }
    created = client.post("/api/shipment-request", json=payload)
    assert created.status_code == 201, created.get_json()
    db.session.expire_all()
    reopened = db.session.get(ShipmentRequest, created.get_json()["id"])
    assert (
        reopened.origin_country_id,
        reopened.origin_international_city_id,
        reopened.dest_country_id,
        reopened.dest_international_city_id,
    ) == (
        payload["origin_country_id"],
        payload["origin_international_city_id"],
        payload["dest_country_id"],
        payload["dest_international_city_id"],
    )
    review = build_admin_request_detail_payload(reopened)
    assert review["origin"]["international_city"] == oslo[0]["name"]
    assert review["destination"]["international_city"] == genoa[0]["name"]


def test_ambiguous_legacy_name_and_cross_country_stable_key_refuse_all_writes(app, catalog):
    catalog = _bounded_rehearsal_catalog(catalog)
    iran = Country(code="IR", name_en="Iran", name_fa="ایران")
    wrong = Country(code="ZZ", name_en="Historical", name_fa="تاریخی")
    db.session.add_all([iran, wrong])
    db.session.flush()
    db.session.add_all(
        [
            InternationalCity(
                country_id=iran.id,
                name_en="Tehran",
                name_fa="تهران",
                city_type="city",
            ),
            InternationalCity(
                country_id=wrong.id,
                name_en="Wrong Tehran",
                name_fa="تهران نادرست",
                city_type="city",
                un_locode="IRTHR",
            ),
        ]
    )
    db.session.commit()
    before = (Country.query.count(), InternationalCity.query.count())
    plan, run = _apply(catalog)
    assert run.status == "refused"
    assert plan.created_count > 0
    assert {item["stable_key"] for item in plan.conflicts}.issuperset({"IRTHR"})
    assert (Country.query.count(), InternationalCity.query.count()) == before
    assert run.created_count == 0 and run.updated_count == 0
