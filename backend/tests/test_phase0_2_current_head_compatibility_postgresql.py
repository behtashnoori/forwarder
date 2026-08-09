"""Integrated-head compatibility for the historical Phase 0.2 PostgreSQL contract.

The revision-pinned historical suite remains in
``test_phase0_2_postgresql_gate.py``.  This suite deliberately asserts the
current Alembic head while replaying the still-relevant catalog, startup, and
concurrent revision-status invariants.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import os

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

from backend import create_app
from backend.migration_runtime import revision_status


def _url() -> str:
    value = os.environ.get("INTEGRATED_RC_POSTGRES_URL", "")
    if not value:
        pytest.skip("explicit disposable Integrated RC PostgreSQL URL not provided")
    parsed = make_url(value)
    assert parsed.get_backend_name() == "postgresql"
    assert parsed.host in {"127.0.0.1", "localhost"}
    assert (parsed.database or "").startswith("forwarder_integrated_rc_")
    return value


def _head() -> str:
    config = Config("backend/migrations/alembic.ini")
    config.set_main_option("script_location", "backend/migrations")
    heads = ScriptDirectory.from_config(config).get_heads()
    assert len(heads) == 1
    return heads[0]


def _catalog_fingerprint(connection) -> str:
    return connection.execute(text(
        "select md5(string_agg(definition, E'\\n' order by definition)) from ("
        "select pg_get_constraintdef(oid, true) definition from pg_constraint "
        "where connamespace = 'public'::regnamespace union all "
        "select pg_get_indexdef(indexrelid) from pg_index where indrelid in "
        "(select oid from pg_class where relnamespace = 'public'::regnamespace)) catalog"
    )).scalar_one()


def test_integrated_head_preserves_phase02_catalog_and_read_only_startup():
    url = _url()
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            assert connection.execute(text("show server_version")).scalar_one().startswith("18.")
            assert connection.execute(text("select version_num from alembic_version")).scalar_one() == _head()
            foreign_keys = inspect(connection).get_foreign_keys("shipment_request")
            for column, target in (("iran_entry_port_id", "iran_port"), ("iran_entry_province_id", "province")):
                matches = [fk for fk in foreign_keys if fk["constrained_columns"] == [column]]
                assert len(matches) == 1 and matches[0]["referred_table"] == target
            before = (tuple(inspect(connection).get_table_names()), _catalog_fingerprint(connection))
        app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": url,
                          "SECRET_KEY": "integrated-phase02-synthetic"}, skip_startup=True)
        client = app.test_client()
        assert client.get("/api/health/ping").status_code == 200
        assert client.get("/api/health").status_code == 200
        assert client.get("/api/health/ready").status_code == 200
        with engine.connect() as connection:
            after = (tuple(inspect(connection).get_table_names()), _catalog_fingerprint(connection))
        assert after == before
    finally:
        engine.dispose()


def test_integrated_head_revision_checks_are_concurrently_consistent():
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(lambda _: revision_status(_url()), range(2)))
    head = _head()
    assert all(status.current == (head,) and status.heads == (head,) and not status.pending
               for status in statuses)
