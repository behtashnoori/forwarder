"""Add immutable structured location evidence to canonical operational events."""

from alembic import op
import sqlalchemy as sa


revision = "20260919_operational_event_location_evidence"
down_revision = "20260918_customer_carrier_role"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "operational_event_location_evidence",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("operational_event_id", sa.BigInteger(), nullable=False),
        sa.Column("logistics_point_id", sa.BigInteger(), nullable=True),
        sa.Column("canonical_location_id", sa.BigInteger(), nullable=True),
        sa.Column("source_type", sa.String(40), nullable=False),
        sa.Column("source_identity", sa.String(100), nullable=True),
        sa.Column("display_name_snapshot", sa.String(200), nullable=True),
        sa.Column("country_code_snapshot", sa.String(3), nullable=True),
        sa.Column("name_en_snapshot", sa.String(160), nullable=True),
        sa.Column("location_type_snapshot", sa.String(64), nullable=True),
        sa.Column("city_name_snapshot", sa.String(160), nullable=True),
        sa.Column("location_text_snapshot", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["operational_event_id"], ["operational_event.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["logistics_point_id"], ["logistics_point.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["canonical_location_id"], ["canonical_location.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("operational_event_id", name="uq_event_location_evidence_event"),
        sa.CheckConstraint("source_type IN ('logistics_point','canonical_location','tracking_location_reference','manual')", name="ck_event_location_evidence_source_type"),
        sa.CheckConstraint("(logistics_point_id IS NULL OR canonical_location_id IS NULL)", name="ck_event_location_evidence_one_master_identity"),
    )
    # No checkpoint_text backfill: it has never been structured location evidence.


def downgrade():
    op.drop_table("operational_event_location_evidence")
