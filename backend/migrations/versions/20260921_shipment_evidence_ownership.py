"""Generalize the existing document authority for shipment-owned evidence.

Revision ID: 20260921_shipment_evidence_ownership
Revises: 20260920_legal_customer_nullable_contact_names
"""
from alembic import op
import sqlalchemy as sa

revision = "20260921_shipment_evidence_ownership"
down_revision = "20260920_legal_customer_nullable_contact_names"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("case_document_file") as batch_op:
        batch_op.add_column(sa.Column("owner_type", sa.String(16), nullable=False, server_default="REQUEST"))
        batch_op.add_column(sa.Column("operational_shipment_id", sa.BigInteger(), nullable=True))
        batch_op.alter_column("shipment_request_id", existing_type=sa.BigInteger(), nullable=True)
        batch_op.create_foreign_key("fk_case_document_file_shipment", "operational_shipment", ["operational_shipment_id"], ["id"], ondelete="RESTRICT")
        batch_op.create_check_constraint("ck_case_document_file_owner_type", "owner_type IN ('REQUEST', 'SHIPMENT')")
        batch_op.create_check_constraint("ck_case_document_file_owner", "(owner_type = 'REQUEST' AND shipment_request_id IS NOT NULL AND operational_shipment_id IS NULL) OR (owner_type = 'SHIPMENT' AND operational_shipment_id IS NOT NULL)")
        batch_op.create_index("ix_case_document_file_owner_type", ["owner_type"])
        batch_op.create_index("ix_case_document_file_operational_shipment_id", ["operational_shipment_id"])


def downgrade():
    bind = op.get_bind()
    if bind.execute(sa.text("SELECT COUNT(*) FROM case_document_file WHERE owner_type = 'SHIPMENT' OR shipment_request_id IS NULL")).scalar_one():
        raise RuntimeError("Cannot downgrade while shipment-owned evidence exists.")
    with op.batch_alter_table("case_document_file") as batch_op:
        batch_op.drop_index("ix_case_document_file_operational_shipment_id")
        batch_op.drop_index("ix_case_document_file_owner_type")
        batch_op.drop_constraint("ck_case_document_file_owner", type_="check")
        batch_op.drop_constraint("ck_case_document_file_owner_type", type_="check")
        batch_op.drop_constraint("fk_case_document_file_shipment", type_="foreignkey")
        batch_op.alter_column("shipment_request_id", existing_type=sa.BigInteger(), nullable=False)
        batch_op.drop_column("operational_shipment_id")
        batch_op.drop_column("owner_type")
