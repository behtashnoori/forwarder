"""Add the MT-1C runtime ownership certification registry.

Revision ID: 20260820_mt1c_quarantine_runtime
Revises: 20260819_v191_acceptance_corrections
"""
from alembic import op
import sqlalchemy as sa


revision = "20260820_mt1c_quarantine_runtime"
down_revision = "20260819_v191_acceptance_corrections"
branch_labels = None
depends_on = None

BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade():
    op.create_table(
        "ownership_certification_scope",
        sa.Column("entity_type", sa.String(80), primary_key=True),
        sa.Column("certified_through_id", sa.BigInteger(), nullable=False),
        sa.Column("census_id", sa.String(64), nullable=False),
        sa.Column("decision_epoch", sa.BigInteger(), nullable=False),
        sa.Column("activated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("certified_through_id >= 0", name="ck_ownership_scope_watermark"),
        sa.CheckConstraint("decision_epoch >= 1", name="ck_ownership_scope_epoch"),
    )
    op.create_table(
        "ownership_certification_decision",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("entity_type", sa.String(80), nullable=False),
        sa.Column("entity_id", sa.BigInteger(), nullable=False),
        sa.Column("classification", sa.String(32), nullable=False),
        sa.Column("census_id", sa.String(64), nullable=False),
        sa.Column("decision_id", sa.String(128), nullable=False),
        sa.Column("decided_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("entity_id > 0", name="ck_ownership_decision_entity_id"),
        sa.CheckConstraint(
            "classification IN ('DETERMINISTIC','QUARANTINED','INVALID_LINEAGE','CONFLICT','UNKNOWN')",
            name="ck_ownership_decision_classification",
        ),
        sa.UniqueConstraint("entity_type", "entity_id", name="uq_ownership_decision_entity"),
    )
    op.create_index(
        "ix_ownership_certification_decision_entity_type",
        "ownership_certification_decision",
        ["entity_type"],
    )


def downgrade():
    op.drop_index(
        "ix_ownership_certification_decision_entity_type",
        table_name="ownership_certification_decision",
    )
    op.drop_table("ownership_certification_decision")
    op.drop_table("ownership_certification_scope")
