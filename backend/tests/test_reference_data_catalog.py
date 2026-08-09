import hashlib
import json

import pytest

from backend import create_app
from backend.extensions import db
from backend.models import CargoType, ReferenceDataSeedRun, ServiceType, UnitOfMeasure
from backend.reference_data_catalog import (
    CATALOG_PATH,
    CatalogApplyError,
    CatalogValidationError,
    apply_catalog,
    load_catalog,
    plan_catalog,
)
from backend.reference_data_cli import main as cli_main


@pytest.fixture()
def app():
    app = create_app(
        {
            "TESTING": True,
            "APP_ENV": "testing",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SECRET_KEY": "reference-catalog-test",
        },
        skip_startup=True,
    )
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def _rewrite_catalog(tmp_path, mutate):
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    mutate(payload)
    unsigned = {key: value for key, value in payload.items() if key != "checksum"}
    encoded = json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    payload["checksum"] = "sha256:" + hashlib.sha256(encoded).hexdigest()
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def test_approved_catalog_is_exact_valid_and_excludes_deferred_values():
    catalog = load_catalog()
    assert catalog.planned_count == 36
    assert len(catalog.resources["cargo_types"]) == 15
    assert len(catalog.resources["service_types"]) == 12
    assert len(catalog.resources["units_of_measure"]) == 9
    codes = {row["code"] for rows in catalog.resources.values() for row in rows}
    assert "CARGO_GENERAL_GOODS" not in codes
    assert "SERVICE_PROJECT_LOGISTICS" not in codes
    assert not {"SERVICE_ROAD_FREIGHT", "SERVICE_RAIL_FREIGHT", "SERVICE_SEA_FREIGHT", "SERVICE_AIR_FREIGHT"} & codes
    symbols = {row["code"]: row["symbol"] for row in catalog.resources["units_of_measure"]}
    assert symbols == {
        "UOM_PIECE": "pcs", "UOM_GRAM": "g", "UOM_KILOGRAM": "kg",
        "UOM_METRIC_TON": "t", "UOM_LITER": "L", "UOM_CUBIC_METER": "m³",
        "UOM_CENTIMETER": "cm", "UOM_METER": "m", "UOM_KILOMETER": "km",
    }


def test_checksum_invalid_dimension_and_missing_parent_fail_validation(tmp_path):
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    payload["cargo_types"][0]["en_name"] = "Tampered"
    bad_checksum = tmp_path / "bad-checksum.json"
    bad_checksum.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(CatalogValidationError, match="checksum"):
        load_catalog(bad_checksum)

    bad_dimension = _rewrite_catalog(
        tmp_path,
        lambda data: data["units_of_measure"][0].update(measurement_dimension="INVALID"),
    )
    with pytest.raises(CatalogValidationError, match="dimension"):
        load_catalog(bad_dimension)

    missing_parent = _rewrite_catalog(
        tmp_path,
        lambda data: data["cargo_types"][0].update(parent_code="CARGO_MISSING"),
    )
    with pytest.raises(CatalogValidationError, match="missing catalog parent"):
        load_catalog(missing_parent)


def test_plan_first_apply_and_repeated_apply_are_idempotent(app):
    catalog = load_catalog()
    with app.app_context():
        first_plan = plan_catalog(catalog, "testing")
        assert (first_plan.created_count, first_plan.unchanged_count, first_plan.conflict_count) == (36, 0, 0)
        assert ReferenceDataSeedRun.query.count() == 0  # plan is read-only

        first, first_run = apply_catalog(
            catalog, environment="testing", executed_by="qa.operator",
            approval_reference="REL-1.5.0-QA",
            expected_checksum=catalog.checksum,
        )
        assert first_run.status == "succeeded" and first_run.created_count == 36
        assert (CargoType.query.count(), ServiceType.query.count(), UnitOfMeasure.query.count()) == (15, 12, 9)

        second, second_run = apply_catalog(
            catalog, environment="testing", executed_by="qa.operator",
            approval_reference="REL-1.5.0-QA",
            expected_checksum=catalog.checksum,
        )
        assert (second.created_count, second.unchanged_count, second.conflict_count) == (0, 36, 0)
        assert second_run.status == "succeeded" and second_run.created_count == 0
        assert ReferenceDataSeedRun.query.count() == 2
        assert (CargoType.query.count(), ServiceType.query.count(), UnitOfMeasure.query.count()) == (15, 12, 9)


@pytest.mark.parametrize("inactive", [False, True])
def test_conflicting_or_inactive_existing_code_refuses_all_writes(app, inactive):
    catalog = load_catalog()
    with app.app_context():
        entry = catalog.resources["service_types"][0]
        db.session.add(ServiceType(
            immutable_code=entry["code"], fa_name=entry["fa_name"], en_name="Drifted",
            description=entry["description"], display_order=entry["display_order"], is_active=not inactive,
        ))
        db.session.commit()
        plan, run = apply_catalog(
            catalog, environment="testing", executed_by="qa.operator",
            approval_reference="REL-1.5.0-QA",
            expected_checksum=catalog.checksum,
        )
        assert plan.conflict_count == 1
        assert run.status == "refused" and run.conflict_count == 1
        assert CargoType.query.count() == 0 and UnitOfMeasure.query.count() == 0
        assert ServiceType.query.count() == 1


def test_same_title_different_code_is_reported_as_possible_duplicate(app):
    catalog = load_catalog()
    with app.app_context():
        entry = catalog.resources["service_types"][0]
        db.session.add(ServiceType(
            immutable_code="SERVICE_MANUAL_DUPLICATE", fa_name=entry["fa_name"],
            en_name="Manual duplicate", description="Manual", display_order=999, is_active=True,
        ))
        db.session.commit()
        plan = plan_catalog(catalog, "testing")
        assert plan.conflict_count == 1
        assert plan.conflicts[0]["reason"] == "same title exists under a different code"


def test_apply_rolls_back_catalog_writes_and_persists_sanitized_failure(app):
    catalog = load_catalog()
    with app.app_context():
        def fail():
            raise RuntimeError("sensitive driver detail must not persist")

        with pytest.raises(CatalogApplyError, match="rolled back"):
            apply_catalog(
                catalog, environment="testing", executed_by="qa.operator",
                approval_reference="REL-1.5.0-QA",
                expected_checksum=catalog.checksum, failure_hook=fail,
            )
        assert (CargoType.query.count(), ServiceType.query.count(), UnitOfMeasure.query.count()) == (0, 0, 0)
        run = ReferenceDataSeedRun.query.one()
        assert run.status == "failed"
        assert run.created_count == 0
        assert "sensitive" not in run.error_summary
        assert "RuntimeError" in run.error_summary


def test_checksum_and_operator_are_required(app):
    catalog = load_catalog()
    with app.app_context():
        with pytest.raises(CatalogApplyError, match="checksum"):
            apply_catalog(
                catalog, environment="testing", executed_by="qa.operator",
                approval_reference="REL-1.5.0-QA",
                expected_checksum="sha256:" + ("0" * 64),
            )
        with pytest.raises(CatalogApplyError, match="operator"):
            apply_catalog(
                catalog, environment="testing", executed_by=" ",
                approval_reference="REL-1.5.0-QA",
                expected_checksum=catalog.checksum,
            )
        assert ReferenceDataSeedRun.query.count() == 0


def test_cli_plan_confirmation_and_production_guards(app, capsys, tmp_path):
    catalog = load_catalog()
    assert cli_main(["plan"], app=app) == 0
    assert '"created_count": 36' in capsys.readouterr().out
    with app.app_context():
        assert ReferenceDataSeedRun.query.count() == 0
    assert cli_main(["apply"], app=app) == 2
    assert "requires --confirm" in capsys.readouterr().err

    production = create_app(
        {
            "TESTING": True,
            "APP_ENV": "production",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SECRET_KEY": "reference-catalog-test",
            "DOCUMENT_STORAGE_ROOT": str(tmp_path / "production-documents"),
        },
        skip_startup=True,
    )
    with production.app_context():
        db.create_all()
        assert cli_main([
            "apply", "--confirm", "--operator", "ops.named",
            "--approval-reference", "REL-1.5.0-QA",
            "--expected-checksum", catalog.checksum,
        ], app=production) == 2
        assert "Production" in capsys.readouterr().err
        assert ReferenceDataSeedRun.query.count() == 0
        db.drop_all()

    unknown = create_app(
        {
            "TESTING": True,
            "APP_ENV": "unknown-environment",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SECRET_KEY": "reference-catalog-test",
        },
        skip_startup=True,
    )
    with unknown.app_context():
        db.create_all()
        assert cli_main([
            "apply", "--confirm", "--operator", "ops.named",
            "--approval-reference", "REL-1.5.0-QA",
            "--expected-checksum", catalog.checksum,
        ], app=unknown) == 2
        assert "recognized explicit environment" in capsys.readouterr().err
        assert ReferenceDataSeedRun.query.count() == 0
        db.drop_all()
