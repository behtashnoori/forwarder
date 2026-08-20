"""Extend governed apply-run evidence for document catalog packages.

Revision ID: 20260901_document_catalog_runs
Revises: 20260831_document_catalog_metadata
"""

from alembic import op
import sqlalchemy as sa

revision = "20260901_document_catalog_runs"
down_revision = "20260831_document_catalog_metadata"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("reference_data_seed_run") as batch:
        batch.drop_constraint(
            "ck_reference_data_seed_run_counts_nonnegative", type_="check"
        )
        batch.add_column(
            sa.Column(
                "catalog_family",
                sa.String(40),
                nullable=False,
                server_default="REFERENCE_DATA",
            )
        )
        batch.add_column(sa.Column("catalog_name", sa.String(100), nullable=True))
        batch.add_column(sa.Column("schema_version", sa.String(32), nullable=True))
        batch.add_column(
            sa.Column("source_bundle_version", sa.String(100), nullable=True)
        )
        batch.add_column(
            sa.Column("updated_count", sa.Integer(), nullable=False, server_default="0")
        )
        batch.add_column(sa.Column("idempotency_key", sa.String(128), nullable=True))
        batch.add_column(sa.Column("request_hash", sa.String(64), nullable=True))
        batch.create_unique_constraint(
            "uq_reference_data_seed_run_idempotency_key", ["idempotency_key"]
        )
        batch.create_check_constraint(
            "ck_reference_data_seed_run_counts_nonnegative",
            "planned_count >= 0 AND created_count >= 0 AND updated_count >= 0 AND unchanged_count >= 0 AND conflict_count >= 0",
        )


def downgrade():
    connection = op.get_bind()
    if connection.execute(
        sa.text(
            "SELECT 1 FROM reference_data_seed_run WHERE catalog_family <> 'REFERENCE_DATA' OR catalog_name IS NOT NULL OR schema_version IS NOT NULL OR source_bundle_version IS NOT NULL OR updated_count <> 0 OR idempotency_key IS NOT NULL OR request_hash IS NOT NULL LIMIT 1"
        )
    ).first():
        raise RuntimeError(
            "Downgrade refused while document-catalog apply evidence exists"
        )
    with op.batch_alter_table("reference_data_seed_run") as batch:
        batch.drop_constraint(
            "ck_reference_data_seed_run_counts_nonnegative", type_="check"
        )
        batch.drop_constraint(
            "uq_reference_data_seed_run_idempotency_key", type_="unique"
        )
        for column in (
            "request_hash",
            "idempotency_key",
            "updated_count",
            "source_bundle_version",
            "schema_version",
            "catalog_name",
            "catalog_family",
        ):
            batch.drop_column(column)
        batch.create_check_constraint(
            "ck_reference_data_seed_run_counts_nonnegative",
            "planned_count >= 0 AND created_count >= 0 AND unchanged_count >= 0 AND conflict_count >= 0",
        )
