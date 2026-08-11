"""Add normalized canonical decision components for MT-1C.1 Core guards.

Revision ID: 20260822_mt1c1_census_fence
Revises: 20260821_mt1d_canonical_census
"""
from alembic import op
import sqlalchemy as sa


revision = "20260822_mt1c1_census_fence"
down_revision = "20260821_mt1d_canonical_census"
branch_labels = None
depends_on = None

BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade():
    op.create_table(
        "ownership_decision_component",
        sa.Column("decision_id", BIGINT, nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("component_name", sa.String(80), nullable=False),
        sa.Column("component_kind", sa.String(16), nullable=False),
        sa.Column("canonical_value", sa.String(1024), nullable=False),
        sa.CheckConstraint("ordinal >= 0", name="ck_ownership_component_ordinal"),
        sa.CheckConstraint(
            "component_kind IN ('INTEGER','STRING','UUID')",
            name="ck_ownership_component_kind",
        ),
        sa.ForeignKeyConstraint(
            ["decision_id"],
            ["ownership_decision.id"],
            name="fk_ownership_component_decision",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "decision_id", "ordinal", name="pk_ownership_decision_component"
        ),
        sa.UniqueConstraint(
            "decision_id", "component_name", name="uq_ownership_component_name"
        ),
    )
    op.create_index(
        "ix_ownership_component_lookup",
        "ownership_decision_component",
        ["component_name", "component_kind", "canonical_value"],
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute("""
            CREATE TRIGGER trg_ownership_decision_component_append_only
            BEFORE UPDATE OR DELETE ON ownership_decision_component
            FOR EACH ROW EXECUTE FUNCTION mt1d_reject_history_rewrite()
        """)
        op.execute(
            "REVOKE INSERT, UPDATE, DELETE ON ownership_decision_component FROM PUBLIC"
        )


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            "DROP TRIGGER IF EXISTS trg_ownership_decision_component_append_only "
            "ON ownership_decision_component"
        )
    op.drop_index(
        "ix_ownership_component_lookup", table_name="ownership_decision_component"
    )
    op.drop_table("ownership_decision_component")
