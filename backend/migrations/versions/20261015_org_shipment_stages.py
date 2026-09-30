"""Organization Shipment stages and exact closure/final-delivery facts."""
from alembic import op
import sqlalchemy as sa


revision = "20261015_org_shipment_stages"
down_revision = "20261014_canonical_geography_locations"
branch_labels = None
depends_on = None


DDL = [
    """CREATE TABLE organization_shipment_stage_policy (
    id BIGSERIAL PRIMARY KEY,
    public_id VARCHAR(36) NOT NULL UNIQUE,
    organization_id BIGINT NOT NULL UNIQUE REFERENCES operational_organization(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_org_shipment_stage_policy_org UNIQUE(id, organization_id)
)""",
    """CREATE TABLE organization_shipment_stage_policy_version (
    id BIGSERIAL PRIMARY KEY,
    public_id VARCHAR(36) NOT NULL UNIQUE,
    organization_id BIGINT NOT NULL,
    policy_id BIGINT NOT NULL,
    version INTEGER NOT NULL,
    effective_from TIMESTAMPTZ NOT NULL,
    actor_user_id BIGINT NOT NULL REFERENCES expert_user(id) ON DELETE RESTRICT,
    recorded_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_org_shipment_stage_version_org UNIQUE(id, organization_id),
    CONSTRAINT uq_org_shipment_stage_version_number UNIQUE(policy_id, version),
    CONSTRAINT uq_org_shipment_stage_version_effective UNIQUE(policy_id, effective_from),
    CONSTRAINT fk_org_shipment_stage_version_policy FOREIGN KEY(policy_id, organization_id)
      REFERENCES organization_shipment_stage_policy(id, organization_id) ON DELETE RESTRICT,
    CONSTRAINT ck_org_shipment_stage_version_positive CHECK(version >= 1)
)""",
    """CREATE TABLE organization_shipment_stage_definition (
    id BIGSERIAL PRIMARY KEY,
    public_id VARCHAR(36) NOT NULL UNIQUE,
    organization_id BIGINT NOT NULL REFERENCES operational_organization(id) ON DELETE RESTRICT,
    code VARCHAR(40) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_org_shipment_stage_definition_org UNIQUE(id, organization_id),
    CONSTRAINT uq_org_shipment_stage_definition_code UNIQUE(organization_id, code),
    CONSTRAINT ck_org_shipment_stage_definition_code CHECK(code IN
      ('PREPARATION_LOADING','ORIGIN_DEPARTURE','IN_TRANSIT','DESTINATION_ARRIVAL','UNLOADING'))
)""",
    """CREATE TABLE organization_shipment_stage_definition_version (
    id BIGSERIAL PRIMARY KEY,
    public_id VARCHAR(36) NOT NULL UNIQUE,
    organization_id BIGINT NOT NULL,
    policy_version_id BIGINT NOT NULL,
    definition_id BIGINT NOT NULL,
    display_name_fa VARCHAR(160) NOT NULL,
    sequence INTEGER NOT NULL,
    is_active BOOLEAN NOT NULL,
    required_for_completion BOOLEAN NOT NULL,
    CONSTRAINT uq_org_shipment_stage_item_version_org UNIQUE(id, policy_version_id, organization_id),
    CONSTRAINT uq_org_shipment_stage_item_definition UNIQUE(policy_version_id, definition_id),
    CONSTRAINT uq_org_shipment_stage_item_sequence UNIQUE(policy_version_id, sequence),
    CONSTRAINT fk_org_shipment_stage_item_version FOREIGN KEY(policy_version_id, organization_id)
      REFERENCES organization_shipment_stage_policy_version(id, organization_id) ON DELETE RESTRICT,
    CONSTRAINT fk_org_shipment_stage_item_definition FOREIGN KEY(definition_id, organization_id)
      REFERENCES organization_shipment_stage_definition(id, organization_id) ON DELETE RESTRICT,
    CONSTRAINT ck_org_shipment_stage_item_sequence CHECK(sequence >= 1),
    CONSTRAINT ck_org_shipment_stage_item_name CHECK(length(trim(display_name_fa)) > 0),
    CONSTRAINT ck_org_shipment_stage_required_active CHECK(NOT required_for_completion OR is_active)
)""",
    """CREATE TABLE shipment_operational_stage_instance (
    id BIGSERIAL PRIMARY KEY,
    public_id VARCHAR(36) NOT NULL UNIQUE,
    organization_id BIGINT NOT NULL,
    operational_shipment_id BIGINT NOT NULL UNIQUE,
    policy_version_id BIGINT NOT NULL,
    pinned_by_user_id BIGINT NOT NULL REFERENCES expert_user(id) ON DELETE RESTRICT,
    pinned_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_shipment_stage_instance_version_org UNIQUE(id, policy_version_id, operational_shipment_id, organization_id),
    CONSTRAINT fk_shipment_stage_instance_shipment FOREIGN KEY(operational_shipment_id, organization_id)
      REFERENCES operational_shipment(id, organization_id) ON DELETE RESTRICT,
    CONSTRAINT fk_shipment_stage_instance_policy_version FOREIGN KEY(policy_version_id, organization_id)
      REFERENCES organization_shipment_stage_policy_version(id, organization_id) ON DELETE RESTRICT
)""",
    """CREATE TABLE shipment_operational_stage_event (
    id BIGSERIAL PRIMARY KEY,
    public_id VARCHAR(36) NOT NULL UNIQUE,
    organization_id BIGINT NOT NULL,
    operational_shipment_id BIGINT NOT NULL,
    instance_id BIGINT NOT NULL,
    policy_version_id BIGINT NOT NULL,
    definition_version_id BIGINT NOT NULL,
    event_type VARCHAR(12) NOT NULL,
    actor_user_id BIGINT NOT NULL REFERENCES expert_user(id) ON DELETE RESTRICT,
    occurred_at TIMESTAMPTZ NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL,
    idempotency_key VARCHAR(100) NOT NULL,
    request_hash VARCHAR(64) NOT NULL,
    CONSTRAINT fk_shipment_stage_event_instance FOREIGN KEY(instance_id, policy_version_id, operational_shipment_id, organization_id)
      REFERENCES shipment_operational_stage_instance(id, policy_version_id, operational_shipment_id, organization_id) ON DELETE RESTRICT,
    CONSTRAINT fk_shipment_stage_event_definition_version FOREIGN KEY(definition_version_id, policy_version_id, organization_id)
      REFERENCES organization_shipment_stage_definition_version(id, policy_version_id, organization_id) ON DELETE RESTRICT,
    CONSTRAINT uq_shipment_stage_event_org_idempotency UNIQUE(organization_id, idempotency_key),
    CONSTRAINT uq_shipment_stage_event_transition UNIQUE(instance_id, definition_version_id, event_type),
    CONSTRAINT ck_shipment_stage_event_type CHECK(event_type IN ('STARTED','COMPLETED'))
)""",
    "CREATE INDEX ix_shipment_stage_event_history ON shipment_operational_stage_event(operational_shipment_id, occurred_at, id)",
]


NEW_CODES = (
    "FINAL_DELIVERY_EXISTS", "REQUIRED_OPERATIONAL_STAGES_COMPLETE", "NO_BLOCKING_OPERATIONAL_ISSUE",
    "ACTUAL_CARGO_UNKNOWN", "ACTUAL_ALLOCATION_DIFFERS_FROM_PLANNED", "DELIVERED_DIFFERS_FROM_PLANNED",
    "OPTIONAL_DOCUMENTS_ABSENT", "ETA_UNAVAILABLE", "NON_BLOCKING_OPERATIONAL_WARNINGS",
)


def upgrade():
    if op.get_bind().dialect.name != "postgresql":
        raise RuntimeError("Organization Shipment Stage migration requires PostgreSQL 18")
    op.add_column("cargo_delivery", sa.Column("is_final", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.drop_constraint("ck_closure_criterion_code", "closure_policy_criterion", type_="check")
    op.create_check_constraint(
        "ck_closure_criterion_code", "closure_policy_criterion",
        "code IN ('ACTUAL_QUANTITY_KNOWN','ALL_CARGO_DELIVERED','REQUIRED_DOCUMENTS_READY','NO_OPEN_EXCEPTIONS','NO_OPEN_FOLLOW_UPS','NO_OPEN_OPERATIONAL_WORK','FINAL_DELIVERY_EXISTS','REQUIRED_OPERATIONAL_STAGES_COMPLETE','NO_BLOCKING_OPERATIONAL_ISSUE','ACTUAL_CARGO_UNKNOWN','ACTUAL_ALLOCATION_DIFFERS_FROM_PLANNED','DELIVERED_DIFFERS_FROM_PLANNED','OPTIONAL_DOCUMENTS_ABSENT','ETA_UNAVAILABLE','NON_BLOCKING_OPERATIONAL_WARNINGS')",
    )
    op.create_check_constraint(
        "ck_closure_v1_blocker", "closure_policy_criterion",
        "code NOT IN ('FINAL_DELIVERY_EXISTS','REQUIRED_OPERATIONAL_STAGES_COMPLETE','NO_BLOCKING_OPERATIONAL_ISSUE','REQUIRED_DOCUMENTS_READY') OR mandatory",
    )
    op.create_check_constraint(
        "ck_closure_v1_warning", "closure_policy_criterion",
        "code NOT IN ('ACTUAL_CARGO_UNKNOWN','ACTUAL_ALLOCATION_DIFFERS_FROM_PLANNED','DELIVERED_DIFFERS_FROM_PLANNED','OPTIONAL_DOCUMENTS_ABSENT','ETA_UNAVAILABLE','NON_BLOCKING_OPERATIONAL_WARNINGS') OR NOT mandatory",
    )
    for statement in DDL:
        op.execute(statement)

    op.execute("""CREATE FUNCTION public.shipment_stage_history_immutable() RETURNS trigger
        LANGUAGE plpgsql SET search_path = pg_catalog AS $$ BEGIN
        RAISE EXCEPTION 'Organization Shipment Stage history is immutable' USING ERRCODE = '23514'; END $$""")
    for table in (
        "organization_shipment_stage_policy", "organization_shipment_stage_policy_version",
        "organization_shipment_stage_definition", "organization_shipment_stage_definition_version",
        "shipment_operational_stage_instance", "shipment_operational_stage_event",
    ):
        op.execute(f"CREATE TRIGGER shipment_stage_immutable BEFORE UPDATE OR DELETE ON public.{table} FOR EACH ROW EXECUTE FUNCTION public.shipment_stage_history_immutable()")

    op.execute("""CREATE FUNCTION public.shipment_stage_version_insert() RETURNS trigger
        LANGUAGE plpgsql SET search_path = pg_catalog AS $$
        DECLARE last_version integer; last_effective timestamptz;
        BEGIN
          PERFORM id FROM public.operational_organization WHERE id = NEW.organization_id FOR UPDATE;
          SELECT version, effective_from INTO last_version, last_effective
            FROM public.organization_shipment_stage_policy_version
            WHERE policy_id = NEW.policy_id ORDER BY version DESC LIMIT 1;
          IF NEW.version != coalesce(last_version, 0) + 1 OR
             (last_version IS NOT NULL AND (NEW.effective_from <= last_effective OR NEW.effective_from < clock_timestamp())) THEN
            RAISE EXCEPTION 'Invalid Organization Shipment Stage version' USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END $$""")
    op.execute("CREATE TRIGGER shipment_stage_version_insert BEFORE INSERT ON public.organization_shipment_stage_policy_version FOR EACH ROW EXECUTE FUNCTION public.shipment_stage_version_insert()")

    op.execute("""CREATE FUNCTION public.shipment_stage_item_insert() RETURNS trigger
        LANGUAGE plpgsql SET search_path = pg_catalog AS $$ BEGIN
          IF NOT EXISTS (SELECT 1 FROM public.organization_shipment_stage_policy_version v
              WHERE v.id = NEW.policy_version_id AND v.organization_id = NEW.organization_id
              AND v.xmin = pg_current_xact_id()::xid) THEN
            RAISE EXCEPTION 'Organization Shipment Stage version is sealed' USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END $$""")
    op.execute("CREATE TRIGGER shipment_stage_item_insert BEFORE INSERT ON public.organization_shipment_stage_definition_version FOR EACH ROW EXECUTE FUNCTION public.shipment_stage_item_insert()")
    op.execute("""CREATE FUNCTION public.shipment_stage_version_committed() RETURNS trigger
        LANGUAGE plpgsql SET search_path = pg_catalog AS $$ BEGIN
          IF (SELECT count(*) FROM public.organization_shipment_stage_definition_version d
              WHERE d.policy_version_id = NEW.id) != 5 THEN
            RAISE EXCEPTION 'Organization Shipment Stage version needs all five canonical definitions' USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END $$""")
    op.execute("CREATE CONSTRAINT TRIGGER shipment_stage_version_committed AFTER INSERT ON public.organization_shipment_stage_policy_version DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.shipment_stage_version_committed()")

    op.execute("""CREATE FUNCTION public.shipment_stage_instance_insert() RETURNS trigger
        LANGUAGE plpgsql SET search_path = pg_catalog AS $$
        DECLARE s public.operational_shipment%ROWTYPE;
        BEGIN
          SELECT * INTO s FROM public.operational_shipment WHERE id = NEW.operational_shipment_id FOR UPDATE;
          IF s.organization_id != NEW.organization_id OR s.lifecycle_status = 'closed' THEN
            RAISE EXCEPTION 'Shipment cannot pin this stage configuration' USING ERRCODE = '23514';
          END IF;
          IF NOT EXISTS (SELECT 1 FROM public.organization_shipment_stage_policy_version v
              WHERE v.id = NEW.policy_version_id AND v.organization_id = NEW.organization_id
              AND v.effective_from <= NEW.pinned_at
              AND NOT EXISTS (SELECT 1 FROM public.organization_shipment_stage_policy_version later
                WHERE later.policy_id = v.policy_id AND later.version > v.version AND later.effective_from <= NEW.pinned_at)) THEN
            RAISE EXCEPTION 'Stage configuration is not applicable' USING ERRCODE = '23514';
          END IF;
          IF NOT EXISTS (SELECT 1 FROM public.expert_user u JOIN public.operational_membership m ON m.user_id = u.id
              JOIN public.operational_organization o ON o.id = m.organization_id AND o.is_active
              WHERE u.id = NEW.pinned_by_user_id AND u.is_active AND u.authority = 'EXPERT'
              AND m.is_active AND m.organization_id = s.organization_id
              AND u.id = s.primary_responsible_expert_id
              AND (SELECT count(*) FROM public.operational_membership x WHERE x.user_id = u.id AND x.is_active) = 1) THEN
            RAISE EXCEPTION 'Stage instance actor is not eligible' USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END $$""")
    op.execute("CREATE TRIGGER shipment_stage_instance_insert BEFORE INSERT ON public.shipment_operational_stage_instance FOR EACH ROW EXECUTE FUNCTION public.shipment_stage_instance_insert()")

    op.execute("""CREATE FUNCTION public.shipment_stage_event_insert() RETURNS trigger
        LANGUAGE plpgsql SET search_path = pg_catalog AS $$
        DECLARE current_sequence integer; started_at timestamptz; shipment_created_at timestamptz; shipment_status text; previous_completed_at timestamptz;
        BEGIN
          SELECT s.created_at, s.lifecycle_status INTO shipment_created_at, shipment_status FROM public.operational_shipment s
            WHERE s.id = NEW.operational_shipment_id FOR UPDATE;
          IF shipment_status = 'closed' THEN
            RAISE EXCEPTION 'Closed Shipment cannot accept stage progress' USING ERRCODE = '23514';
          END IF;
          IF NEW.occurred_at > clock_timestamp() OR NEW.occurred_at < shipment_created_at THEN
            RAISE EXCEPTION 'Stage event occurrence is outside the Shipment timeline' USING ERRCODE = '23514';
          END IF;
          SELECT d.sequence INTO current_sequence FROM public.organization_shipment_stage_definition_version d
            WHERE d.id = NEW.definition_version_id AND d.policy_version_id = NEW.policy_version_id
              AND d.organization_id = NEW.organization_id AND d.is_active;
          IF current_sequence IS NULL THEN
            RAISE EXCEPTION 'Stage definition is not active in the pinned version' USING ERRCODE = '23514';
          END IF;
          IF NOT EXISTS (SELECT 1 FROM public.expert_user u JOIN public.operational_membership m ON m.user_id = u.id
              JOIN public.operational_shipment s ON s.id = NEW.operational_shipment_id
              WHERE u.id = NEW.actor_user_id AND u.is_active AND u.authority = 'EXPERT'
              AND m.user_id = u.id AND m.organization_id = NEW.organization_id AND m.is_active
              AND u.id = s.primary_responsible_expert_id
              AND (SELECT count(*) FROM public.operational_membership x WHERE x.user_id = u.id AND x.is_active) = 1) THEN
            RAISE EXCEPTION 'Stage event actor is not eligible' USING ERRCODE = '23514';
          END IF;
          IF EXISTS (SELECT 1 FROM public.organization_shipment_stage_definition_version prior
              WHERE prior.policy_version_id = NEW.policy_version_id AND prior.is_active AND prior.sequence < current_sequence
              AND NOT EXISTS (SELECT 1 FROM public.shipment_operational_stage_event e
                WHERE e.instance_id = NEW.instance_id AND e.definition_version_id = prior.id AND e.event_type = 'COMPLETED')) THEN
            RAISE EXCEPTION 'Previous stages are incomplete' USING ERRCODE = '23514';
          END IF;
          SELECT max(e.occurred_at) INTO previous_completed_at
            FROM public.organization_shipment_stage_definition_version prior
            JOIN public.shipment_operational_stage_event e
              ON e.definition_version_id = prior.id AND e.instance_id = NEW.instance_id AND e.event_type = 'COMPLETED'
            WHERE prior.policy_version_id = NEW.policy_version_id AND prior.is_active AND prior.sequence < current_sequence;
          IF previous_completed_at IS NOT NULL AND NEW.occurred_at < previous_completed_at THEN
            RAISE EXCEPTION 'Stage event precedes the previous stage completion' USING ERRCODE = '23514';
          END IF;
          SELECT e.occurred_at INTO started_at FROM public.shipment_operational_stage_event e
            WHERE e.instance_id = NEW.instance_id AND e.definition_version_id = NEW.definition_version_id AND e.event_type = 'STARTED';
          IF (NEW.event_type = 'STARTED' AND started_at IS NOT NULL) OR
             (NEW.event_type = 'COMPLETED' AND (started_at IS NULL OR NEW.occurred_at < started_at)) THEN
            RAISE EXCEPTION 'Invalid stage transition' USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END $$""")
    op.execute("CREATE TRIGGER shipment_stage_event_insert BEFORE INSERT ON public.shipment_operational_stage_event FOR EACH ROW EXECUTE FUNCTION public.shipment_stage_event_insert()")

    op.execute("""CREATE FUNCTION public.delivery_finality_insert() RETURNS trigger
        LANGUAGE plpgsql SET search_path = pg_catalog AS $$ BEGIN
          IF NEW.is_final AND EXISTS (SELECT 1 FROM public.cargo_delivery d
              WHERE d.operational_shipment_id = NEW.operational_shipment_id AND d.organization_id = NEW.organization_id
              AND d.is_final AND d.id IS DISTINCT FROM NEW.supersedes_delivery_id
              AND NOT EXISTS (SELECT 1 FROM public.cargo_delivery successor WHERE successor.supersedes_delivery_id = d.id)) THEN
            RAISE EXCEPTION 'Shipment already has a current final Delivery' USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END $$""")
    op.execute("CREATE TRIGGER delivery_finality_insert BEFORE INSERT ON public.cargo_delivery FOR EACH ROW EXECUTE FUNCTION public.delivery_finality_insert()")

    op.execute("""CREATE FUNCTION public.closure_fence_shipment_operational_stage_event() RETURNS trigger
        LANGUAGE plpgsql SET search_path = pg_catalog AS $$ BEGIN
          PERFORM id FROM public.operational_shipment WHERE id = coalesce(NEW.operational_shipment_id, OLD.operational_shipment_id) FOR UPDATE;
          IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
          RETURN NEW;
        END $$""")
    op.execute("CREATE TRIGGER closure_source_fence BEFORE INSERT OR UPDATE OR DELETE ON public.shipment_operational_stage_event FOR EACH ROW EXECUTE FUNCTION public.closure_fence_shipment_operational_stage_event()")


def downgrade():
    bind = op.get_bind()
    for table in (
        "shipment_operational_stage_event", "shipment_operational_stage_instance",
        "organization_shipment_stage_definition_version", "organization_shipment_stage_definition",
        "organization_shipment_stage_policy_version", "organization_shipment_stage_policy",
    ):
        if bind.execute(sa.text(f"SELECT EXISTS (SELECT 1 FROM public.{table})")).scalar():
            raise RuntimeError("Refusing downgrade: Organization Shipment Stage evidence exists")
    if bind.execute(sa.text("SELECT EXISTS (SELECT 1 FROM public.cargo_delivery WHERE is_final)" )).scalar():
        raise RuntimeError("Refusing downgrade: explicit final Delivery evidence exists")
    if bind.execute(sa.text("SELECT EXISTS (SELECT 1 FROM public.closure_policy_criterion WHERE code = ANY(:codes))"), {"codes": list(NEW_CODES)}).scalar():
        raise RuntimeError("Refusing downgrade: exact closure criteria exist")
    op.execute("DROP TRIGGER closure_source_fence ON public.shipment_operational_stage_event")
    op.execute("DROP FUNCTION public.closure_fence_shipment_operational_stage_event()")
    op.execute("DROP TRIGGER delivery_finality_insert ON public.cargo_delivery")
    op.execute("DROP FUNCTION public.delivery_finality_insert()")
    for table in (
        "shipment_operational_stage_event", "shipment_operational_stage_instance",
        "organization_shipment_stage_definition_version", "organization_shipment_stage_definition",
        "organization_shipment_stage_policy_version", "organization_shipment_stage_policy",
    ):
        op.drop_table(table)
    for name in (
        "shipment_stage_history_immutable", "shipment_stage_version_insert", "shipment_stage_item_insert",
        "shipment_stage_version_committed", "shipment_stage_instance_insert", "shipment_stage_event_insert",
    ):
        op.execute(f"DROP FUNCTION public.{name}()")
    op.drop_constraint("ck_closure_v1_warning", "closure_policy_criterion", type_="check")
    op.drop_constraint("ck_closure_v1_blocker", "closure_policy_criterion", type_="check")
    op.drop_constraint("ck_closure_criterion_code", "closure_policy_criterion", type_="check")
    op.create_check_constraint(
        "ck_closure_criterion_code", "closure_policy_criterion",
        "code IN ('ACTUAL_QUANTITY_KNOWN','ALL_CARGO_DELIVERED','REQUIRED_DOCUMENTS_READY','NO_OPEN_EXCEPTIONS','NO_OPEN_FOLLOW_UPS','NO_OPEN_OPERATIONAL_WORK')",
    )
    op.drop_column("cargo_delivery", "is_final")

