"""Drop the invalid generic update trigger from shipment_request.

Revision ID: 20260716_drop_invalid_shipment_update_trigger
Revises: 20260715_multi_unit_tracking
Create Date: 2026-07-16
"""
from alembic import op


revision = "20260716_drop_invalid_shipment_update_trigger"
down_revision = "20260715_multi_unit_tracking"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # shipment_request has purpose-specific timestamps, but no updated_at column.
    # Keep the shared function and its five valid table triggers intact.
    op.execute(
        "DROP TRIGGER IF EXISTS update_shipment_request_updated_at "
        "ON shipment_request"
    )


def downgrade() -> None:
    op.execute(
        "CREATE TRIGGER update_shipment_request_updated_at "
        "BEFORE UPDATE ON shipment_request "
        "FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()"
    )
