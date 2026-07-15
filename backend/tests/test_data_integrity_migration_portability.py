"""Portability contracts for the historical data-integrity migration."""
from __future__ import annotations

import importlib.util
from pathlib import Path


MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "migrations"
    / "versions"
    / "20240925_add_data_integrity_constraints.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location("data_integrity_migration", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_boolean_predicates_are_native_for_postgresql_and_compatible_with_sqlite():
    migration = _load_migration()
    assert migration._boolean_predicates("postgresql") == (
        "is_active IN (TRUE, FALSE)",
        "is_active IS TRUE",
    )
    assert migration._boolean_predicates("sqlite") == (
        "is_active IN (0, 1)",
        "is_active = 1",
    )


def test_migration_uses_partial_indexes_with_matching_downgrade():
    source = MIGRATION_PATH.read_text(encoding="utf-8-sig")
    assert "op.create_unique_constraint" not in source
    assert "postgresql_where=sa.text(\"is_active = 1\")" not in source
    assert "op.drop_index('uq_expert_user_username_active'" in source
    assert "op.drop_index('uq_customer_email_active'" in source
