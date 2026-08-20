from __future__ import annotations

import copy
import json

import pytest

from backend import create_app
from backend.document_catalog_package import (
    PackageApplyError,
    PackageValidationError,
    apply_package,
    checksum_for_payload,
    load_package,
    plan_package,
)
from backend.document_catalog_cli import main as cli_main
from backend.extensions import db
from backend.models import (
    DocumentCatalogAuditEvent,
    DocumentDefinition,
    DocumentDefinitionAlias,
    ReferenceDataSeedRun,
)


@pytest.fixture()
def package_app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def _definition(code="synthetic_invoice", lifecycle="DRAFT"):
    confirmed = lifecycle in {"SOURCE_CONFIRMED", "ACTIVE"}
    review = "SOURCE_CONFIRMED" if confirmed else "SOURCE_CONFIRMATION_REQUIRED"
    return {
        "code": code,
        "name_fa": "سند آزمایشی",
        "name_en": "Synthetic document",
        "family": "COMMERCIAL",
        "description_fa": None,
        "description_en": None,
        "reference_number_label_fa": None,
        "reference_number_label_en": None,
        "expiry_applicable": None,
        "organization_overridable": True,
        "lifecycle_target": lifecycle,
        "source_review_status": review,
        "aliases": [
            {
                "locale": "en",
                "display_value": f"{code} alias",
                "alias_kind": "COMMON_NAME",
            }
        ],
        "jurisdictions": [{"kind": "GLOBAL"}],
        "transport_modes": ["MODE_INDEPENDENT"],
        "process_stages": ["PRE_SHIPMENT"],
        "business_scopes": ["REQUEST"],
        "provenance": [
            {
                "source_authority_code": "SYNTHETIC_AUTHORITY",
                "source_authority_name": "Synthetic Authority",
                "source_title": "Synthetic test source",
                "source_reference": "TEST-ONLY",
                "source_url": "https://example.invalid/test-only",
                "source_version": "test-1",
                "source_date": "2026-01-01",
                "jurisdiction_key": "GLOBAL",
                "review_status": review,
                "notes": "Synthetic fixture; not catalog content.",
            }
        ],
        "compatibility": {
            "title": "Synthetic legacy title",
            "description": None,
            "applicability_scope": "all",
            "allowed_formats": ["pdf"],
            "max_file_size_bytes": 1024,
            "max_active_file_count": 1,
            "sort_order": 0,
        },
    }


def _payload(definitions=None):
    result = {
        "schema_version": "1",
        "catalog_name": "synthetic-test-catalog",
        "catalog_version": "test-1",
        "jurisdiction_bundle": "synthetic-global",
        "source_bundle_version": "test-source-1",
        "checksum": "sha256:" + "0" * 64,
        "definitions": definitions or [_definition()],
    }
    result["checksum"] = checksum_for_payload(result)
    return result


def _load(tmp_path, payload=None):
    path = tmp_path / "synthetic-document-catalog.json"
    path.write_text(json.dumps(payload or _payload()), encoding="utf-8")
    return load_package(path)


def _apply(package, plan, **changes):
    arguments = {
        "environment": "test",
        "operator": "synthetic-test-operator",
        "approval_reference": "TEST-APPROVAL",
        "expected_checksum": package.checksum,
        "expected_plan_fingerprint": plan.database_fingerprint,
        "idempotency_key": "synthetic-run-1",
        "confirm": True,
    }
    arguments.update(changes)
    return apply_package(package, **arguments)


def test_schema_checksum_and_canonical_order_validation(package_app, tmp_path):
    payload = _payload([_definition("synthetic_b"), _definition("synthetic_a")])
    reordered = copy.deepcopy(payload)
    reordered["definitions"].reverse()
    assert checksum_for_payload(payload) == checksum_for_payload(reordered)
    changed = copy.deepcopy(payload)
    changed["definitions"][0]["name_en"] = "Changed"
    assert checksum_for_payload(payload) != checksum_for_payload(changed)
    assert _load(tmp_path, payload).checksum == payload["checksum"]

    for mutation in ("unknown", "bad_url", "duplicate"):
        invalid = _payload()
        if mutation == "unknown":
            invalid["unexpected"] = True
        elif mutation == "bad_url":
            invalid["definitions"][0]["provenance"][0]["source_url"] = "http://[invalid"
        else:
            invalid["definitions"].append(copy.deepcopy(invalid["definitions"][0]))
        invalid["checksum"] = checksum_for_payload(invalid)
        with pytest.raises(PackageValidationError):
            _load(tmp_path, invalid)


def test_plan_is_read_only_and_reports_create(package_app, tmp_path):
    package = _load(tmp_path)
    before = (
        DocumentDefinition.query.count(),
        ReferenceDataSeedRun.query.count(),
        DocumentCatalogAuditEvent.query.count(),
    )
    plan = plan_package(package, "test")
    assert plan.created_count == 1
    assert plan.conflict_count == 0
    assert before == (
        DocumentDefinition.query.count(),
        ReferenceDataSeedRun.query.count(),
        DocumentCatalogAuditEvent.query.count(),
    )


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"confirm": False}, "confirmation"),
        ({"operator": ""}, "operator"),
        ({"approval_reference": ""}, "approval"),
        ({"expected_checksum": "sha256:" + "f" * 64}, "checksum"),
        ({"expected_plan_fingerprint": "sha256:" + "f" * 64}, "fingerprint"),
        ({"environment": "unspecified"}, "environment"),
        ({"environment": "production"}, "production confirmation"),
    ],
)
def test_apply_prerequisites(package_app, tmp_path, changes, message):
    package = _load(tmp_path)
    plan = plan_package(package, "test")
    with pytest.raises(PackageApplyError, match=message):
        _apply(package, plan, **changes)
    assert DocumentDefinition.query.count() == 0


def test_apply_is_audited_idempotent_and_reapply_is_no_change(package_app, tmp_path):
    package = _load(tmp_path)
    plan = plan_package(package, "test")
    applied, run = _apply(package, plan)
    assert (applied.created_count, run.status) == (1, "succeeded")
    assert run.catalog_family == "DOCUMENT_MASTER"
    assert DocumentCatalogAuditEvent.query.count() == 1
    assert DocumentDefinition.query.one().is_required is False

    _, replay = _apply(package, plan)
    assert replay.public_id == run.public_id
    assert ReferenceDataSeedRun.query.count() == 1
    assert DocumentCatalogAuditEvent.query.count() == 1

    no_change = plan_package(package, "test")
    assert no_change.unchanged_count == 1
    second, second_run = _apply(
        package,
        no_change,
        idempotency_key="synthetic-run-2",
        expected_plan_fingerprint=no_change.database_fingerprint,
    )
    assert second.unchanged_count == 1
    assert second_run.created_count == second_run.updated_count == 0


def test_idempotency_key_cannot_be_reused_for_a_different_request(
    package_app, tmp_path
):
    package = _load(tmp_path)
    plan = plan_package(package, "test")
    _apply(package, plan)
    with pytest.raises(PackageApplyError, match="different request"):
        _apply(package, plan, approval_reference="OTHER")


def test_manual_definition_can_only_be_additively_enriched(package_app, tmp_path):
    definition = _definition()
    compatibility = definition["compatibility"]
    row = DocumentDefinition(
        code=definition["code"],
        title=compatibility["title"],
        description=compatibility["description"],
        allowed_formats='["pdf"]',
        max_file_size_bytes=1024,
        max_active_file_count=1,
        applicability_scope="all",
        sort_order=0,
        organization_overridable=True,
        is_required=False,
    )
    db.session.add(row)
    db.session.commit()
    package = _load(tmp_path)
    plan = plan_package(package, "test")
    assert plan.updated_count == 1
    _apply(package, plan)
    assert DocumentDefinition.query.one().name_en == "Synthetic document"

    conflicting = _payload()
    conflicting["definitions"][0]["compatibility"]["title"] = "Overwrite attempt"
    conflicting["checksum"] = checksum_for_payload(conflicting)
    conflict_plan = plan_package(_load(tmp_path, conflicting), "test")
    assert conflict_plan.conflict_count == 1


def test_alias_collision_and_missing_country_are_plan_conflicts(package_app, tmp_path):
    owner = DocumentDefinition(
        code="synthetic_owner",
        title="Owner",
        allowed_formats='["pdf"]',
        max_file_size_bytes=1024,
        max_active_file_count=1,
        applicability_scope="all",
        is_required=False,
    )
    db.session.add(owner)
    db.session.flush()
    db.session.add(
        DocumentDefinitionAlias(
            document_definition_id=owner.id,
            locale="en",
            display_value="synthetic_invoice alias",
            normalized_value="synthetic_invoice alias",
            alias_kind="COMMON_NAME",
        )
    )
    db.session.commit()
    package = _load(tmp_path)
    assert plan_package(package, "test").conflict_count == 1

    country_payload = _payload([_definition("synthetic_country")])
    country_payload["definitions"][0]["aliases"] = []
    country_payload["definitions"][0]["jurisdictions"] = [
        {"kind": "COUNTRY", "country_code": "ZZZ"}
    ]
    country_payload["checksum"] = checksum_for_payload(country_payload)
    assert plan_package(_load(tmp_path, country_payload), "test").conflict_count == 1


def test_active_requires_confirmed_provenance(package_app, tmp_path):
    payload = _payload()
    payload["definitions"][0]["lifecycle_target"] = "ACTIVE"
    payload["checksum"] = checksum_for_payload(payload)
    with pytest.raises(PackageValidationError, match="confirmed"):
        _load(tmp_path, payload)


def test_unsafe_lifecycle_is_a_sanitized_conflict(package_app, tmp_path):
    definition = _definition()
    compatibility = definition["compatibility"]
    row = DocumentDefinition(
        code=definition["code"],
        title=compatibility["title"],
        description=compatibility["description"],
        name_fa=definition["name_fa"],
        name_en=definition["name_en"],
        family_code=definition["family"],
        allowed_formats='["pdf"]',
        max_file_size_bytes=1024,
        max_active_file_count=1,
        applicability_scope="all",
        sort_order=0,
        organization_overridable=True,
        catalog_lifecycle_status="ACTIVE",
        source_review_status="SOURCE_CONFIRMATION_REQUIRED",
        is_required=False,
    )
    db.session.add(row)
    db.session.commit()
    package = _load(tmp_path)
    item = plan_package(package, "test").definitions[0]
    assert item.action == "CONFLICT"
    assert item.conflicts == ["unsafe lifecycle change"]
    assert "Synthetic legacy title" not in json.dumps(item.as_dict())


def test_cli_exit_codes_and_machine_readable_plan(package_app, tmp_path, capsys):
    package_path = tmp_path / "synthetic-cli.json"
    package_path.write_text(json.dumps(_payload()), encoding="utf-8")
    assert cli_main(["plan", "--file", str(package_path)], app=package_app) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["created_count"] == 1
    assert output["checksum"].startswith("sha256:")
    assert cli_main(["apply", "--file", str(package_path)], app=package_app) == 2
    assert "REFUSED" in capsys.readouterr().err


def test_apply_rolls_back_catalog_writes_and_persists_sanitized_failure(
    package_app, tmp_path
):
    package = _load(tmp_path)
    plan = plan_package(package, "test")

    def fail():
        raise RuntimeError("sensitive synthetic detail")

    with pytest.raises(PackageApplyError, match="rolled back"):
        _apply(package, plan, failure_hook=fail)
    assert DocumentDefinition.query.count() == 0
    run = ReferenceDataSeedRun.query.one()
    assert run.status == "failed"
    assert "sensitive" not in run.error_summary


def test_omitted_existing_definition_is_untouched(package_app, tmp_path):
    row = DocumentDefinition(
        code="synthetic_out_of_scope",
        title="Untouched",
        allowed_formats='["pdf"]',
        max_file_size_bytes=1024,
        max_active_file_count=1,
        applicability_scope="all",
        is_required=True,
    )
    db.session.add(row)
    db.session.commit()
    package = _load(tmp_path)
    plan = plan_package(package, "test")
    _apply(package, plan)
    db.session.refresh(row)
    assert row.title == "Untouched"
    assert row.is_required is True
