"""Qualification checks for the frozen GeoNames Admin1/City package."""

from pathlib import Path

import pytest

from backend.geonames_geography_catalog import (
    COUNTRY_SCOPE,
    GeoNamesCatalogError,
    load,
)


def test_package_is_qualified_complete_and_contains_required_corridor_locations():
    payload = load()
    qualification = payload["qualification"]

    assert qualification["passed"] is True
    assert qualification["admin1_count"] == 416
    assert qualification["city_count"] == 30_553
    assert qualification["duplicate_admin1_identities"] == 0
    assert qualification["duplicate_city_identities"] == 0
    assert qualification["orphan_city_count"] == 0
    assert qualification["invalid_coordinate_count"] == 0
    assert qualification["invalid_alias_count"] == 0
    assert {row["country_code"] for row in payload["admin1"]} == COUNTRY_SCOPE
    assert {row["country_code"] for row in payload["cities"]} == COUNTRY_SCOPE

    names = {
        alias.casefold()
        for row in payload["cities"]
        for alias in [row["name_fa"], row["name_ascii"], *row["aliases"]]
    }
    for required in (
        "تهران", "اصفهان", "بندرعباس", "Shanghai", "Shenzhen", "Horgos",
        "Almaty", "Astana", "Aktau", "Ashgabat", "Tashkent", "Bishkek",
        "Dushanbe", "Baku", "Yerevan", "Istanbul", "Karachi", "Kabul",
        "Moscow", "Astrakhan",
    ):
        assert required.casefold() in names


def test_package_records_auditable_sources_and_processing_rules():
    payload = load()

    assert payload["license"]["name"] == "Creative Commons Attribution 4.0"
    assert payload["sources"]
    assert all(row["url"].startswith("https://download.geonames.org/") for row in payload["sources"])
    assert all(len(row["sha256"]) == 64 and row["bytes"] > 0 for row in payload["sources"])
    assert payload["processing_rules"]


def test_package_checksum_is_fail_closed(tmp_path: Path):
    damaged = tmp_path / "damaged.json.gz"
    canonical = Path(__file__).parents[1] / "reference_data" / "geonames-admin1-city-v1.json.gz"
    raw = bytearray(canonical.read_bytes())
    raw[-1] ^= 1
    damaged.write_bytes(raw)

    with pytest.raises(GeoNamesCatalogError, match="checksum"):
        load(damaged)
