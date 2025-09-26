"""Add performance indexes for better query performance

Revision ID: 20240925_add_performance_indexes
Revises: 20240925_add_crm_models
Create Date: 2024-09-25 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20240925_add_performance_indexes'
down_revision = '20240925_add_crm_models'
branch_labels = None
depends_on = None


def upgrade():
    # Indexes for ShipmentRequest table
    op.create_index('idx_shipment_request_status', 'shipment_request', ['status'])
    op.create_index('idx_shipment_request_created_at', 'shipment_request', ['created_at'])
    op.create_index('idx_shipment_request_assigned_to', 'shipment_request', ['assigned_to'])
    op.create_index('idx_shipment_request_priority', 'shipment_request', ['priority'])
    op.create_index('idx_shipment_request_sla_due_at', 'shipment_request', ['sla_due_at'])
    
    # Composite indexes for common queries
    op.create_index('idx_shipment_request_status_created', 'shipment_request', ['status', 'created_at'])
    op.create_index('idx_shipment_request_assigned_status', 'shipment_request', ['assigned_to', 'status'])
    
    # Indexes for Customer table
    op.create_index('idx_customer_email', 'customer', ['email'])
    op.create_index('idx_customer_phone', 'customer', ['phone'])
    op.create_index('idx_customer_customer_type', 'customer', ['customer_type'])
    op.create_index('idx_customer_status', 'customer', ['status'])
    op.create_index('idx_customer_created_at', 'customer', ['created_at'])
    op.create_index('idx_customer_last_contact_at', 'customer', ['last_contact_at'])
    
    # Composite indexes for customer queries
    op.create_index('idx_customer_type_status', 'customer', ['customer_type', 'status'])
    op.create_index('idx_customer_created_type', 'customer', ['created_at', 'customer_type'])
    
    # Indexes for Opportunity table
    op.create_index('idx_opportunity_customer_id', 'opportunity', ['customer_id'])
    op.create_index('idx_opportunity_stage', 'opportunity', ['stage'])
    op.create_index('idx_opportunity_status', 'opportunity', ['status'])
    op.create_index('idx_opportunity_assigned_to', 'opportunity', ['assigned_to'])
    op.create_index('idx_opportunity_created_at', 'opportunity', ['created_at'])
    op.create_index('idx_opportunity_expected_close_date', 'opportunity', ['expected_close_date'])
    
    # Composite indexes for opportunity queries
    op.create_index('idx_opportunity_stage_status', 'opportunity', ['stage', 'status'])
    op.create_index('idx_opportunity_assigned_stage', 'opportunity', ['assigned_to', 'stage'])
    
    # Indexes for Activity table
    op.create_index('idx_activity_customer_id', 'activity', ['customer_id'])
    op.create_index('idx_activity_opportunity_id', 'activity', ['opportunity_id'])
    op.create_index('idx_activity_expert_user_id', 'activity', ['expert_user_id'])
    op.create_index('idx_activity_type', 'activity', ['activity_type'])
    op.create_index('idx_activity_status', 'activity', ['status'])
    op.create_index('idx_activity_created_at', 'activity', ['created_at'])
    op.create_index('idx_activity_due_date', 'activity', ['due_date'])
    
    # Composite indexes for activity queries
    op.create_index('idx_activity_expert_status', 'activity', ['expert_user_id', 'status'])
    op.create_index('idx_activity_customer_type', 'activity', ['customer_id', 'activity_type'])
    
    # Indexes for Task table
    op.create_index('idx_task_assigned_to', 'task', ['assigned_to'])
    op.create_index('idx_task_created_by', 'task', ['created_by'])
    op.create_index('idx_task_status', 'task', ['status'])
    op.create_index('idx_task_priority', 'task', ['priority'])
    op.create_index('idx_task_due_date', 'task', ['due_date'])
    op.create_index('idx_task_created_at', 'task', ['created_at'])
    
    # Composite indexes for task queries
    op.create_index('idx_task_assigned_status', 'task', ['assigned_to', 'status'])
    op.create_index('idx_task_priority_due', 'task', ['priority', 'due_date'])
    
    # Indexes for ExpertUser table
    op.create_index('idx_expert_user_username', 'expert_user', ['username'])
    op.create_index('idx_expert_user_email', 'expert_user', ['email'])
    op.create_index('idx_expert_user_role', 'expert_user', ['role'])
    op.create_index('idx_expert_user_is_active', 'expert_user', ['is_active'])
    
    # Indexes for ExpertConsoleLog table
    op.create_index('idx_expert_console_log_shipment_request_id', 'expert_console_log', ['shipment_request_id'])
    op.create_index('idx_expert_console_log_expert_user_id', 'expert_console_log', ['expert_user_id'])
    op.create_index('idx_expert_console_log_created_at', 'expert_console_log', ['created_at'])
    op.create_index('idx_expert_console_log_action', 'expert_console_log', ['action'])
    
    # Indexes for ExpertConsoleMessage table
    op.create_index('idx_expert_console_message_shipment_request_id', 'expert_console_message', ['shipment_request_id'])
    op.create_index('idx_expert_console_message_expert_user_id', 'expert_console_message', ['expert_user_id'])
    op.create_index('idx_expert_console_message_created_at', 'expert_console_message', ['created_at'])
    op.create_index('idx_expert_console_message_type', 'expert_console_message', ['message_type'])
    
    # Indexes for ExpertConsoleNotification table
    op.create_index('idx_expert_console_notification_expert_user_id', 'expert_console_notification', ['expert_user_id'])
    op.create_index('idx_expert_console_notification_is_read', 'expert_console_notification', ['is_read'])
    op.create_index('idx_expert_console_notification_created_at', 'expert_console_notification', ['created_at'])
    op.create_index('idx_expert_console_notification_type', 'expert_console_notification', ['notification_type'])


def downgrade():
    # Drop all indexes
    op.drop_index('idx_expert_console_notification_type')
    op.drop_index('idx_expert_console_notification_created_at')
    op.drop_index('idx_expert_console_notification_is_read')
    op.drop_index('idx_expert_console_notification_expert_user_id')
    
    op.drop_index('idx_expert_console_message_type')
    op.drop_index('idx_expert_console_message_created_at')
    op.drop_index('idx_expert_console_message_expert_user_id')
    op.drop_index('idx_expert_console_message_shipment_request_id')
    
    op.drop_index('idx_expert_console_log_action')
    op.drop_index('idx_expert_console_log_created_at')
    op.drop_index('idx_expert_console_log_expert_user_id')
    op.drop_index('idx_expert_console_log_shipment_request_id')
    
    op.drop_index('idx_expert_user_is_active')
    op.drop_index('idx_expert_user_role')
    op.drop_index('idx_expert_user_email')
    op.drop_index('idx_expert_user_username')
    
    op.drop_index('idx_task_priority_due')
    op.drop_index('idx_task_assigned_status')
    op.drop_index('idx_task_created_at')
    op.drop_index('idx_task_due_date')
    op.drop_index('idx_task_priority')
    op.drop_index('idx_task_status')
    op.drop_index('idx_task_created_by')
    op.drop_index('idx_task_assigned_to')
    
    op.drop_index('idx_activity_customer_type')
    op.drop_index('idx_activity_expert_status')
    op.drop_index('idx_activity_due_date')
    op.drop_index('idx_activity_created_at')
    op.drop_index('idx_activity_status')
    op.drop_index('idx_activity_type')
    op.drop_index('idx_activity_expert_user_id')
    op.drop_index('idx_activity_opportunity_id')
    op.drop_index('idx_activity_customer_id')
    
    op.drop_index('idx_opportunity_assigned_stage')
    op.drop_index('idx_opportunity_stage_status')
    op.drop_index('idx_opportunity_expected_close_date')
    op.drop_index('idx_opportunity_created_at')
    op.drop_index('idx_opportunity_assigned_to')
    op.drop_index('idx_opportunity_status')
    op.drop_index('idx_opportunity_stage')
    op.drop_index('idx_opportunity_customer_id')
    
    op.drop_index('idx_customer_created_type')
    op.drop_index('idx_customer_type_status')
    op.drop_index('idx_customer_last_contact_at')
    op.drop_index('idx_customer_created_at')
    op.drop_index('idx_customer_status')
    op.drop_index('idx_customer_customer_type')
    op.drop_index('idx_customer_phone')
    op.drop_index('idx_customer_email')
    
    op.drop_index('idx_shipment_request_assigned_status')
    op.drop_index('idx_shipment_request_status_created')
    op.drop_index('idx_shipment_request_sla_due_at')
    op.drop_index('idx_shipment_request_priority')
    op.drop_index('idx_shipment_request_assigned_to')
    op.drop_index('idx_shipment_request_created_at')
    op.drop_index('idx_shipment_request_status')
