"""Phase 3 P3-01 central reference families and organization activation.

Revision ID: 20260930_phase3_reference_catalog
Revises: 20260929_operational_monitoring_reliability
"""

from alembic import op
import sqlalchemy as sa


revision = "20260930_phase3_reference_catalog"
down_revision = "20260929_operational_monitoring_reliability"
branch_labels = None
depends_on = None

BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def _create_central_table(table_name, prefix):
    op.create_table(
        table_name,
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column("immutable_code", sa.String(64), nullable=False),
        sa.Column("fa_name", sa.String(160), nullable=False),
        sa.Column("en_name", sa.String(160), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.UniqueConstraint("public_id", name=f"uq_{prefix}_public_id"),
        sa.UniqueConstraint("immutable_code", name=f"uq_{prefix}_immutable_code"),
        sa.CheckConstraint("version >= 1", name=f"ck_{prefix}_version_positive"),
    )
    op.create_index(f"ix_{prefix}_is_active", table_name, ["is_active"])


def _create_activation_table(table_name, prefix, definition_column, definition_table):
    op.create_table(
        table_name,
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column("organization_id", BIGINT, nullable=False),
        sa.Column(definition_column, BIGINT, nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="ACTIVE"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("created_by", BIGINT, nullable=False),
        sa.Column("updated_by", BIGINT, nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["operational_organization.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            [definition_column], [f"{definition_table}.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["expert_user.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["updated_by"], ["expert_user.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("public_id", name=f"uq_{prefix}_public_id"),
        sa.UniqueConstraint(
            "organization_id", definition_column, name=f"uq_{prefix}"
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE','INACTIVE')", name=f"ck_{prefix}_status"
        ),
        sa.CheckConstraint("version >= 1", name=f"ck_{prefix}_version"),
    )
    op.create_index(
        f"ix_{prefix}_org_status", table_name, ["organization_id", "status"]
    )
    op.create_index(
        f"ix_{prefix}_definition", table_name, [definition_column]
    )


def upgrade():
    _create_central_table("packaging_type", "packaging_type")
    _create_central_table("transport_means_type", "transport_means_type")
    _create_central_table("transport_equipment_type", "transport_equipment_type")

    _create_activation_table(
        "organization_cargo_type_activation",
        "org_cargo_type_activation",
        "cargo_type_id",
        "cargo_type",
    )
    _create_activation_table(
        "organization_unit_of_measure_activation",
        "org_unit_of_measure_activation",
        "unit_of_measure_id",
        "unit_of_measure",
    )
    _create_activation_table(
        "organization_packaging_type_activation",
        "org_packaging_type_activation",
        "packaging_type_id",
        "packaging_type",
    )
    _create_activation_table(
        "organization_transport_means_type_activation",
        "org_transport_means_type_activation",
        "transport_means_type_id",
        "transport_means_type",
    )
    _create_activation_table(
        "organization_transport_equipment_type_activation",
        "org_transport_equipment_type_activation",
        "transport_equipment_type_id",
        "transport_equipment_type",
    )


def downgrade():
    bind = op.get_bind()
    guarded_tables = (
        "organization_cargo_type_activation",
        "organization_unit_of_measure_activation",
        "organization_packaging_type_activation",
        "organization_transport_means_type_activation",
        "organization_transport_equipment_type_activation",
        "packaging_type",
        "transport_means_type",
        "transport_equipment_type",
    )
    populated = [
        table
        for table in guarded_tables
        if bind.execute(sa.text(f'SELECT count(*) FROM "{table}"')).scalar_one()
    ]
    if populated:
        raise RuntimeError(
            "Downgrade refused: Phase 3 reference catalog data exists in "
            + ", ".join(populated)
            + "."
        )

    for table_name, prefix in (
        (
            "organization_transport_equipment_type_activation",
            "org_transport_equipment_type_activation",
        ),
        (
            "organization_transport_means_type_activation",
            "org_transport_means_type_activation",
        ),
        ("organization_packaging_type_activation", "org_packaging_type_activation"),
        (
            "organization_unit_of_measure_activation",
            "org_unit_of_measure_activation",
        ),
        ("organization_cargo_type_activation", "org_cargo_type_activation"),
    ):
        op.drop_index(f"ix_{prefix}_definition", table_name=table_name)
        op.drop_index(f"ix_{prefix}_org_status", table_name=table_name)
        op.drop_table(table_name)

    for table_name, prefix in (
        ("transport_equipment_type", "transport_equipment_type"),
        ("transport_means_type", "transport_means_type"),
        ("packaging_type", "packaging_type"),
    ):
        op.drop_index(f"ix_{prefix}_is_active", table_name=table_name)
        op.drop_table(table_name)
