"""Certify the Slice 2 package engine on disposable loopback PostgreSQL."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

from alembic import command
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend import create_app  # noqa: E402
from backend.document_catalog_package import (  # noqa: E402
    PackageApplyError,
    apply_package,
    checksum_for_payload,
    load_package,
    plan_package,
)
from backend.extensions import db  # noqa: E402
from backend.migration_runtime import (  # noqa: E402
    alembic_config,
    prepare_version_table_for_upgrade,
)
from backend.models import (  # noqa: E402
    DocumentCatalogAuditEvent,
    DocumentDefinition,
    DocumentDefinitionAlias,
    DocumentDefinitionBusinessScope,
    DocumentDefinitionJurisdiction,
    DocumentDefinitionMode,
    DocumentDefinitionProvenance,
    DocumentDefinitionStage,
    ReferenceDataSeedRun,
)

PREDECESSOR = "20260831_document_catalog_metadata"
HEAD = "20260901_document_catalog_runs"
url = make_url(os.environ["DOCUMENT_CATALOG_PACKAGE_CERT_DATABASE_URL"])
if url.get_backend_name() != "postgresql" or url.host not in {
    "127.0.0.1",
    "localhost",
    "::1",
}:
    raise SystemExit("Refusing: gate requires disposable loopback PostgreSQL")

rendered = url.render_as_string(hide_password=False)
config = alembic_config(rendered)
prepare_version_table_for_upgrade(rendered, config)
command.upgrade(config, PREDECESSOR)
command.upgrade(config, HEAD)
engine = create_engine(url)
with engine.connect() as connection:
    assert (
        connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        == HEAD
    )
    columns = {
        item["name"]
        for item in inspect(connection).get_columns("reference_data_seed_run")
    }
    assert {
        "catalog_family",
        "catalog_name",
        "schema_version",
        "source_bundle_version",
        "updated_count",
        "idempotency_key",
        "request_hash",
    }.issubset(columns)


def definition(code: str) -> dict:
    return {
        "code": code,
        "name_fa": "سند آزمایشی",
        "name_en": "Synthetic certification document",
        "family": "COMMERCIAL",
        "description_fa": None,
        "description_en": None,
        "reference_number_label_fa": None,
        "reference_number_label_en": None,
        "expiry_applicable": None,
        "organization_overridable": True,
        "lifecycle_target": "DRAFT",
        "source_review_status": "SOURCE_CONFIRMATION_REQUIRED",
        "aliases": [],
        "jurisdictions": [{"kind": "GLOBAL"}],
        "transport_modes": ["MODE_INDEPENDENT"],
        "process_stages": ["PRE_SHIPMENT"],
        "business_scopes": ["REQUEST"],
        "provenance": [],
        "compatibility": {
            "title": "Synthetic certification title",
            "description": None,
            "applicability_scope": "all",
            "allowed_formats": ["pdf"],
            "max_file_size_bytes": 1024,
            "max_active_file_count": 1,
            "sort_order": 0,
        },
    }


def package_payload(code: str) -> dict:
    payload = {
        "schema_version": "1",
        "catalog_name": "synthetic-postgresql-certification",
        "catalog_version": "test-1",
        "jurisdiction_bundle": "synthetic-global",
        "source_bundle_version": "test-source-1",
        "checksum": "sha256:" + "0" * 64,
        "definitions": [definition(code)],
    }
    payload["checksum"] = checksum_for_payload(payload)
    return payload


app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": rendered})
with TemporaryDirectory() as temporary_directory, app.app_context():
    path = Path(temporary_directory) / "synthetic-package.json"
    path.write_text(
        json.dumps(package_payload("synthetic_pg_success")), encoding="utf-8"
    )
    package = load_package(path)
    plan = plan_package(package, "test")
    assert plan.created_count == 1
    applied, run = apply_package(
        package,
        environment="test",
        operator="postgres-certification",
        approval_reference="SYNTHETIC-CERT",
        expected_checksum=package.checksum,
        expected_plan_fingerprint=plan.database_fingerprint,
        idempotency_key="synthetic-pg-success-1",
        confirm=True,
    )
    assert applied.created_count == 1 and run.status == "succeeded"
    no_change = plan_package(package, "test")
    assert no_change.unchanged_count == 1
    _, repeated_run = apply_package(
        package,
        environment="test",
        operator="postgres-certification",
        approval_reference="SYNTHETIC-CERT",
        expected_checksum=package.checksum,
        expected_plan_fingerprint=no_change.database_fingerprint,
        idempotency_key="synthetic-pg-success-2",
        confirm=True,
    )
    assert repeated_run.created_count == repeated_run.updated_count == 0

    path.write_text(
        json.dumps(package_payload("synthetic_pg_rollback")), encoding="utf-8"
    )
    rollback_package = load_package(path)
    rollback_plan = plan_package(rollback_package, "test")
    try:
        apply_package(
            rollback_package,
            environment="test",
            operator="postgres-certification",
            approval_reference="SYNTHETIC-CERT",
            expected_checksum=rollback_package.checksum,
            expected_plan_fingerprint=rollback_plan.database_fingerprint,
            idempotency_key="synthetic-pg-rollback-1",
            confirm=True,
            failure_hook=lambda: (_ for _ in ()).throw(RuntimeError("synthetic")),
        )
    except PackageApplyError:
        pass
    else:
        raise AssertionError("forced rollback unexpectedly succeeded")
    assert DocumentDefinition.query.filter_by(code="synthetic_pg_rollback").count() == 0

try:
    command.downgrade(config, PREDECESSOR)
except RuntimeError as exc:
    assert "evidence exists" in str(exc)
else:
    raise AssertionError("evidence-bearing downgrade was not refused")

with app.app_context():
    synthetic_ids = [
        item.id
        for item in DocumentDefinition.query.filter(
            DocumentDefinition.code.like("synthetic_pg_%")
        ).all()
    ]
    DocumentCatalogAuditEvent.query.filter(
        DocumentCatalogAuditEvent.definition_code.like("synthetic_pg_%")
    ).delete(synchronize_session=False)
    for relation_model in (
        DocumentDefinitionAlias,
        DocumentDefinitionJurisdiction,
        DocumentDefinitionMode,
        DocumentDefinitionStage,
        DocumentDefinitionBusinessScope,
        DocumentDefinitionProvenance,
    ):
        relation_model.query.filter(
            relation_model.document_definition_id.in_(synthetic_ids)
        ).delete(synchronize_session=False)
    DocumentDefinition.query.filter(
        DocumentDefinition.code.like("synthetic_pg_%")
    ).delete(synchronize_session=False)
    ReferenceDataSeedRun.query.filter_by(catalog_family="DOCUMENT_MASTER").delete(
        synchronize_session=False
    )
    db.session.commit()

command.downgrade(config, PREDECESSOR)
command.upgrade(config, HEAD)
with engine.connect() as connection:
    assert (
        connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        == HEAD
    )
engine.dispose()
print(
    "document-catalog-package-postgresql-gate=PASS migration=PASS apply=PASS "
    "reapply=NO_CHANGE rollback=PASS downgrade-refusal=PASS reupgrade=PASS"
)
