"""Add customer gamification system

Revision ID: 20250120_add_customer_gamification_system
Revises: 20251006_124249_add_international_shipping_fields
Create Date: 2025-01-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250120_add_customer_gamification_system'
down_revision = '20250120_add_separate_transport_methods'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add customer gamification system tables and fields."""
    
    # Create customer_gamification table
    op.create_table(
        'customer_gamification',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('email', sa.String(length=100), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=True),
        sa.Column('last_name', sa.String(length=100), nullable=True),
        sa.Column('is_email_verified', sa.Boolean(), nullable=True),
        sa.Column('email_verification_token', sa.String(length=100), nullable=True),
        sa.Column('verification_expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('last_login_at', sa.DateTime(), nullable=True),
        sa.Column('total_requests', sa.Integer(), nullable=True),
        sa.Column('completed_requests', sa.Integer(), nullable=True),
        sa.Column('loyalty_points', sa.Integer(), nullable=True),
        sa.Column('customer_level', sa.String(length=20), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    
    # Create customer_workflow_step table
    op.create_table(
        'customer_workflow_step',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('customer_id', sa.BigInteger(), nullable=False),
        sa.Column('shipment_request_id', sa.BigInteger(), nullable=False),
        sa.Column('step_name', sa.String(length=50), nullable=False),
        sa.Column('step_order', sa.Integer(), nullable=False),
        sa.Column('is_completed', sa.Boolean(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('points_earned', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['customer_id'], ['customer_gamification.id'], ),
        sa.ForeignKeyConstraint(['shipment_request_id'], ['shipment_request.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add gamification_customer_id to shipment_request table
    op.add_column('shipment_request', sa.Column('gamification_customer_id', sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        'fk_shipment_request_gamification_customer',
        'shipment_request', 'customer_gamification',
        ['gamification_customer_id'], ['id']
    )


def downgrade() -> None:
    """Remove customer gamification system tables and fields."""
    
    # Remove foreign key and column from shipment_request
    op.drop_constraint('fk_shipment_request_gamification_customer', 'shipment_request', type_='foreignkey')
    op.drop_column('shipment_request', 'gamification_customer_id')
    
    # Drop tables
    op.drop_table('customer_workflow_step')
    op.drop_table('customer_gamification')
