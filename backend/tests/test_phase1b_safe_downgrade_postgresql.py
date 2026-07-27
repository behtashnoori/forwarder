"""Direct PostgreSQL evidence for Phase 1B fail-closed downgrades."""
import os

import pytest
import sqlalchemy as sa
from alembic import command
from sqlalchemy.engine import make_url

from backend.migration_runtime import alembic_config


HEAD = "20260801_route_exception"
PHASE1B = "20260730_multileg_route"


def _url(name):
    value = os.environ.get(name, "")
    if not value:
        pytest.skip(f"explicit disposable PostgreSQL URL not provided: {name}")
    parsed = make_url(value)
    assert parsed.host in {"127.0.0.1", "localhost"}
    assert parsed.database.startswith("forwarder_phase1a_test_phase1b_")
    return value


def _snapshot(url):
    engine = sa.create_engine(url)
    try:
        with engine.connect() as connection:
            scalar = lambda sql: connection.execute(sa.text(sql)).scalar_one()
            return {
                "revision": scalar("select version_num from alembic_version"),
                "tables": scalar(
                    "select count(*) from information_schema.tables "
                    "where table_schema='public' and table_type='BASE TABLE'"
                ),
                "columns": scalar(
                    "select count(*) from information_schema.columns "
                    "where table_schema='public'"
                ),
                "indexes": scalar(
                    "select count(*) from pg_indexes where schemaname='public'"
                ),
                "constraints": scalar(
                    "select count(*) from information_schema.table_constraints "
                    "where constraint_schema='public'"
                ),
                "triggers": scalar(
                    "select count(*) from information_schema.triggers "
                    "where trigger_schema='public'"
                ),
                "functions": scalar(
                    "select count(*) from pg_proc p join pg_namespace n "
                    "on n.oid=p.pronamespace where n.nspname='public'"
                ),
                "organizations": scalar(
                    "select count(*) from operational_organization"
                ),
                "idempotency": scalar(
                    "select count(*) from operational_idempotency"
                ),
            }
    finally:
        engine.dispose()


def _insert_guard_scope(url, *, response_json):
    engine = sa.create_engine(url)
    try:
        with engine.begin() as connection:
            organization_id = connection.execute(
                sa.text(
                    "insert into operational_organization"
                    "(public_id,name,is_active,created_at) "
                    "values (:public_id,:name,true,now()) returning id"
                ),
                {
                    "public_id": (
                        "safe-head-guard" if response_json else "safe-scope-guard"
                    ),
                    "name": "Safe downgrade guard",
                },
            ).scalar_one()
            connection.execute(
                sa.text(
                    "insert into operational_idempotency"
                    "(organization_id,operation,idempotency_key,request_hash,"
                    "resource_id,created_at,resource_type,command_resource_id"
                    + (",response_json" if response_json else "")
                    + ") values "
                    "(:organization_id,'safe-downgrade','safe-key',"
                    "repeat('a',64),null,now(),'route_plan',42"
                    + (",'1'::json" if response_json else "")
                    + ")"
                ),
                {"organization_id": organization_id},
            )
    finally:
        engine.dispose()


def _assert_rejected_without_partial_ddl(url, target, expected_revision):
    before = _snapshot(url)
    assert before["revision"] == expected_revision
    with pytest.raises((RuntimeError, sa.exc.DBAPIError)):
        command.downgrade(alembic_config(url), target)
    after = _snapshot(url)
    assert after == before
    engine = sa.create_engine(url)
    try:
        with engine.connect() as connection:
            assert connection.execute(sa.text("select 1")).scalar_one() == 1
    finally:
        engine.dispose()


def test_20260801_response_replay_guard_precedes_all_ddl():
    url = _url("FORWARDER_PHASE1B_SAFE_DOWNGRADE_HEAD_URL")
    _insert_guard_scope(url, response_json=True)
    _assert_rejected_without_partial_ddl(url, PHASE1B, HEAD)


def test_20260730_scoped_idempotency_guard_precedes_all_ddl():
    url = _url("FORWARDER_PHASE1B_SAFE_DOWNGRADE_PHASE1B_URL")
    _insert_guard_scope(url, response_json=False)
    _assert_rejected_without_partial_ddl(
        url, "20260729_operational_vertical_slice", PHASE1B
    )
