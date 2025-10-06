"""Add international shipping models - countries and cities

Revision ID: 20250110_add_international_models
Revises: 20251006_124249_add_international_shipping_fields
Create Date: 2025-01-10 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250110_add_international_models'
down_revision = '20251006_124249'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create country table
    op.create_table('country',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('name_en', sa.String(length=100), nullable=False),
        sa.Column('name_fa', sa.String(length=100), nullable=False),
        sa.Column('code', sa.String(length=3), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    
    # Create international_city table
    op.create_table('international_city',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('name_en', sa.String(length=100), nullable=False),
        sa.Column('name_fa', sa.String(length=100), nullable=False),
        sa.Column('country_id', sa.BigInteger(), nullable=False),
        sa.Column('city_type', sa.String(length=20), nullable=False),
        sa.Column('is_major_port', sa.Boolean(), nullable=True),
        sa.Column('is_major_airport', sa.Boolean(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['country_id'], ['country.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('international_city')
    op.drop_table('country')
