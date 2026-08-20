"""Create, certify, and remove a disposable local ADR-038 database."""
from __future__ import annotations

import os
from pathlib import Path
import runpy
import sys
from uuid import uuid4

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

base = make_url(os.environ["DATABASE_URL"])
if base.get_backend_name() != "postgresql" or base.host not in {"127.0.0.1", "localhost", "::1"}:
    raise SystemExit("Refusing: certification requires loopback PostgreSQL")

database_name = f"forwarder_request_identity_cert_{uuid4().hex[:12]}"
admin_url = base.set(database="postgres")
target_url = base.set(database=database_name)
admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
try:
    with admin_engine.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{database_name}"'))
    os.environ["SHIPMENT_REQUEST_IDENTITY_CERT_DATABASE_URL"] = target_url.render_as_string(
        hide_password=False
    )
    runpy.run_path(
        str(ROOT / "scripts" / "shipment_request_public_id_postgres_gate.py"),
        run_name="__main__",
    )
finally:
    with admin_engine.connect() as connection:
        connection.execute(text(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname=:name AND pid <> pg_backend_pid()"
        ), {"name": database_name})
        connection.execute(text(f'DROP DATABASE IF EXISTS "{database_name}"'))
    admin_engine.dispose()
