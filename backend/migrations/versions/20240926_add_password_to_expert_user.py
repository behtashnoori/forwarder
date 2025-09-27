"""add password to expert user

Revision ID: 20240926_add_password_to_expert_user
Revises: 20240925_fix_customer_shipment_relationship
Create Date: 2024-09-26 16:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20240926_add_password_to_expert_user'
down_revision = '20240925_fix_customer_shipment_relationship'
branch_labels = None
depends_on = None


def upgrade():
    # Add password_hash column to expert_user table
    op.add_column('expert_user', sa.Column('password_hash', sa.String(length=128), nullable=True))
    
    # Update existing users with default password hash (password: "expert123")
    # This is a bcrypt hash of "expert123"
    default_password_hash = '$2b$12$LQv3c1yqBWVHxkd0LQ4Q2e7Tq4lY8k9Z6p5v3nF7j8K2w4N9m1X8d'
    op.execute(f"UPDATE expert_user SET password_hash = '{default_password_hash}' WHERE password_hash IS NULL")
    
    # Make password_hash NOT NULL
    op.alter_column('expert_user', 'password_hash', nullable=False)


def downgrade():
    # Remove password_hash column
    op.drop_column('expert_user', 'password_hash')

