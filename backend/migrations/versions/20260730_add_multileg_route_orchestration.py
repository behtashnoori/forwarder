"""Add safe versioned multi-leg route orchestration.

Revision ID: 20260730_multileg_route
Revises: 20260729_operational_vertical_slice
"""
from alembic import op
import sqlalchemy as sa

revision = "20260730_multileg_route"
down_revision = "20260729_operational_vertical_slice"
branch_labels = None
depends_on = None
BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")

CHECKPOINT_TYPES = "'origin_loading','export_customs','border_exit','transit_border_entry','transit_border_exit','border_entry','import_customs','port_entry','port_exit','terminal_arrival','transshipment','destination_arrival','unloading','final_delivery'"
DEPENDENCY_TYPES = "'finish_to_start','arrival_before_departure','previous_leg_arrival_before_next_leg_departure','customs_clearance_before_border_exit','unloading_before_final_delivery'"


def upgrade():
    with op.batch_alter_table("operational_shipment") as b:
        b.create_unique_constraint("uq_operational_shipment_id_org", ["id", "organization_id"])

    with op.batch_alter_table("route_plan") as b:
        b.create_unique_constraint("uq_route_plan_id_shipment", ["id", "operational_shipment_id"])
        b.add_column(sa.Column("status", sa.String(20), nullable=False, server_default="active"))
        b.add_column(sa.Column("created_from_plan_id", BIGINT))
        b.add_column(sa.Column("replan_reason", sa.Text()))
        b.add_column(sa.Column("effective_at", sa.DateTime(timezone=True)))
        b.add_column(sa.Column("timeline_reconciled_at", sa.DateTime(timezone=True)))
        b.add_column(sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
        b.create_foreign_key("fk_route_plan_created_from", "route_plan", ["created_from_plan_id"], ["id"], ondelete="RESTRICT")
        b.create_check_constraint("ck_route_plan_status", "status IN ('draft','active','superseded','cancelled')")
    op.execute("UPDATE route_plan SET effective_at=created_at WHERE is_active")

    with op.batch_alter_table("route_leg") as b:
        b.drop_constraint("ck_route_leg_status", type_="check")
        b.create_check_constraint("ck_route_leg_status", "status IN ('planned','ready','in_progress','completed','blocked','cancelled')")
        b.create_unique_constraint("uq_route_leg_id_plan", ["id", "route_plan_id"])
        b.add_column(sa.Column("source_route_leg_id", BIGINT))
        b.add_column(sa.Column("carrier_reference", sa.String(120)))
        b.add_column(sa.Column("actual_departure", sa.DateTime(timezone=True)))
        b.add_column(sa.Column("actual_arrival", sa.DateTime(timezone=True)))
        b.add_column(sa.Column("projected_departure", sa.DateTime(timezone=True)))
        b.add_column(sa.Column("projected_arrival", sa.DateTime(timezone=True)))
        b.create_foreign_key("fk_route_leg_source", "route_leg", ["source_route_leg_id"], ["id"], ondelete="RESTRICT")
        b.create_check_constraint("ck_route_leg_actual_timeline", "actual_arrival IS NULL OR actual_departure IS NULL OR actual_arrival >= actual_departure")

    op.create_table(
        "operational_checkpoint",
        sa.Column("id", BIGINT, primary_key=True), sa.Column("source_checkpoint_id", BIGINT),
        sa.Column("route_plan_id", BIGINT, nullable=False), sa.Column("route_leg_id", BIGINT),
        sa.Column("sequence_number", sa.Integer(), nullable=False), sa.Column("checkpoint_type", sa.String(40), nullable=False),
        sa.Column("canonical_location_id", BIGINT, nullable=False),
        sa.Column("planned_arrival_at", sa.DateTime(timezone=True)), sa.Column("planned_departure_at", sa.DateTime(timezone=True)),
        sa.Column("projected_arrival_at", sa.DateTime(timezone=True)), sa.Column("projected_departure_at", sa.DateTime(timezone=True)),
        sa.Column("actual_arrival_at", sa.DateTime(timezone=True)), sa.Column("actual_departure_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(24), nullable=False, server_default="planned"),
        sa.Column("verification_state", sa.String(20), nullable=False, server_default="planned"),
        sa.Column("responsible_party", sa.String(160)), sa.Column("notes", sa.Text()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"), sa.Column("created_by_user_id", BIGINT, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["route_plan_id"], ["route_plan.id"], name="fk_checkpoint_route_plan", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["route_leg_id", "route_plan_id"], ["route_leg.id", "route_leg.route_plan_id"], name="fk_checkpoint_leg_same_plan", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_checkpoint_id"], ["operational_checkpoint.id"], name="fk_checkpoint_source", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["canonical_location_id"], ["canonical_location.id"], name="fk_checkpoint_location", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["expert_user.id"], name="fk_checkpoint_created_by", ondelete="RESTRICT"),
        sa.UniqueConstraint("route_plan_id", "sequence_number", name="uq_operational_checkpoint_plan_sequence"),
        sa.UniqueConstraint("id", "route_plan_id", name="uq_operational_checkpoint_id_plan"),
        sa.CheckConstraint("sequence_number >= 1", name="ck_operational_checkpoint_sequence_positive"),
        sa.CheckConstraint("planned_departure_at IS NULL OR planned_arrival_at IS NULL OR planned_departure_at >= planned_arrival_at", name="ck_operational_checkpoint_planned_timeline"),
        sa.CheckConstraint("actual_departure_at IS NULL OR actual_arrival_at IS NOT NULL", name="ck_operational_checkpoint_actual_timeline"),
        sa.CheckConstraint("status IN ('planned','approaching','arrived','processing','ready_to_depart','departed','completed','blocked','cancelled')", name="ck_operational_checkpoint_status"),
        sa.CheckConstraint(f"checkpoint_type IN ({CHECKPOINT_TYPES})", name="ck_operational_checkpoint_type"),
        sa.CheckConstraint("verification_state IN ('planned','reported','verified')", name="ck_operational_checkpoint_verification"),
    )
    op.create_index("ix_operational_checkpoint_plan_status", "operational_checkpoint", ["route_plan_id", "status"])

    with op.batch_alter_table("operational_milestone") as b:
        b.drop_constraint("ck_operational_milestone_type", type_="check")
        b.drop_constraint("uq_operational_milestone_leg_type", type_="unique")
        b.alter_column("milestone_type", existing_type=sa.String(20), type_=sa.String(40), existing_nullable=False)
        b.alter_column("route_leg_id", existing_type=BIGINT, nullable=True)
        b.add_column(sa.Column("route_plan_id", BIGINT))
        b.add_column(sa.Column("checkpoint_id", BIGINT))
        b.add_column(sa.Column("source_milestone_id", BIGINT))
        b.add_column(sa.Column("projected_at", sa.DateTime(timezone=True)))
    op.execute("UPDATE operational_milestone m SET route_plan_id=l.route_plan_id, projected_at=m.planned_at FROM route_leg l WHERE l.id=m.route_leg_id" if op.get_bind().dialect.name == "postgresql" else "UPDATE operational_milestone SET route_plan_id=(SELECT route_plan_id FROM route_leg WHERE route_leg.id=operational_milestone.route_leg_id), projected_at=planned_at")
    with op.batch_alter_table("operational_milestone") as b:
        b.alter_column("route_plan_id", existing_type=BIGINT, nullable=False)
        b.create_foreign_key("fk_milestone_route_plan", "route_plan", ["route_plan_id"], ["id"], ondelete="CASCADE")
        b.create_foreign_key("fk_milestone_checkpoint_same_plan", "operational_checkpoint", ["checkpoint_id", "route_plan_id"], ["id", "route_plan_id"], ondelete="CASCADE")
        b.create_foreign_key("fk_milestone_source", "operational_milestone", ["source_milestone_id"], ["id"], ondelete="RESTRICT")
        b.create_unique_constraint("uq_operational_milestone_id_plan", ["id", "route_plan_id"])
        b.create_unique_constraint("uq_operational_milestone_leg_type", ["route_leg_id", "milestone_type"])
        b.create_check_constraint("ck_operational_milestone_type", "milestone_type IN ('departure','arrival','checkpoint_arrival','checkpoint_processing_complete','checkpoint_departure')")
        b.create_check_constraint("ck_operational_milestone_single_owner", "(route_leg_id IS NOT NULL AND checkpoint_id IS NULL) OR (route_leg_id IS NULL AND checkpoint_id IS NOT NULL)")

    op.create_table(
        "route_dependency", sa.Column("id", BIGINT, primary_key=True), sa.Column("route_plan_id", BIGINT, nullable=False),
        sa.Column("predecessor_checkpoint_id", BIGINT, nullable=False), sa.Column("successor_checkpoint_id", BIGINT, nullable=False),
        sa.Column("dependency_type", sa.String(60), nullable=False, server_default="finish_to_start"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["route_plan_id"], ["route_plan.id"], name="fk_dependency_route_plan", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["predecessor_checkpoint_id", "route_plan_id"], ["operational_checkpoint.id", "operational_checkpoint.route_plan_id"], name="fk_dependency_predecessor_same_plan", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["successor_checkpoint_id", "route_plan_id"], ["operational_checkpoint.id", "operational_checkpoint.route_plan_id"], name="fk_dependency_successor_same_plan", ondelete="CASCADE"),
        sa.UniqueConstraint("route_plan_id", "predecessor_checkpoint_id", "successor_checkpoint_id", "dependency_type", name="uq_route_dependency_edge"),
        sa.CheckConstraint("predecessor_checkpoint_id <> successor_checkpoint_id", name="ck_route_dependency_no_self_reference"),
        sa.CheckConstraint(f"dependency_type IN ({DEPENDENCY_TYPES})", name="ck_route_dependency_type"),
    )

    with op.batch_alter_table("operational_work_item") as b:
        b.drop_constraint("ck_operational_work_item_type", type_="check")
        b.alter_column("milestone_id", existing_type=BIGINT, nullable=True)
        b.add_column(sa.Column("route_plan_id", BIGINT))
        b.add_column(sa.Column("checkpoint_id", BIGINT))
        b.add_column(sa.Column("severity", sa.String(16), nullable=False, server_default="warning"))
        b.add_column(sa.Column("detected_at", sa.DateTime(timezone=True)))
        b.add_column(sa.Column("resolution_reason", sa.Text()))
        b.create_foreign_key("fk_work_item_shipment_same_org", "operational_shipment", ["operational_shipment_id", "organization_id"], ["id", "organization_id"], ondelete="CASCADE")
        b.create_foreign_key("fk_work_item_plan_same_shipment", "route_plan", ["route_plan_id", "operational_shipment_id"], ["id", "operational_shipment_id"], ondelete="CASCADE")
        b.create_foreign_key("fk_work_item_checkpoint_same_plan", "operational_checkpoint", ["checkpoint_id", "route_plan_id"], ["id", "route_plan_id"], ondelete="CASCADE")
        b.create_check_constraint("ck_operational_work_item_type", "work_type IN ('OVERDUE_MILESTONE','CHECKPOINT_OVERDUE','ROUTE_DEPENDENCY_BLOCKED','REPLAN_REQUIRED')")
        b.create_check_constraint(
            "ck_operational_work_item_owner_scope",
            "(work_type = 'OVERDUE_MILESTONE' AND milestone_id IS NOT NULL AND route_plan_id IS NULL AND checkpoint_id IS NULL) "
            "OR (work_type IN ('CHECKPOINT_OVERDUE','ROUTE_DEPENDENCY_BLOCKED','REPLAN_REQUIRED') "
            "AND milestone_id IS NULL AND route_plan_id IS NOT NULL AND checkpoint_id IS NOT NULL)",
        )
    op.execute("UPDATE operational_work_item SET detected_at=created_at WHERE detected_at IS NULL")
    with op.batch_alter_table("operational_work_item") as b:
        b.alter_column("detected_at", existing_type=sa.DateTime(timezone=True), nullable=False)
    op.create_index("uq_route_exception_open", "operational_work_item", ["route_plan_id", "checkpoint_id", "work_type"], unique=True, postgresql_where=sa.text("status='open' AND route_plan_id IS NOT NULL"), sqlite_where=sa.text("status='open' AND route_plan_id IS NOT NULL"))
    if op.get_bind().dialect.name == "postgresql":
        op.execute("""CREATE OR REPLACE FUNCTION public.phase1a_validate_work_item_scope_v1() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM operational_shipment s WHERE s.id=NEW.operational_shipment_id AND s.organization_id=NEW.organization_id)
             OR (
               NEW.milestone_id IS NOT NULL AND NOT EXISTS (
                 SELECT 1 FROM operational_milestone m JOIN route_plan p ON p.id=m.route_plan_id
                 WHERE m.id=NEW.milestone_id AND p.operational_shipment_id=NEW.operational_shipment_id
               )
             )
             OR (
               NEW.milestone_id IS NULL AND NEW.checkpoint_id IS NOT NULL AND NOT EXISTS (
                 SELECT 1 FROM operational_checkpoint c JOIN route_plan p ON p.id=c.route_plan_id
                 WHERE c.id=NEW.checkpoint_id AND c.route_plan_id=NEW.route_plan_id AND p.operational_shipment_id=NEW.operational_shipment_id
               )
             )
          THEN RAISE EXCEPTION 'work item scope mismatch' USING ERRCODE = '23514'; END IF;
          RETURN NEW;
        END; $$""")

    with op.batch_alter_table("operational_idempotency") as b:
        b.drop_constraint("uq_operational_idempotency_key", type_="unique")
        b.add_column(sa.Column("resource_type", sa.String(40), nullable=False, server_default="organization"))
        b.add_column(sa.Column("command_resource_id", BIGINT, nullable=False, server_default="0"))
        b.create_unique_constraint("uq_operational_idempotency_scope", ["organization_id", "operation", "resource_type", "command_resource_id", "idempotency_key"])


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # Phase 1B operational data cannot be represented losslessly by Phase 1A.
        # Fail before any DDL so the transaction and Alembic revision remain intact.
        op.execute("""DO $$ BEGIN
          IF EXISTS (SELECT 1 FROM operational_checkpoint)
             OR EXISTS (SELECT 1 FROM route_dependency)
             OR EXISTS (
               SELECT 1 FROM route_plan
               WHERE created_from_plan_id IS NOT NULL
                  OR replan_reason IS NOT NULL
                  OR timeline_reconciled_at IS NOT NULL
                  OR version <> 1
                  OR status <> 'active'
             )
             OR EXISTS (
               SELECT 1 FROM route_leg
               WHERE source_route_leg_id IS NOT NULL
                  OR carrier_reference IS NOT NULL
                  OR actual_departure IS NOT NULL
                  OR actual_arrival IS NOT NULL
                  OR projected_departure IS NOT NULL
                  OR projected_arrival IS NOT NULL
                  OR status IN ('ready','blocked')
             )
             OR EXISTS (
               SELECT 1 FROM operational_milestone
               WHERE checkpoint_id IS NOT NULL
                  OR source_milestone_id IS NOT NULL
                  OR route_leg_id IS NULL
                  OR milestone_type NOT IN ('departure','arrival')
                  OR projected_at IS DISTINCT FROM planned_at
             )
             OR EXISTS (
               SELECT 1 FROM operational_work_item
               WHERE route_plan_id IS NOT NULL
                  OR checkpoint_id IS NOT NULL
                  OR severity <> 'warning'
                  OR detected_at IS DISTINCT FROM created_at
                  OR resolution_reason IS NOT NULL
             )
             OR EXISTS (
               SELECT 1 FROM operational_idempotency
               WHERE resource_type <> 'organization'
                  OR command_resource_id <> 0
             )
          THEN RAISE EXCEPTION 'SAFE_DOWNGRADE_GUARD: Phase 1B operational data exists';
          END IF;
        END $$""")
    else:
        counts = sum(bind.execute(sa.text(f"SELECT count(*) FROM {t}")).scalar_one() for t in ("operational_checkpoint", "route_dependency"))
        if counts:
            raise RuntimeError("SAFE_DOWNGRADE_GUARD: Phase 1B operational data exists")

    with op.batch_alter_table("operational_idempotency") as b:
        b.drop_constraint("uq_operational_idempotency_scope", type_="unique")
        b.drop_column("command_resource_id"); b.drop_column("resource_type")
        b.create_unique_constraint("uq_operational_idempotency_key", ["organization_id", "operation", "idempotency_key"])
    op.drop_index("uq_route_exception_open", table_name="operational_work_item")
    with op.batch_alter_table("operational_work_item") as b:
        b.drop_constraint("ck_operational_work_item_type", type_="check")
        b.drop_constraint("ck_operational_work_item_owner_scope", type_="check")
        b.drop_constraint("fk_work_item_checkpoint_same_plan", type_="foreignkey")
        b.drop_constraint("fk_work_item_plan_same_shipment", type_="foreignkey")
        b.drop_constraint("fk_work_item_shipment_same_org", type_="foreignkey")
        b.drop_column("resolution_reason"); b.drop_column("detected_at"); b.drop_column("severity"); b.drop_column("checkpoint_id"); b.drop_column("route_plan_id")
        b.alter_column("milestone_id", existing_type=BIGINT, nullable=False)
        b.create_check_constraint("ck_operational_work_item_type", "work_type IN ('OVERDUE_MILESTONE')")
    if op.get_bind().dialect.name == "postgresql":
        op.execute("""CREATE OR REPLACE FUNCTION public.phase1a_validate_work_item_scope_v1() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM operational_shipment s WHERE s.id=NEW.operational_shipment_id AND s.organization_id=NEW.organization_id)
             OR NOT EXISTS (SELECT 1 FROM operational_milestone m JOIN route_leg l ON l.id=m.route_leg_id JOIN route_plan p ON p.id=l.route_plan_id WHERE m.id=NEW.milestone_id AND p.operational_shipment_id=NEW.operational_shipment_id)
          THEN RAISE EXCEPTION 'work item scope mismatch' USING ERRCODE = '23514'; END IF;
          RETURN NEW;
        END; $$""")
    op.drop_table("route_dependency")
    with op.batch_alter_table("operational_milestone") as b:
        b.drop_constraint("ck_operational_milestone_single_owner", type_="check")
        b.drop_constraint("ck_operational_milestone_type", type_="check")
        b.drop_constraint("uq_operational_milestone_id_plan", type_="unique")
        b.drop_constraint("fk_milestone_source", type_="foreignkey"); b.drop_constraint("fk_milestone_checkpoint_same_plan", type_="foreignkey"); b.drop_constraint("fk_milestone_route_plan", type_="foreignkey")
        b.drop_column("projected_at"); b.drop_column("source_milestone_id"); b.drop_column("checkpoint_id"); b.drop_column("route_plan_id")
        b.alter_column("milestone_type", existing_type=sa.String(40), type_=sa.String(20), existing_nullable=False)
        b.alter_column("route_leg_id", existing_type=BIGINT, nullable=False)
        b.create_check_constraint("ck_operational_milestone_type", "milestone_type IN ('departure','arrival')")
    op.drop_index("ix_operational_checkpoint_plan_status", table_name="operational_checkpoint")
    op.drop_table("operational_checkpoint")
    with op.batch_alter_table("route_leg") as b:
        b.drop_constraint("ck_route_leg_actual_timeline", type_="check"); b.drop_constraint("fk_route_leg_source", type_="foreignkey")
        b.drop_constraint("uq_route_leg_id_plan", type_="unique")
        b.drop_column("projected_arrival"); b.drop_column("projected_departure"); b.drop_column("actual_arrival"); b.drop_column("actual_departure"); b.drop_column("carrier_reference"); b.drop_column("source_route_leg_id")
        b.drop_constraint("ck_route_leg_status", type_="check")
        b.create_check_constraint("ck_route_leg_status", "status IN ('planned','in_progress','completed','cancelled')")
    with op.batch_alter_table("route_plan") as b:
        b.drop_constraint("ck_route_plan_status", type_="check"); b.drop_constraint("fk_route_plan_created_from", type_="foreignkey")
        b.drop_column("version"); b.drop_column("timeline_reconciled_at"); b.drop_column("effective_at"); b.drop_column("replan_reason"); b.drop_column("created_from_plan_id"); b.drop_column("status")
        b.drop_constraint("uq_route_plan_id_shipment", type_="unique")
    with op.batch_alter_table("operational_shipment") as b:
        b.drop_constraint("uq_operational_shipment_id_org", type_="unique")
