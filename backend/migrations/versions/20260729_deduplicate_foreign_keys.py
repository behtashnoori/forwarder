"""Remove duplicate PostgreSQL foreign-key constraints by semantic signature.

Revision ID: 20260729_deduplicate_foreign_keys
Revises: 20260728_add_quote_customer_response
"""
from __future__ import annotations

from collections import defaultdict

from alembic import op
from sqlalchemy import inspect


revision = "20260729_deduplicate_foreign_keys"
down_revision = "20260728_add_quote_customer_response"
branch_labels = None
depends_on = None


def foreign_key_signature(foreign_key: dict) -> tuple:
    """Return full relationship semantics, excluding only constraint name."""
    options = foreign_key.get("options") or {}
    return (
        tuple(foreign_key.get("constrained_columns") or ()),
        foreign_key.get("referred_schema"),
        foreign_key.get("referred_table"),
        tuple(foreign_key.get("referred_columns") or ()),
        tuple(
            (key, options.get(key))
            for key in ("ondelete", "onupdate", "deferrable", "initially", "match")
        ),
    )


def duplicate_constraint_names(foreign_keys: list[dict]) -> list[str]:
    """Choose redundant named constraints while retaining one deterministically."""
    grouped: dict[tuple, list[dict]] = defaultdict(list)
    for foreign_key in foreign_keys:
        grouped[foreign_key_signature(foreign_key)].append(foreign_key)

    redundant: list[str] = []
    for matches in grouped.values():
        if len(matches) < 2:
            continue
        named = [item for item in matches if item.get("name")]
        if len(named) < 2:
            continue
        # Prefer the explicit project naming convention over database-generated
        # names, then keep lexicographically for repeatability.
        named.sort(key=lambda item: (not str(item["name"]).startswith("fk_"), item["name"]))
        redundant.extend(str(item["name"]) for item in named[1:])
    return sorted(redundant)


def upgrade() -> None:
    connection = op.get_bind()
    # PostgreSQL is the production dialect and exposes stable names for every
    # FK. SQLite table reconstruction is intentionally not attempted here.
    if connection.dialect.name != "postgresql":
        return
    inspector = inspect(connection)
    for table_name in inspector.get_table_names():
        for constraint_name in duplicate_constraint_names(
            inspector.get_foreign_keys(table_name)
        ):
            op.drop_constraint(constraint_name, table_name, type_="foreignkey")


def downgrade() -> None:
    # Duplicate constraints have no distinct semantic value and must not be
    # recreated. Downgrade is intentionally a no-op.
    return
