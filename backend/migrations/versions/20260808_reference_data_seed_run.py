"""Add persistent reference-data seed execution evidence.

Revision ID: 20260808_reference_seed
Revises: 20260807_master_data
"""
from alembic import op
import sqlalchemy as sa

revision = "20260808_reference_seed"
down_revision = "20260807_master_data"
branch_labels = None
depends_on = None
BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade():
    op.create_table(
        "reference_data_seed_run",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column("catalog_version", sa.String(64), nullable=False),
        sa.Column("checksum", sa.String(71), nullable=False),
        sa.Column("environment", sa.String(32), nullable=False),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("planned_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unchanged_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("conflict_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("executed_by", sa.String(160), nullable=False),
        sa.Column("approval_reference", sa.String(200), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime()),
        sa.Column("error_summary", sa.String(500)),
        sa.UniqueConstraint("public_id", name="uq_reference_data_seed_run_public_id"),
        sa.CheckConstraint("mode IN ('apply')", name="ck_reference_data_seed_run_mode"),
        sa.CheckConstraint(
            "status IN ('started','succeeded','failed','refused')",
            name="ck_reference_data_seed_run_status",
        ),
        sa.CheckConstraint(
            "planned_count >= 0 AND created_count >= 0 AND unchanged_count >= 0 AND conflict_count >= 0",
            name="ck_reference_data_seed_run_counts_nonnegative",
        ),
    )
    op.create_index(
        "ix_reference_data_seed_run_catalog_target",
        "reference_data_seed_run",
        ["catalog_version", "checksum", "environment"],
    )
    op.create_index(
        "ix_reference_data_seed_run_status_started",
        "reference_data_seed_run",
        ["status", "started_at"],
    )


def downgrade():
    op.drop_index("ix_reference_data_seed_run_status_started", table_name="reference_data_seed_run")
    op.drop_index("ix_reference_data_seed_run_catalog_target", table_name="reference_data_seed_run")
    op.drop_table("reference_data_seed_run")
