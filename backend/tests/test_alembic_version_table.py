"""Safety tests for long Alembic revision identifiers."""
from __future__ import annotations

import ast
from pathlib import Path

import pytest
import sqlalchemy as sa

from backend.migrations.version_table import (
    AlembicVersionTableError,
    VERSION_COLUMN_CAPACITY,
    ensure_version_table_capacity,
)


class _Result:
    def __init__(self, values=()):
        self.values = tuple(values)

    def scalars(self):
        return self

    def all(self):
        return list(self.values)


class _Dialect:
    name = "postgresql"


class _Connection:
    dialect = _Dialect()

    def __init__(self, revisions=(), fail_on_alter=False):
        self.revisions = tuple(revisions)
        self.fail_on_alter = fail_on_alter
        self.statements = []

    def execute(self, statement):
        sql = str(statement)
        self.statements.append(sql)
        if self.fail_on_alter and sql.startswith("ALTER TABLE"):
            raise RuntimeError("synthetic DDL failure")
        return _Result(self.revisions)


class _Inspector:
    def __init__(self, *, exists=True, length=32, nullable=False, pk=None):
        self.exists = exists
        self.length = length
        self.nullable = nullable
        self.pk = ["version_num"] if pk is None else pk

    def has_table(self, name):
        return self.exists

    def get_columns(self, name):
        return [{"name": "version_num", "type": sa.String(self.length), "nullable": self.nullable}]

    def get_pk_constraint(self, name):
        return {"constrained_columns": self.pk}


def _factory(inspector):
    return lambda connection: inspector


def _revision_ids():
    versions = Path(__file__).parents[1] / "migrations" / "versions"
    revisions = []
    for path in versions.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "revision"
                for target in node.targets
            ):
                revisions.append(ast.literal_eval(node.value))
    return revisions


def test_historical_long_revision_ids_are_detected_and_graph_has_one_feature_head():
    revisions = _revision_ids()
    assert max(map(len, revisions)) > 32
    assert "20240918_add_shipment_request_log" in revisions
    assert len(revisions) == len(set(revisions))

    from alembic.config import Config
    from alembic.script import ScriptDirectory

    config = Config(str(Path(__file__).parents[1] / "migrations" / "alembic.ini"))
    config.set_main_option("script_location", str(Path(__file__).parents[1] / "migrations"))
    heads = ScriptDirectory.from_config(config).get_heads()
    assert heads == ["20260818_immutable_fx_provenance"]


def test_empty_postgresql_creates_only_a_wide_empty_version_table():
    connection = _Connection()
    ensure_version_table_capacity(
        connection, inspector_factory=_factory(_Inspector(exists=False))
    )
    assert connection.statements == [
        "CREATE TABLE alembic_version (version_num VARCHAR(255) NOT NULL, "
        "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))"
    ]
    assert not any("INSERT" in sql or "DELETE" in sql for sql in connection.statements)


def test_existing_short_version_column_is_widened_without_changing_revision():
    connection = _Connection(revisions=("synthetic_parent",))
    ensure_version_table_capacity(connection, inspector_factory=_factory(_Inspector(length=32)))
    assert connection.statements == [
        "SELECT version_num FROM alembic_version",
        "ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(255)",
    ]
    assert not any("INSERT" in sql or "DELETE" in sql for sql in connection.statements)


def test_repeated_execution_is_idempotent_when_capacity_is_sufficient():
    connection = _Connection(revisions=("synthetic_parent",))
    inspector = _Inspector(length=VERSION_COLUMN_CAPACITY)
    ensure_version_table_capacity(connection, inspector_factory=_factory(inspector))
    ensure_version_table_capacity(connection, inspector_factory=_factory(inspector))
    assert connection.statements == [
        "SELECT version_num FROM alembic_version",
        "SELECT version_num FROM alembic_version",
    ]


def test_multiple_revisions_and_incompatible_schema_fail_closed():
    with pytest.raises(AlembicVersionTableError, match="more than one"):
        ensure_version_table_capacity(
            _Connection(revisions=("branch_a", "branch_b")),
            inspector_factory=_factory(_Inspector()),
        )
    with pytest.raises(AlembicVersionTableError, match="NOT NULL"):
        ensure_version_table_capacity(
            _Connection(), inspector_factory=_factory(_Inspector(nullable=True))
        )


def test_valid_parallel_revision_rows_are_preserved():
    connection = _Connection(revisions=("branch_a", "branch_b"))
    ensure_version_table_capacity(
        connection,
        inspector_factory=_factory(_Inspector(length=VERSION_COLUMN_CAPACITY)),
        multiple_revision_validator=lambda revisions: set(revisions)
        == {"branch_a", "branch_b"},
    )
    assert connection.statements == ["SELECT version_num FROM alembic_version"]


def test_sqlite_is_untouched_and_postgresql_ddl_errors_are_not_swallowed():
    engine = sa.create_engine("sqlite:///:memory:")
    with engine.connect() as connection:
        ensure_version_table_capacity(connection)
        assert sa.inspect(connection).get_table_names() == []

    with pytest.raises(RuntimeError, match="synthetic DDL failure"):
        ensure_version_table_capacity(
            _Connection(revisions=("synthetic_parent",), fail_on_alter=True),
            inspector_factory=_factory(_Inspector(length=32)),
        )


def test_migration_runners_do_not_stamp_or_rewrite_revision_values():
    backend = Path(__file__).parents[1]
    sources = "\n".join(
        (backend / name).read_text(encoding="utf-8-sig")
        for name in ("startup.py", "run_upgrade.py")
    )
    forbidden = (
        "DELETE FROM alembic_version",
        "INSERT INTO alembic_version",
        "stamp head",
        "command.stamp",
    )
    assert not any(token in sources for token in forbidden)
