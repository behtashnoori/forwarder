"""Add governed master-data foundation tables.

Revision ID: 20260807_master_data
Revises: 20260806_execution_units
"""
from alembic import op
import sqlalchemy as sa

revision = "20260807_master_data"
down_revision = "20260806_execution_units"
branch_labels = None
depends_on = None
BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def _common(table_name):
    return (
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column("immutable_code", sa.String(64), nullable=False),
        sa.Column("fa_name", sa.String(160), nullable=False),
        sa.Column("en_name", sa.String(160), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.UniqueConstraint("public_id", name=f"uq_{table_name}_public_id"),
        sa.UniqueConstraint("immutable_code", name=f"uq_{table_name}_immutable_code"),
        sa.CheckConstraint("version >= 1", name=f"ck_{table_name}_version_positive"),
    )


def upgrade():
    op.create_table(
        "cargo_type", *_common("cargo_type"),
        sa.Column("parent_id", BIGINT),
        sa.ForeignKeyConstraint(["parent_id"], ["cargo_type.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("parent_id IS NULL OR parent_id <> id", name="ck_cargo_type_not_self_parent"),
    )
    op.create_index("ix_cargo_type_active_order", "cargo_type", ["is_active", "display_order"])
    op.create_index("ix_cargo_type_parent_id", "cargo_type", ["parent_id"])
    op.create_table("service_type", *_common("service_type"))
    op.create_index("ix_service_type_active_order", "service_type", ["is_active", "display_order"])
    op.create_table(
        "unit_of_measure", *_common("unit_of_measure"),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("measurement_dimension", sa.String(32), nullable=False),
        sa.CheckConstraint(
            "measurement_dimension IN ('COUNT','WEIGHT','VOLUME','LENGTH','OTHER_GOVERNED')",
            name="ck_unit_of_measure_dimension",
        ),
    )
    op.create_index("ix_unit_of_measure_active_order", "unit_of_measure", ["is_active", "display_order"])
    op.create_index("ix_unit_of_measure_dimension", "unit_of_measure", ["measurement_dimension"])


def downgrade():
    op.drop_index("ix_unit_of_measure_dimension", table_name="unit_of_measure")
    op.drop_index("ix_unit_of_measure_active_order", table_name="unit_of_measure")
    op.drop_table("unit_of_measure")
    op.drop_index("ix_service_type_active_order", table_name="service_type")
    op.drop_table("service_type")
    op.drop_index("ix_cargo_type_parent_id", table_name="cargo_type")
    op.drop_index("ix_cargo_type_active_order", table_name="cargo_type")
    op.drop_table("cargo_type")
