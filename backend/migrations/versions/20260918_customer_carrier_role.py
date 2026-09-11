"""Add multi-role party eligibility and backfill current carrier relationships."""
from alembic import op
import sqlalchemy as sa

revision = "20260918_customer_carrier_role"
down_revision = "20260917_shared_transport_execution"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("customer_role_assignment", sa.Column("id", sa.BigInteger(), primary_key=True), sa.Column("customer_id", sa.BigInteger(), nullable=False), sa.Column("operational_organization_id", sa.BigInteger(), nullable=False), sa.Column("role_code", sa.String(32), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")), sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")), sa.Column("created_by", sa.BigInteger(), nullable=True), sa.Column("updated_by", sa.BigInteger(), nullable=True), sa.ForeignKeyConstraint(["customer_id", "operational_organization_id"], ["customer.id", "customer.operational_organization_id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["created_by"], ["expert_user.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["updated_by"], ["expert_user.id"], ondelete="RESTRICT"), sa.UniqueConstraint("customer_id", "role_code", name="uq_customer_role_assignment"), sa.CheckConstraint("role_code = 'CARRIER'", name="ck_customer_role_assignment_code"))
    op.create_index("ix_customer_role_assignment_active_lookup", "customer_role_assignment", ["operational_organization_id", "role_code", "is_active"])
    op.execute("""INSERT INTO customer_role_assignment (customer_id, operational_organization_id, role_code, is_active, created_at, updated_at) SELECT DISTINCT eu.carrier_customer_id, eu.organization_id, 'CARRIER', TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP FROM execution_unit eu JOIN customer c ON c.id = eu.carrier_customer_id WHERE eu.carrier_customer_id IS NOT NULL AND c.operational_organization_id = eu.organization_id ON CONFLICT (customer_id, role_code) DO NOTHING""")

def downgrade():
    op.drop_index("ix_customer_role_assignment_active_lookup", table_name="customer_role_assignment")
    op.drop_table("customer_role_assignment")
