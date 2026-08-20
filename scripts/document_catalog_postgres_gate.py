"""Certify ADR-036 Slice 1 on an explicitly supplied disposable PostgreSQL database."""

from __future__ import annotations

import os
from pathlib import Path
import sys
from uuid import uuid4

from alembic import command
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.migration_runtime import alembic_config, prepare_version_table_for_upgrade  # noqa: E402

PREDECESSOR = "20260830_logistics_point_tracking_convergence"
HEAD = "20260831_document_catalog_metadata"
url = make_url(os.environ["DOCUMENT_CATALOG_CERT_DATABASE_URL"])
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
engine = create_engine(url)
public_id = str(uuid4())

with engine.begin() as connection:
    connection.execute(
        text(
            "INSERT INTO document_definition (public_id,code,title,description,is_required,allowed_formats,max_file_size_bytes,max_active_file_count,sort_order,is_active,applicability_scope,revision,created_at,updated_at) VALUES (:public_id,'preexisting_document','Legacy title','Legacy description',true,'[\"pdf\"]',1024,1,7,true,'all',3,now(),now())"
        ),
        {"public_id": public_id},
    )
    definition_id = connection.execute(
        text("SELECT id FROM document_definition WHERE public_id=:public_id"),
        {"public_id": public_id},
    ).scalar_one()
    before_policy = connection.execute(
        text("SELECT count(*) FROM organization_document_requirement")
    ).scalar_one()

command.upgrade(config, HEAD)
with engine.connect() as connection:
    inspector = inspect(connection)
    assert (
        connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        == HEAD
    )
    expected_tables = {
        "document_definition_alias",
        "document_definition_jurisdiction",
        "document_definition_mode",
        "document_definition_stage",
        "document_definition_business_scope",
        "document_definition_provenance",
        "document_catalog_audit_event",
    }
    assert expected_tables.issubset(set(inspector.get_table_names()))
    row = (
        connection.execute(
            text(
                "SELECT public_id,code,title,description,is_required,applicability_scope,revision,name_fa,family_code,catalog_lifecycle_status,source_review_status FROM document_definition WHERE id=:id"
            ),
            {"id": definition_id},
        )
        .mappings()
        .one()
    )
    assert (
        row["public_id"] == public_id
        and row["code"] == "preexisting_document"
        and row["title"] == "Legacy title"
    )
    assert (
        row["description"] == "Legacy description"
        and row["is_required"] is True
        and row["applicability_scope"] == "all"
        and row["revision"] == 3
    )
    assert row["name_fa"] is None and row["family_code"] is None
    assert (
        row["catalog_lifecycle_status"] == "DRAFT"
        and row["source_review_status"] == "SOURCE_CONFIRMATION_REQUIRED"
    )
    assert (
        connection.execute(
            text("SELECT count(*) FROM organization_document_requirement")
        ).scalar_one()
        == before_policy
    )
    constraints = {
        item[0]
        for item in connection.execute(
            text(
                "SELECT conname FROM pg_constraint WHERE conrelid='document_definition'::regclass"
            )
        )
    }
    assert {
        "ck_document_definition_family",
        "ck_document_definition_catalog_lifecycle",
        "ck_document_definition_source_review",
    }.issubset(constraints)
    alias_uniques = {
        item["name"]
        for item in inspector.get_unique_constraints("document_definition_alias")
    }
    assert "uq_document_definition_alias_normalized" in alias_uniques

command.downgrade(config, PREDECESSOR)
with engine.connect() as connection:
    inspector = inspect(connection)
    assert (
        connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        == PREDECESSOR
    )
    assert not inspector.has_table("document_definition_alias")
    columns = {item["name"] for item in inspector.get_columns("document_definition")}
    assert "name_fa" not in columns and "catalog_lifecycle_status" not in columns
    row = connection.execute(
        text(
            "SELECT public_id,code,title,revision FROM document_definition WHERE id=:id"
        ),
        {"id": definition_id},
    ).one()
    assert tuple(row) == (public_id, "preexisting_document", "Legacy title", 3)

command.upgrade(config, HEAD)
with engine.connect() as connection:
    assert (
        connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        == HEAD
    )
    assert inspect(connection).has_table("document_definition_provenance")
    assert (
        connection.execute(
            text("SELECT count(*) FROM organization_document_requirement")
        ).scalar_one()
        == before_policy
    )
engine.dispose()
print(
    "document-catalog-postgresql-gate=PASS upgrade=PASS downgrade=PASS reupgrade=PASS preservation=PASS constraints=PASS policy_creation=ZERO"
)
