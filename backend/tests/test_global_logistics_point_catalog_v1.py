"""Read-only package contract for the China→Iran GlobalLogisticsPoint V1 review."""
import copy
import importlib.util
import json
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "catalog_v1_validator", ROOT / "scripts/validate_global_logistics_point_catalog_v1.py"
)
validator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(validator)


def _artifacts():
    package = json.loads(validator.PACKAGE.read_text(encoding="utf-8"))
    reconciliation = json.loads(
        validator.RECONCILIATION.read_text(encoding="utf-8")
    )["rows"]
    return package, reconciliation


def test_catalog_v1_is_deterministic_bounded_and_reconciles_exact_legacy_64():
    package, reconciliation = _artifacts()
    assert validator.validate(package, reconciliation) == []
    expected = validator.unsigned_package()
    expected["checksum"] = validator.checksum(expected)
    assert package == expected
    rows = package["global_logistics_points"]
    assert len(rows) == 39
    assert sum(x["review"]["tier"] == "CORE_V1" for x in rows) == 29
    assert sum(x["review"]["tier"] == "OPTIONAL_V1" for x in rows) == 10
    assert len(reconciliation) == len(validator.ROWS) == 64
    assert all(x["runtime_candidate"]["proposed_lifecycle_status"] == "DRAFT" for x in rows)
    assert all(x["runtime_candidate"]["proposed_verification_status"] == "UNVERIFIED" for x in rows)
    assert all("public_id" not in x["runtime_candidate"] for x in rows)


def test_catalog_v1_validator_rejects_duplicates_invalid_values_and_missing_provenance():
    package, reconciliation = _artifacts()
    broken = copy.deepcopy(package)
    first, second = broken["global_logistics_points"][:2]
    second["runtime_candidate"]["immutable_code"] = first["runtime_candidate"]["immutable_code"]
    first["runtime_candidate"]["supported_modes"] = ["SPACE"]
    first["runtime_candidate"]["point_type_code"] = "CITY"
    first["review"]["package_review_status"] = "READY_FOR_OWNER_APPROVAL"
    first["review"]["sources"] = [x for x in first["review"]["sources"] if x["source_type"] != "EXTERNAL-VERIFIED"]
    broken["checksum"] = validator.checksum(broken)
    errors = validator.validate(broken, reconciliation)
    assert any("duplicate code" in x for x in errors)
    assert any("invalid modes" in x for x in errors)
    assert any("invalid type" in x for x in errors)
    assert any("lacks provenance" in x for x in errors)


@pytest.mark.skipif(
    not os.environ.get("CATALOG_V1_DISPOSABLE_POSTGRES_URL"),
    reason="requires explicit Catalog V1 disposable PostgreSQL URL",
)
def test_catalog_v1_all_candidates_create_as_draft_through_governance_service():
    from backend import create_app
    from backend.extensions import db
    from backend.logistics_network_models import LogisticsPointType
    from backend.models import Country, ExpertUser
    from backend.services import global_logistics_point_service as service

    url = os.environ["CATALOG_V1_DISPOSABLE_POSTGRES_URL"]
    assert "127.0.0.1" in url and "catalog_v1_review_" in url
    app = create_app(
        {"TESTING": True, "SQLALCHEMY_DATABASE_URI": url, "SECRET_KEY": "catalog-v1"},
        skip_startup=True,
    )
    package, _ = _artifacts()
    with app.app_context():
        actor = ExpertUser(
            username="catalog-v1-platform-reviewer", password_hash="x",
            full_name="Catalog V1 Reviewer", role="admin",
            authority="PLATFORM_ADMIN", is_active=True,
        )
        db.session.add(actor); db.session.flush()
        type_codes = {x["runtime_candidate"]["point_type_code"] for x in package["global_logistics_points"]}
        types = {}
        for order, code in enumerate(sorted(type_codes), 1):
            row = LogisticsPointType(
                immutable_code=code, fa_name=code, en_name=code,
                display_order=order, created_by=actor.id, updated_by=actor.id,
            )
            db.session.add(row); types[code] = row
        countries = {}
        for code in sorted({x["runtime_candidate"]["country_code"] for x in package["global_logistics_points"]}):
            row = Country.query.filter_by(code=code).one_or_none()
            if row is None:
                row = Country(code=code, name_en=code, name_fa=code)
                db.session.add(row)
            countries[code] = row
        db.session.commit()

        for item in package["global_logistics_points"]:
            row = item["runtime_candidate"]
            payload = {
                "immutable_code": row["immutable_code"],
                "point_type_public_id": types[row["point_type_code"]].public_id,
                "country_code": row["country_code"],
                "fa_name": row["fa_name"], "en_name": row["en_name"],
                "facility_identity_key": row["facility_identity_key"],
                "region_name": row["region_name"], "city_name": row["city_name"],
                "short_address": row["short_address"], "latitude": row["latitude"],
                "longitude": row["longitude"], "timezone": row["timezone"],
                "un_locode": row["un_locode"], "border_pair_key": row["border_pair_key"],
                "border_side": row["border_side"], "supported_modes": row["supported_modes"],
                "corridor_tags": row["corridor_tags"], "aliases": row["aliases"],
                "external_codes": row["external_codes"],
                "sources": [{"organization": s["source_organization"],
                             "reference": s["source_reference"], "version": s["source_version"]}
                            for s in item["review"]["sources"]],
            }
            created = service.create(payload, actor.id)
            assert created.lifecycle_status == "DRAFT"
            assert created.verification_status == "UNVERIFIED"
        assert service.list_points({"status": "ALL", "per_page": 100})["total"] == 39
