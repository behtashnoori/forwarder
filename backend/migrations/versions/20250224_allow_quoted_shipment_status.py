"""Allow quoted as a shipment request lifecycle status.

Revision ID: 20250224_allow_quoted_status
Revises: 20250223_ensure_quote
Create Date: 2025-02-24

"""
from alembic import op


revision = "20250224_allow_quoted_status"
down_revision = "20250223_ensure_quote"
branch_labels = None
depends_on = None


OLD_STATUS_CHECK = (
    "status IN ('new', 'assigned', 'in_progress', "
    "'waiting_for_customer', 'won', 'lost', 'closed')"
)
NEW_STATUS_CHECK = (
    "status IN ('new', 'assigned', 'in_progress', 'quoted', "
    "'waiting_for_customer', 'won', 'lost', 'closed')"
)


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.drop_constraint("ck_shipment_request_status", "shipment_request", type_="check")
    op.create_check_constraint(
        "ck_shipment_request_status",
        "shipment_request",
        NEW_STATUS_CHECK,
    )


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.drop_constraint("ck_shipment_request_status", "shipment_request", type_="check")
    op.create_check_constraint(
        "ck_shipment_request_status",
        "shipment_request",
        OLD_STATUS_CHECK,
    )
