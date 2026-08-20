import copy
import json
from pathlib import Path

import pytest

from backend import create_app
from backend.extensions import db
from backend.external_reference_models import ExternalReferenceType
from backend.external_reference_type_package import (
    PackageApplyError,
    PackageValidationError,
    apply_package,
    checksum_for_payload,
    load_package,
    plan_package,
)
from backend.models import ExpertUser, ReferenceDataSeedRun


PACKAGE_PATH = (
    Path(__file__).parents[1]
    / "reference_data"
    / "external_references"
    / "external-reference-types-v1.0.0.json"
)


@pytest.fixture()
def package_app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SQLALCHEMY_ENGINE_OPTIONS": {},
        }
    )
    with app.app_context():
        db.create_all()
        actor = ExpertUser(
            username="external-reference-package-operator",
            password_hash="disabled-test-account",
            full_name="Package Operator",
            authority="PLATFORM_ADMIN",
            is_active=False,
        )
        db.session.add(actor)
        db.session.commit()
        app.config["PACKAGE_ACTOR_ID"] = actor.id
    return app


def _apply(package, actor_id, key, fingerprint):
    return apply_package(
        package,
        environment="testing",
        operator="External reference package test",
        approval_reference="ADR-039 test approval",
        expected_checksum=package.checksum,
        expected_plan_fingerprint=fingerprint,
        idempotency_key=key,
        confirm=True,
        actor_id=actor_id,
    )


def test_reviewed_package_checksum_and_clean_plan(package_app):
    with package_app.app_context():
        package = load_package(PACKAGE_PATH)
        plan = plan_package(package, "testing")

        assert package.checksum == checksum_for_payload(package.payload)
        assert {item["code"] for item in package.definitions} == {
            "BILL_OF_LADING_NUMBER",
            "AIR_WAYBILL_NUMBER",
            "CMR_NUMBER",
        }
        assert plan.created_count == 3
        assert plan.unchanged_count == plan.conflict_count == 0
        assert ExternalReferenceType.query.count() == 0
        assert ReferenceDataSeedRun.query.count() == 0


def test_apply_replay_no_change_and_request_hash_conflict(package_app):
    with package_app.app_context():
        package = load_package(PACKAGE_PATH)
        plan = plan_package(package, "testing")
        _, run = _apply(
            package,
            package_app.config["PACKAGE_ACTOR_ID"],
            "package-apply-1",
            plan.database_fingerprint,
        )
        _, replay = _apply(
            package,
            package_app.config["PACKAGE_ACTOR_ID"],
            "package-apply-1",
            plan.database_fingerprint,
        )

        converged = plan_package(package, "testing")
        assert run.public_id == replay.public_id
        assert run.status == "succeeded"
        assert ExternalReferenceType.query.count() == 3
        assert converged.created_count == converged.conflict_count == 0
        assert converged.unchanged_count == 3
        assert {row.revision for row in ExternalReferenceType.query.all()} == {1}

        with pytest.raises(PackageApplyError, match="different request"):
            apply_package(
                package,
                environment="testing",
                operator="External reference package test",
                approval_reference="changed approval",
                expected_checksum=package.checksum,
                expected_plan_fingerprint=plan.database_fingerprint,
                idempotency_key="package-apply-1",
                confirm=True,
                actor_id=package_app.config["PACKAGE_ACTOR_ID"],
            )


def test_invalid_fourth_type_and_checksum_fail_closed(package_app, tmp_path):
    payload = json.loads(PACKAGE_PATH.read_text(encoding="utf-8"))
    payload["definitions"].append(
        {**copy.deepcopy(payload["definitions"][0]), "code": "COTAGE_NUMBER"}
    )
    payload["checksum"] = checksum_for_payload(payload)
    candidate = tmp_path / "invalid.json"
    candidate.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    with package_app.app_context():
        with pytest.raises(PackageValidationError, match="schema validation failed"):
            load_package(candidate)
        assert ExternalReferenceType.query.count() == 0


def test_mid_apply_failure_rolls_back_catalog_rows(package_app):
    with package_app.app_context():
        package = load_package(PACKAGE_PATH)
        plan = plan_package(package, "testing")

        def fail():
            raise RuntimeError("synthetic package failure")

        with pytest.raises(PackageApplyError, match="rolled back"):
            apply_package(
                package,
                environment="testing",
                operator="External reference package test",
                approval_reference="ADR-039 rollback test",
                expected_checksum=package.checksum,
                expected_plan_fingerprint=plan.database_fingerprint,
                idempotency_key="package-rollback-1",
                confirm=True,
                actor_id=package_app.config["PACKAGE_ACTOR_ID"],
                failure_hook=fail,
            )

        run = ReferenceDataSeedRun.query.one()
        assert run.status == "failed"
        assert ExternalReferenceType.query.count() == 0
