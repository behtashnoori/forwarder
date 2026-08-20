"""Index catalog-to-shipment cargo traceability reads.

Revision ID: 20260829_cargo_traceability_index
Revises: 20260828_referral_state_compat
"""

from alembic import op


revision = "20260829_cargo_traceability_index"
down_revision = "20260828_referral_state_compat"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "ix_shipment_cargo_item_catalog_shipment",
        "shipment_cargo_item",
        ["catalog_item_id", "operational_shipment_id"],
    )


def downgrade():
    op.drop_index(
        "ix_shipment_cargo_item_catalog_shipment",
        table_name="shipment_cargo_item",
    )
