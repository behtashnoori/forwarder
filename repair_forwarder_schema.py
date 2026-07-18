from __future__ import annotations

from datetime import date
from typing import Any

import sqlalchemy as sa
from alembic.script import ScriptDirectory
from flask import current_app
from sqlalchemy import inspect, text
from sqlalchemy.schema import AddConstraint, CreateColumn

from backend import create_app
from backend.extensions import db

EXPECTED_DATABASE = "forwarder_db"


def qtable(connection, table: sa.Table) -> str:
    p = connection.dialect.identifier_preparer
    name = p.quote(table.name)
    return f"{p.quote_schema(table.schema)}.{name}" if table.schema else name


def qcol(connection, name: str) -> str:
    return connection.dialect.identifier_preparer.quote(name)


def scalar_default(column: sa.Column[Any]) -> tuple[bool, Any]:
    default = column.default
    if default is None:
        return False, None
    if getattr(default, "is_scalar", False):
        return True, default.arg
    if callable(default.arg):
        try:
            return True, default.arg()
        except TypeError:
            return False, None
    return False, None


def server_default_sql(connection, column: sa.Column[Any]) -> str | None:
    if column.server_default is None:
        return None
    arg = column.server_default.arg
    try:
        return str(
            arg.compile(
                dialect=connection.dialect,
                compile_kwargs={"literal_binds": True},
            )
        )
    except AttributeError:
        return str(arg)


def backfill(connection, column: sa.Column[Any]) -> tuple[str | None, dict[str, Any]]:
    server_sql = server_default_sql(connection, column)
    if server_sql:
        return server_sql, {}

    ok, value = scalar_default(column)
    if ok:
        return ":repair_value", {"repair_value": value}

    if isinstance(column.type, sa.Boolean):
        return ":repair_value", {"repair_value": column.name == "is_active"}

    if isinstance(column.type, (sa.DateTime, sa.TIMESTAMP)) and column.name in {
        "created_at",
        "updated_at",
    }:
        return "CURRENT_TIMESTAMP", {}

    if isinstance(column.type, sa.Date) and column.name == "effective_from":
        return ":repair_value", {"repair_value": date.today()}

    return None, {}


def fk_signature(item: dict[str, Any]) -> tuple[Any, ...]:
    return (
        tuple(item.get("constrained_columns") or ()),
        item.get("referred_schema"),
        item.get("referred_table"),
        tuple(item.get("referred_columns") or ()),
    )


app = create_app(skip_startup=True)

with app.app_context():
    cfg = current_app.extensions["migrate"].migrate.get_config("backend/migrations")
    heads = ScriptDirectory.from_config(cfg).get_heads()

    if len(heads) != 1:
        raise SystemExit(f"STOP: expected one Alembic head, found {heads}")

    target_head = heads[0]
    engine = db.engine

    with engine.connect() as connection:
        database_name = connection.execute(text("SELECT current_database()")).scalar_one()
        current_versions = connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalars().all()
        inspector = inspect(connection)

        missing_tables = [
            table
            for table in db.metadata.sorted_tables
            if table.name != "alembic_version"
            and not inspector.has_table(table.name, schema=table.schema)
        ]

        missing_columns: list[tuple[sa.Table, sa.Column[Any]]] = []
        for table in db.metadata.sorted_tables:
            if table.name == "alembic_version" or table in missing_tables:
                continue
            existing = {
                item["name"]
                for item in inspector.get_columns(table.name, schema=table.schema)
            }
            for column in table.columns:
                if column.name not in existing:
                    missing_columns.append((table, column))

    print("DATABASE:", database_name)
    print("CURRENT_ALEMBIC_VERSION:", current_versions)
    print("TARGET_HEAD:", target_head)
    print("MISSING_TABLES_BEFORE:", [t.fullname for t in missing_tables])
    print(
        "MISSING_COLUMNS_BEFORE:",
        [f"{t.fullname}.{c.name}" for t, c in missing_columns],
    )

    if database_name != EXPECTED_DATABASE:
        raise SystemExit(
            f"STOP: expected database {EXPECTED_DATABASE!r}, found {database_name!r}"
        )

    blockers: list[str] = []
    with engine.connect() as connection:
        for table, column in missing_columns:
            if column.nullable:
                continue
            count = connection.execute(
                text(f"SELECT COUNT(*) FROM {qtable(connection, table)}")
            ).scalar_one()
            expression, _ = backfill(connection, column)
            if count > 0 and expression is None:
                blockers.append(
                    f"{table.fullname}.{column.name}: "
                    "NOT NULL on populated table with no safe backfill"
                )

    if blockers:
        print("BLOCKERS:")
        for item in blockers:
            print(" -", item)
        raise SystemExit("STOP: no changes were made.")

    created_tables: list[str] = []
    added_columns: list[str] = []
    added_fks: list[str] = []
    added_uniques: list[str] = []
    created_indexes: list[str] = []

    with engine.begin() as connection:
        connection.execute(
            text(
                "SELECT pg_advisory_xact_lock("
                "hashtext('forwarder_schema_repair_v1'))"
            )
        )

        for table in db.metadata.sorted_tables:
            if table.name == "alembic_version":
                continue
            if not inspect(connection).has_table(table.name, schema=table.schema):
                table.create(bind=connection, checkfirst=True)
                created_tables.append(table.fullname)

        for table in db.metadata.sorted_tables:
            if table.name == "alembic_version":
                continue

            existing = {
                item["name"]
                for item in inspect(connection).get_columns(
                    table.name,
                    schema=table.schema,
                )
            }

            for column in table.columns:
                if column.name in existing:
                    continue

                table_name = qtable(connection, table)
                column_name = qcol(connection, column.name)
                temp_column = sa.Column(
                    column.name,
                    column.type,
                    nullable=True,
                    server_default=column.server_default,
                )
                column_ddl = str(
                    CreateColumn(temp_column).compile(
                        dialect=connection.dialect
                    )
                )

                connection.execute(
                    text(
                        f"ALTER TABLE {table_name} "
                        f"ADD COLUMN IF NOT EXISTS {column_ddl}"
                    )
                )

                if not column.nullable:
                    count = connection.execute(
                        text(f"SELECT COUNT(*) FROM {table_name}")
                    ).scalar_one()
                    if count > 0:
                        expression, params = backfill(connection, column)
                        if expression is None:
                            raise RuntimeError(
                                f"No safe backfill for "
                                f"{table.fullname}.{column.name}"
                            )
                        connection.execute(
                            text(
                                f"UPDATE {table_name} "
                                f"SET {column_name} = {expression} "
                                f"WHERE {column_name} IS NULL"
                            ),
                            params,
                        )
                    connection.execute(
                        text(
                            f"ALTER TABLE {table_name} "
                            f"ALTER COLUMN {column_name} SET NOT NULL"
                        )
                    )

                added_columns.append(f"{table.fullname}.{column.name}")

        for table in db.metadata.sorted_tables:
            if table.name == "alembic_version":
                continue

            existing_fks = {
                fk_signature(item)
                for item in inspect(connection).get_foreign_keys(
                    table.name,
                    schema=table.schema,
                )
            }

            for constraint in table.foreign_key_constraints:
                signature = (
                    tuple(e.parent.name for e in constraint.elements),
                    constraint.referred_table.schema,
                    constraint.referred_table.name,
                    tuple(e.column.name for e in constraint.elements),
                )
                if signature not in existing_fks:
                    connection.execute(AddConstraint(constraint))
                    added_fks.append(
                        constraint.name
                        or f"{table.fullname}:{','.join(signature[0])}"
                    )

        for table in db.metadata.sorted_tables:
            if table.name == "alembic_version":
                continue

            existing_unique_sets = {
                tuple(item.get("column_names") or ())
                for item in inspect(connection).get_unique_constraints(
                    table.name,
                    schema=table.schema,
                )
            }

            for constraint in table.constraints:
                if not isinstance(constraint, sa.UniqueConstraint):
                    continue
                columns = tuple(column.name for column in constraint.columns)
                if columns not in existing_unique_sets:
                    connection.execute(AddConstraint(constraint))
                    added_uniques.append(
                        constraint.name
                        or f"{table.fullname}:{','.join(columns)}"
                    )

        for table in db.metadata.sorted_tables:
            if table.name == "alembic_version":
                continue

            existing_index_names = {
                item.get("name")
                for item in inspect(connection).get_indexes(
                    table.name,
                    schema=table.schema,
                )
            }

            for index in table.indexes:
                if index.name not in existing_index_names:
                    index.create(bind=connection, checkfirst=True)
                    created_indexes.append(index.name or repr(index))

        final_inspector = inspect(connection)
        remaining_tables: list[str] = []
        remaining_columns: list[str] = []

        for table in db.metadata.sorted_tables:
            if table.name == "alembic_version":
                continue

            if not final_inspector.has_table(table.name, schema=table.schema):
                remaining_tables.append(table.fullname)
                continue

            existing = {
                item["name"]
                for item in final_inspector.get_columns(
                    table.name,
                    schema=table.schema,
                )
            }
            for column in table.columns:
                if column.name not in existing:
                    remaining_columns.append(f"{table.fullname}.{column.name}")

        if remaining_tables or remaining_columns:
            raise RuntimeError(
                f"Final verification failed. "
                f"tables={remaining_tables}, columns={remaining_columns}"
            )

        connection.execute(
            text(
                "ALTER TABLE alembic_version "
                "ALTER COLUMN version_num TYPE VARCHAR(255)"
            )
        )
        connection.execute(text("DELETE FROM alembic_version"))
        connection.execute(
            text(
                "INSERT INTO alembic_version (version_num) "
                "VALUES (:target_head)"
            ),
            {"target_head": target_head},
        )

    with engine.connect() as connection:
        final_versions = connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalars().all()

    if final_versions != [target_head]:
        raise SystemExit(
            f"STOP: final Alembic revision mismatch: {final_versions}"
        )

    print("CREATED_TABLES:", created_tables)
    print("ADDED_COLUMNS:", added_columns)
    print("ADDED_FOREIGN_KEYS:", added_fks)
    print("ADDED_UNIQUE_CONSTRAINTS:", added_uniques)
    print("CREATED_INDEXES:", created_indexes)
    print("FORWARDER_SCHEMA_REPAIR_OK")
    print("FINAL_ALEMBIC_VERSION:", final_versions)