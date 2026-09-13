"""CLI regression coverage for governed external-reference initialization."""

from __future__ import annotations

import json

import pytest

from backend import create_app
from backend.extensions import db
from backend.external_reference_models import ExternalReferenceType
from backend.external_reference_type_cli import PACKAGE_PATH, main
from backend.external_reference_type_package import load_package, plan_package
from backend.external_reference_type_package import PackageApplyError
from backend.models import ExpertUser


@pytest.fixture()
def cli_app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"}, skip_startup=True)
    with app.app_context():
        db.create_all()
        admin = ExpertUser(username="reference-platform-admin", password_hash="x", full_name="Admin", authority="PLATFORM_ADMIN", is_active=True)
        expert = ExpertUser(username="reference-expert", password_hash="x", full_name="Expert", authority="EXPERT", is_active=True)
        db.session.add_all([admin, expert]); db.session.commit()
        yield app, admin.id, expert.id
        db.session.remove(); db.drop_all()


def _apply_args(app, actor_id, key):
    with app.app_context():
        package = load_package(PACKAGE_PATH)
        plan = plan_package(package, "development")
    return ["apply", "--confirm", "--operator", "Release operator", "--approval-reference", "ADR-039", "--actor-id", str(actor_id), "--expected-checksum", package.checksum, "--expected-plan-fingerprint", plan.database_fingerprint, "--idempotency-key", key]


def test_cli_creates_only_authoritative_types_and_is_idempotent(cli_app, capsys):
    app, admin_id, _ = cli_app
    assert main(_apply_args(app, admin_id, "reference-cli-1"), app=app) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["created_count"] == 3
    with app.app_context():
        assert {(row.code, row.lifecycle_status, row.allows_operational_shipment) for row in ExternalReferenceType.query.all()} == {
            ("BILL_OF_LADING_NUMBER", "ACTIVE", True), ("AIR_WAYBILL_NUMBER", "ACTIVE", True), ("CMR_NUMBER", "ACTIVE", True),
        }
    assert main(_apply_args(app, admin_id, "reference-cli-2"), app=app) == 0
    assert json.loads(capsys.readouterr().out)["unchanged_count"] == 3


def test_cli_rejects_non_platform_admin_without_writes(cli_app):
    app, _, expert_id = cli_app
    with pytest.raises(PackageApplyError, match="Platform Admin"):
        main(_apply_args(app, expert_id, "reference-cli-denied"), app=app)
    with app.app_context():
        assert ExternalReferenceType.query.count() == 0
