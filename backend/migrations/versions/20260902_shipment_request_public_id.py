"""Add opaque authenticated identity to ShipmentRequest.

Revision ID: 20260902_shipment_request_public_id
Revises: 20260901_document_catalog_runs
"""
from __future__ import annotations

from uuid import UUID, uuid4

from alembic import op
import sqlalchemy as sa

revision = "20260902_shipment_request_public_id"
down_revision = "20260901_document_catalog_runs"
branch_labels = None
depends_on = None

TABLE = "shipment_request"
COLUMN = "public_id"
UNIQUE_CONSTRAINT = "uq_shipment_request_public_id"


def _canonical_uuid4(value: object) -> bool:
    if not isinstance(value, str) or len(value) != 36:
        return False
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError, TypeError):
        return False
    return parsed.version == 4 and value == str(parsed)


def _backfill_public_ids(bind) -> None:
    """Fill null rows only, preserving identities across retries."""
    table = sa.table(TABLE, sa.column("id"), sa.column(COLUMN))
    existing = set(
        bind.execute(sa.select(table.c.public_id).where(table.c.public_id.is_not(None)))
        .scalars()
        .all()
    )
    row_ids = bind.execute(
        sa.select(table.c.id).where(table.c.public_id.is_(None)).order_by(table.c.id)
    ).scalars().all()
    for row_id in row_ids:
        candidate = str(uuid4())
        while candidate in existing:
            candidate = str(uuid4())
        result = bind.execute(
            table.update()
            .where(table.c.id == row_id, table.c.public_id.is_(None))
            .values(public_id=candidate)
        )
        if result.rowcount:
            existing.add(candidate)


def _validate_public_ids(bind) -> None:
    table = sa.table(TABLE, sa.column("id"), sa.column(COLUMN))
    values = bind.execute(sa.select(table.c.public_id)).scalars().all()
    if any(value is None for value in values):
        raise RuntimeError("ShipmentRequest public_id backfill left null rows")
    if len(values) != len(set(values)):
        raise RuntimeError("ShipmentRequest public_id backfill produced duplicates")
    if any(not _canonical_uuid4(value) for value in values):
        raise RuntimeError("ShipmentRequest public_id backfill produced a non-UUID-v4 value")


def upgrade() -> None:
    with op.batch_alter_table(TABLE) as batch:
        batch.add_column(sa.Column(COLUMN, sa.String(36), nullable=True))
    bind = op.get_bind()
    _backfill_public_ids(bind)
    _validate_public_ids(bind)
    with op.batch_alter_table(TABLE) as batch:
        batch.create_unique_constraint(UNIQUE_CONSTRAINT, [COLUMN])


def downgrade() -> None:
    with op.batch_alter_table(TABLE) as batch:
        batch.drop_constraint(UNIQUE_CONSTRAINT, type_="unique")
        batch.drop_column(COLUMN)
