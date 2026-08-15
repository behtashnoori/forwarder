"""Certify the organization document policy migration on disposable loopback PostgreSQL."""
import os
from pathlib import Path
import sys
import uuid

from alembic import command
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.migration_runtime import alembic_config, prepare_version_table_for_upgrade

load_dotenv(ROOT / ".env")
base = make_url(os.environ["DATABASE_URL"])
if base.get_backend_name() != "postgresql" or base.host not in {"127.0.0.1", "localhost", "::1"}:
    raise SystemExit("Refusing: gate requires loopback PostgreSQL")
name = f"forwarder_integrated_cert_org_policy_{uuid.uuid4().hex[:8]}"
gate = base.set(database=name)
admin = create_engine(base.set(database="postgres"), isolation_level="AUTOCOMMIT")
with admin.connect() as connection:
    connection.exec_driver_sql(f'CREATE DATABASE "{name}"')
try:
    url = gate.render_as_string(hide_password=False)
    config = alembic_config(url)
    prepare_version_table_for_upgrade(url, config)
    command.upgrade(config, "20260825_admin_multitenant")
    command.upgrade(config, "20260826_org_document_policy")
    engine = create_engine(gate)
    with engine.connect() as connection:
        assert connection.execute(text("select version_num from alembic_version")).scalar_one() == "20260826_org_document_policy"
        columns = {column["name"]: column for column in inspect(connection).get_columns("organization_document_requirement")}
        assert columns["organization_id"]["nullable"] is False
        assert columns["document_definition_id"]["nullable"] is False
        assert columns["requirement_level"]["nullable"] is False
        uniques = {tuple(item["column_names"]) for item in inspect(connection).get_unique_constraints("organization_document_requirement")}
        assert ("organization_id", "document_definition_id") in uniques
    engine.dispose()
    command.downgrade(config, "20260825_admin_multitenant")
    command.upgrade(config, "20260826_org_document_policy")
    print("organization-document-policy-postgresql-gate=PASS")
finally:
    with admin.connect() as connection:
        connection.execute(text("select pg_terminate_backend(pid) from pg_stat_activity where datname=:name and pid<>pg_backend_pid()"), {"name": name})
        connection.exec_driver_sql(f'DROP DATABASE IF EXISTS "{name}"')
    admin.dispose()
