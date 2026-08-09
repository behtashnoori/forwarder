"""Create an explicitly local disposable PostgreSQL DB and verify FE-2 migration."""
import os
from pathlib import Path
import sys
import uuid

from alembic import command
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.migration_runtime import alembic_config, prepare_version_table_for_upgrade

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
base=make_url(os.environ["DATABASE_URL"])
if base.get_backend_name()!="postgresql" or base.host not in {"127.0.0.1","localhost"}:
    raise SystemExit("Refusing: FE-2 gate requires an explicitly local PostgreSQL server")
name=f"forwarder_fe2_gate_{uuid.uuid4().hex[:8]}"
gate=base.set(database=name)
admin=create_engine(base.set(database="postgres"),isolation_level="AUTOCOMMIT")
with admin.connect() as connection:
    connection.execute(text(f'CREATE DATABASE "{name}"'))
try:
    url=gate.render_as_string(hide_password=False);cfg=alembic_config(url);prepare_version_table_for_upgrade(url,cfg);command.upgrade(cfg,"head")
    engine=create_engine(gate)
    with engine.connect() as connection:
        revision=connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        tables={row[0] for row in connection.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name LIKE 'economic_%'"))}
    assert revision=="20260818_immutable_fx_provenance"
    assert tables=={"economic_line","economic_observation","economic_observation_fx","economic_evidence_association","economic_fx_rate","economic_audit"}
    try: command.downgrade(cfg,"20260816_oip_projection_health")
    except RuntimeError as exc: assert "fail-closed" in str(exc).lower() or "downgrade refused" in str(exc).lower()
    else: raise AssertionError("FE-2 downgrade did not fail closed")
    print(f"FE-2 PostgreSQL migration gate passed: {revision}; tables={len(tables)}; downgrade=fail-closed")
finally:
    with admin.connect() as connection:
        connection.execute(text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=:name AND pid<>pg_backend_pid()"),{"name":name})
        connection.execute(text(f'DROP DATABASE "{name}"'))
