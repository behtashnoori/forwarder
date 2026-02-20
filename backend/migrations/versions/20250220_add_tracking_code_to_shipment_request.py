"""Add tracking_code to shipment_request for non-guessable public tracking.

Revision ID: 20250220_add_tracking_code
Revises: 20250120_add_customer_gamification_system
Create Date: 2025-02-20

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20250220_add_tracking_code"
down_revision = "20250120_add_customer_gamification_system"
branch_labels = None
depends_on = None

INDEX_NAME = "ix_shipment_request_tracking_code"
TABLE_NAME = "shipment_request"
COLUMN_NAME = "tracking_code"


def _column_exists(conn, table, column):
    insp = inspect(conn)
    cols = [c["name"] for c in insp.get_columns(table)]
    return column in cols


def _index_exists(conn, index_name, table_name):
    insp = inspect(conn)
    for idx in insp.get_indexes(table_name):
        if idx["name"] == index_name:
            return True
    return False


def upgrade() -> None:
    conn = op.get_bind()
    try:
        col_exists = _column_exists(conn, TABLE_NAME, COLUMN_NAME)
    except Exception as e:
        # Fallback: assume column does not exist (e.g. Inspector API difference)
        col_exists = False
    if not col_exists:
        op.add_column(
            TABLE_NAME,
            sa.Column(COLUMN_NAME, sa.String(length=32), nullable=True),
        )
    try:
        idx_exists = _index_exists(conn, INDEX_NAME, TABLE_NAME)
    except Exception:
        idx_exists = False
    if not idx_exists:
        op.create_index(
            INDEX_NAME,
            TABLE_NAME,
            [COLUMN_NAME],
            unique=True,
        )
    # Backfill existing rows with legacy format SR{id:06d}
    try:
        if conn.dialect.name == "sqlite":
            op.execute(sa.text(
                "UPDATE shipment_request SET tracking_code = 'SR' || printf('%06d', id) WHERE tracking_code IS NULL"
            ))
        else:
            op.execute(sa.text(
                "UPDATE shipment_request SET tracking_code = 'SR' || LPAD(CAST(id AS VARCHAR(20)), 6, '0') WHERE tracking_code IS NULL"
            ))
    except Exception:
        pass


def downgrade() -> None:
    conn = op.get_bind()
    if _index_exists(conn, INDEX_NAME, TABLE_NAME):
        op.drop_index(INDEX_NAME, table_name=TABLE_NAME)
    if _column_exists(conn, TABLE_NAME, COLUMN_NAME):
        op.drop_column(TABLE_NAME, COLUMN_NAME)
