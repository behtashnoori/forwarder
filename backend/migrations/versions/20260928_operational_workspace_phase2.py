"""Add organization SLA, bounded Action, and Exception context.

Revision ID: 20260928_operational_workspace_phase2
Revises: 20260927_customer_portal_account_lifecycle
"""

from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision = "20260928_operational_workspace_phase2"
down_revision = "20260927_customer_portal_account_lifecycle"
branch_labels = None
depends_on = None

BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade():
    with op.batch_alter_table("operational_exception", schema=None) as batch_op:
        batch_op.add_column(sa.Column("impact_summary", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("evidence_summary", sa.Text(), nullable=True))
        batch_op.create_unique_constraint(
            "uq_exception_id_shipment", ["id", "operational_shipment_id"]
        )

    with op.batch_alter_table("operational_work_item", schema=None) as batch_op:
        batch_op.drop_constraint(
            "ck_operational_work_item_type", type_="check"
        )
        batch_op.drop_constraint(
            "ck_operational_work_item_owner_scope", type_="check"
        )
        batch_op.add_column(sa.Column("public_id", sa.String(36), nullable=True))
        batch_op.add_column(sa.Column("exception_id", BIGINT, nullable=True))
        batch_op.add_column(
            sa.Column("action_context_type", sa.String(16), nullable=True)
        )
        batch_op.add_column(sa.Column("process_type", sa.String(40), nullable=True))
        batch_op.add_column(sa.Column("expected_result", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("latest_follow_up", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column("latest_follow_up_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(sa.Column("created_by_user_id", BIGINT, nullable=True))
        batch_op.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            )
        )
        batch_op.create_check_constraint(
            "ck_operational_work_item_type",
            "work_type IN ('OVERDUE_MILESTONE','CHECKPOINT_OVERDUE','ROUTE_DEPENDENCY_BLOCKED','REPLAN_REQUIRED','FOLLOW_UP')",
        )
        batch_op.create_check_constraint(
            "ck_operational_work_item_owner_scope",
            "(work_type = 'OVERDUE_MILESTONE' AND milestone_id IS NOT NULL AND route_plan_id IS NULL AND checkpoint_id IS NULL) "
            "OR (work_type IN ('CHECKPOINT_OVERDUE','ROUTE_DEPENDENCY_BLOCKED','REPLAN_REQUIRED') "
            "AND milestone_id IS NULL AND route_plan_id IS NOT NULL AND checkpoint_id IS NOT NULL) "
            "OR (work_type = 'FOLLOW_UP' AND milestone_id IS NULL AND route_plan_id IS NULL AND checkpoint_id IS NULL)",
        )
        batch_op.create_check_constraint(
            "ck_operational_work_item_action_context",
            "action_context_type IS NULL OR action_context_type IN ('SHIPMENT','EXCEPTION','PROCESS')",
        )
        batch_op.create_check_constraint(
            "ck_operational_work_item_process_type",
            "process_type IS NULL OR process_type IN ('EXCEPTION_RESPONSE','ACTION_FOLLOW_UP')",
        )
        batch_op.create_check_constraint(
            "ck_operational_work_item_follow_up_context",
            "work_type != 'FOLLOW_UP' OR "
            "(action_context_type = 'SHIPMENT' AND exception_id IS NULL AND process_type IS NULL) OR "
            "(action_context_type = 'EXCEPTION' AND exception_id IS NOT NULL AND process_type IS NULL) OR "
            "(action_context_type = 'PROCESS' AND exception_id IS NULL AND process_type IS NOT NULL)",
        )
        batch_op.create_foreign_key(
            "fk_work_item_exception_same_shipment",
            "operational_exception",
            ["exception_id", "operational_shipment_id"],
            ["id", "operational_shipment_id"],
            ondelete="RESTRICT",
        )
        batch_op.create_foreign_key(
            "fk_work_item_created_by_user",
            "expert_user",
            ["created_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )

    work_item = sa.table(
        "operational_work_item",
        sa.column("id", BIGINT),
        sa.column("public_id", sa.String(36)),
    )
    bind = op.get_bind()
    for item_id in bind.execute(
        sa.select(work_item.c.id)
        .where(work_item.c.public_id.is_(None))
        .order_by(work_item.c.id)
    ).scalars():
        bind.execute(
            work_item.update()
            .where(work_item.c.id == item_id)
            .values(public_id=str(uuid4()))
        )

    with op.batch_alter_table("operational_work_item", schema=None) as batch_op:
        batch_op.alter_column(
            "public_id", existing_type=sa.String(36), nullable=False
        )
        batch_op.alter_column(
            "updated_at",
            existing_type=sa.DateTime(timezone=True),
            server_default=None,
        )
        batch_op.create_unique_constraint(
            "uq_operational_work_item_public_id", ["public_id"]
        )

    op.create_table(
        "organization_sla_rule",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column("organization_id", BIGINT, nullable=False),
        sa.Column("process_type", sa.String(40), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("warning_minutes", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", BIGINT, nullable=False),
        sa.Column("updated_by_user_id", BIGINT, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "process_type IN ('EXCEPTION_RESPONSE','ACTION_FOLLOW_UP')",
            name="ck_organization_sla_process",
        ),
        sa.CheckConstraint(
            "duration_minutes > 0 AND duration_minutes <= 525600",
            name="ck_organization_sla_duration",
        ),
        sa.CheckConstraint(
            "warning_minutes IS NULL OR (warning_minutes > 0 AND warning_minutes < duration_minutes)",
            name="ck_organization_sla_warning",
        ),
        sa.CheckConstraint("version >= 1", name="ck_organization_sla_version"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["operational_organization.id"],
            name="fk_organization_sla_rule_org",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["expert_user.id"],
            name="fk_organization_sla_rule_created_by",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_user_id"],
            ["expert_user.id"],
            name="fk_organization_sla_rule_updated_by",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("public_id", name="uq_organization_sla_rule_public_id"),
        sa.UniqueConstraint(
            "id", "organization_id", name="uq_organization_sla_rule_id_org"
        ),
        sa.UniqueConstraint(
            "organization_id", "process_type", name="uq_organization_sla_process"
        ),
    )
    op.create_index(
        "ix_organization_sla_rule_active",
        "organization_sla_rule",
        ["organization_id", "is_active", "effective_from"],
    )

    op.create_table(
        "operational_sla_commitment",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column("organization_id", BIGINT, nullable=False),
        sa.Column("rule_id", BIGINT, nullable=False),
        sa.Column("rule_version", sa.Integer(), nullable=False),
        sa.Column("process_type", sa.String(40), nullable=False),
        sa.Column("operational_shipment_id", BIGINT, nullable=False),
        sa.Column("responsible_user_id", BIGINT, nullable=False),
        sa.Column("source_type", sa.String(40), nullable=False),
        sa.Column("source_public_id", sa.String(36), nullable=False),
        sa.Column("source_version", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("warning_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("evaluation_status", sa.String(16), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_watermark", sa.String(160), nullable=False),
        sa.Column("rule_snapshot", sa.JSON(), nullable=False),
        sa.Column("explanation", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "process_type IN ('EXCEPTION_RESPONSE','ACTION_FOLLOW_UP')",
            name="ck_operational_sla_process",
        ),
        sa.CheckConstraint(
            "source_type IN ('OperationalException','OperationalWorkItem')",
            name="ck_operational_sla_source_type",
        ),
        sa.CheckConstraint(
            "evaluation_status IN ('WITHIN','WARNING','BREACHED','MET')",
            name="ck_operational_sla_status",
        ),
        sa.CheckConstraint(
            "warning_at IS NULL OR (warning_at >= started_at AND warning_at < due_at)",
            name="ck_operational_sla_warning_at",
        ),
        sa.CheckConstraint("due_at > started_at", name="ck_operational_sla_due_at"),
        sa.CheckConstraint(
            "rule_version >= 1", name="ck_operational_sla_rule_version"
        ),
        sa.CheckConstraint("version >= 1", name="ck_operational_sla_version"),
        sa.ForeignKeyConstraint(
            ["rule_id", "organization_id"],
            ["organization_sla_rule.id", "organization_sla_rule.organization_id"],
            name="fk_operational_sla_rule_org",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["operational_shipment_id", "organization_id"],
            ["operational_shipment.id", "operational_shipment.organization_id"],
            name="fk_operational_sla_shipment_org",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["responsible_user_id"],
            ["expert_user.id"],
            name="fk_operational_sla_responsible_user",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "public_id", name="uq_operational_sla_commitment_public_id"
        ),
        sa.UniqueConstraint(
            "organization_id",
            "process_type",
            "source_public_id",
            name="uq_operational_sla_source",
        ),
    )
    op.create_index(
        "ix_operational_sla_shipment_status",
        "operational_sla_commitment",
        [
            "organization_id",
            "operational_shipment_id",
            "evaluation_status",
            "due_at",
        ],
    )


def downgrade():
    op.drop_index(
        "ix_operational_sla_shipment_status",
        table_name="operational_sla_commitment",
    )
    op.drop_table("operational_sla_commitment")
    op.drop_index(
        "ix_organization_sla_rule_active", table_name="organization_sla_rule"
    )
    op.drop_table("organization_sla_rule")

    # FOLLOW_UP rows cannot be represented by the predecessor schema. The
    # downgrade removes only Phase 2 Action records before restoring its
    # narrower WorkItem constraints.
    op.execute(
        sa.text("DELETE FROM operational_work_item WHERE work_type = 'FOLLOW_UP'")
    )

    with op.batch_alter_table("operational_work_item", schema=None) as batch_op:
        batch_op.drop_constraint(
            "uq_operational_work_item_public_id", type_="unique"
        )
        batch_op.drop_constraint(
            "fk_work_item_created_by_user", type_="foreignkey"
        )
        batch_op.drop_constraint(
            "fk_work_item_exception_same_shipment", type_="foreignkey"
        )
        batch_op.drop_constraint(
            "ck_operational_work_item_follow_up_context", type_="check"
        )
        batch_op.drop_constraint(
            "ck_operational_work_item_process_type", type_="check"
        )
        batch_op.drop_constraint(
            "ck_operational_work_item_action_context", type_="check"
        )
        batch_op.drop_constraint(
            "ck_operational_work_item_owner_scope", type_="check"
        )
        batch_op.drop_constraint(
            "ck_operational_work_item_type", type_="check"
        )
        for column in (
            "updated_at",
            "created_by_user_id",
            "latest_follow_up_at",
            "latest_follow_up",
            "expected_result",
            "process_type",
            "action_context_type",
            "exception_id",
            "public_id",
        ):
            batch_op.drop_column(column)
        batch_op.create_check_constraint(
            "ck_operational_work_item_type",
            "work_type IN ('OVERDUE_MILESTONE','CHECKPOINT_OVERDUE','ROUTE_DEPENDENCY_BLOCKED','REPLAN_REQUIRED')",
        )
        batch_op.create_check_constraint(
            "ck_operational_work_item_owner_scope",
            "(work_type = 'OVERDUE_MILESTONE' AND milestone_id IS NOT NULL AND route_plan_id IS NULL AND checkpoint_id IS NULL) "
            "OR (work_type IN ('CHECKPOINT_OVERDUE','ROUTE_DEPENDENCY_BLOCKED','REPLAN_REQUIRED') "
            "AND milestone_id IS NULL AND route_plan_id IS NOT NULL AND checkpoint_id IS NOT NULL)",
        )

    with op.batch_alter_table("operational_exception", schema=None) as batch_op:
        batch_op.drop_constraint("uq_exception_id_shipment", type_="unique")
        batch_op.drop_column("evidence_summary")
        batch_op.drop_column("impact_summary")

