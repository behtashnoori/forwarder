"""Order-safety contracts for the parallel expert-console migrations."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


VERSIONS = Path(__file__).parents[1] / "migrations" / "versions"
SHARED_COLUMNS = {
    "assigned_to",
    "status",
    "sla_due_at",
    "last_customer_touch_at",
    "has_unread_for_assignee",
    "priority",
    "estimated_value",
}
SHARED_TABLES = {
    "expert_user",
    "expert_console_log",
    "expert_console_message",
    "expert_console_notification",
}


def _load(filename, module_name):
    spec = importlib.util.spec_from_file_location(module_name, VERSIONS / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _run_in_order(first_filename, second_filename):
    engine = sa.create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(sa.text("CREATE TABLE shipment_request (id INTEGER PRIMARY KEY)"))
        operations = Operations(MigrationContext.configure(connection))
        first = _load(first_filename, f"first_{first_filename}")
        second = _load(second_filename, f"second_{second_filename}")
        first.op = operations
        second.op = operations
        first.upgrade()
        second.upgrade()

        inspector = sa.inspect(connection)
        columns = {item["name"] for item in inspector.get_columns("shipment_request")}
        tables = set(inspector.get_table_names())
        assert SHARED_COLUMNS <= columns
        assert SHARED_TABLES <= tables
        assert len(columns & SHARED_COLUMNS) == len(SHARED_COLUMNS)
    engine.dispose()


def test_tables_then_fields_branch_is_order_safe():
    _run_in_order(
        "20240924_add_expert_console_tables.py",
        "20240924_add_expert_console_fields.py",
    )


def test_fields_then_tables_branch_is_order_safe():
    _run_in_order(
        "20240924_add_expert_console_fields.py",
        "20240924_add_expert_console_tables.py",
    )


def test_both_downgrades_guard_shared_objects():
    for filename in (
        "20240924_add_expert_console_tables.py",
        "20240924_add_expert_console_fields.py",
    ):
        source = (VERSIONS / filename).read_text(encoding="utf-8-sig")
        assert "if _foreign_key_exists" in source
        assert "if _table_exists" in source
        assert "if _column_exists" in source
