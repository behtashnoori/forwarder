"""Add Iran destination point fields to shipment_request

Revision ID: 20260727_add_iran_destination_point
Revises: 20260726_seed_iran_tracking_reference
Create Date: 2026-07-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260727_add_iran_destination_point"
down_revision = "20260726_seed_iran_tracking_reference"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("shipment_request", schema=None) as batch_op:
        batch_op.add_column(sa.Column("iran_dest_type", sa.String(length=10), nullable=True))
        batch_op.add_column(sa.Column("iran_dest_customs_office_id", sa.BigInteger(), nullable=True))
        batch_op.add_column(sa.Column("iran_dest_city_id", sa.BigInteger(), nullable=True))
        batch_op.create_foreign_key(
            "fk_shipment_request_iran_dest_customs_office",
            "customs_office",
            ["iran_dest_customs_office_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_shipment_request_iran_dest_city",
            "city",
            ["iran_dest_city_id"],
            ["id"],
        )


def downgrade():
    with op.batch_alter_table("shipment_request", schema=None) as batch_op:
        batch_op.drop_constraint("fk_shipment_request_iran_dest_city", type_="foreignkey")
        batch_op.drop_constraint("fk_shipment_request_iran_dest_customs_office", type_="foreignkey")
        batch_op.drop_column("iran_dest_city_id")
        batch_op.drop_column("iran_dest_customs_office_id")
        batch_op.drop_column("iran_dest_type")
