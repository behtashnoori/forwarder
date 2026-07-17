"""Add internal tracking location references and immutable update snapshots.

Revision ID: 20260725_add_tracking_location_reference
Revises: 20260720_expand_reference_data_identity
"""
from alembic import op
import sqlalchemy as sa

revision="20260725_add_tracking_location_reference"
down_revision="20260720_expand_reference_data_identity"
branch_labels=None
depends_on=None
BIGINT=sa.BigInteger().with_variant(sa.Integer(),"sqlite")

def upgrade():
    op.create_table(
        "tracking_location_reference",
        sa.Column("id",BIGINT,sa.Identity(),primary_key=True),
        sa.Column("internal_key",sa.String(100),nullable=False),
        sa.Column("name_fa",sa.String(160),nullable=False),sa.Column("name_en",sa.String(160)),
        sa.Column("country_code",sa.String(2),nullable=False),sa.Column("location_type",sa.String(32),nullable=False),
        sa.Column("aliases",sa.JSON()),sa.Column("reference_status",sa.String(32),nullable=False,server_default="internal_reference"),
        sa.Column("sort_order",sa.Integer(),nullable=False,server_default="0"),sa.Column("is_active",sa.Boolean(),nullable=False,server_default=sa.true()),
        sa.Column("notes",sa.Text()),sa.Column("created_at",sa.DateTime(),nullable=False,server_default=sa.func.now()),sa.Column("updated_at",sa.DateTime(),nullable=False,server_default=sa.func.now()),
        sa.UniqueConstraint("internal_key",name="uq_tracking_location_reference_internal_key"),
        sa.CheckConstraint("location_type IN ('origin_city','commercial_hub','seaport','rail_terminal','road_terminal','border_point','transit_city','iran_gateway','destination_city','other')",name="ck_tracking_location_reference_type"),
        sa.CheckConstraint("reference_status IN ('internal_reference','verified_internal','inactive')",name="ck_tracking_location_reference_status"),
        sa.CheckConstraint("sort_order >= 0",name="ck_tracking_location_reference_sort_order"),
    )
    op.create_index("ix_tracking_location_reference_active_sort","tracking_location_reference",["is_active","sort_order"])
    op.create_index("ix_tracking_location_reference_country_type","tracking_location_reference",["country_code","location_type"])
    with op.batch_alter_table("shipment_transport_unit_update",recreate="auto") as batch:
        batch.add_column(sa.Column("location_reference_id",BIGINT,nullable=True))
        batch.add_column(sa.Column("location_name_snapshot",sa.String(160),nullable=True))
        batch.add_column(sa.Column("country_code_snapshot",sa.String(2),nullable=True))
        batch.add_column(sa.Column("location_text",sa.String(255),nullable=True))
        batch.create_foreign_key("fk_tracking_update_location_reference","tracking_location_reference",["location_reference_id"],["id"],ondelete="RESTRICT")
    op.create_index("ix_tracking_update_location_reference_id","shipment_transport_unit_update",["location_reference_id"])

def downgrade():
    op.drop_index("ix_tracking_update_location_reference_id",table_name="shipment_transport_unit_update")
    with op.batch_alter_table("shipment_transport_unit_update",recreate="auto") as batch:
        batch.drop_constraint("fk_tracking_update_location_reference",type_="foreignkey")
        batch.drop_column("location_text");batch.drop_column("country_code_snapshot");batch.drop_column("location_name_snapshot");batch.drop_column("location_reference_id")
    op.drop_index("ix_tracking_location_reference_country_type",table_name="tracking_location_reference")
    op.drop_index("ix_tracking_location_reference_active_sort",table_name="tracking_location_reference")
    op.drop_table("tracking_location_reference")
