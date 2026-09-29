"""Qualified plan/apply boundary for the canonical GeoNames V1 package."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path

from sqlalchemy import select

from backend.extensions import db
from backend.models import City, Country, Province, ReferenceDataSeedRun


DATASET_ID = "GEONAMES_ADMIN1_CITY_V1"
PACKAGE_PATH = Path(__file__).with_name("reference_data") / "geonames-admin1-city-v1.json.gz"
PACKAGE_SHA256 = "62c7ecc05c5860e0f48f6e84d6087897a967df41acbdaaa8af0add44e22e16f2"
COUNTRY_SCOPE = frozenset({"IR", "CN", "KZ", "TM", "UZ", "KG", "TJ", "AF", "PK", "AZ", "AM", "GE", "TR", "RU"})


class GeoNamesCatalogError(RuntimeError):
    pass


@dataclass
class Plan:
    admin1_create: list[dict]
    city_create: list[dict]
    unchanged_admin1: int
    unchanged_city: int
    conflicts: list[dict]

    def as_dict(self):
        return {
            "dataset_id": DATASET_ID,
            "admin1_created": len(self.admin1_create), "city_created": len(self.city_create),
            "admin1_unchanged": self.unchanged_admin1, "city_unchanged": self.unchanged_city,
            "conflict_count": len(self.conflicts), "conflicts": self.conflicts[:100],
            "planned_count": len(self.admin1_create) + len(self.city_create),
        }


def load(path: Path = PACKAGE_PATH) -> dict:
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PACKAGE_SHA256:
        raise GeoNamesCatalogError("GeoNames package checksum mismatch")
    try:
        payload = json.loads(gzip.decompress(raw))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise GeoNamesCatalogError("GeoNames package is not valid deterministic UTF-8 gzip JSON") from exc
    qualification = payload.get("qualification", {})
    if payload.get("dataset_id") != DATASET_ID or qualification.get("passed") is not True:
        raise GeoNamesCatalogError("GeoNames package identity or qualification is invalid")
    if {row.get("country_code") for row in payload.get("admin1", [])} != COUNTRY_SCOPE:
        raise GeoNamesCatalogError("GeoNames Admin1 country scope is incomplete")
    if {row.get("country_code") for row in payload.get("cities", [])} != COUNTRY_SCOPE:
        raise GeoNamesCatalogError("GeoNames city country scope is incomplete")
    if len(payload["admin1"]) != qualification.get("admin1_count") or len(payload["cities"]) != qualification.get("city_count"):
        raise GeoNamesCatalogError("GeoNames package counts do not match qualification evidence")
    return payload


def plan(payload: dict | None = None) -> Plan:
    payload = payload or load()
    countries = {row.code: row for row in db.session.scalars(select(Country).where(Country.code.in_(COUNTRY_SCOPE))).all()}
    conflicts = []
    for code in sorted(COUNTRY_SCOPE - countries.keys()):
        conflicts.append({"kind": "country", "identity": code, "reason": "canonical country is missing"})
    existing_admin = {row.geoname_id: row for row in db.session.scalars(select(Province).where(Province.geoname_id.is_not(None))).all()}
    existing_city = {row.geoname_id: row for row in db.session.scalars(select(City).where(City.geoname_id.is_not(None))).all()}
    admin_create, city_create = [], []
    unchanged_admin = unchanged_city = 0
    for item in payload["admin1"]:
        row = existing_admin.get(item["geoname_id"])
        country = countries.get(item["country_code"])
        if row is None:
            admin_create.append(item)
        elif country is None or row.country_id != country.id or row.code != item["admin1_code"]:
            conflicts.append({"kind": "admin1", "identity": item["geoname_id"], "reason": "stable identity conflicts with existing ancestry"})
        else:
            unchanged_admin += 1
    source_admin = {row["geoname_id"] for row in payload["admin1"]}
    for item in payload["cities"]:
        if item["admin1_geoname_id"] not in source_admin:
            conflicts.append({"kind": "city", "identity": item["geoname_id"], "reason": "source parent is missing"})
            continue
        row = existing_city.get(item["geoname_id"])
        country = countries.get(item["country_code"])
        if row is None:
            city_create.append(item)
        elif country is None or row.country_id != country.id or not row.province or row.province.geoname_id != item["admin1_geoname_id"]:
            conflicts.append({"kind": "city", "identity": item["geoname_id"], "reason": "stable identity conflicts with existing ancestry"})
        else:
            unchanged_city += 1
    return Plan(admin_create, city_create, unchanged_admin, unchanged_city, conflicts)


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def apply(*, expected_checksum: str, operator: str, approval_reference: str, environment: str):
    payload = load()
    if expected_checksum not in {PACKAGE_SHA256, f"sha256:{PACKAGE_SHA256}"}:
        raise GeoNamesCatalogError("expected checksum does not match qualified package")
    if not all(isinstance(value, str) and value.strip() for value in (operator, approval_reference, environment)):
        raise GeoNamesCatalogError("operator, approval reference, and environment are required")
    result = plan(payload)
    if result.conflicts:
        raise GeoNamesCatalogError(f"apply refused with {len(result.conflicts)} conflict(s)")
    run = ReferenceDataSeedRun(
        catalog_version=DATASET_ID, catalog_family="GEOGRAPHY", catalog_name="GeoNames Admin1 and City V1",
        schema_version="1", source_bundle_version="daily-qualified", checksum=f"sha256:{PACKAGE_SHA256}",
        environment=environment.strip().lower(), mode="apply",
        planned_count=len(result.admin1_create) + len(result.city_create), created_count=0,
        updated_count=0, unchanged_count=result.unchanged_admin1 + result.unchanged_city,
        conflict_count=0, status="started", executed_by=operator.strip(),
        approval_reference=approval_reference.strip(),
    )
    try:
        db.session.add(run)
        countries = {row.code: row for row in db.session.scalars(select(Country).where(Country.code.in_(COUNTRY_SCOPE))).all()}
        for item in result.admin1_create:
            db.session.add(Province(
                code=item["admin1_code"], name_fa=item["name_fa"], name_en=item["name_ascii"],
                geoname_id=item["geoname_id"], aliases=item["aliases"],
                latitude=item["latitude"], longitude=item["longitude"], timezone=item["timezone"],
                country_id=countries[item["country_code"]].id, is_active=True,
                source_organization="GeoNames", source_reference=f"https://www.geonames.org/{item['geoname_id']}",
                source_version="daily-qualified", dataset_id=DATASET_ID,
            ))
        db.session.flush()
        parents = {row.geoname_id: row for row in db.session.scalars(select(Province).where(Province.geoname_id.is_not(None))).all()}
        for item in result.city_create:
            parent = parents[item["admin1_geoname_id"]]
            db.session.add(City(
                code=str(item["geoname_id"]), name_fa=item["name_fa"], name_en=item["name_ascii"],
                geoname_id=item["geoname_id"], country_id=countries[item["country_code"]].id,
                province_id=parent.id, county_id=None, feature_code=item["feature_code"],
                aliases=item["aliases"], latitude=item["latitude"], longitude=item["longitude"],
                population=item["population"], timezone=item["timezone"], is_active=True,
                source_organization="GeoNames", source_reference=f"https://www.geonames.org/{item['geoname_id']}",
                source_version="daily-qualified", dataset_id=DATASET_ID,
            ))
        run.created_count = len(result.admin1_create) + len(result.city_create)
        run.status = "succeeded"
        run.completed_at = _now()
        db.session.commit()
        return result, run
    except Exception as exc:
        db.session.rollback()
        raise GeoNamesCatalogError("GeoNames apply failed and rolled back") from exc
