"""Phase 0.2 checks that run only against an explicit disposable PostgreSQL DB."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import os

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

from backend import create_app
from backend.migration_runtime import revision_status


HEAD = "20260728_add_quote_customer_response"


def _url() -> str:
    url = os.environ.get("FORWARDER_PHASE02_POSTGRES_URL", "")
    if not url:
        pytest.skip("explicit Phase 0.2 disposable PostgreSQL URL not provided")
    parsed = make_url(url)
    assert parsed.get_backend_name() == "postgresql"
    assert parsed.host in {"127.0.0.1", "localhost"}
    assert parsed.database and parsed.database.startswith("forwarder_phase02_test_")
    return url


def test_phase02_catalog_has_one_revision_and_expected_entry_foreign_keys():
    engine = create_engine(_url())
    try:
        with engine.connect() as connection:
            assert connection.execute(text("select current_database()" )).scalar_one().startswith(
                "forwarder_phase02_test_"
            )
            assert connection.execute(text("select version_num from alembic_version")).scalar_one() == HEAD
            inspector = inspect(connection)
            foreign_keys = inspector.get_foreign_keys("shipment_request")
            for column, target in (
                ("iran_entry_port_id", "iran_port"),
                ("iran_entry_province_id", "province"),
            ):
                matches = [
                    item
                    for item in foreign_keys
                    if item["constrained_columns"] == [column]
                ]
                assert len(matches) == 1
                assert matches[0]["referred_table"] == target
    finally:
        engine.dispose()


def test_phase02_startup_and_probes_are_read_only_at_head():
    url = _url()
    engine = create_engine(url)
    try:
        def catalog_fingerprint(connection):
            return connection.execute(
                text(
                    "select md5(string_agg(definition, E'\\n' order by definition)) "
                    "from ("
                    "select pg_get_constraintdef(oid, true) definition "
                    "from pg_constraint where connamespace = 'public'::regnamespace "
                    "union all select pg_get_indexdef(indexrelid) from pg_index "
                    "where indrelid in (select oid from pg_class where relnamespace = 'public'::regnamespace)"
                    ") catalog"
                )
            ).scalar_one()

        with engine.connect() as connection:
            before_tables = tuple(inspect(connection).get_table_names())
            before_catalog = catalog_fingerprint(connection)
        app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": url,
                "SECRET_KEY": "phase02-synthetic-only",
            },
            skip_startup=True,
        )
        client = app.test_client()
        assert client.get("/api/health/ping").status_code == 200
        assert client.get("/api/health").status_code == 200
        assert client.get("/api/health/ready").status_code == 200
        with engine.connect() as connection:
            after_tables = tuple(inspect(connection).get_table_names())
            after_catalog = catalog_fingerprint(connection)
        assert after_tables == before_tables
        assert after_catalog == before_catalog
    finally:
        engine.dispose()


def test_phase02_parallel_revision_checks_are_consistent():
    url = _url()
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(lambda _: revision_status(url), range(2)))
    assert all(status.current == (HEAD,) for status in statuses)
    assert all(status.heads == (HEAD,) for status in statuses)
    assert all(not status.pending for status in statuses)
