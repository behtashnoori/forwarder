"""Pinned route distance and immutable structured progress for ETA v2."""

from alembic import op
import sqlalchemy as sa


revision = "20261013_structured_route_progress_eta"
down_revision = "20261012_phase3_cargo_eta"
branch_labels = None
depends_on = None

BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade():
    op.add_column(
        "organization_route_time_version",
        sa.Column("planned_distance_km", sa.Numeric(12, 3), nullable=True),
    )
    op.create_check_constraint(
        "ck_route_time_planned_distance",
        "organization_route_time_version",
        "planned_distance_km IS NULL OR planned_distance_km > 0",
    )
    op.create_unique_constraint(
        "uq_route_time_basis_exact_progress", "route_leg_time_basis",
        ["id", "route_leg_id", "organization_id"],
    )
    op.create_unique_constraint(
        "uq_route_stage_execution_exact_progress", "route_stage_execution",
        ["id", "route_plan_id", "route_leg_id", "execution_unit_id"],
    )
    op.drop_constraint("ck_cargo_eta_ruleset", "cargo_eta_snapshot", type_="check")
    op.create_check_constraint(
        "ck_cargo_eta_ruleset", "cargo_eta_snapshot",
        "ruleset IN ('ETA_RULESET_V1','ETA_RULESET_V2')",
    )
    op.create_table(
        "operational_event_route_progress",
        sa.Column("operational_event_id", BIGINT, nullable=False),
        sa.Column("organization_id", BIGINT, nullable=False),
        sa.Column("operational_shipment_id", BIGINT, nullable=False),
        sa.Column("route_plan_id", BIGINT, nullable=False),
        sa.Column("route_leg_id", BIGINT, nullable=False),
        sa.Column("route_stage_execution_id", BIGINT, nullable=False),
        sa.Column("execution_unit_id", BIGINT, nullable=False),
        sa.Column("route_leg_time_basis_id", BIGINT, nullable=True),
        sa.Column("progress_kind", sa.String(32), nullable=False),
        sa.Column("distance_remaining_km", sa.Numeric(12, 3), nullable=False),
        sa.Column("planned_distance_km", sa.Numeric(12, 3), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("operational_event_id"),
        sa.ForeignKeyConstraint(
            ["operational_event_id", "organization_id"],
            ["operational_event.id", "operational_event.organization_id"],
            name="fk_route_progress_event_org", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["operational_event_id", "execution_unit_id"],
            ["operational_event.id", "operational_event.execution_unit_id"],
            name="fk_route_progress_event_unit", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["operational_event_id", "operational_shipment_id"],
            ["operational_event_report_context.operational_event_id",
             "operational_event_report_context.operational_shipment_id"],
            name="fk_route_progress_report_context", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["operational_shipment_id", "organization_id"],
            ["operational_shipment.id", "operational_shipment.organization_id"],
            name="fk_route_progress_shipment_org", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["route_plan_id", "operational_shipment_id"],
            ["route_plan.id", "route_plan.operational_shipment_id"],
            name="fk_route_progress_plan_shipment", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["route_leg_id", "route_plan_id"],
            ["route_leg.id", "route_leg.route_plan_id"],
            name="fk_route_progress_leg_plan", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["route_stage_execution_id", "route_plan_id", "route_leg_id", "execution_unit_id"],
            ["route_stage_execution.id", "route_stage_execution.route_plan_id",
             "route_stage_execution.route_leg_id", "route_stage_execution.execution_unit_id"],
            name="fk_route_progress_exact_stage", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["route_leg_time_basis_id", "route_leg_id", "organization_id"],
            ["route_leg_time_basis.id", "route_leg_time_basis.route_leg_id",
             "route_leg_time_basis.organization_id"],
            name="fk_route_progress_exact_basis", ondelete="RESTRICT",
        ),
        sa.CheckConstraint("progress_kind = 'DISTANCE_REMAINING_KM'", name="ck_route_progress_kind"),
        sa.CheckConstraint("distance_remaining_km >= 0", name="ck_route_progress_nonnegative"),
        sa.CheckConstraint(
            "planned_distance_km IS NULL OR (planned_distance_km > 0 AND distance_remaining_km <= planned_distance_km)",
            name="ck_route_progress_distance_bounds",
        ),
        sa.CheckConstraint(
            "(route_leg_time_basis_id IS NULL AND planned_distance_km IS NULL) OR "
            "(route_leg_time_basis_id IS NOT NULL AND planned_distance_km IS NOT NULL)",
            name="ck_route_progress_basis_pair",
        ),
    )
    op.create_index(
        "ix_route_progress_plan_leg_occurred", "operational_event_route_progress",
        ["route_plan_id", "route_leg_id", "operational_event_id"],
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute("""CREATE FUNCTION protect_route_progress_history() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'Structured route progress is immutable; append a correction'; END $$""")
        op.execute("CREATE TRIGGER route_progress_immutable BEFORE UPDATE OR DELETE ON operational_event_route_progress FOR EACH ROW EXECUTE FUNCTION protect_route_progress_history()")


def downgrade():
    bind = op.get_bind()
    if bind.execute(sa.text("SELECT 1 FROM operational_event_route_progress LIMIT 1")).first():
        raise RuntimeError("Structured route progress exists; downgrade would erase evidence")
    if bind.execute(sa.text("SELECT 1 FROM organization_route_time_version WHERE planned_distance_km IS NOT NULL LIMIT 1")).first():
        raise RuntimeError("Planned route distance exists; downgrade would erase the route baseline")
    if bind.execute(sa.text("SELECT 1 FROM cargo_eta_snapshot WHERE ruleset='ETA_RULESET_V2' LIMIT 1")).first():
        raise RuntimeError("ETA v2 history exists; downgrade would invalidate immutable evidence")
    if bind.dialect.name == "postgresql":
        op.execute("DROP TRIGGER route_progress_immutable ON operational_event_route_progress")
        op.execute("DROP FUNCTION protect_route_progress_history()")
    op.drop_table("operational_event_route_progress")
    op.drop_constraint("ck_cargo_eta_ruleset", "cargo_eta_snapshot", type_="check")
    op.create_check_constraint("ck_cargo_eta_ruleset", "cargo_eta_snapshot", "ruleset = 'ETA_RULESET_V1'")
    op.drop_constraint("uq_route_stage_execution_exact_progress", "route_stage_execution", type_="unique")
    op.drop_constraint("uq_route_time_basis_exact_progress", "route_leg_time_basis", type_="unique")
    op.drop_constraint("ck_route_time_planned_distance", "organization_route_time_version", type_="check")
    op.drop_column("organization_route_time_version", "planned_distance_km")
