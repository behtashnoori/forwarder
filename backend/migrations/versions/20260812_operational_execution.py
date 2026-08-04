"""Bounded operational execution foundation (Release 1.9.0).

Revision ID: 20260812_operational_execution
Revises: security_credential_remediation
"""

from alembic import op
import sqlalchemy as sa

revision = "20260812_operational_execution"
down_revision = "security_credential_remediation"
branch_labels = None
depends_on = None


def upgrade():
    for column in (
        sa.Column("public_id", sa.String(36), nullable=True),
        sa.Column("organization_id", sa.BigInteger(), nullable=True),
        sa.Column("operational_shipment_id", sa.BigInteger(), nullable=True),
        sa.Column("project_milestone_definition_id", sa.BigInteger(), nullable=True),
        sa.Column("milestone_type_snapshot", sa.JSON(), nullable=True),
        sa.Column("expected_point_id", sa.BigInteger(), nullable=True),
        sa.Column("expected_point_snapshot", sa.JSON(), nullable=True),
        sa.Column("target_metadata", sa.JSON(), nullable=True),
        sa.Column("sequence", sa.Integer(), nullable=True),
        sa.Column(
            "lifecycle_status", sa.String(20), nullable=False, server_default="PENDING"
        ),
        sa.Column("prior_active_status", sa.String(20), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("skipped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("blocked_at", sa.DateTime(timezone=True), nullable=True),
    ):
        op.add_column("operational_milestone", column)
    op.execute(
        "UPDATE operational_milestone SET public_id = gen_random_uuid()::text WHERE public_id IS NULL"
    )
    op.execute(
        "UPDATE operational_milestone m SET operational_shipment_id=p.operational_shipment_id, organization_id=s.organization_id FROM route_plan p JOIN operational_shipment s ON s.id=p.operational_shipment_id WHERE m.route_plan_id=p.id"
    )
    op.alter_column("operational_milestone", "public_id", nullable=False)
    op.alter_column("operational_milestone", "organization_id", nullable=False)
    op.alter_column("operational_milestone", "operational_shipment_id", nullable=False)
    op.alter_column("operational_milestone", "planned_at", nullable=True)
    op.drop_constraint(
        "ck_operational_milestone_type", "operational_milestone", type_="check"
    )
    op.drop_constraint(
        "ck_operational_milestone_single_owner", "operational_milestone", type_="check"
    )
    op.create_check_constraint(
        "ck_operational_milestone_type",
        "operational_milestone",
        "length(trim(milestone_type)) > 0",
    )
    op.create_check_constraint(
        "ck_operational_milestone_lifecycle",
        "operational_milestone",
        "lifecycle_status IN ('PENDING','READY','IN_PROGRESS','COMPLETED','SKIPPED','CANCELLED','BLOCKED')",
    )
    op.create_check_constraint(
        "ck_operational_milestone_sequence",
        "operational_milestone",
        "sequence IS NULL OR sequence >= 1",
    )
    op.create_check_constraint(
        "ck_operational_milestone_single_owner",
        "operational_milestone",
        "(route_leg_id IS NOT NULL AND checkpoint_id IS NULL) OR (route_leg_id IS NULL AND checkpoint_id IS NOT NULL) OR (route_leg_id IS NULL AND checkpoint_id IS NULL AND project_milestone_definition_id IS NOT NULL)",
    )
    op.create_unique_constraint(
        "uq_operational_milestone_public_id", "operational_milestone", ["public_id"]
    )
    op.create_unique_constraint(
        "uq_operational_milestone_id_shipment",
        "operational_milestone",
        ["id", "operational_shipment_id"],
    )
    op.create_unique_constraint(
        "uq_operational_milestone_definition_lineage",
        "operational_milestone",
        ["operational_shipment_id", "project_milestone_definition_id"],
    )
    op.create_foreign_key(
        "fk_operational_milestone_shipment_org",
        "operational_milestone",
        "operational_shipment",
        ["operational_shipment_id", "organization_id"],
        ["id", "organization_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_operational_milestone_definition",
        "operational_milestone",
        "project_milestone_definition",
        ["project_milestone_definition_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_operational_milestone_expected_point",
        "operational_milestone",
        "project_logistics_point",
        ["expected_point_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_operational_milestone_shipment_sequence",
        "operational_milestone",
        ["organization_id", "operational_shipment_id", "sequence"],
    )

    for column in (
        sa.Column("public_id", sa.String(36), nullable=True),
        sa.Column("organization_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "source_channel",
            sa.String(32),
            nullable=False,
            server_default="internal_ui",
        ),
        sa.Column("event_location_id", sa.BigInteger(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "verification_state",
            sa.String(20),
            nullable=False,
            server_default="unverified",
        ),
        sa.Column("verified_by_user_id", sa.BigInteger(), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
    ):
        op.add_column("milestone_event", column)
    op.execute(
        "UPDATE milestone_event e SET public_id=gen_random_uuid()::text, organization_id=m.organization_id FROM operational_milestone m WHERE e.milestone_id=m.id"
    )
    op.alter_column("milestone_event", "public_id", nullable=False)
    op.alter_column("milestone_event", "organization_id", nullable=False)
    op.drop_constraint("ck_milestone_event_type", "milestone_event", type_="check")
    op.drop_constraint(
        "ck_milestone_event_correction", "milestone_event", type_="check"
    )
    op.create_check_constraint(
        "ck_milestone_event_type",
        "milestone_event",
        "event_type IN ('reported','verified','corrected','INITIALIZED','READY','STARTED','COMPLETED','SKIPPED','CANCELLED','BLOCKED','UNBLOCKED','CORRECTED','REOPENED','VERIFIED')",
    )
    op.create_check_constraint(
        "ck_milestone_event_correction",
        "milestone_event",
        "event_type NOT IN ('corrected','CORRECTED') OR (reason IS NOT NULL AND length(trim(reason)) > 0 AND supersedes_event_id IS NOT NULL)",
    )
    op.create_unique_constraint(
        "uq_milestone_event_public_id", "milestone_event", ["public_id"]
    )
    op.create_foreign_key(
        "fk_milestone_event_org",
        "milestone_event",
        "operational_organization",
        ["organization_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_milestone_event_location",
        "milestone_event",
        "project_logistics_point",
        ["event_location_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_milestone_event_verifier",
        "milestone_event",
        "expert_user",
        ["verified_by_user_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    def reason_columns():
        return [
            sa.Column("id", sa.BigInteger(), primary_key=True),
            sa.Column("public_id", sa.String(36), nullable=False, unique=True),
            sa.Column("organization_id", sa.BigInteger(), nullable=False),
            sa.Column("immutable_code", sa.String(64), nullable=False),
            sa.Column("fa_name", sa.String(160), nullable=False),
            sa.Column("en_name", sa.String(160), nullable=False),
            sa.Column("definition", sa.Text()),
            sa.Column(
                "display_order", sa.Integer(), nullable=False, server_default="0"
            ),
            sa.Column(
                "is_active", sa.Boolean(), nullable=False, server_default=sa.true()
            ),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("created_by_user_id", sa.BigInteger(), nullable=False),
            sa.Column("updated_by_user_id", sa.BigInteger(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        ]

    for table in ("delay_reason", "exception_reason"):
        op.create_table(
            table,
            *reason_columns(),
            sa.ForeignKeyConstraint(
                ["organization_id"],
                ["operational_organization.id"],
                ondelete="RESTRICT",
            ),
            sa.ForeignKeyConstraint(
                ["created_by_user_id"], ["expert_user.id"], ondelete="RESTRICT"
            ),
            sa.ForeignKeyConstraint(
                ["updated_by_user_id"], ["expert_user.id"], ondelete="RESTRICT"
            ),
            sa.UniqueConstraint(
                "organization_id", "immutable_code", name=f"uq_{table}_org_code"
            ),
            sa.UniqueConstraint("id", "organization_id", name=f"uq_{table}_id_org"),
            sa.CheckConstraint("version >= 1", name=f"ck_{table}_version"),
        )
        op.create_index(
            f"ix_{table}_org_active_order",
            table,
            ["organization_id", "is_active", "display_order"],
        )
    for table, reason, instant in (
        ("operational_delay", "delay_reason", "started_at"),
        ("operational_exception", "exception_reason", "occurred_at"),
    ):
        op.create_table(
            table,
            sa.Column("id", sa.BigInteger(), primary_key=True),
            sa.Column("public_id", sa.String(36), nullable=False, unique=True),
            sa.Column("organization_id", sa.BigInteger(), nullable=False),
            sa.Column("operational_shipment_id", sa.BigInteger(), nullable=False),
            sa.Column("milestone_id", sa.BigInteger()),
            sa.Column("reason_id", sa.BigInteger(), nullable=False),
            sa.Column(instant, sa.DateTime(timezone=True), nullable=False),
            sa.Column("resolved_at", sa.DateTime(timezone=True)),
            sa.Column("note", sa.Text()),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("created_by_user_id", sa.BigInteger(), nullable=False),
            sa.Column("resolved_by_user_id", sa.BigInteger()),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.ForeignKeyConstraint(
                ["operational_shipment_id", "organization_id"],
                ["operational_shipment.id", "operational_shipment.organization_id"],
                ondelete="RESTRICT",
            ),
            sa.ForeignKeyConstraint(
                ["milestone_id", "operational_shipment_id"],
                [
                    "operational_milestone.id",
                    "operational_milestone.operational_shipment_id",
                ],
                ondelete="RESTRICT",
            ),
            sa.ForeignKeyConstraint(
                ["reason_id", "organization_id"],
                [f"{reason}.id", f"{reason}.organization_id"],
                ondelete="RESTRICT",
            ),
            sa.ForeignKeyConstraint(
                ["created_by_user_id"], ["expert_user.id"], ondelete="RESTRICT"
            ),
            sa.ForeignKeyConstraint(
                ["resolved_by_user_id"], ["expert_user.id"], ondelete="RESTRICT"
            ),
            sa.CheckConstraint(
                f"resolved_at IS NULL OR resolved_at >= {instant}",
                name=f"ck_{'delay' if table.endswith('delay') else 'exception'}_timestamps",
            ),
            sa.CheckConstraint(
                "version >= 1",
                name=f"ck_{'delay' if table.endswith('delay') else 'exception'}_version",
            ),
        )
        op.create_index(
            f"ix_{'delay' if table.endswith('delay') else 'exception'}_org_shipment_active",
            table,
            ["organization_id", "operational_shipment_id", "resolved_at"],
        )


def downgrade():
    op.drop_table("operational_exception")
    op.drop_table("operational_delay")
    op.drop_table("exception_reason")
    op.drop_table("delay_reason")
    op.drop_constraint(
        "fk_milestone_event_verifier", "milestone_event", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_milestone_event_location", "milestone_event", type_="foreignkey"
    )
    op.drop_constraint("fk_milestone_event_org", "milestone_event", type_="foreignkey")
    op.drop_constraint(
        "uq_milestone_event_public_id", "milestone_event", type_="unique"
    )
    op.drop_constraint(
        "ck_milestone_event_correction", "milestone_event", type_="check"
    )
    op.drop_constraint("ck_milestone_event_type", "milestone_event", type_="check")
    op.create_check_constraint(
        "ck_milestone_event_type",
        "milestone_event",
        "event_type IN ('reported','verified','corrected')",
    )
    op.create_check_constraint(
        "ck_milestone_event_correction",
        "milestone_event",
        "event_type <> 'corrected' OR (reason IS NOT NULL AND length(trim(reason)) > 0 AND supersedes_event_id IS NOT NULL)",
    )
    for name in (
        "verified_at",
        "verified_by_user_id",
        "verification_state",
        "note",
        "event_location_id",
        "source_channel",
        "organization_id",
        "public_id",
    ):
        op.drop_column("milestone_event", name)
    op.drop_index(
        "ix_operational_milestone_shipment_sequence", table_name="operational_milestone"
    )
    op.drop_constraint(
        "fk_operational_milestone_expected_point",
        "operational_milestone",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_operational_milestone_definition",
        "operational_milestone",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_operational_milestone_shipment_org",
        "operational_milestone",
        type_="foreignkey",
    )
    op.drop_constraint(
        "uq_operational_milestone_definition_lineage",
        "operational_milestone",
        type_="unique",
    )
    op.drop_constraint(
        "uq_operational_milestone_id_shipment", "operational_milestone", type_="unique"
    )
    op.drop_constraint(
        "uq_operational_milestone_public_id", "operational_milestone", type_="unique"
    )
    op.drop_constraint(
        "ck_operational_milestone_sequence", "operational_milestone", type_="check"
    )
    op.drop_constraint(
        "ck_operational_milestone_lifecycle", "operational_milestone", type_="check"
    )
    op.drop_constraint(
        "ck_operational_milestone_single_owner", "operational_milestone", type_="check"
    )
    op.drop_constraint(
        "ck_operational_milestone_type", "operational_milestone", type_="check"
    )
    op.create_check_constraint(
        "ck_operational_milestone_type",
        "operational_milestone",
        "milestone_type IN ('departure','arrival','checkpoint_arrival','checkpoint_processing_complete','checkpoint_departure')",
    )
    op.create_check_constraint(
        "ck_operational_milestone_single_owner",
        "operational_milestone",
        "(route_leg_id IS NOT NULL AND checkpoint_id IS NULL) OR (route_leg_id IS NULL AND checkpoint_id IS NOT NULL)",
    )
    op.alter_column("operational_milestone", "planned_at", nullable=False)
    for name in (
        "blocked_at",
        "cancelled_at",
        "skipped_at",
        "completed_at",
        "started_at",
        "prior_active_status",
        "lifecycle_status",
        "sequence",
        "target_metadata",
        "expected_point_snapshot",
        "expected_point_id",
        "milestone_type_snapshot",
        "project_milestone_definition_id",
        "operational_shipment_id",
        "organization_id",
        "public_id",
    ):
        op.drop_column("operational_milestone", name)
