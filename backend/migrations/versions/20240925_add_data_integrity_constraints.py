"""Add data integrity constraints and optimizations

Revision ID: 20240925_add_data_integrity_constraints
Revises: 20240925_add_performance_indexes
Create Date: 2024-09-25 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20240925_add_data_integrity_constraints'
down_revision = '20240925_add_performance_indexes'
branch_labels = None
depends_on = None


def upgrade():
    # Add check constraints for data integrity
    
    # Customer constraints
    op.create_check_constraint(
        'ck_customer_email_format',
        'customer',
        "email IS NULL OR email LIKE '%@%'"
    )
    
    op.create_check_constraint(
        'ck_customer_phone_format',
        'customer',
        "phone IS NULL OR phone ~ '^[0-9+\\-\\s()]+$'"
    )
    
    op.create_check_constraint(
        'ck_customer_customer_type',
        'customer',
        "customer_type IN ('prospect', 'customer', 'partner', 'vendor')"
    )
    
    op.create_check_constraint(
        'ck_customer_status',
        'customer',
        "status IN ('active', 'inactive', 'blocked')"
    )
    
    op.create_check_constraint(
        'ck_customer_company_size',
        'customer',
        "company_size IS NULL OR company_size IN ('small', 'medium', 'large', 'enterprise')"
    )
    
    # Opportunity constraints
    op.create_check_constraint(
        'ck_opportunity_stage',
        'opportunity',
        "stage IN ('lead', 'qualified', 'proposal', 'negotiation', 'closed_won', 'closed_lost')"
    )
    
    op.create_check_constraint(
        'ck_opportunity_status',
        'opportunity',
        "status IN ('open', 'won', 'lost', 'cancelled')"
    )
    
    op.create_check_constraint(
        'ck_opportunity_probability',
        'opportunity',
        "probability >= 0 AND probability <= 100"
    )
    
    op.create_check_constraint(
        'ck_opportunity_value',
        'opportunity',
        "value IS NULL OR value >= 0"
    )
    
    # Activity constraints
    op.create_check_constraint(
        'ck_activity_type',
        'activity',
        "activity_type IN ('call', 'email', 'meeting', 'task', 'note', 'follow_up')"
    )
    
    op.create_check_constraint(
        'ck_activity_status',
        'activity',
        "status IN ('pending', 'completed', 'cancelled')"
    )
    
    op.create_check_constraint(
        'ck_activity_priority',
        'activity',
        "priority IN ('low', 'normal', 'high', 'urgent')"
    )
    
    op.create_check_constraint(
        'ck_activity_duration',
        'activity',
        "duration_minutes IS NULL OR duration_minutes >= 0"
    )
    
    # Task constraints
    op.create_check_constraint(
        'ck_task_status',
        'task',
        "status IN ('pending', 'in_progress', 'completed', 'cancelled')"
    )
    
    op.create_check_constraint(
        'ck_task_priority',
        'task',
        "priority IN ('low', 'normal', 'high', 'urgent')"
    )
    
    # ShipmentRequest constraints
    op.create_check_constraint(
        'ck_shipment_request_status',
        'shipment_request',
        "status IN ('new', 'assigned', 'in_progress', 'waiting_for_customer', 'won', 'lost', 'closed')"
    )
    
    op.create_check_constraint(
        'ck_shipment_request_priority',
        'shipment_request',
        "priority IN ('low', 'normal', 'high', 'urgent')"
    )
    
    op.create_check_constraint(
        'ck_shipment_request_weight',
        'shipment_request',
        "cargo_weight IS NULL OR cargo_weight > 0"
    )
    
    op.create_check_constraint(
        'ck_shipment_request_volume',
        'shipment_request',
        "cargo_volume IS NULL OR cargo_volume > 0"
    )
    
    op.create_check_constraint(
        'ck_shipment_request_value',
        'shipment_request',
        "cargo_value IS NULL OR cargo_value >= 0"
    )
    
    # ExpertUser constraints
    op.create_check_constraint(
        'ck_expert_user_email_format',
        'expert_user',
        "email IS NULL OR email LIKE '%@%'"
    )
    
    op.create_check_constraint(
        'ck_expert_user_role',
        'expert_user',
        "role IN ('expert', 'admin', 'manager')"
    )
    
    op.create_check_constraint(
        'ck_expert_user_is_active',
        'expert_user',
        "is_active IN (0, 1)"
    )
    
    # Add unique constraints where needed
    op.create_unique_constraint(
        'uq_customer_email_active',
        'customer',
        ['email'],
        postgresql_where=sa.text("email IS NOT NULL AND status = 'active'")
    )
    
    op.create_unique_constraint(
        'uq_expert_user_username_active',
        'expert_user',
        ['username'],
        postgresql_where=sa.text("is_active = 1")
    )
    
    # Add foreign key constraints with proper actions
    op.create_foreign_key(
        'fk_customer_contact_customer_id',
        'customer_contact',
        'customer',
        ['customer_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    op.create_foreign_key(
        'fk_opportunity_customer_id',
        'opportunity',
        'customer',
        ['customer_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    op.create_foreign_key(
        'fk_opportunity_assigned_to',
        'opportunity',
        'expert_user',
        ['assigned_to'],
        ['id'],
        ondelete='SET NULL'
    )
    
    op.create_foreign_key(
        'fk_activity_customer_id',
        'activity',
        'customer',
        ['customer_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    op.create_foreign_key(
        'fk_activity_opportunity_id',
        'activity',
        'opportunity',
        ['opportunity_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    op.create_foreign_key(
        'fk_activity_expert_user_id',
        'activity',
        'expert_user',
        ['expert_user_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    op.create_foreign_key(
        'fk_task_assigned_to',
        'task',
        'expert_user',
        ['assigned_to'],
        ['id'],
        ondelete='CASCADE'
    )
    
    op.create_foreign_key(
        'fk_task_created_by',
        'task',
        'expert_user',
        ['created_by'],
        ['id'],
        ondelete='CASCADE'
    )
    
    op.create_foreign_key(
        'fk_task_customer_id',
        'task',
        'customer',
        ['customer_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    op.create_foreign_key(
        'fk_task_opportunity_id',
        'task',
        'opportunity',
        ['opportunity_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    op.create_foreign_key(
        'fk_report_created_by',
        'report',
        'expert_user',
        ['created_by'],
        ['id'],
        ondelete='CASCADE'
    )
    
    # Add triggers for automatic timestamp updates
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    
    # Apply triggers to relevant tables
    op.execute("""
        CREATE TRIGGER update_customer_updated_at 
        BEFORE UPDATE ON customer 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)
    
    op.execute("""
        CREATE TRIGGER update_opportunity_updated_at 
        BEFORE UPDATE ON opportunity 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)
    
    op.execute("""
        CREATE TRIGGER update_activity_updated_at 
        BEFORE UPDATE ON activity 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)
    
    op.execute("""
        CREATE TRIGGER update_task_updated_at 
        BEFORE UPDATE ON task 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)
    
    op.execute("""
        CREATE TRIGGER update_report_updated_at 
        BEFORE UPDATE ON report 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)
    
    op.execute("""
        CREATE TRIGGER update_shipment_request_updated_at 
        BEFORE UPDATE ON shipment_request 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)


def downgrade():
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS update_shipment_request_updated_at ON shipment_request;")
    op.execute("DROP TRIGGER IF EXISTS update_report_updated_at ON report;")
    op.execute("DROP TRIGGER IF EXISTS update_task_updated_at ON task;")
    op.execute("DROP TRIGGER IF EXISTS update_activity_updated_at ON activity;")
    op.execute("DROP TRIGGER IF EXISTS update_opportunity_updated_at ON opportunity;")
    op.execute("DROP TRIGGER IF EXISTS update_customer_updated_at ON customer;")
    
    # Drop function
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column();")
    
    # Drop foreign key constraints
    op.drop_constraint('fk_report_created_by', 'report')
    op.drop_constraint('fk_task_opportunity_id', 'task')
    op.drop_constraint('fk_task_customer_id', 'task')
    op.drop_constraint('fk_task_created_by', 'task')
    op.drop_constraint('fk_task_assigned_to', 'task')
    op.drop_constraint('fk_activity_expert_user_id', 'activity')
    op.drop_constraint('fk_activity_opportunity_id', 'activity')
    op.drop_constraint('fk_activity_customer_id', 'activity')
    op.drop_constraint('fk_opportunity_assigned_to', 'opportunity')
    op.drop_constraint('fk_opportunity_customer_id', 'opportunity')
    op.drop_constraint('fk_customer_contact_customer_id', 'customer_contact')
    
    # Drop unique constraints
    op.drop_constraint('uq_expert_user_username_active', 'expert_user')
    op.drop_constraint('uq_customer_email_active', 'customer')
    
    # Drop check constraints
    op.drop_constraint('ck_expert_user_is_active', 'expert_user')
    op.drop_constraint('ck_expert_user_role', 'expert_user')
    op.drop_constraint('ck_expert_user_email_format', 'expert_user')
    op.drop_constraint('ck_shipment_request_value', 'shipment_request')
    op.drop_constraint('ck_shipment_request_volume', 'shipment_request')
    op.drop_constraint('ck_shipment_request_weight', 'shipment_request')
    op.drop_constraint('ck_shipment_request_priority', 'shipment_request')
    op.drop_constraint('ck_shipment_request_status', 'shipment_request')
    op.drop_constraint('ck_task_priority', 'task')
    op.drop_constraint('ck_task_status', 'task')
    op.drop_constraint('ck_activity_duration', 'activity')
    op.drop_constraint('ck_activity_priority', 'activity')
    op.drop_constraint('ck_activity_status', 'activity')
    op.drop_constraint('ck_activity_type', 'activity')
    op.drop_constraint('ck_opportunity_value', 'opportunity')
    op.drop_constraint('ck_opportunity_probability', 'opportunity')
    op.drop_constraint('ck_opportunity_status', 'opportunity')
    op.drop_constraint('ck_opportunity_stage', 'opportunity')
    op.drop_constraint('ck_customer_company_size', 'customer')
    op.drop_constraint('ck_customer_status', 'customer')
    op.drop_constraint('ck_customer_customer_type', 'customer')
    op.drop_constraint('ck_customer_phone_format', 'customer')
    op.drop_constraint('ck_customer_email_format', 'customer')
