"""Empty, additive route reference configuration and explicit plan basis."""
from alembic import op
import sqlalchemy as sa

revision = "20261009_phase3_route_time"
down_revision = "20261008_phase3_cargo_delivery"
branch_labels = None
depends_on = None

# Frozen DDL: no runtime model imports and no defaults/backfill.
DDL = [
    """CREATE TABLE organization_route_time (
	id BIGSERIAL NOT NULL,
	public_id VARCHAR(36) NOT NULL,
	organization_id BIGINT NOT NULL,
	origin_location_id BIGINT NOT NULL,
	destination_location_id BIGINT NOT NULL,
	origin_point_id BIGINT,
	destination_point_id BIGINT,
	origin_snapshot JSON NOT NULL,
	destination_snapshot JSON NOT NULL,
	transport_mode VARCHAR(32) NOT NULL,
	actor_user_id BIGINT NOT NULL,
	recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_route_time_public UNIQUE (public_id),
	CONSTRAINT uq_route_time_id_org UNIQUE (id, organization_id),
	CONSTRAINT fk_route_time_origin_org FOREIGN KEY(origin_point_id, organization_id) REFERENCES logistics_point (id, organization_id) ON DELETE RESTRICT,
	CONSTRAINT fk_route_time_destination_org FOREIGN KEY(destination_point_id, organization_id) REFERENCES logistics_point (id, organization_id) ON DELETE RESTRICT,
	CONSTRAINT ck_route_time_mode CHECK (transport_mode IN ('road','rail','sea','air','multimodal_transfer','customs_handling')),
	CONSTRAINT ck_route_time_distinct CHECK (origin_location_id <> destination_location_id OR COALESCE(origin_point_id,0) <> COALESCE(destination_point_id,0)),
	FOREIGN KEY(organization_id) REFERENCES operational_organization (id) ON DELETE RESTRICT,
	FOREIGN KEY(origin_location_id) REFERENCES canonical_location (id) ON DELETE RESTRICT,
	FOREIGN KEY(destination_location_id) REFERENCES canonical_location (id) ON DELETE RESTRICT,
	FOREIGN KEY(actor_user_id) REFERENCES expert_user (id) ON DELETE RESTRICT
)""",
    """CREATE TABLE organization_route_time_version (
	id BIGSERIAL NOT NULL,
	public_id VARCHAR(36) NOT NULL,
	organization_id BIGINT NOT NULL,
	reference_id BIGINT NOT NULL,
	version INTEGER NOT NULL,
	movement_min_minutes INTEGER,
	movement_max_minutes INTEGER,
	stop_min_minutes INTEGER,
	stop_max_minutes INTEGER,
	effective_from TIMESTAMP WITH TIME ZONE NOT NULL,
	actor_user_id BIGINT NOT NULL,
	recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_route_time_version_public UNIQUE (public_id),
	CONSTRAINT uq_route_time_version_id_org UNIQUE (id, organization_id),
	CONSTRAINT uq_route_time_version UNIQUE (reference_id, version),
	CONSTRAINT uq_route_time_effective UNIQUE (reference_id, effective_from),
	CONSTRAINT fk_route_time_version_org FOREIGN KEY(reference_id, organization_id) REFERENCES organization_route_time (id, organization_id) ON DELETE RESTRICT,
	CONSTRAINT ck_route_time_version_positive CHECK (version >= 1),
	CONSTRAINT ck_route_time_movement_range CHECK ((movement_min_minutes IS NULL AND movement_max_minutes IS NULL) OR (movement_min_minutes IS NOT NULL AND movement_max_minutes IS NOT NULL AND movement_min_minutes >= 1 AND movement_max_minutes >= movement_min_minutes AND movement_max_minutes <= 525600)),
	CONSTRAINT ck_route_time_stop_range CHECK ((stop_min_minutes IS NULL AND stop_max_minutes IS NULL) OR (stop_min_minutes IS NOT NULL AND stop_max_minutes IS NOT NULL AND stop_min_minutes >= 0 AND stop_max_minutes >= stop_min_minutes AND stop_max_minutes <= 525600)),
	CONSTRAINT ck_route_time_defined CHECK (movement_min_minutes IS NOT NULL OR stop_min_minutes IS NOT NULL),
	FOREIGN KEY(organization_id) REFERENCES operational_organization (id) ON DELETE RESTRICT,
	FOREIGN KEY(actor_user_id) REFERENCES expert_user (id) ON DELETE RESTRICT
)""",
    """CREATE TABLE route_leg_time_basis (
	id BIGSERIAL NOT NULL,
	public_id VARCHAR(36) NOT NULL,
	organization_id BIGINT NOT NULL,
	operational_shipment_id BIGINT NOT NULL,
	route_plan_id BIGINT NOT NULL,
	route_leg_id BIGINT NOT NULL,
	reference_version_id BIGINT NOT NULL,
	selection_revision INTEGER NOT NULL,
	leg_basis JSON NOT NULL,
	reference_at TIMESTAMP WITH TIME ZONE NOT NULL,
	actor_user_id BIGINT NOT NULL,
	recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_route_time_basis_public UNIQUE (public_id),
	CONSTRAINT uq_route_time_basis_revision UNIQUE (route_leg_id, selection_revision),
	CONSTRAINT ck_route_time_basis_revision CHECK (selection_revision >= 1),
	CONSTRAINT fk_route_time_basis_shipment FOREIGN KEY(operational_shipment_id, organization_id) REFERENCES operational_shipment (id, organization_id) ON DELETE RESTRICT,
	CONSTRAINT fk_route_time_basis_plan FOREIGN KEY(route_plan_id, operational_shipment_id) REFERENCES route_plan (id, operational_shipment_id) ON DELETE RESTRICT,
	CONSTRAINT fk_route_time_basis_leg FOREIGN KEY(route_leg_id, route_plan_id) REFERENCES route_leg (id, route_plan_id) ON DELETE RESTRICT,
	CONSTRAINT fk_route_time_basis_version FOREIGN KEY(reference_version_id, organization_id) REFERENCES organization_route_time_version (id, organization_id) ON DELETE RESTRICT,
	FOREIGN KEY(organization_id) REFERENCES operational_organization (id) ON DELETE RESTRICT,
	FOREIGN KEY(actor_user_id) REFERENCES expert_user (id) ON DELETE RESTRICT
)""",
    """CREATE UNIQUE INDEX uq_route_time_key ON organization_route_time (organization_id, origin_location_id, destination_location_id, coalesce(origin_point_id, 0), coalesce(destination_point_id, 0), transport_mode)""",
]


def upgrade():
    for statement in DDL:
        op.execute(statement)
    op.execute("""CREATE FUNCTION protect_route_time_history() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN RAISE EXCEPTION 'Route reference history is immutable; append a version or selection'; END $$""")
    for table in ("organization_route_time", "organization_route_time_version", "route_leg_time_basis"):
        op.execute(f"CREATE TRIGGER route_time_immutable BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION protect_route_time_history()")
    op.execute("""CREATE FUNCTION check_route_time_version() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE previous record;
    BEGIN
      PERFORM id FROM organization_route_time WHERE id=NEW.reference_id AND organization_id=NEW.organization_id FOR UPDATE;
      SELECT version,effective_from INTO previous FROM organization_route_time_version WHERE reference_id=NEW.reference_id ORDER BY version DESC LIMIT 1;
      IF NEW.version <> COALESCE(previous.version,0)+1 THEN RAISE EXCEPTION 'Reference version must be sequential'; END IF;
      IF previous.version IS NOT NULL AND (NEW.effective_from <= previous.effective_from OR NEW.effective_from < transaction_timestamp()) THEN RAISE EXCEPTION 'Reference update must have a later prospective effective date'; END IF;
      RETURN NEW;
    END $$""")
    op.execute("CREATE TRIGGER route_time_version_guard BEFORE INSERT ON organization_route_time_version FOR EACH ROW EXECUTE FUNCTION check_route_time_version()")
    op.execute("""CREATE FUNCTION check_route_time_basis() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE leg record; reference record; latest integer;
    BEGIN
      SELECT l.*,p.status AS plan_status INTO leg FROM route_leg l JOIN route_plan p ON p.id=l.route_plan_id WHERE l.id=NEW.route_leg_id FOR UPDATE OF l;
      SELECT r.*,v.effective_from,v.id AS version_id INTO reference FROM organization_route_time_version v JOIN organization_route_time r ON r.id=v.reference_id WHERE v.id=NEW.reference_version_id FOR UPDATE OF r;
      SELECT COALESCE(MAX(selection_revision),0) INTO latest FROM route_leg_time_basis WHERE route_leg_id=NEW.route_leg_id;
      IF NEW.selection_revision <> latest+1 THEN RAISE EXCEPTION 'Selection revision must be sequential'; END IF;
      IF leg.plan_status <> 'draft' THEN RAISE EXCEPTION 'Published route basis is immutable'; END IF;
      IF reference.origin_location_id IS DISTINCT FROM leg.origin_location_id OR reference.destination_location_id IS DISTINCT FROM leg.destination_location_id OR reference.origin_point_id IS DISTINCT FROM leg.origin_logistics_point_id OR reference.destination_point_id IS DISTINCT FROM leg.destination_logistics_point_id OR reference.transport_mode IS DISTINCT FROM leg.transport_mode THEN RAISE EXCEPTION 'Reference does not match route leg'; END IF;
      IF leg.planned_departure IS NOT NULL AND leg.planned_departure IS DISTINCT FROM NEW.reference_at THEN RAISE EXCEPTION 'Reference basis differs from planned departure'; END IF;
      IF reference.effective_from > NEW.reference_at OR EXISTS (SELECT 1 FROM organization_route_time_version v WHERE v.reference_id=reference.id AND v.effective_from > reference.effective_from AND v.effective_from <= NEW.reference_at) THEN RAISE EXCEPTION 'Reference version is not applicable'; END IF;
      RETURN NEW;
    END $$""")
    op.execute("CREATE TRIGGER route_time_basis_guard BEFORE INSERT ON route_leg_time_basis FOR EACH ROW EXECUTE FUNCTION check_route_time_basis()")


def downgrade():
    bind = op.get_bind()
    tables = ("route_leg_time_basis", "organization_route_time_version", "organization_route_time")
    if any(bind.execute(sa.text(f"SELECT 1 FROM {table} LIMIT 1")).first() for table in tables):
        raise RuntimeError("P3-10 reference history exists; downgrade would erase configuration or plan evidence")
    for table in tables:
        op.drop_table(table)
    for function in ("check_route_time_basis", "check_route_time_version", "protect_route_time_history"):
        op.execute(f"DROP FUNCTION {function}()")
