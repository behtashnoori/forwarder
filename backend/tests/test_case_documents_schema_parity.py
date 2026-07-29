from __future__ import annotations

import os
import re

import pytest
from sqlalchemy import CheckConstraint, UniqueConstraint, create_engine, inspect, text
from sqlalchemy.dialects import postgresql

from backend.extensions import db
from backend.models import (
    CaseDocumentFile,
    CaseDocumentRequirement,
    DocumentAuditEvent,
    DocumentDefinition,
)


POSTGRES_URL = os.environ.get("DMS_DISPOSABLE_POSTGRES_URL")
pytestmark = pytest.mark.skipif(
    not POSTGRES_URL,
    reason="requires explicit DMS_DISPOSABLE_POSTGRES_URL",
)

DMS_MODELS = (
    DocumentDefinition,
    CaseDocumentRequirement,
    CaseDocumentFile,
    DocumentAuditEvent,
)


def _columns(items):
    return tuple(items or ())


def _type_sql(column_type):
    value = column_type.compile(dialect=postgresql.dialect()).upper()
    return value.replace("TIMESTAMP WITHOUT TIME ZONE", "TIMESTAMP")


def _normalize_check(value):
    value = re.sub(r"::[a-z ]+(?:\[\])?", "", value.lower())
    value = value.replace('"', "").replace(" = true", "").replace("is_miscellaneous", "misc")
    value = value.replace("misc = false", "not misc")
    value = value.replace("= any (array[", " in (").replace("])", ")")
    value = value.replace("(", "").replace(")", "")
    value = re.sub(r"\s+", " ", value)
    return value


def test_postgresql_migration_matches_dms_orm_schema_exactly():
    assert POSTGRES_URL.startswith(("postgresql://", "postgresql+psycopg"))
    assert "dms1a_" in POSTGRES_URL
    engine = create_engine(POSTGRES_URL)
    inspector = inspect(engine)
    with engine.connect() as connection:
        assert connection.execute(text("show server_version")).scalar_one().startswith("18.")
        assert connection.execute(text("select current_database()")).scalar_one().startswith("dms1a_")
        assert connection.execute(text("select version_num from alembic_version")).scalar_one() == "20260804_case_documents"

    expected_tables = {model.__table__.name for model in DMS_MODELS}
    assert expected_tables == {
        "document_definition",
        "case_document_requirement",
        "case_document_file",
        "document_audit_event",
    }

    for model in DMS_MODELS:
        table = model.__table__
        actual_columns = {item["name"]: item for item in inspector.get_columns(table.name)}
        assert set(actual_columns) == {column.name for column in table.columns}, table.name
        for column in table.columns:
            actual = actual_columns[column.name]
            assert _type_sql(actual["type"]) == _type_sql(column.type), (table.name, column.name)
            assert actual["nullable"] == column.nullable, (table.name, column.name, "nullable")
            expected_default = (
                str(column.server_default.arg) if column.server_default is not None else None
            )
            actual_default = actual.get("default")
            if column.primary_key and column.autoincrement in {True, "auto"}:
                assert actual_default and actual_default.startswith("nextval(")
            else:
                assert actual_default == expected_default, (table.name, column.name, "server_default")

        actual_pk = inspector.get_pk_constraint(table.name)
        assert _columns(actual_pk["constrained_columns"]) == tuple(
            column.name for column in table.primary_key.columns
        )

        actual_fks = {
            (
                _columns(item["constrained_columns"]),
                item["referred_table"],
                _columns(item["referred_columns"]),
                (item.get("options") or {}).get("ondelete"),
            )
            for item in inspector.get_foreign_keys(table.name)
        }
        expected_fks = {
            (
                tuple(element.parent.name for element in constraint.elements),
                constraint.elements[0].column.table.name,
                tuple(element.column.name for element in constraint.elements),
                constraint.ondelete,
            )
            for constraint in table.foreign_key_constraints
        }
        assert actual_fks == expected_fks, (table.name, "foreign_keys")

        actual_uniques = {
            (item["name"], _columns(item["column_names"]))
            for item in inspector.get_unique_constraints(table.name)
        }
        expected_uniques = {
            (constraint.name, tuple(column.name for column in constraint.columns))
            for constraint in table.constraints
            if isinstance(constraint, UniqueConstraint)
        }
        assert {columns for _, columns in actual_uniques} == {
            columns for _, columns in expected_uniques
        }, (table.name, "unique_constraints")
        expected_named_uniques = {
            (name, columns) for name, columns in expected_uniques if name is not None
        }
        assert expected_named_uniques <= actual_uniques, (table.name, "named_unique_constraints")

        actual_indexes = {
            (item["name"], _columns(item["column_names"]), bool(item["unique"]))
            for item in inspector.get_indexes(table.name)
            if not item.get("duplicates_constraint")
        }
        expected_indexes = {
            (index.name, tuple(column.name for column in index.columns), bool(index.unique))
            for index in table.indexes
        }
        assert actual_indexes == expected_indexes, (table.name, "indexes")

        actual_checks = {
            (item["name"], _normalize_check(item["sqltext"]))
            for item in inspector.get_check_constraints(table.name)
        }
        expected_checks = {
            (constraint.name, _normalize_check(str(constraint.sqltext)))
            for constraint in table.constraints
            if isinstance(constraint, CheckConstraint)
        }
        assert actual_checks == expected_checks, (table.name, "check_constraints")
