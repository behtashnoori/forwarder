"""Fix customer-shipment relationship

Revision ID: 20240925_fix_customer_shipment_relationship
Revises: 20240925_add_data_integrity_constraints
Create Date: 2024-09-25 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20240925_fix_customer_shipment_relationship'
down_revision = '20240925_add_data_integrity_constraints'
branch_labels = None
depends_on = None


def upgrade():
    # Add customer_id column to shipment_request table
    op.add_column('shipment_request', sa.Column('customer_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True))
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_shipment_request_customer_id',
        'shipment_request',
        'customer',
        ['customer_id'],
        ['id'],
        ondelete='SET NULL'
    )
    
    # Add index for performance
    op.create_index('idx_shipment_request_customer_id', 'shipment_request', ['customer_id'])


def downgrade():
    # Drop index
    op.drop_index('idx_shipment_request_customer_id', 'shipment_request')
    
    # Drop foreign key constraint
    op.drop_constraint('fk_shipment_request_customer_id', 'shipment_request')
    
    # Drop column
    op.drop_column('shipment_request', 'customer_id')

