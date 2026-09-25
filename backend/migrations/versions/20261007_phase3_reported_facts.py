"""Typed report context/impacts on the existing OperationalEvent envelope."""
from alembic import op
import sqlalchemy as sa

revision = "20261007_phase3_reported_facts"
down_revision = "20261006_customer_entitlement"
branch_labels = None
depends_on = None
BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
SCOPE = (
    "(scope = 'SHIPMENT' AND route_plan_id IS NULL AND route_leg_id IS NULL AND execution_unit_id IS NULL AND cargo_item_id IS NULL) OR "
    "(scope = 'ROUTE_STAGE' AND route_plan_id IS NOT NULL AND route_leg_id IS NOT NULL AND execution_unit_id IS NULL AND cargo_item_id IS NULL) OR "
    "(scope = 'EXECUTION_UNIT' AND route_plan_id IS NULL AND route_leg_id IS NULL AND execution_unit_id IS NOT NULL AND cargo_item_id IS NULL) OR "
    "(scope = 'CARGO' AND route_plan_id IS NULL AND route_leg_id IS NULL AND execution_unit_id IS NULL AND cargo_item_id IS NOT NULL)"
)


def upgrade():
    if op.get_bind().execute(sa.text("SELECT 1 FROM operational_event WHERE event_type='phase3_reported_fact' LIMIT 1")).first():
        raise RuntimeError("Reserved P3-07 event type collides with legacy data; explicit classification required, no inferred backfill")
    op.add_column("operational_event", sa.Column("organization_id", BIGINT, nullable=True))
    op.execute("UPDATE operational_event e SET organization_id=u.organization_id FROM execution_unit u WHERE e.execution_unit_id=u.id")
    if op.get_bind().execute(sa.text("SELECT 1 FROM operational_event WHERE organization_id IS NULL LIMIT 1")).first():
        raise RuntimeError("Every legacy event must have a proven ExecutionUnit tenant owner")
    op.alter_column("operational_event", "organization_id", existing_type=BIGINT, nullable=False)
    op.create_foreign_key("fk_operational_event_organization", "operational_event", "operational_organization", ["organization_id"], ["id"], ondelete="RESTRICT")
    op.create_unique_constraint("uq_operational_event_id_org", "operational_event", ["id", "organization_id"])
    op.create_foreign_key("fk_operational_event_unit_org", "operational_event", "execution_unit", ["execution_unit_id", "organization_id"], ["id", "organization_id"], ondelete="RESTRICT")
    op.execute("""CREATE FUNCTION inherit_legacy_event_tenant() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF NEW.organization_id IS NULL AND NEW.execution_unit_id IS NOT NULL THEN
        SELECT organization_id INTO NEW.organization_id FROM execution_unit WHERE id=NEW.execution_unit_id;
      END IF;
      RETURN NEW;
    END $$""")
    op.execute("CREATE TRIGGER inherit_event_tenant BEFORE INSERT ON operational_event FOR EACH ROW EXECUTE FUNCTION inherit_legacy_event_tenant()")
    op.alter_column("operational_event", "execution_unit_id", existing_type=BIGINT, nullable=True)
    op.create_unique_constraint("uq_operational_event_id_unit", "operational_event", ["id", "execution_unit_id"])
    op.create_check_constraint("ck_event_report_or_unit", "operational_event", "execution_unit_id IS NOT NULL OR event_type = 'phase3_reported_fact'")
    op.create_check_constraint("ck_event_report_source", "operational_event", "event_type <> 'phase3_reported_fact' OR source IN ('CARRIER_REPORT','DRIVER_REPORT','INTERNAL_EXPERT','OTHER_OPERATIONAL_SOURCE')")
    op.create_index("uq_report_event_successor", "operational_event", ["supersedes_event_id"], unique=True,
                    postgresql_where=sa.text("event_type = 'phase3_reported_fact' AND supersedes_event_id IS NOT NULL"),
                    sqlite_where=sa.text("event_type = 'phase3_reported_fact' AND supersedes_event_id IS NOT NULL"))
    op.create_table("operational_event_report_context",
        sa.Column("operational_event_id", BIGINT, sa.ForeignKey("operational_event.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("organization_id", BIGINT, nullable=False),
        sa.Column("operational_shipment_id", BIGINT, nullable=False),
        sa.Column("scope", sa.String(24), nullable=False),
        sa.Column("route_plan_id", BIGINT), sa.Column("route_leg_id", BIGINT),
        sa.Column("execution_unit_id", BIGINT), sa.Column("cargo_item_id", BIGINT),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("customer_effect", sa.String(12), nullable=False),
        sa.Column("correction_reason", sa.String(500)),
        sa.UniqueConstraint("operational_event_id", "operational_shipment_id", name="uq_report_event_shipment"),
        sa.ForeignKeyConstraint(["operational_event_id", "organization_id"], ["operational_event.id", "operational_event.organization_id"], name="fk_report_event_org", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["operational_shipment_id", "organization_id"], ["operational_shipment.id", "operational_shipment.organization_id"], name="fk_report_shipment_org", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["route_plan_id", "operational_shipment_id"], ["route_plan.id", "route_plan.operational_shipment_id"], name="fk_report_plan_shipment", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["route_leg_id", "route_plan_id"], ["route_leg.id", "route_leg.route_plan_id"], name="fk_report_leg_plan", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["execution_unit_id", "organization_id"], ["execution_unit.id", "execution_unit.organization_id"], name="fk_report_unit_org", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["operational_event_id", "execution_unit_id"], ["operational_event.id", "operational_event.execution_unit_id"], name="fk_report_event_unit", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cargo_item_id", "operational_shipment_id"], ["shipment_cargo_item.id", "shipment_cargo_item.operational_shipment_id"], name="fk_report_cargo_shipment", ondelete="RESTRICT"),
        sa.CheckConstraint(SCOPE, name="ck_report_exact_scope"),
        sa.CheckConstraint("kind IN ('LOCATION','PROGRESS','TRANSPORT_CHANGE','EFFECT')", name="ck_report_kind"),
        sa.CheckConstraint("customer_effect IN ('CHANGE','DELAY')", name="ck_report_customer_effect"),
    )
    op.create_index("ix_report_shipment_event", "operational_event_report_context", ["operational_shipment_id", "operational_event_id"])
    op.create_table("operational_event_cargo_impact",
        sa.Column("operational_event_id", BIGINT, primary_key=True),
        sa.Column("cargo_item_id", BIGINT, primary_key=True),
        sa.Column("operational_shipment_id", BIGINT, nullable=False),
        sa.ForeignKeyConstraint(["operational_event_id", "operational_shipment_id"], ["operational_event_report_context.operational_event_id", "operational_event_report_context.operational_shipment_id"], name="fk_report_impact_context_shipment", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cargo_item_id", "operational_shipment_id"], ["shipment_cargo_item.id", "shipment_cargo_item.operational_shipment_id"], name="fk_report_impact_cargo_shipment", ondelete="RESTRICT"),
    )
    op.execute("""CREATE FUNCTION protect_phase3_report_fact() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_TABLE_NAME = 'operational_event' THEN
        IF OLD.event_type = 'phase3_reported_fact' THEN
          RAISE EXCEPTION 'Reported facts are immutable; append a correction';
        END IF;
      ELSE
        RAISE EXCEPTION 'Reported fact context and impacts are immutable';
      END IF;
      IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
      RETURN NEW;
    END $$""")
    for table in ("operational_event", "operational_event_report_context", "operational_event_cargo_impact"):
        op.execute(f"CREATE TRIGGER protect_report_fact BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION protect_phase3_report_fact()")


def downgrade():
    if op.get_bind().execute(sa.text("SELECT 1 FROM operational_event WHERE event_type='phase3_reported_fact' LIMIT 1")).first():
        raise RuntimeError("P3-07 reported facts exist; rollback would erase operational evidence")
    for table in ("operational_event_cargo_impact", "operational_event_report_context", "operational_event"):
        op.execute(f"DROP TRIGGER protect_report_fact ON {table}")
    op.execute("DROP FUNCTION protect_phase3_report_fact()")
    op.drop_table("operational_event_cargo_impact")
    op.drop_table("operational_event_report_context")
    op.drop_index("uq_report_event_successor", table_name="operational_event")
    op.drop_constraint("ck_event_report_source", "operational_event", type_="check")
    op.drop_constraint("ck_event_report_or_unit", "operational_event", type_="check")
    op.drop_constraint("uq_operational_event_id_unit", "operational_event", type_="unique")
    op.drop_constraint("fk_operational_event_unit_org", "operational_event", type_="foreignkey")
    op.execute("DROP TRIGGER inherit_event_tenant ON operational_event")
    op.execute("DROP FUNCTION inherit_legacy_event_tenant()")
    op.drop_constraint("uq_operational_event_id_org", "operational_event", type_="unique")
    op.drop_constraint("fk_operational_event_organization", "operational_event", type_="foreignkey")
    op.drop_column("operational_event", "organization_id")
    op.alter_column("operational_event", "execution_unit_id", existing_type=BIGINT, nullable=False)
