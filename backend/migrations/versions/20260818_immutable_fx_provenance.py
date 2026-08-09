"""Immutable observation FX provenance. Revision: 20260818_immutable_fx_provenance."""
from alembic import op
import sqlalchemy as sa

revision = "20260818_immutable_fx_provenance"
down_revision = "20260817_shipment_economics_core"
branch_labels = None
depends_on = None
BIG = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade():
    op.create_table(
        "economic_observation_fx",
        sa.Column("id", BIG, primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column("organization_id", BIG, nullable=False),
        sa.Column("observation_id", BIG, nullable=False),
        sa.Column("fx_rate_id", BIG, nullable=False),
        sa.Column("fx_rate_public_id", sa.String(36), nullable=False),
        sa.Column("fx_rate_version", sa.Integer, nullable=False),
        sa.Column("from_currency", sa.String(3), nullable=False),
        sa.Column("to_currency", sa.String(3), nullable=False),
        sa.Column("rate", sa.Numeric(24, 12), nullable=False),
        sa.Column("rate_type", sa.String(24), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("authority", sa.String(120), nullable=False),
        sa.Column("source", sa.String(120), nullable=False),
        sa.Column("bound_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["operational_organization.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["observation_id"], ["economic_observation.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["fx_rate_id"], ["economic_fx_rate.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("observation_id", name="uq_economic_observation_fx_observation"),
        sa.UniqueConstraint("public_id", name="uq_economic_observation_fx_public_id"),
        sa.CheckConstraint("rate > 0", name="ck_economic_observation_fx_positive"),
        sa.CheckConstraint("from_currency <> to_currency", name="ck_economic_observation_fx_pair"),
    )


def downgrade():
    connection = op.get_bind()
    if connection.execute(sa.text("SELECT 1 FROM economic_observation_fx LIMIT 1")).first():
        raise RuntimeError("Downgrade refused: consequential immutable FX provenance exists")
    op.drop_table("economic_observation_fx")
