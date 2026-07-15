"""Fail-closed Alembic version-table capacity management."""
from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import inspect, text
from sqlalchemy.sql.sqltypes import String


VERSION_TABLE_NAME = "alembic_version"
VERSION_COLUMN_NAME = "version_num"
VERSION_COLUMN_CAPACITY = 255


class AlembicVersionTableError(RuntimeError):
    """Raised when the Alembic version table cannot be handled safely."""


def ensure_version_table_capacity(
    connection,
    *,
    inspector_factory: Callable = inspect,
) -> None:
    """Create or widen Alembic's PostgreSQL version column without changing revisions.

    Non-PostgreSQL databases are intentionally left to Alembic. SQLite does not
    enforce declared VARCHAR lengths, and offline mode never calls this helper.
    The caller owns the transaction so inspection or DDL failures remain visible.
    """
    if connection.dialect.name != "postgresql":
        return

    inspector = inspector_factory(connection)
    if not inspector.has_table(VERSION_TABLE_NAME):
        connection.execute(
            text(
                "CREATE TABLE alembic_version ("
                "version_num VARCHAR(255) NOT NULL, "
                "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)"
                ")"
            )
        )
        return

    columns = inspector.get_columns(VERSION_TABLE_NAME)
    version_columns = [column for column in columns if column["name"] == VERSION_COLUMN_NAME]
    if len(version_columns) != 1:
        raise AlembicVersionTableError(
            "alembic_version must contain exactly one version_num column"
        )

    version_column = version_columns[0]
    column_type = version_column["type"]
    if not isinstance(column_type, String):
        raise AlembicVersionTableError("alembic_version.version_num must be a string column")
    if version_column.get("nullable", True):
        raise AlembicVersionTableError("alembic_version.version_num must be NOT NULL")

    primary_key = inspector.get_pk_constraint(VERSION_TABLE_NAME) or {}
    constrained_columns = primary_key.get("constrained_columns") or []
    if constrained_columns not in ([], [VERSION_COLUMN_NAME]):
        raise AlembicVersionTableError("alembic_version has an incompatible primary key")

    row_count = connection.execute(text("SELECT COUNT(*) FROM alembic_version")).scalar_one()
    if row_count > 1:
        raise AlembicVersionTableError(
            "alembic_version unexpectedly contains more than one stored revision"
        )

    current_capacity = getattr(column_type, "length", None)
    if current_capacity is not None and current_capacity < VERSION_COLUMN_CAPACITY:
        connection.execute(
            text(
                "ALTER TABLE alembic_version "
                "ALTER COLUMN version_num TYPE VARCHAR(255)"
            )
        )
