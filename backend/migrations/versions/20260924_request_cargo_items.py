"""Add optional Request-owned multi-item Cargo.

Revision ID: 20260924_request_cargo_items
Revises: 20260923_notification_lifecycle
"""

from alembic import op
import sqlalchemy as sa


revision = "20260924_request_cargo_items"
down_revision = "20260923_notification_lifecycle"
branch_labels = None
depends_on = None

BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade():
    op.create_table(
        "request_cargo_item",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column("shipment_request_id", BIGINT, nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("cargo_type_id", BIGINT, nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=True),
        sa.Column("uom_id", BIGINT, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["shipment_request_id"],
            ["shipment_request.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["cargo_type_id"], ["cargo_type.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["uom_id"], ["unit_of_measure.id"], ondelete="RESTRICT"
        ),
        sa.UniqueConstraint("public_id", name="uq_request_cargo_item_public_id"),
        sa.UniqueConstraint(
            "shipment_request_id",
            "position",
            name="uq_request_cargo_item_request_position",
        ),
        sa.CheckConstraint(
            "position >= 1", name="ck_request_cargo_item_position_positive"
        ),
        sa.CheckConstraint(
            "description IS NULL OR length(trim(description)) > 0",
            name="ck_request_cargo_item_description_nonblank",
        ),
        sa.CheckConstraint(
            "quantity IS NULL OR quantity > 0",
            name="ck_request_cargo_item_quantity_positive",
        ),
        sa.CheckConstraint(
            "(quantity IS NULL AND uom_id IS NULL) OR "
            "(quantity IS NOT NULL AND uom_id IS NOT NULL)",
            name="ck_request_cargo_item_quantity_uom_pair",
        ),
        sa.CheckConstraint(
            "cargo_type_id IS NOT NULL OR description IS NOT NULL OR "
            "(quantity IS NOT NULL AND uom_id IS NOT NULL)",
            name="ck_request_cargo_item_meaningful",
        ),
    )
    op.create_index(
        "ix_request_cargo_item_request",
        "request_cargo_item",
        ["shipment_request_id", "position"],
    )


def downgrade():
    bind = op.get_bind()
    item_count = bind.execute(
        sa.text("SELECT COUNT(*) FROM request_cargo_item")
    ).scalar_one()
    if item_count:
        raise RuntimeError(
            "Cannot downgrade while Request Cargo Item evidence exists."
        )

    op.drop_index(
        "ix_request_cargo_item_request", table_name="request_cargo_item"
    )
    op.drop_table("request_cargo_item")
