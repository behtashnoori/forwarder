"""ADR-045 additive notification actions and attempts; preserve existing history."""
from alembic import op
import sqlalchemy as sa

revision = '20260916_fwd01_notifications'
down_revision = '20260908_governed_international_geography'
branch_labels = None
depends_on = None
BIGINT = sa.BigInteger().with_variant(sa.Integer, 'sqlite')


def upgrade():
    with op.batch_alter_table('operational_outbox') as batch:
        batch.create_unique_constraint('uq_operational_outbox_tenant', ['id', 'organization_id'])
    op.create_index('uq_outbox_quote_available', 'operational_outbox', ['organization_id', 'aggregate_id'],
        unique=True, postgresql_where=sa.text("event_type = 'commercial.quote.available.v1'"),
        sqlite_where=sa.text("event_type = 'commercial.quote.available.v1'"))
    op.create_table('notification_action',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organization_id', BIGINT, sa.ForeignKey('operational_organization.id'), nullable=False),
        sa.Column('request_id', BIGINT, nullable=False),
        sa.Column('event_id', BIGINT, nullable=False),
        sa.Column('actor_id', BIGINT, sa.ForeignKey('expert_user.id'), nullable=False),
        sa.Column('policy', sa.String(80), nullable=False),
        sa.Column('channel', sa.String(20), nullable=False),
        sa.Column('intent_digest', sa.String(64), nullable=False),
        sa.Column('state', sa.String(20), nullable=False),
        sa.Column('reason', sa.String(80), nullable=False),
        sa.Column('approval', sa.String(32), nullable=False),
        sa.Column('attempt_count', sa.Integer, nullable=False),
        sa.Column('active_attempt_id', sa.String(36)),
        sa.Column('next_attempt_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('id', 'organization_id', name='uq_notification_action_tenant'),
        sa.UniqueConstraint('event_id', 'policy', 'channel', name='uq_notification_event_policy'),
        sa.ForeignKeyConstraint(['request_id', 'organization_id'],
            ['shipment_request.id', 'shipment_request.operational_organization_id'], name='fk_notification_request_tenant', ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['event_id', 'organization_id'],
            ['operational_outbox.id', 'operational_outbox.organization_id'], name='fk_notification_event_tenant', ondelete='RESTRICT'),
        sa.CheckConstraint("state IN ('BLOCKED','PREPARED','IN_FLIGHT','ACCEPTED','SENT','DELIVERED','FAILED','UNKNOWN')", name='ck_notification_state'),
    )
    op.create_index('ix_notification_pending', 'notification_action', ['state', 'next_attempt_at'])
    op.create_table('notification_attempt',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organization_id', BIGINT, sa.ForeignKey('operational_organization.id'), nullable=False),
        sa.Column('action_id', sa.String(36), nullable=False),
        sa.Column('number', sa.Integer, nullable=False),
        sa.Column('provider', sa.String(40), nullable=False),
        sa.Column('provider_reference', sa.String(80), nullable=False),
        sa.Column('simulated', sa.Boolean, nullable=False),
        sa.Column('outcome', sa.String(20), nullable=False),
        sa.Column('reason', sa.String(80), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('lease_until', sa.DateTime(timezone=True), nullable=False),
        sa.Column('finished_at', sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(['action_id', 'organization_id'], ['notification_action.id', 'notification_action.organization_id'], name='fk_notification_attempt_tenant', ondelete='RESTRICT'),
        sa.UniqueConstraint('action_id', 'number', name='uq_notification_attempt_number'),
        sa.CheckConstraint("outcome IN ('IN_FLIGHT','ACCEPTED','SENT','DELIVERED','FAILED','UNKNOWN')", name='ck_notification_attempt_outcome'),
    )


def downgrade():
    # Retain evidence on populated installations; application rollback is enough.
    connection = op.get_bind()
    if connection.execute(sa.text('SELECT count(*) FROM notification_action')).scalar():
        raise RuntimeError('Notification history exists; retain schema and roll forward')
    op.drop_table('notification_attempt')
    op.drop_index('ix_notification_pending', table_name='notification_action')
    op.drop_table('notification_action')
    op.drop_index('uq_outbox_quote_available', table_name='operational_outbox')
    with op.batch_alter_table('operational_outbox') as batch:
        batch.drop_constraint('uq_operational_outbox_tenant', type_='unique')
