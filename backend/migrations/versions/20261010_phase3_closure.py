"""Versioned closure policy and explicit completed-only terminal decisions."""
from alembic import op
import sqlalchemy as sa

revision = "20261010_phase3_closure"
down_revision = "20261009_phase3_route_time"
branch_labels = None
depends_on = None

DDL = [
    """CREATE TABLE closure_policy (
    id BIGSERIAL NOT NULL,
    public_id VARCHAR(36) NOT NULL,
    organization_id BIGINT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_closure_policy_org UNIQUE (id, organization_id),
    UNIQUE (public_id),
    UNIQUE (organization_id),
    FOREIGN KEY(organization_id) REFERENCES operational_organization (id) ON DELETE RESTRICT
)""",
    """CREATE TABLE closure_policy_version (
    id BIGSERIAL NOT NULL,
    public_id VARCHAR(36) NOT NULL,
    organization_id BIGINT NOT NULL,
    policy_id BIGINT NOT NULL,
    version INTEGER NOT NULL,
    effective_from TIMESTAMP WITH TIME ZONE NOT NULL,
    actor_user_id BIGINT NOT NULL,
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_closure_version_org UNIQUE (id, organization_id),
    CONSTRAINT uq_closure_version_number UNIQUE (policy_id, version),
    CONSTRAINT uq_closure_version_effective UNIQUE (policy_id, effective_from),
    CONSTRAINT fk_closure_version_policy FOREIGN KEY(policy_id, organization_id) REFERENCES closure_policy (id, organization_id) ON DELETE RESTRICT,
    CONSTRAINT ck_closure_version_positive CHECK (version >= 1),
    UNIQUE (public_id),
    FOREIGN KEY(actor_user_id) REFERENCES expert_user (id) ON DELETE RESTRICT
)""",
    """CREATE TABLE closure_policy_criterion (
    id BIGSERIAL NOT NULL,
    public_id VARCHAR(36) NOT NULL,
    organization_id BIGINT NOT NULL,
    policy_version_id BIGINT NOT NULL,
    scope VARCHAR(24) NOT NULL,
    code VARCHAR(40) NOT NULL,
    mandatory BOOLEAN NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT fk_closure_criterion_version FOREIGN KEY(policy_version_id, organization_id) REFERENCES closure_policy_version (id, organization_id) ON DELETE RESTRICT,
    CONSTRAINT uq_closure_criterion_identity UNIQUE (policy_version_id, scope, code),
    CONSTRAINT ck_closure_criterion_scope CHECK (scope IN ('GENERAL','road','rail','sea','air','multimodal_transfer','customs_handling')),
    CONSTRAINT ck_closure_criterion_code CHECK (code IN ('ACTUAL_QUANTITY_KNOWN','ALL_CARGO_DELIVERED','REQUIRED_DOCUMENTS_READY','NO_OPEN_EXCEPTIONS','NO_OPEN_FOLLOW_UPS','NO_OPEN_OPERATIONAL_WORK')),
    UNIQUE (public_id)
)""",
    """CREATE TABLE shipment_closure_decision (
    id BIGSERIAL NOT NULL,
    public_id VARCHAR(36) NOT NULL,
    organization_id BIGINT NOT NULL,
    operational_shipment_id BIGINT NOT NULL,
    policy_version_id BIGINT NOT NULL,
    previous_state VARCHAR(20) NOT NULL,
    kind VARCHAR(12) NOT NULL,
    actor_user_id BIGINT NOT NULL,
    actor_label VARCHAR(200) NOT NULL,
    reason VARCHAR(1000),
    shipment_version INTEGER NOT NULL,
    assessment_fingerprint VARCHAR(64) NOT NULL,
    assessment JSON NOT NULL,
    missing_items JSON NOT NULL,
    occurred_at TIMESTAMP WITH TIME ZONE NOT NULL,
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT fk_closure_decision_shipment FOREIGN KEY(operational_shipment_id, organization_id) REFERENCES operational_shipment (id, organization_id) ON DELETE RESTRICT,
    CONSTRAINT fk_closure_decision_policy FOREIGN KEY(policy_version_id, organization_id) REFERENCES closure_policy_version (id, organization_id) ON DELETE RESTRICT,
    CONSTRAINT ck_closure_completed_predecessor CHECK (previous_state = 'completed'),
    CONSTRAINT ck_closure_decision_kind CHECK (kind IN ('NORMAL','EXCEPTIONAL')),
    CONSTRAINT ck_closure_exception_reason CHECK (kind != 'EXCEPTIONAL' OR (reason IS NOT NULL AND length(trim(reason)) > 0)),
    UNIQUE (public_id),
    UNIQUE (operational_shipment_id),
    FOREIGN KEY(actor_user_id) REFERENCES expert_user (id) ON DELETE RESTRICT
)""",
]

# Static, per-source parent fences include absent-row inserts. They do not deny
# repairs after closure; explicit domain commands enforce that Product matrix.
FENCES = {
    "shipment_cargo_item": "SELECT (j->>'operational_shipment_id')::bigint AS id FROM rows",
    "cargo_delivery": "SELECT (j->>'operational_shipment_id')::bigint AS id FROM rows",
    "operational_document_requirement": "SELECT (j->>'operational_shipment_id')::bigint AS id FROM rows",
    "operational_artifact_association": "SELECT r.operational_shipment_id AS id FROM public.operational_document_requirement r JOIN rows ON r.id = (j->>'requirement_id')::bigint",
    "operational_document_assessment": "SELECT r.operational_shipment_id AS id FROM public.operational_document_requirement r JOIN public.operational_artifact_association a ON a.requirement_id = r.id JOIN rows ON a.id = (j->>'association_id')::bigint",
    "case_document_file": "SELECT (j->>'operational_shipment_id')::bigint AS id FROM rows UNION SELECT r.operational_shipment_id FROM public.operational_document_requirement r JOIN public.operational_artifact_association a ON a.requirement_id = r.id JOIN rows ON a.document_file_id = (j->>'id')::bigint",
    "operational_exception": "SELECT (j->>'operational_shipment_id')::bigint AS id FROM rows",
    "operational_work_item": "SELECT (j->>'operational_shipment_id')::bigint AS id FROM rows",
    "route_plan": "SELECT (j->>'operational_shipment_id')::bigint AS id FROM rows",
    "route_leg": "SELECT p.operational_shipment_id AS id FROM public.route_plan p JOIN rows ON p.id = (j->>'route_plan_id')::bigint",
    "route_stage_execution": "SELECT (j->>'operational_shipment_id')::bigint AS id FROM rows",
}


def upgrade():
    if op.get_bind().dialect.name != "postgresql":
        raise RuntimeError("P3-12 migration requires PostgreSQL; SQLite create_all is only a bounded unit-test adapter")
    for statement in DDL:
        op.execute(statement)
    op.drop_constraint("ck_operational_shipment_status", "operational_shipment", type_="check")
    op.create_check_constraint("ck_operational_shipment_status", "operational_shipment",
        "lifecycle_status IN ('planned','in_progress','completed','cancelled','closed')")
    op.execute("""CREATE FUNCTION public.closure_history_immutable() RETURNS trigger
        LANGUAGE plpgsql SET search_path = pg_catalog AS $$ BEGIN
        RAISE EXCEPTION 'Closure history is immutable' USING ERRCODE = '23514'; END $$""")
    for table in ("closure_policy", "closure_policy_version", "closure_policy_criterion", "shipment_closure_decision"):
        op.execute(f"CREATE TRIGGER closure_immutable BEFORE UPDATE OR DELETE ON public.{table} FOR EACH ROW EXECUTE FUNCTION public.closure_history_immutable()")
    op.execute("""CREATE FUNCTION public.closure_version_insert() RETURNS trigger
        LANGUAGE plpgsql SET search_path = pg_catalog AS $$
        DECLARE last_version integer; last_effective timestamptz;
        BEGIN
          PERFORM id FROM public.operational_organization WHERE id = NEW.organization_id FOR UPDATE;
          SELECT version, effective_from INTO last_version, last_effective
            FROM public.closure_policy_version WHERE policy_id = NEW.policy_id ORDER BY version DESC LIMIT 1;
          IF NEW.version != coalesce(last_version, 0) + 1 OR
             (last_version IS NOT NULL AND (NEW.effective_from <= last_effective OR NEW.effective_from < clock_timestamp())) THEN
            RAISE EXCEPTION 'Invalid closure version sequence/effective date' USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END $$""")
    op.execute("CREATE TRIGGER closure_version_insert BEFORE INSERT ON public.closure_policy_version FOR EACH ROW EXECUTE FUNCTION public.closure_version_insert()")
    op.execute("""CREATE FUNCTION public.closure_criterion_insert() RETURNS trigger
        LANGUAGE plpgsql SET search_path = pg_catalog AS $$ BEGIN
          IF NOT EXISTS (SELECT 1 FROM public.closure_policy_version v
              WHERE v.id = NEW.policy_version_id AND v.organization_id = NEW.organization_id
              AND v.xmin = pg_current_xact_id()::xid) THEN
            RAISE EXCEPTION 'Closure version criteria are sealed' USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END $$""")
    op.execute("CREATE TRIGGER closure_criterion_insert BEFORE INSERT ON public.closure_policy_criterion FOR EACH ROW EXECUTE FUNCTION public.closure_criterion_insert()")
    op.execute("""CREATE FUNCTION public.closure_version_committed() RETURNS trigger
        LANGUAGE plpgsql SET search_path = pg_catalog AS $$ BEGIN
          IF NOT EXISTS (SELECT 1 FROM public.closure_policy_criterion c WHERE c.policy_version_id = NEW.id) THEN
            RAISE EXCEPTION 'A closure version needs explicit criteria' USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END $$""")
    op.execute("CREATE CONSTRAINT TRIGGER closure_version_committed AFTER INSERT ON public.closure_policy_version DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.closure_version_committed()")
    op.execute("""CREATE FUNCTION public.closure_decision_insert() RETURNS trigger
        LANGUAGE plpgsql SET search_path = pg_catalog AS $$
        DECLARE s public.operational_shipment%ROWTYPE;
        BEGIN
          SELECT * INTO s FROM public.operational_shipment WHERE id = NEW.operational_shipment_id FOR UPDATE;
          IF s.lifecycle_status != 'completed' OR NEW.shipment_version != s.version + 1 OR NEW.organization_id != s.organization_id THEN
            RAISE EXCEPTION 'Closure requires current completed predecessor/version' USING ERRCODE = '23514';
          END IF;
          IF NOT EXISTS (SELECT 1 FROM public.expert_user u JOIN public.operational_membership m ON m.user_id = u.id
              JOIN public.operational_organization o ON o.id = m.organization_id AND o.is_active
              WHERE u.id = NEW.actor_user_id AND u.is_active AND m.is_active AND m.organization_id = s.organization_id
              AND (SELECT count(*) FROM public.operational_membership all_memberships
                   WHERE all_memberships.user_id = u.id AND all_memberships.is_active) = 1
              AND ((NEW.kind = 'NORMAL' AND u.authority = 'EXPERT' AND u.id = s.primary_responsible_expert_id)
                OR (NEW.kind = 'EXCEPTIONAL' AND u.authority = 'ORGANIZATION_ADMIN'))) THEN
            RAISE EXCEPTION 'Closure actor is not eligible' USING ERRCODE = '23514';
          END IF;
          IF NOT EXISTS (SELECT 1 FROM public.closure_policy_version v WHERE v.id = NEW.policy_version_id
              AND v.organization_id = s.organization_id AND v.effective_from <= NEW.occurred_at
              AND NOT EXISTS (SELECT 1 FROM public.closure_policy_version later
                WHERE later.policy_id = v.policy_id AND later.version > v.version AND later.effective_from <= NEW.occurred_at)) THEN
            RAISE EXCEPTION 'Closure policy is not current' USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END $$""")
    op.execute("CREATE TRIGGER closure_decision_insert BEFORE INSERT ON public.shipment_closure_decision FOR EACH ROW EXECUTE FUNCTION public.closure_decision_insert()")
    op.execute("""CREATE FUNCTION public.closure_terminal_guard() RETURNS trigger
        LANGUAGE plpgsql SET search_path = pg_catalog AS $$ BEGIN
          IF TG_OP = 'INSERT' THEN
            IF NEW.lifecycle_status = 'closed' THEN RAISE EXCEPTION 'Cannot create closed shipment' USING ERRCODE = '23514'; END IF;
          ELSIF OLD.lifecycle_status = 'closed' AND NEW.lifecycle_status != 'closed' THEN
            RAISE EXCEPTION 'Closed shipment is terminal' USING ERRCODE = '23514';
          ELSIF NEW.lifecycle_status = 'closed' AND OLD.lifecycle_status != 'closed' THEN
            IF OLD.lifecycle_status != 'completed' OR NEW.version != OLD.version + 1 OR NOT EXISTS
                (SELECT 1 FROM public.shipment_closure_decision d WHERE d.operational_shipment_id = NEW.id
                  AND d.shipment_version = NEW.version AND d.xmin = pg_current_xact_id()::xid) THEN
              RAISE EXCEPTION 'Explicit closure decision required' USING ERRCODE = '23514';
            END IF;
          END IF;
          RETURN NEW;
        END $$""")
    op.execute("CREATE TRIGGER closure_terminal_guard BEFORE INSERT OR UPDATE ON public.operational_shipment FOR EACH ROW EXECUTE FUNCTION public.closure_terminal_guard()")
    op.execute("""CREATE FUNCTION public.closure_decision_committed() RETURNS trigger
        LANGUAGE plpgsql SET search_path = pg_catalog AS $$ BEGIN
          IF NOT EXISTS (SELECT 1 FROM public.operational_shipment s WHERE s.id = NEW.operational_shipment_id
              AND s.lifecycle_status = 'closed' AND s.version >= NEW.shipment_version) THEN
            RAISE EXCEPTION 'Closure decision and terminal transition must commit together' USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END $$""")
    op.execute("CREATE CONSTRAINT TRIGGER closure_decision_committed AFTER INSERT ON public.shipment_closure_decision DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.closure_decision_committed()")
    for table, query in FENCES.items():
        op.execute(f"""CREATE FUNCTION public.closure_fence_{table}() RETURNS trigger
            LANGUAGE plpgsql SET search_path = pg_catalog AS $$
            DECLARE before_row jsonb; after_row jsonb;
            BEGIN
              IF TG_OP != 'INSERT' THEN before_row = to_jsonb(OLD); END IF;
              IF TG_OP != 'DELETE' THEN after_row = to_jsonb(NEW); END IF;
              PERFORM s.id FROM public.operational_shipment s WHERE s.id IN (
                WITH rows AS (SELECT before_row AS j UNION ALL SELECT after_row) {query}
              ) ORDER BY s.id FOR UPDATE;
              IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
              RETURN NEW;
            END $$""")
        op.execute(f"CREATE TRIGGER closure_source_fence BEFORE INSERT OR UPDATE OR DELETE ON public.{table} FOR EACH ROW EXECUTE FUNCTION public.closure_fence_{table}()")


def downgrade():
    bind = op.get_bind()
    for table in ("shipment_closure_decision", "closure_policy_criterion", "closure_policy_version", "closure_policy"):
        if bind.execute(sa.text(f"SELECT EXISTS (SELECT 1 FROM public.{table})")).scalar():
            raise RuntimeError("Refusing downgrade: closure policy/decision evidence exists")
    for table in FENCES:
        op.execute(f"DROP TRIGGER closure_source_fence ON public.{table}")
        op.execute(f"DROP FUNCTION public.closure_fence_{table}()")
    op.execute("DROP TRIGGER closure_terminal_guard ON public.operational_shipment")
    op.execute("DROP FUNCTION public.closure_terminal_guard()")
    for table in ("shipment_closure_decision", "closure_policy_criterion", "closure_policy_version", "closure_policy"):
        op.drop_table(table)
    for name in ("closure_history_immutable", "closure_version_insert", "closure_criterion_insert", "closure_version_committed", "closure_decision_insert", "closure_decision_committed"):
        op.execute(f"DROP FUNCTION public.{name}()")
    op.drop_constraint("ck_operational_shipment_status", "operational_shipment", type_="check")
    op.create_check_constraint("ck_operational_shipment_status", "operational_shipment",
        "lifecycle_status IN ('planned','in_progress','completed','cancelled')")
