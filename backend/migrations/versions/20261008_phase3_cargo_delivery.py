"""Real partial delivery facts and DELIVERY context; no inferred backfill."""
from alembic import op
import sqlalchemy as sa

revision = "20261008_phase3_cargo_delivery"
down_revision = "20261007_phase3_reported_facts"
branch_labels = None
depends_on = None
BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
OLD_TARGETS = (
    "(context_type = 'SHIPMENT' AND cargo_item_id IS NULL AND route_leg_id IS NULL AND execution_unit_id IS NULL) OR "
    "(context_type = 'CARGO' AND cargo_item_id IS NOT NULL AND route_leg_id IS NULL AND execution_unit_id IS NULL) OR "
    "(context_type = 'ROUTE_LEG' AND cargo_item_id IS NULL AND route_leg_id IS NOT NULL AND execution_unit_id IS NULL) OR "
    "(context_type = 'EXECUTION_UNIT' AND cargo_item_id IS NULL AND route_leg_id IS NULL AND execution_unit_id IS NOT NULL)"
)
NEW_TARGETS = "((" + OLD_TARGETS + ") AND delivery_id IS NULL) OR (context_type = 'DELIVERY' AND delivery_id IS NOT NULL AND cargo_item_id IS NULL AND route_leg_id IS NULL AND execution_unit_id IS NULL)"


def _context_checks(delivery):
    values = "'SHIPMENT','CARGO','ROUTE_LEG','EXECUTION_UNIT'" + (",'DELIVERY'" if delivery else "")
    op.create_check_constraint("ck_operational_document_context_type", "operational_document_context", f"context_type IN ({values})")
    op.create_check_constraint("ck_operational_document_context_one_target", "operational_document_context", NEW_TARGETS if delivery else OLD_TARGETS)
    op.create_check_constraint("ck_operational_document_cargo_owner_scope", "operational_document_context", "visibility <> 'CARGO_OWNER' OR context_type IN ('CARGO','DELIVERY')" if delivery else "visibility <> 'CARGO_OWNER' OR context_type = 'CARGO'")


def _drop_context_checks():
    for name in ("ck_operational_document_context_type", "ck_operational_document_context_one_target", "ck_operational_document_cargo_owner_scope"):
        op.drop_constraint(name, "operational_document_context", type_="check")


def upgrade():
    op.create_unique_constraint("uq_shipment_cargo_id_uom", "shipment_cargo_item", ["id", "uom_id"])
    op.create_table("cargo_delivery",
        sa.Column("id", BIGINT, primary_key=True), sa.Column("public_id", sa.String(36), nullable=False, unique=True),
        sa.Column("organization_id", BIGINT, sa.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("operational_shipment_id", BIGINT, nullable=False), sa.Column("cargo_item_id", BIGINT, nullable=False),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("uom_id", BIGINT, sa.ForeignKey("unit_of_measure.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("uom_code_snapshot", sa.String(64), nullable=False), sa.Column("uom_symbol_snapshot", sa.String(32), nullable=False),
        sa.Column("destination_text", sa.String(255), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False), sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_user_id", BIGINT, sa.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("supersedes_delivery_id", BIGINT), sa.Column("revision", sa.Integer, nullable=False), sa.Column("reason", sa.String(500)),
        sa.UniqueConstraint("id", "cargo_item_id", name="uq_delivery_id_cargo"),
        sa.UniqueConstraint("id", "operational_shipment_id", "organization_id", name="uq_delivery_id_shipment_org"),
        sa.UniqueConstraint("supersedes_delivery_id", name="uq_delivery_successor"),
        sa.ForeignKeyConstraint(["operational_shipment_id", "organization_id"], ["operational_shipment.id", "operational_shipment.organization_id"], name="fk_delivery_shipment_org", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cargo_item_id", "operational_shipment_id"], ["shipment_cargo_item.id", "shipment_cargo_item.operational_shipment_id"], name="fk_delivery_cargo_shipment", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cargo_item_id", "uom_id"], ["shipment_cargo_item.id", "shipment_cargo_item.uom_id"], name="fk_delivery_cargo_uom", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["supersedes_delivery_id", "cargo_item_id"], ["cargo_delivery.id", "cargo_delivery.cargo_item_id"], name="fk_delivery_predecessor_cargo", ondelete="RESTRICT"),
        sa.CheckConstraint("quantity > 0", name="ck_delivery_positive_quantity"),
        sa.CheckConstraint("(supersedes_delivery_id IS NULL AND revision = 1) OR (supersedes_delivery_id IS NOT NULL AND revision > 1)", name="ck_delivery_revision"),
    )
    op.create_index("ix_delivery_shipment_history", "cargo_delivery", ["operational_shipment_id", "occurred_at", "id"])
    op.create_index("ix_delivery_cargo_history", "cargo_delivery", ["cargo_item_id", "id"])
    op.create_table("cargo_delivery_evidence",
        sa.Column("delivery_id", BIGINT, primary_key=True), sa.Column("document_file_id", BIGINT, primary_key=True),
        sa.Column("operational_shipment_id", BIGINT, nullable=False),
        sa.Column("organization_id", BIGINT, sa.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("actor_user_id", BIGINT, sa.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["delivery_id", "operational_shipment_id", "organization_id"], ["cargo_delivery.id", "cargo_delivery.operational_shipment_id", "cargo_delivery.organization_id"], name="fk_delivery_evidence_parent", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["document_file_id", "operational_shipment_id", "organization_id"], ["case_document_file.id", "case_document_file.operational_shipment_id", "case_document_file.operational_organization_id"], name="fk_delivery_evidence_file", ondelete="RESTRICT"),
    )
    op.add_column("operational_document_context", sa.Column("delivery_id", BIGINT))
    op.create_foreign_key("fk_document_context_delivery_parent", "operational_document_context", "cargo_delivery", ["delivery_id", "operational_shipment_id", "organization_id"], ["id", "operational_shipment_id", "organization_id"], ondelete="RESTRICT")
    _drop_context_checks()
    _context_checks(True)
    op.execute("""CREATE FUNCTION protect_cargo_delivery_fact() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN RAISE EXCEPTION 'Delivery facts and evidence are immutable; append a correction'; END $$""")
    for table in ("cargo_delivery", "cargo_delivery_evidence"):
        op.execute(f"CREATE TRIGGER protect_delivery_fact BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION protect_cargo_delivery_fact()")


def downgrade():
    bind = op.get_bind()
    if any(bind.execute(sa.text(f"SELECT 1 FROM {table} LIMIT 1")).first() for table in ("cargo_delivery", "cargo_delivery_evidence")):
        raise RuntimeError("P3-08 delivery facts exist; rollback would erase operational evidence")
    _drop_context_checks()
    op.drop_constraint("fk_document_context_delivery_parent", "operational_document_context", type_="foreignkey")
    op.drop_column("operational_document_context", "delivery_id")
    _context_checks(False)
    for table in ("cargo_delivery_evidence", "cargo_delivery"):
        op.execute(f"DROP TRIGGER protect_delivery_fact ON {table}")
        op.drop_table(table)
    op.execute("DROP FUNCTION protect_cargo_delivery_fact()")
    op.drop_constraint("uq_shipment_cargo_id_uom", "shipment_cargo_item", type_="unique")
