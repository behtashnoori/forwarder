"""ADR-047 additive governed quote grants/history; explicit execution only."""
from alembic import op
import sqlalchemy as sa
revision = '20260916_fwd05_quote_response'
down_revision = '20260916_fwd03_transport_intent'
branch_labels = None
depends_on = None
BIGINT = sa.BigInteger().with_variant(sa.Integer, 'sqlite')

def upgrade():
    op.add_column('shipment_request', sa.Column('quote_recipient_generation', BIGINT, nullable=False, server_default='0'))
    op.add_column('customer', sa.Column('quote_recipient_generation', BIGINT, nullable=False, server_default='0'))
    op.add_column('customer_gamification', sa.Column('quote_recipient_generation', BIGINT, nullable=False, server_default='0'))
    op.add_column('operational_organization', sa.Column('quotation_validity_timezone', sa.String(64), nullable=True))
    with op.batch_alter_table('expert_quote') as batch:
        batch.alter_column('amount', existing_type=BIGINT, nullable=True)
        batch.alter_column('customer_response', existing_type=sa.String(10), type_=sa.String(24), existing_nullable=True)
        batch.drop_constraint('ck_expert_quote_customer_response', type_='check')
        batch.add_column(sa.Column('amount_exact', sa.Numeric(precision=21, scale=2), nullable=True))
        batch.add_column(sa.Column('money_contract', sa.String(length=24), nullable=True))
        batch.add_column(sa.Column('public_id', sa.String(length=36), nullable=True))
        batch.add_column(sa.Column('content_revision', sa.Integer(), nullable=True))
        batch.add_column(sa.Column('content_digest', sa.String(length=64), nullable=True))
        batch.add_column(sa.Column('published_at', sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column('validity_timezone', sa.String(length=64), nullable=True))
        batch.add_column(sa.Column('validity_policy', sa.String(length=32), nullable=True))
        batch.add_column(sa.Column('predecessor_id', BIGINT, nullable=True))
        batch.add_column(sa.Column('superseded_by_id', BIGINT, nullable=True))
        batch.add_column(sa.Column('response_version', sa.Integer(), nullable=True))
        batch.add_column(sa.Column('response_received_at', sa.DateTime(timezone=True), nullable=True))
        batch.create_unique_constraint('uq_expert_quote_tenant', ['id', 'operational_organization_id'])
        batch.create_unique_constraint('uq_quote_public_id', ['public_id'])
        batch.create_unique_constraint('uq_quote_predecessor', ['predecessor_id'])
        batch.create_unique_constraint('uq_quote_successor', ['superseded_by_id'])
        batch.create_check_constraint('ck_expert_quote_customer_response', "customer_response IS NULL OR customer_response IN ('accepted', 'negotiation_requested', 'declined')")
        batch.create_check_constraint('ck_quote_exact_money', "(money_contract IS NULL AND amount IS NOT NULL) OR (money_contract = 'quote-major.v1' AND amount_exact IS NOT NULL AND amount_exact >= 0 AND amount_exact <= 9223372036854775807 AND currency IN ('IRR','USD','EUR') AND (currency <> 'IRR' OR amount_exact = floor(amount_exact)))")
        batch.create_check_constraint('ck_quote_governed_version', 'content_revision IS NULL OR (content_revision = 1 AND response_version >= 0)')
        batch.create_foreign_key('fk_quote_predecessor_tenant', 'expert_quote', ['predecessor_id', 'operational_organization_id'], ['id', 'operational_organization_id'], ondelete='RESTRICT')
        batch.create_foreign_key('fk_quote_root_tenant', 'shipment_request', ['shipment_request_id', 'operational_organization_id'], ['id', 'operational_organization_id'], ondelete='RESTRICT')
        batch.create_foreign_key('fk_quote_successor_tenant', 'expert_quote', ['superseded_by_id', 'operational_organization_id'], ['id', 'operational_organization_id'], ondelete='RESTRICT')
    op.create_table('quote_key_policy',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('epoch', sa.Integer(), nullable=False),
        sa.Column('active_key', sa.String(length=32), nullable=False),
        sa.Column('states', sa.JSON(), nullable=False),
        sa.Column('changed_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('id = 1 AND epoch > 0', name='ck_quote_key_policy_singleton'))
    op.create_table('quote_key_policy_audit',
        sa.Column('id', sa.String(length=36), primary_key=True, nullable=False),
        sa.Column('epoch', sa.Integer(), nullable=False),
        sa.Column('active_key', sa.String(length=32), nullable=False),
        sa.Column('states', sa.JSON(), nullable=False),
        sa.Column('reason', sa.String(length=32), nullable=False),
        sa.Column('provenance', sa.String(length=32), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('epoch', name=None))
    op.create_table('quote_response_grant',
        sa.Column('id', sa.String(length=36), primary_key=True, nullable=False),
        sa.Column('organization_id', BIGINT, sa.ForeignKey('operational_organization.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('request_id', BIGINT, nullable=False),
        sa.Column('quote_id', BIGINT, nullable=False),
        sa.Column('customer_id', BIGINT, nullable=False),
        sa.Column('verified_customer_id', BIGINT, sa.ForeignKey('customer_gamification.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('subject', sa.String(length=36), nullable=False),
        sa.Column('claims', sa.JSON(), nullable=False),
        sa.Column('key_version', sa.String(length=32), nullable=False),
        sa.Column('token_digest', sa.String(length=64), nullable=False),
        sa.Column('recipient_hash', sa.String(length=64), nullable=False),
        sa.Column('root_generation', BIGINT, nullable=False),
        sa.Column('customer_generation', BIGINT, nullable=False),
        sa.Column('verified_generation', BIGINT, nullable=False),
        sa.Column('issued_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('read_expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('write_expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_reason', sa.String(length=32), nullable=True),
        sa.CheckConstraint('root_generation >= 0 AND customer_generation >= 0 AND verified_generation >= 0', name='ck_quote_grant_generations'),
        sa.CheckConstraint('read_expires_at > issued_at AND write_expires_at < read_expires_at', name='ck_quote_grant_horizon'),
        sa.ForeignKeyConstraint(['customer_id', 'organization_id'], ['customer.id', 'customer.operational_organization_id'], name='fk_quote_grant_customer_tenant', ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['quote_id', 'organization_id'], ['expert_quote.id', 'expert_quote.operational_organization_id'], name='fk_quote_grant_quote_tenant', ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['request_id', 'organization_id'], ['shipment_request.id', 'shipment_request.operational_organization_id'], name='fk_quote_grant_root_tenant', ondelete='RESTRICT'),
        sa.UniqueConstraint('id', 'organization_id', name='uq_quote_grant_tenant'))
    op.create_index('ix_quote_grant_quote', 'quote_response_grant', ['quote_id'], unique=False)
    op.create_table('quote_response_fact',
        sa.Column('id', sa.String(length=36), primary_key=True, nullable=False),
        sa.Column('organization_id', BIGINT, sa.ForeignKey('operational_organization.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('request_id', BIGINT, nullable=False),
        sa.Column('quote_id', BIGINT, nullable=False),
        sa.Column('grant_id', sa.String(length=36), nullable=False),
        sa.Column('subject', sa.String(length=36), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('prior_response', sa.String(length=24), nullable=True),
        sa.Column('response', sa.String(length=24), nullable=False),
        sa.Column('reason', sa.String(length=32), nullable=False),
        sa.Column('snapshot', sa.JSON(), nullable=False),
        sa.Column('response_received_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("sequence > 0 AND response IN ('accepted','negotiation_requested','declined')", name='ck_quote_fact_response'),
        sa.ForeignKeyConstraint(['grant_id', 'organization_id'], ['quote_response_grant.id', 'quote_response_grant.organization_id'], name='fk_quote_fact_grant_tenant', ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['quote_id', 'organization_id'], ['expert_quote.id', 'expert_quote.operational_organization_id'], name='fk_quote_fact_quote_tenant', ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['request_id', 'organization_id'], ['shipment_request.id', 'shipment_request.operational_organization_id'], name='fk_quote_fact_root_tenant', ondelete='RESTRICT'),
        sa.UniqueConstraint('quote_id', 'sequence', name='uq_quote_fact_sequence'),
        sa.UniqueConstraint('id', 'organization_id', name='uq_quote_fact_tenant'))
    op.create_table('quote_response_receipt',
        sa.Column('id', sa.String(length=36), primary_key=True, nullable=False),
        sa.Column('organization_id', BIGINT, sa.ForeignKey('operational_organization.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('request_id', BIGINT, nullable=False),
        sa.Column('quote_id', BIGINT, nullable=False),
        sa.Column('grant_id', sa.String(length=36), nullable=False),
        sa.Column('fact_id', sa.String(length=36), nullable=False),
        sa.Column('idempotency_key', sa.String(length=64), nullable=False),
        sa.Column('request_digest', sa.String(length=64), nullable=False),
        sa.Column('result', sa.JSON(), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['fact_id', 'organization_id'], ['quote_response_fact.id', 'quote_response_fact.organization_id'], name='fk_quote_receipt_fact_tenant', ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['grant_id', 'organization_id'], ['quote_response_grant.id', 'quote_response_grant.organization_id'], name='fk_quote_receipt_grant_tenant', ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['quote_id', 'organization_id'], ['expert_quote.id', 'expert_quote.operational_organization_id'], name='fk_quote_receipt_quote_tenant', ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['request_id', 'organization_id'], ['shipment_request.id', 'shipment_request.operational_organization_id'], name='fk_quote_receipt_root_tenant', ondelete='RESTRICT'),
        sa.UniqueConstraint('grant_id', 'quote_id', 'idempotency_key', name='uq_quote_receipt_operation'))
    with op.batch_alter_table('expert_console_notification') as batch:
        batch.add_column(sa.Column('quote_response_fact_id', sa.String(36), nullable=True))
        batch.create_unique_constraint('uq_quote_response_attention_recipient', ['quote_response_fact_id','expert_user_id'])
        batch.create_foreign_key('fk_quote_response_attention_fact_tenant', 'quote_response_fact',
            ['quote_response_fact_id','operational_organization_id'], ['id','organization_id'], ondelete='RESTRICT')
        batch.create_check_constraint('ck_quote_response_attention_fact', "quote_response_fact_id IS NULL OR (notification_type = 'customer_quote_response' AND operational_organization_id IS NOT NULL)")
    _install_postgres_guards()


def _install_postgres_guards():
    if op.get_bind().dialect.name != 'postgresql':
        return
    op.execute("""
    CREATE FUNCTION fwd05_recipient_generation_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE changed boolean; old_data jsonb := to_jsonb(OLD); new_data jsonb := to_jsonb(NEW);
    BEGIN
      IF NEW.quote_recipient_generation IS DISTINCT FROM OLD.quote_recipient_generation THEN
        RAISE EXCEPTION 'FWD05 recipient generation is owner controlled';
      END IF;
      IF TG_TABLE_NAME = 'shipment_request' THEN
        changed := (new_data->'customer_id' IS DISTINCT FROM old_data->'customer_id')
          OR (new_data->'gamification_customer_id' IS DISTINCT FROM old_data->'gamification_customer_id');
      ELSE
        changed := lower(trim(coalesce(new_data->>'email',''))) IS DISTINCT FROM lower(trim(coalesce(old_data->>'email','')));
        IF TG_TABLE_NAME = 'customer' THEN
          changed := changed OR (new_data->'status' IS DISTINCT FROM old_data->'status');
        ELSE
          changed := changed OR (new_data->'is_email_verified' IS DISTINCT FROM old_data->'is_email_verified');
        END IF;
      END IF;
      IF changed THEN NEW.quote_recipient_generation := OLD.quote_recipient_generation + 1; END IF;
      RETURN NEW;
    END $$;
    """)
    for table in ('shipment_request', 'customer', 'customer_gamification'):
        op.execute(f'CREATE TRIGGER fwd05_recipient_generation BEFORE UPDATE ON {table} FOR EACH ROW EXECUTE FUNCTION fwd05_recipient_generation_guard()')
        op.create_check_constraint(f'ck_{table}_quote_generation', table, 'quote_recipient_generation >= 0')
    op.execute("""
    CREATE FUNCTION fwd05_append_only_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN RAISE EXCEPTION 'FWD05 history is append only'; END $$;
    CREATE FUNCTION fwd05_grant_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'FWD05 grant history retained'; END IF;
      IF (to_jsonb(NEW) - 'revoked_at' - 'revoked_reason') IS DISTINCT FROM (to_jsonb(OLD) - 'revoked_at' - 'revoked_reason')
         OR (OLD.revoked_at IS NOT NULL AND to_jsonb(NEW) IS DISTINCT FROM to_jsonb(OLD)) THEN
        RAISE EXCEPTION 'FWD05 grant immutable or terminally revoked';
      END IF;
      RETURN NEW;
    END $$;
    CREATE FUNCTION fwd05_quote_content_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF OLD.money_contract = 'quote-major.v1' THEN
        IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'FWD05 publication history retained'; END IF;
        IF (to_jsonb(NEW) - 'superseded_by_id' - 'customer_response' - 'response_version' - 'response_received_at' - 'responded_at')
          IS DISTINCT FROM (to_jsonb(OLD) - 'superseded_by_id' - 'customer_response' - 'response_version' - 'response_received_at' - 'responded_at') THEN
          RAISE EXCEPTION 'FWD05 published content immutable';
        END IF;
        IF OLD.superseded_by_id IS NOT NULL AND NEW.superseded_by_id IS DISTINCT FROM OLD.superseded_by_id THEN
          RAISE EXCEPTION 'FWD05 replacement history immutable';
        END IF;
      END IF;
      IF TG_OP = 'DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
    END $$;
    """)
    for table in ('quote_response_fact', 'quote_response_receipt', 'quote_key_policy_audit'):
        op.execute(f'CREATE TRIGGER fwd05_history_guard BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION fwd05_append_only_guard()')
    op.execute('CREATE TRIGGER fwd05_grant_history_guard BEFORE UPDATE OR DELETE ON quote_response_grant FOR EACH ROW EXECUTE FUNCTION fwd05_grant_guard()')
    op.execute('CREATE TRIGGER fwd05_content_guard BEFORE UPDATE OR DELETE ON expert_quote FOR EACH ROW EXECUTE FUNCTION fwd05_quote_content_guard()')
    op.execute("""
    CREATE FUNCTION fwd05_grant_audit_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF OLD.action LIKE 'authorization.quote-capability.%' OR (TG_OP = 'UPDATE' AND NEW.action LIKE 'authorization.quote-capability.%') THEN
        RAISE EXCEPTION 'FWD05 grant management audit append-only';
      END IF;
      IF TG_OP = 'DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
    END $$;
    CREATE TRIGGER fwd05_grant_audit_guard BEFORE UPDATE OR DELETE ON operational_audit
      FOR EACH ROW EXECUTE FUNCTION fwd05_grant_audit_guard();
    CREATE FUNCTION fwd05_attention_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF OLD.quote_response_fact_id IS NOT NULL OR (TG_OP = 'UPDATE' AND NEW.quote_response_fact_id IS NOT NULL) THEN
        IF TG_OP = 'DELETE' OR (to_jsonb(NEW) - 'is_read') IS DISTINCT FROM (to_jsonb(OLD) - 'is_read') THEN
          RAISE EXCEPTION 'FWD05 response attention envelope immutable';
        END IF;
      END IF;
      IF TG_OP = 'DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
    END $$;
    CREATE TRIGGER fwd05_attention_guard BEFORE UPDATE OR DELETE ON expert_console_notification
      FOR EACH ROW EXECUTE FUNCTION fwd05_attention_guard();
    """)


def downgrade():
    connection = op.get_bind()
    tables = ('quote_response_receipt', 'quote_response_fact', 'quote_response_grant',
              'quote_key_policy_audit', 'quote_key_policy', 'expert_quote',
              'shipment_request', 'customer', 'customer_gamification', 'operational_organization',
              'operational_audit', 'expert_console_notification')
    if connection.dialect.name == 'postgresql':
        connection.execute(sa.text('LOCK TABLE ' + ','.join(tables) + ' IN ACCESS EXCLUSIVE MODE'))
    populated = any(connection.execute(sa.text(f'SELECT count(*) FROM {table}')).scalar()
                    for table in tables[:5])
    populated = populated or connection.execute(sa.text("SELECT count(*) FROM expert_quote WHERE money_contract IS NOT NULL OR public_id IS NOT NULL OR amount IS NULL")).scalar()
    populated = populated or connection.execute(sa.text('SELECT count(*) FROM operational_organization WHERE quotation_validity_timezone IS NOT NULL')).scalar()
    populated = populated or connection.execute(sa.text("SELECT count(*) FROM operational_audit WHERE action LIKE 'authorization.quote-capability.%'")).scalar()
    for table in ('shipment_request', 'customer', 'customer_gamification'):
        populated = populated or connection.execute(sa.text(f'SELECT count(*) FROM {table} WHERE quote_recipient_generation <> 0')).scalar()
    if populated:
        raise RuntimeError('FWD05 history/policy exists; retain schema and disable writes/dispatch')
    if connection.dialect.name == 'postgresql':
        for table in ('shipment_request', 'customer', 'customer_gamification'):
            op.execute(f'DROP TRIGGER fwd05_recipient_generation ON {table}')
            op.drop_constraint(f'ck_{table}_quote_generation', table, type_='check')
        op.execute('DROP TRIGGER fwd05_content_guard ON expert_quote')
        op.execute('DROP TRIGGER fwd05_grant_audit_guard ON operational_audit')
        op.execute('DROP TRIGGER fwd05_attention_guard ON expert_console_notification')
    with op.batch_alter_table('expert_console_notification') as batch:
        batch.drop_constraint('fk_quote_response_attention_fact_tenant', type_='foreignkey')
        batch.drop_constraint('uq_quote_response_attention_recipient', type_='unique')
        batch.drop_constraint('ck_quote_response_attention_fact', type_='check')
        batch.drop_column('quote_response_fact_id')
    for table in tables[:5]:
        op.drop_table(table)
    if connection.dialect.name == 'postgresql':
        for function in ('fwd05_recipient_generation_guard', 'fwd05_append_only_guard', 'fwd05_grant_guard', 'fwd05_quote_content_guard', 'fwd05_grant_audit_guard', 'fwd05_attention_guard'):
            op.execute(f'DROP FUNCTION {function}()')
    with op.batch_alter_table('expert_quote') as batch:
        for name in ('fk_quote_predecessor_tenant', 'fk_quote_successor_tenant', 'fk_quote_root_tenant'):
            batch.drop_constraint(name, type_='foreignkey')
        for name in ('uq_quote_predecessor', 'uq_quote_successor', 'uq_quote_public_id', 'uq_expert_quote_tenant'):
            batch.drop_constraint(name, type_='unique')
        for name in ('ck_quote_exact_money', 'ck_quote_governed_version', 'ck_expert_quote_customer_response'):
            batch.drop_constraint(name, type_='check')
        for name in ('response_received_at', 'response_version', 'superseded_by_id', 'predecessor_id', 'validity_policy',
                     'validity_timezone', 'expires_at', 'published_at', 'content_digest', 'content_revision',
                     'public_id', 'money_contract', 'amount_exact'):
            batch.drop_column(name)
        batch.alter_column('amount', existing_type=BIGINT, nullable=False)
        batch.alter_column('customer_response', existing_type=sa.String(24), type_=sa.String(10), existing_nullable=True)
        batch.create_check_constraint('ck_expert_quote_customer_response', "customer_response IS NULL OR customer_response IN ('accepted','declined')")
    op.drop_column('operational_organization', 'quotation_validity_timezone')
    for table in ('shipment_request', 'customer', 'customer_gamification'):
        op.drop_column(table, 'quote_recipient_generation')
