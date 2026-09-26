"""Empty, additive immutable Cargo ETA snapshots and provenance links."""
from alembic import op
import sqlalchemy as sa

revision = "20261010_phase3_cargo_eta"
down_revision = "20261009_phase3_route_time"
branch_labels = None
depends_on = None

# Frozen schema; no runtime model imports, seed or fabricated historical estimate.
DDL = [
    """CREATE TABLE cargo_eta_snapshot (
    id BIGSERIAL NOT NULL,
    public_id VARCHAR(36) NOT NULL,
    organization_id BIGINT NOT NULL,
    operational_shipment_id BIGINT NOT NULL,
    cargo_item_id BIGINT NOT NULL,
    route_plan_id BIGINT,
    audience VARCHAR(12) NOT NULL,
    sequence INTEGER NOT NULL,
    ruleset VARCHAR(32) NOT NULL,
    source_fingerprint VARCHAR(64) NOT NULL,
    calculated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    result JSON NOT NULL,
    source_basis JSON NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_cargo_eta_public UNIQUE (public_id),
    CONSTRAINT uq_cargo_eta_id_org UNIQUE (id, organization_id),
    CONSTRAINT uq_cargo_eta_sequence UNIQUE (cargo_item_id, audience, sequence),
    CONSTRAINT fk_cargo_eta_shipment FOREIGN KEY(operational_shipment_id, organization_id) REFERENCES operational_shipment (id, organization_id) ON DELETE RESTRICT,
    CONSTRAINT fk_cargo_eta_cargo FOREIGN KEY(cargo_item_id, operational_shipment_id) REFERENCES shipment_cargo_item (id, operational_shipment_id) ON DELETE RESTRICT,
    CONSTRAINT fk_cargo_eta_plan FOREIGN KEY(route_plan_id, operational_shipment_id) REFERENCES route_plan (id, operational_shipment_id) ON DELETE RESTRICT,
    CONSTRAINT ck_cargo_eta_audience CHECK (audience IN ('INTERNAL','CUSTOMER')),
    CONSTRAINT ck_cargo_eta_sequence CHECK (sequence >= 1),
    CONSTRAINT ck_cargo_eta_ruleset CHECK (ruleset = 'ETA_RULESET_V1')
)""",
    """CREATE INDEX ix_cargo_eta_history ON cargo_eta_snapshot (organization_id, cargo_item_id, audience, sequence)""",
    """CREATE TABLE cargo_eta_input (
    id BIGSERIAL NOT NULL,
    snapshot_id BIGINT NOT NULL,
    organization_id BIGINT NOT NULL,
    reference_version_id BIGINT,
    operational_event_id BIGINT,
    milestone_event_id BIGINT,
    traversal_id BIGINT,
    PRIMARY KEY (id),
    CONSTRAINT fk_eta_input_snapshot FOREIGN KEY(snapshot_id, organization_id) REFERENCES cargo_eta_snapshot (id, organization_id) ON DELETE RESTRICT,
    CONSTRAINT fk_eta_input_reference FOREIGN KEY(reference_version_id, organization_id) REFERENCES organization_route_time_version (id, organization_id) ON DELETE RESTRICT,
    CONSTRAINT ck_eta_input_one_source CHECK ((CASE WHEN reference_version_id IS NULL THEN 0 ELSE 1 END + CASE WHEN operational_event_id IS NULL THEN 0 ELSE 1 END + CASE WHEN milestone_event_id IS NULL THEN 0 ELSE 1 END + CASE WHEN traversal_id IS NULL THEN 0 ELSE 1 END) = 1),
    FOREIGN KEY(operational_event_id) REFERENCES operational_event (id) ON DELETE RESTRICT,
    FOREIGN KEY(milestone_event_id) REFERENCES milestone_event (id) ON DELETE RESTRICT,
    FOREIGN KEY(traversal_id) REFERENCES route_traversal_fact (id) ON DELETE RESTRICT
)""",
]


def upgrade():
    for statement in DDL:
        op.execute(statement)
    op.execute("""CREATE FUNCTION protect_cargo_eta_history() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN RAISE EXCEPTION 'Cargo ETA history is immutable'; END $$""")
    for table in ("cargo_eta_snapshot", "cargo_eta_input"):
        op.execute(f"CREATE TRIGGER cargo_eta_immutable BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION protect_cargo_eta_history()")
    op.execute("""CREATE FUNCTION check_cargo_eta_sequence() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE previous integer;
    BEGIN
      PERFORM pg_advisory_xact_lock(hashtextextended('cargo_eta:' || NEW.cargo_item_id::text, 0));
      SELECT COALESCE(MAX(sequence),0) INTO previous FROM cargo_eta_snapshot
        WHERE cargo_item_id=NEW.cargo_item_id AND audience=NEW.audience;
      IF NEW.sequence <> previous+1 THEN RAISE EXCEPTION 'ETA sequence must be consecutive'; END IF;
      RETURN NEW;
    END $$""")
    op.execute("CREATE TRIGGER cargo_eta_sequence BEFORE INSERT ON cargo_eta_snapshot FOR EACH ROW EXECUTE FUNCTION check_cargo_eta_sequence()")
    op.execute("""CREATE FUNCTION check_cargo_eta_source() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE shipment bigint;
    BEGIN
      IF NOT EXISTS (SELECT 1 FROM cargo_eta_snapshot s WHERE s.id=NEW.snapshot_id
          AND s.xmin = pg_current_xact_id()::xid) THEN
        RAISE EXCEPTION 'ETA provenance must be sealed in the snapshot transaction';
      END IF;
      SELECT operational_shipment_id INTO shipment FROM cargo_eta_snapshot WHERE id=NEW.snapshot_id AND organization_id=NEW.organization_id;
      IF NEW.operational_event_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM operational_event_report_context c WHERE c.operational_event_id=NEW.operational_event_id
        AND c.organization_id=NEW.organization_id AND c.operational_shipment_id=shipment
      ) THEN RAISE EXCEPTION 'ETA report source scope mismatch'; END IF;
      IF NEW.milestone_event_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM milestone_event e JOIN operational_milestone m ON m.id=e.milestone_id
        WHERE e.id=NEW.milestone_event_id AND e.organization_id=NEW.organization_id
        AND m.organization_id=NEW.organization_id AND m.operational_shipment_id=shipment
      ) THEN RAISE EXCEPTION 'ETA milestone source scope mismatch'; END IF;
      IF NEW.traversal_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM route_traversal_fact f WHERE f.id=NEW.traversal_id AND f.operational_shipment_id=shipment
      ) THEN RAISE EXCEPTION 'ETA traversal source scope mismatch'; END IF;
      RETURN NEW;
    END $$""")
    op.execute("CREATE TRIGGER cargo_eta_source BEFORE INSERT ON cargo_eta_input FOR EACH ROW EXECUTE FUNCTION check_cargo_eta_source()")


def downgrade():
    bind = op.get_bind()
    if any(bind.execute(sa.text(f"SELECT 1 FROM {table} LIMIT 1")).first()
           for table in ("cargo_eta_snapshot", "cargo_eta_input")):
        raise RuntimeError("ETA history exists; downgrade would erase calculation evidence")
    op.drop_table("cargo_eta_input")
    op.drop_table("cargo_eta_snapshot")
    for function in ("check_cargo_eta_source", "check_cargo_eta_sequence", "protect_cargo_eta_history"):
        op.execute(f"DROP FUNCTION {function}()")
