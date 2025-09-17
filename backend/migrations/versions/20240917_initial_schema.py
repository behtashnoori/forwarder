"""Initial schema for shipment request service.

Revision ID: 20240917_initial_schema
Revises: 
Create Date: 2024-09-17 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20240917_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create province, county, city, and shipment_request tables."""
    op.create_table(
        "province",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("code", sa.Text(), nullable=True),
        sa.Column("name_fa", sa.Text(), nullable=False),
    )

    op.create_table(
        "county",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("province_id", sa.BigInteger(), nullable=False),
        sa.Column("name_fa", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["province_id"],
            ["province.id"],
            name="fk_county_province_id",
            ondelete="CASCADE",
        ),
    )

    op.create_table(
        "city",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("county_id", sa.BigInteger(), nullable=False),
        sa.Column("province_id", sa.BigInteger(), nullable=False),
        sa.Column("name_fa", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["county_id"],
            ["county.id"],
            name="fk_city_county_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["province_id"],
            ["province.id"],
            name="fk_city_province_id",
            ondelete="CASCADE",
        ),
    )

    op.create_table(
        "shipment_request",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("origin_province_id", sa.BigInteger(), nullable=False),
        sa.Column("origin_county_id", sa.BigInteger(), nullable=False),
        sa.Column("origin_city_id", sa.BigInteger(), nullable=False),
        sa.Column("dest_province_id", sa.BigInteger(), nullable=False),
        sa.Column("dest_county_id", sa.BigInteger(), nullable=False),
        sa.Column("dest_city_id", sa.BigInteger(), nullable=False),
        sa.Column("contact_phone", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("ready_at", sa.DateTime(), nullable=False),
        sa.Column("status_request_status", sa.String(length=32), nullable=False),
        sa.Column("request_user_id", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(
            ["origin_province_id"],
            ["province.id"],
            name="fk_shipment_request_origin_province_id",
        ),
        sa.ForeignKeyConstraint(
            ["origin_county_id"],
            ["county.id"],
            name="fk_shipment_request_origin_county_id",
        ),
        sa.ForeignKeyConstraint(
            ["origin_city_id"],
            ["city.id"],
            name="fk_shipment_request_origin_city_id",
        ),
        sa.ForeignKeyConstraint(
            ["dest_province_id"],
            ["province.id"],
            name="fk_shipment_request_dest_province_id",
        ),
        sa.ForeignKeyConstraint(
            ["dest_county_id"],
            ["county.id"],
            name="fk_shipment_request_dest_county_id",
        ),
        sa.ForeignKeyConstraint(
            ["dest_city_id"],
            ["city.id"],
            name="fk_shipment_request_dest_city_id",
        ),
    )


def downgrade() -> None:
    """Drop all tables created in this revision."""
    op.drop_table("shipment_request")
    op.drop_table("city")
    op.drop_table("county")
    op.drop_table("province")
