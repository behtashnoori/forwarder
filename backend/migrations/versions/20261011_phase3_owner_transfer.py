"""ADR-069 narrow owner transfer with immutable receipts and role separation."""
from alembic import op
import sqlalchemy as sa

revision = "20261011_phase3_owner_transfer"
down_revision = "20261010_phase3_closure"
branch_labels = None
depends_on = None

OWNER = "forwarder_owner_transfer_owner"
CALLER = "forwarder_owner_transfer_caller"
SIGNATURE = "public.transfer_shipment_owner(bigint,bigint,bigint,bigint,bigint,integer,text,text,bigint,jsonb)"

ROLE_DDL = """
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname='forwarder_owner_transfer_owner') THEN
    CREATE ROLE forwarder_owner_transfer_owner NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname='forwarder_owner_transfer_caller') THEN
    CREATE ROLE forwarder_owner_transfer_caller NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
  END IF;
  IF EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname IN
      ('forwarder_owner_transfer_owner','forwarder_owner_transfer_caller')
      AND (rolcanlogin OR rolinherit OR rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls))
    OR EXISTS (SELECT 1 FROM pg_catalog.pg_auth_members m JOIN pg_catalog.pg_roles r
      ON r.oid=m.roleid OR r.oid=m.member WHERE r.rolname='forwarder_owner_transfer_owner')
    OR EXISTS (SELECT 1 FROM pg_catalog.pg_class c JOIN pg_catalog.pg_roles r ON r.oid=c.relowner
      WHERE r.rolname='forwarder_owner_transfer_owner')
    OR EXISTS (SELECT 1 FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_roles r ON r.oid=p.proowner
      WHERE r.rolname='forwarder_owner_transfer_owner')
    OR EXISTS (SELECT 1 FROM pg_catalog.pg_namespace n JOIN pg_catalog.pg_roles r ON r.oid=n.nspowner
      WHERE r.rolname='forwarder_owner_transfer_owner')
  THEN RAISE EXCEPTION 'Dedicated owner-transfer roles are not safely isolated'; END IF;
END $$;
"""

HISTORY_GUARD = """
CREATE FUNCTION public.owner_transfer_history_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,pg_temp AS $$ BEGIN
  IF TG_OP != 'INSERT' OR current_user != 'forwarder_owner_transfer_owner' THEN
    RAISE EXCEPTION 'Owner transfer history is immutable' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END $$
"""

OWNER_GUARD = """
CREATE OR REPLACE FUNCTION public.prevent_operational_shipment_owner_change() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,pg_temp AS $$ BEGIN
  IF NEW.primary_responsible_expert_id IS DISTINCT FROM OLD.primary_responsible_expert_id THEN
    IF current_user != 'forwarder_owner_transfer_owner'
       OR NEW.organization_id IS DISTINCT FROM OLD.organization_id
       OR NEW.version != OLD.version + 1
       OR NOT EXISTS (SELECT 1 FROM public.shipment_owner_transfer h
         WHERE h.operational_shipment_id=OLD.id AND h.organization_id=OLD.organization_id
           AND h.old_owner_id=OLD.primary_responsible_expert_id
           AND h.new_owner_id=NEW.primary_responsible_expert_id
           AND h.previous_shipment_version=OLD.version AND h.next_shipment_version=NEW.version
           AND h.xmin=pg_catalog.pg_current_xact_id()::pg_catalog.xid
           AND (h.sequence_number=1 OR EXISTS (SELECT 1 FROM public.shipment_owner_transfer p
             WHERE p.id=h.previous_transfer_id AND p.operational_shipment_id=h.operational_shipment_id
               AND p.organization_id=h.organization_id AND p.sequence_number=h.sequence_number-1
               AND p.new_owner_id=h.old_owner_id AND p.next_shipment_version<=h.previous_shipment_version)))
    THEN RAISE EXCEPTION 'OperationalShipment responsible Expert is immutable' USING ERRCODE='23514'; END IF;
  END IF;
  RETURN NEW;
END $$
"""

COMMIT_GUARD = """
CREATE FUNCTION public.owner_transfer_committed() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,pg_temp AS $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM public.operational_shipment s
      JOIN public.shipment_owner_transfer h ON h.operational_shipment_id=s.id AND h.organization_id=s.organization_id
      WHERE s.id=NEW.operational_shipment_id AND s.organization_id=NEW.organization_id
        AND h.sequence_number=(SELECT max(last.sequence_number) FROM public.shipment_owner_transfer last
          WHERE last.operational_shipment_id=s.id AND last.organization_id=s.organization_id)
        AND s.primary_responsible_expert_id=h.new_owner_id AND s.version>=h.next_shipment_version)
  THEN RAISE EXCEPTION 'Owner transfer receipt requires its committed owner/version' USING ERRCODE='23514'; END IF;
  RETURN NEW;
END $$
"""

TRANSFER = """
CREATE FUNCTION public.transfer_shipment_owner(
  p_org bigint, p_shipment bigint, p_actor bigint, p_target bigint, p_expected_owner bigint,
  p_expected_version integer, p_reason text, p_key text, p_previous_transfer bigint, p_census jsonb
) RETURNS TABLE(transfer_id bigint, created boolean)
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE
  v_shipment record;
  v_replay public.shipment_owner_transfer%ROWTYPE;
  v_previous public.shipment_owner_transfer%ROWTYPE;
  v_actor_label text; v_old_label text; v_target_label text;
  v_public text; v_id bigint; v_sequence integer;
  v_occurred timestamptz; v_recorded timestamptz;
  v_metadata json;
BEGIN
  IF p_org IS NULL OR p_shipment IS NULL OR p_actor IS NULL OR p_target IS NULL OR p_expected_owner IS NULL
     OR p_expected_version IS NULL OR p_expected_version<1
     OR p_reason IS NULL OR length(btrim(p_reason))=0 OR p_reason !~ '[^[:space:]]' OR length(p_reason)>1000
     OR p_key IS NULL OR length(btrim(p_key))=0 OR length(p_key)>100
     OR p_census IS NULL OR jsonb_typeof(p_census)!='object'
     OR NOT (p_census ?& ARRAY['census_id','cache_version','cache_token'])
     OR jsonb_typeof(p_census->'census_id')!='string'
     OR jsonb_typeof(p_census->'cache_version')!='number'
     OR jsonb_typeof(p_census->'cache_token') NOT IN ('string','number')
  THEN RAISE EXCEPTION 'OWNER_TRANSFER_INVALID' USING ERRCODE='P0001'; END IF;
  p_reason:=btrim(p_reason); p_key:=btrim(p_key);

  PERFORM o.id FROM public.operational_organization o WHERE o.id=p_org FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'OWNER_TRANSFER_TENANT_INVALID' USING ERRCODE='P0001'; END IF;
  SELECT s.id,s.organization_id,s.primary_responsible_expert_id,s.version INTO v_shipment
    FROM public.operational_shipment s WHERE s.id=p_shipment AND s.organization_id=p_org FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'OWNER_TRANSFER_SHIPMENT_INVALID' USING ERRCODE='P0001'; END IF;
  PERFORM e.id FROM public.expert_user e WHERE e.id IN (p_actor,p_target) ORDER BY e.id FOR UPDATE;
  PERFORM m.id FROM public.operational_membership m WHERE m.user_id IN (p_actor,p_target) ORDER BY m.id FOR UPDATE;
  -- Expert locks fence new membership FK inserts; these locks also fence changes
  -- to organization activity used by the existing target-eligibility contract.
  PERFORM o.id FROM public.operational_organization o WHERE o.id IN
    (SELECT m.organization_id FROM public.operational_membership m WHERE m.user_id IN (p_actor,p_target))
    ORDER BY o.id FOR SHARE;

  SELECT a.full_name INTO v_actor_label FROM public.expert_user a
    WHERE a.id=p_actor AND a.is_active AND a.authority='ORGANIZATION_ADMIN'
      AND (SELECT count(*) FROM public.operational_membership m WHERE m.user_id=a.id AND m.is_active)=1
      AND EXISTS (SELECT 1 FROM public.operational_membership m JOIN public.operational_organization o ON o.id=m.organization_id
        WHERE m.user_id=a.id AND m.is_active AND m.organization_id=p_org AND o.is_active);
  IF NOT FOUND THEN RAISE EXCEPTION 'OWNER_TRANSFER_ACTOR_INVALID' USING ERRCODE='P0001'; END IF;

  SELECT h.* INTO v_replay FROM public.shipment_owner_transfer h
    WHERE h.operational_shipment_id=p_shipment AND h.idempotency_key=p_key;
  IF FOUND THEN
    IF v_replay.organization_id!=p_org OR v_replay.actor_user_id!=p_actor
       OR v_replay.old_owner_id!=p_expected_owner OR v_replay.new_owner_id!=p_target
       OR v_replay.previous_shipment_version!=p_expected_version OR v_replay.reason!=p_reason
    THEN RAISE EXCEPTION 'OWNER_TRANSFER_KEY_CONFLICT' USING ERRCODE='P0001'; END IF;
    RETURN QUERY SELECT v_replay.id,false; RETURN;
  END IF;

  SELECT t.full_name INTO v_target_label FROM public.expert_user t
    WHERE t.id=p_target AND t.is_active AND upper(coalesce(t.authority,''))='EXPERT'
      AND (SELECT count(*) FROM public.operational_membership m JOIN public.operational_organization o ON o.id=m.organization_id
        WHERE m.user_id=t.id AND m.is_active AND o.is_active)=1
      AND EXISTS (SELECT 1 FROM public.operational_membership m JOIN public.operational_organization o ON o.id=m.organization_id
        WHERE m.user_id=t.id AND m.is_active AND m.organization_id=p_org AND o.is_active);
  IF NOT FOUND THEN RAISE EXCEPTION 'OWNER_TRANSFER_TARGET_INVALID' USING ERRCODE='P0001'; END IF;
  IF p_target=p_expected_owner THEN RAISE EXCEPTION 'OWNER_TRANSFER_UNCHANGED' USING ERRCODE='P0001'; END IF;
  IF v_shipment.primary_responsible_expert_id!=p_expected_owner OR v_shipment.version!=p_expected_version
  THEN RAISE EXCEPTION 'OWNER_TRANSFER_STALE' USING ERRCODE='P0001'; END IF;
  SELECT h.* INTO v_previous FROM public.shipment_owner_transfer h
    WHERE h.operational_shipment_id=p_shipment AND h.organization_id=p_org ORDER BY h.sequence_number DESC LIMIT 1;
  IF p_previous_transfer IS DISTINCT FROM v_previous.id OR (v_previous.id IS NOT NULL AND
    (v_previous.new_owner_id!=p_expected_owner OR v_previous.next_shipment_version>p_expected_version))
  THEN RAISE EXCEPTION 'OWNER_TRANSFER_CHAIN_INVALID' USING ERRCODE='P0001'; END IF;

  SELECT e.full_name INTO v_old_label FROM public.expert_user e WHERE e.id=p_expected_owner;
  IF NOT FOUND THEN RAISE EXCEPTION 'OWNER_TRANSFER_PREDECESSOR_INVALID' USING ERRCODE='P0001'; END IF;
  v_public:=pg_catalog.gen_random_uuid()::text;
  v_sequence:=coalesce(v_previous.sequence_number,0)+1;
  v_occurred:=pg_catalog.clock_timestamp(); v_recorded:=pg_catalog.clock_timestamp();
  INSERT INTO public.shipment_owner_transfer(public_id,organization_id,operational_shipment_id,
    old_owner_id,new_owner_id,actor_user_id,old_owner_label,new_owner_label,actor_label,reason,
    occurred_at,recorded_at,sequence_number,previous_shipment_version,next_shipment_version,previous_transfer_id,idempotency_key)
  VALUES(v_public,p_org,p_shipment,p_expected_owner,p_target,p_actor,v_old_label,v_target_label,v_actor_label,p_reason,
    v_occurred,v_recorded,v_sequence,p_expected_version,p_expected_version+1,v_previous.id,p_key)
  RETURNING id INTO v_id;
  UPDATE public.operational_shipment SET primary_responsible_expert_id=p_target,
    version=p_expected_version+1,updated_at=v_recorded
    WHERE id=p_shipment AND organization_id=p_org AND primary_responsible_expert_id=p_expected_owner AND version=p_expected_version;
  IF NOT FOUND THEN RAISE EXCEPTION 'OWNER_TRANSFER_STALE' USING ERRCODE='P0001'; END IF;
  v_metadata:=pg_catalog.json_build_object('transfer_public_id',v_public,'old_owner_id',p_expected_owner,
    'new_owner_id',p_target,'previous_version',p_expected_version,'next_version',p_expected_version+1,'sequence',v_sequence);
  INSERT INTO public.operational_audit(organization_id,actor_user_id,action,entity_type,entity_id,metadata_json,recorded_at)
    VALUES(p_org,p_actor,'shipment.owner_transferred','OperationalShipment',p_shipment,v_metadata,v_recorded);
  INSERT INTO public.operational_outbox(organization_id,event_type,aggregate_type,aggregate_id,payload,created_at)
    VALUES(p_org,'shipment.owner_transferred','OperationalShipment',p_shipment,
      (v_metadata::jsonb || pg_catalog.jsonb_build_object('_ownership_census',p_census))::json,v_recorded);
  RETURN QUERY SELECT v_id,true;
END $$
"""


def upgrade():
    if op.get_bind().dialect.name != "postgresql":
        raise RuntimeError("P3-13 requires PostgreSQL; unmigrated SQLite fixtures are not a security proof")
    op.execute(ROLE_DDL)
    op.create_table("shipment_owner_transfer",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False, unique=True),
        sa.Column("organization_id", sa.BigInteger(), nullable=False),
        sa.Column("operational_shipment_id", sa.BigInteger(), nullable=False),
        *[sa.Column(name, sa.BigInteger(), sa.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False)
          for name in ("old_owner_id", "new_owner_id", "actor_user_id")],
        *[sa.Column(name, sa.String(100), nullable=False) for name in ("old_owner_label", "new_owner_label", "actor_label")],
        sa.Column("reason", sa.String(1000), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("previous_shipment_version", sa.Integer(), nullable=False),
        sa.Column("next_shipment_version", sa.Integer(), nullable=False),
        sa.Column("previous_transfer_id", sa.BigInteger(), nullable=True),
        sa.Column("idempotency_key", sa.String(100), nullable=False),
        sa.ForeignKeyConstraint(["operational_shipment_id","organization_id"], ["operational_shipment.id","operational_shipment.organization_id"], name="fk_owner_transfer_shipment", ondelete="RESTRICT"),
        sa.UniqueConstraint("id","operational_shipment_id","organization_id",name="uq_owner_transfer_parent"),
        sa.ForeignKeyConstraint(["previous_transfer_id","operational_shipment_id","organization_id"], ["shipment_owner_transfer.id","shipment_owner_transfer.operational_shipment_id","shipment_owner_transfer.organization_id"],name="fk_owner_transfer_predecessor",ondelete="RESTRICT"),
        sa.UniqueConstraint("operational_shipment_id","sequence_number",name="uq_owner_transfer_sequence"),
        sa.UniqueConstraint("operational_shipment_id","next_shipment_version",name="uq_owner_transfer_version"),
        sa.UniqueConstraint("operational_shipment_id","idempotency_key",name="uq_owner_transfer_command"),
        sa.CheckConstraint("old_owner_id != new_owner_id",name="ck_owner_transfer_changed"),
        sa.CheckConstraint("previous_shipment_version >= 1 AND next_shipment_version = previous_shipment_version + 1",name="ck_owner_transfer_version"),
        sa.CheckConstraint("sequence_number >= 1 AND ((sequence_number = 1 AND previous_transfer_id IS NULL) OR (sequence_number > 1 AND previous_transfer_id IS NOT NULL))",name="ck_owner_transfer_chain"),
        sa.CheckConstraint("length(trim(reason)) > 0 AND length(reason) <= 1000",name="ck_owner_transfer_reason"),
        sa.CheckConstraint("length(trim(idempotency_key)) > 0 AND length(idempotency_key) <= 100",name="ck_owner_transfer_key"),
    )
    op.execute(HISTORY_GUARD)
    op.execute("CREATE TRIGGER owner_transfer_history_guard BEFORE INSERT OR UPDATE OR DELETE ON public.shipment_owner_transfer FOR EACH ROW EXECUTE FUNCTION public.owner_transfer_history_guard()")
    op.execute(OWNER_GUARD)
    op.execute(COMMIT_GUARD)
    op.execute("CREATE CONSTRAINT TRIGGER owner_transfer_committed AFTER INSERT ON public.shipment_owner_transfer DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.owner_transfer_committed()")
    op.execute("GRANT USAGE ON SCHEMA public TO forwarder_owner_transfer_owner")
    op.execute("GRANT SELECT(id,is_active), UPDATE(id) ON public.operational_organization TO forwarder_owner_transfer_owner")
    op.execute("GRANT SELECT(id,organization_id,primary_responsible_expert_id,version), UPDATE(primary_responsible_expert_id,version,updated_at) ON public.operational_shipment TO forwarder_owner_transfer_owner")
    op.execute("GRANT SELECT(id,is_active,authority,full_name), UPDATE(id) ON public.expert_user TO forwarder_owner_transfer_owner")
    op.execute("GRANT SELECT(id,user_id,organization_id,is_active), UPDATE(id) ON public.operational_membership TO forwarder_owner_transfer_owner")
    op.execute("GRANT SELECT,INSERT ON public.shipment_owner_transfer TO forwarder_owner_transfer_owner")
    op.execute("GRANT INSERT(organization_id,actor_user_id,action,entity_type,entity_id,metadata_json,recorded_at) ON public.operational_audit TO forwarder_owner_transfer_owner")
    op.execute("GRANT INSERT(organization_id,event_type,aggregate_type,aggregate_id,payload,created_at) ON public.operational_outbox TO forwarder_owner_transfer_owner")
    op.execute("GRANT USAGE ON SEQUENCE public.shipment_owner_transfer_id_seq,public.operational_audit_id_seq,public.operational_outbox_id_seq TO forwarder_owner_transfer_owner")
    op.execute(TRANSFER)
    op.execute(f"ALTER FUNCTION {SIGNATURE} OWNER TO {OWNER}")
    op.execute(f"REVOKE ALL ON FUNCTION {SIGNATURE} FROM PUBLIC")
    op.execute(f"GRANT EXECUTE ON FUNCTION {SIGNATURE} TO {CALLER}")
    for function in ("owner_transfer_history_guard", "owner_transfer_committed"):
        op.execute(f"REVOKE ALL ON FUNCTION public.{function}() FROM PUBLIC")
    if op.get_bind().execute(sa.text("SELECT has_schema_privilege('forwarder_owner_transfer_owner','public','CREATE')")).scalar():
        raise RuntimeError("Function owner must not have schema CREATE; unsafe role/schema configuration")


def downgrade():
    if op.get_bind().execute(sa.text("SELECT count(*) FROM public.shipment_owner_transfer")).scalar():
        raise RuntimeError("Owner transfer history exists; destructive downgrade is unsupported; retain history and roll forward")
    op.execute(f"DROP FUNCTION {SIGNATURE}")
    op.execute("""CREATE OR REPLACE FUNCTION public.prevent_operational_shipment_owner_change() RETURNS trigger
      LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,pg_temp AS $$ BEGIN
      IF NEW.primary_responsible_expert_id IS DISTINCT FROM OLD.primary_responsible_expert_id THEN
        RAISE EXCEPTION 'OperationalShipment responsible Expert is immutable' USING ERRCODE='23514';
      END IF; RETURN NEW; END $$""")
    op.execute("DROP TRIGGER owner_transfer_committed ON public.shipment_owner_transfer")
    op.execute("DROP FUNCTION public.owner_transfer_committed()")
    op.execute("DROP TRIGGER owner_transfer_history_guard ON public.shipment_owner_transfer")
    op.execute("DROP FUNCTION public.owner_transfer_history_guard()")
    op.execute("REVOKE SELECT(id,is_active), UPDATE(id) ON public.operational_organization FROM forwarder_owner_transfer_owner")
    op.execute("REVOKE SELECT(id,organization_id,primary_responsible_expert_id,version), UPDATE(primary_responsible_expert_id,version,updated_at) ON public.operational_shipment FROM forwarder_owner_transfer_owner")
    op.execute("REVOKE SELECT(id,is_active,authority,full_name), UPDATE(id) ON public.expert_user FROM forwarder_owner_transfer_owner")
    op.execute("REVOKE SELECT(id,user_id,organization_id,is_active), UPDATE(id) ON public.operational_membership FROM forwarder_owner_transfer_owner")
    op.execute("REVOKE INSERT(organization_id,actor_user_id,action,entity_type,entity_id,metadata_json,recorded_at) ON public.operational_audit FROM forwarder_owner_transfer_owner")
    op.execute("REVOKE INSERT(organization_id,event_type,aggregate_type,aggregate_id,payload,created_at) ON public.operational_outbox FROM forwarder_owner_transfer_owner")
    op.execute("REVOKE USAGE ON SEQUENCE public.operational_audit_id_seq,public.operational_outbox_id_seq FROM forwarder_owner_transfer_owner")
    op.execute("REVOKE USAGE ON SCHEMA public FROM forwarder_owner_transfer_owner")
    op.drop_table("shipment_owner_transfer")
    # Cluster roles may serve other databases. All privileges introduced in this
    # database are removed; do not delete shared roles or other database grants.
