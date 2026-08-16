"""Certify Organization hostname routing on disposable loopback PostgreSQL."""

import os
from pathlib import Path
import sys

from alembic import command
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.migration_runtime import alembic_config, prepare_version_table_for_upgrade


url = make_url(os.environ["V195_CERT_DATABASE_URL"])
if url.get_backend_name() != "postgresql" or url.host not in {
    "127.0.0.1",
    "localhost",
    "::1",
}:
    raise SystemExit("Refusing: gate requires disposable loopback PostgreSQL")

rendered_url = url.render_as_string(hide_password=False)
config = alembic_config(rendered_url)
prepare_version_table_for_upgrade(rendered_url, config)
command.upgrade(config, "20260826_org_document_policy")
engine = create_engine(url)

with engine.connect() as connection:
    assert connection.execute(text("select version_num from alembic_version")).scalar_one() == "20260826_org_document_policy"
    organization_count = connection.execute(text("select count(*) from operational_organization")).scalar_one()
    request_count = connection.execute(text("select count(*) from shipment_request")).scalar_one()

command.upgrade(config, "20260827_org_hostname")
with engine.connect() as connection:
    assert connection.execute(text("select version_num from alembic_version")).scalar_one() == "20260827_org_hostname"
    assert connection.execute(text("select count(*) from organization_hostname")).scalar_one() == 0
    assert connection.execute(text("select count(*) from operational_organization")).scalar_one() == organization_count == 0
    assert connection.execute(text("select count(*) from shipment_request")).scalar_one() == request_count == 0
    columns = {
        column["name"]: column
        for column in inspect(connection).get_columns("organization_hostname")
    }
    assert set(columns) == {
        "id", "public_id", "organization_id", "hostname", "is_primary",
        "is_active", "created_at", "updated_at",
    }
    assert not columns["organization_id"]["nullable"]
    assert not columns["hostname"]["nullable"]
    indexes = {
        index["name"]: index
        for index in inspect(connection).get_indexes("organization_hostname")
    }
    assert indexes["uq_organization_hostname_active_hostname"]["unique"]
    assert indexes["uq_organization_hostname_primary"]["unique"]
    constraints = {
        row[0]
        for row in connection.execute(
            text(
                "select conname from pg_constraint "
                "where conrelid='organization_hostname'::regclass"
            )
        )
    }
    assert "ck_organization_hostname_lowercase" in constraints
    assert "uq_organization_hostname_public_id" in constraints

command.downgrade(config, "20260826_org_document_policy")
with engine.connect() as connection:
    assert connection.execute(text("select version_num from alembic_version")).scalar_one() == "20260826_org_document_policy"
    assert not inspect(connection).has_table("organization_hostname")
    assert connection.execute(text("select count(*) from operational_organization")).scalar_one() == 0
    assert connection.execute(text("select count(*) from shipment_request")).scalar_one() == 0

command.upgrade(config, "20260827_org_hostname")
with engine.connect() as connection:
    assert connection.execute(text("select version_num from alembic_version")).scalar_one() == "20260827_org_hostname"
    assert inspect(connection).has_table("organization_hostname")
    assert connection.execute(text("select count(*) from organization_hostname")).scalar_one() == 0

engine.dispose()
print(
    "organization-hostname-postgresql-gate=PASS "
    "upgrade=PASS downgrade=PASS reupgrade=PASS constraints=PASS "
    "ownership_backfill=NONE"
)
