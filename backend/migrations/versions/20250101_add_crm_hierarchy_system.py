"""Add CRM hierarchy system with managers and business experts

Revision ID: 20250101_add_crm_hierarchy_system
Revises: 20240926_add_password_to_expert_user
Create Date: 2025-01-01 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '20250101_add_crm_hierarchy_system'
down_revision = '20240926_add_password_to_expert_user'
branch_labels = None
depends_on = None


def upgrade():
    # Add new fields to ExpertUser table for hierarchy
    op.add_column('expert_user', sa.Column('manager_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True))
    op.add_column('expert_user', sa.Column('department', sa.String(length=50), nullable=True))
    op.add_column('expert_user', sa.Column('specialization', sa.Text(), nullable=True))  # JSON string for specializations
    
    # Create TransportMethod table
    op.create_table('transport_method',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('name_fa', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create ExpertSpecialization table (many-to-many relationship)
    op.create_table('expert_specialization',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('expert_user_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('transport_method_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('proficiency_level', sa.String(length=20), default='intermediate'),  # beginner, intermediate, advanced, expert
        sa.Column('is_primary', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['expert_user_id'], ['expert_user.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['transport_method_id'], ['transport_method.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('expert_user_id', 'transport_method_id', name='uq_expert_transport_method')
    )
    
    # Create AssignmentRule table for automatic assignment logic
    op.create_table('assignment_rule',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('rule_type', sa.String(length=50), nullable=False),  # transport_method, location, priority, workload
        sa.Column('conditions', sa.Text(), nullable=False),  # JSON string for rule conditions
        sa.Column('priority', sa.Integer(), default=1),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_by', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['expert_user.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create AssignmentLog table to track automatic assignments
    op.create_table('assignment_log',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('shipment_request_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('assigned_expert_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('assignment_rule_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True),
        sa.Column('assignment_method', sa.String(length=20), nullable=False),  # automatic, manual, override
        sa.Column('assignment_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['shipment_request_id'], ['shipment_request.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assigned_expert_id'], ['expert_user.id']),
        sa.ForeignKeyConstraint(['assignment_rule_id'], ['assignment_rule.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add foreign key constraint for manager_id
    op.create_foreign_key(
        'fk_expert_user_manager',
        'expert_user',
        'expert_user',
        ['manager_id'],
        ['id'],
        ondelete='SET NULL'
    )
    
    # Create indexes for performance
    op.create_index('idx_expert_user_manager_id', 'expert_user', ['manager_id'])
    op.create_index('idx_expert_user_department', 'expert_user', ['department'])
    op.create_index('idx_expert_specialization_expert', 'expert_specialization', ['expert_user_id'])
    op.create_index('idx_expert_specialization_transport', 'expert_specialization', ['transport_method_id'])
    op.create_index('idx_assignment_rule_type', 'assignment_rule', ['rule_type'])
    op.create_index('idx_assignment_rule_active', 'assignment_rule', ['is_active'])
    op.create_index('idx_assignment_log_request', 'assignment_log', ['shipment_request_id'])
    op.create_index('idx_assignment_log_expert', 'assignment_log', ['assigned_expert_id'])


def downgrade():
    # Drop indexes
    op.drop_index('idx_assignment_log_expert')
    op.drop_index('idx_assignment_log_request')
    op.drop_index('idx_assignment_rule_active')
    op.drop_index('idx_assignment_rule_type')
    op.drop_index('idx_expert_specialization_transport')
    op.drop_index('idx_expert_specialization_expert')
    op.drop_index('idx_expert_user_department')
    op.drop_index('idx_expert_user_manager_id')
    
    # Drop foreign key constraint
    op.drop_constraint('fk_expert_user_manager', 'expert_user')
    
    # Drop tables
    op.drop_table('assignment_log')
    op.drop_table('assignment_rule')
    op.drop_table('expert_specialization')
    op.drop_table('transport_method')
    
    # Drop columns from expert_user
    op.drop_column('expert_user', 'specialization')
    op.drop_column('expert_user', 'department')
    op.drop_column('expert_user', 'manager_id')
