"""Allow legal customers without a fabricated contact name.

Revision ID: 20260920_legal_customer_nullable_contact_names
Revises: 20260919_operational_event_location_evidence
"""
from alembic import op
import sqlalchemy as sa


revision = "20260920_legal_customer_nullable_contact_names"
down_revision = "20260919_operational_event_location_evidence"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("customer") as batch_op:
        batch_op.alter_column("first_name", existing_type=sa.String(length=100), nullable=True)
        batch_op.alter_column("last_name", existing_type=sa.String(length=100), nullable=True)


def downgrade():
    bind = op.get_bind()
    missing = bind.execute(sa.text(
        "SELECT COUNT(*) FROM customer WHERE first_name IS NULL OR last_name IS NULL"
    )).scalar_one()
    if missing:
        raise RuntimeError(
            "Cannot restore customer contact NOT NULL constraints while legal customers have no contact names."
        )
    with op.batch_alter_table("customer") as batch_op:
        batch_op.alter_column("first_name", existing_type=sa.String(length=100), nullable=False)
        batch_op.alter_column("last_name", existing_type=sa.String(length=100), nullable=False)
