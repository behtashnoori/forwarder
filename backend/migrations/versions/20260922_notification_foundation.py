"""Add the dormant, channel-neutral notification persistence foundation.

Revision ID: 20260922_notification_foundation
Revises: 20260921_shipment_evidence_ownership
"""
from alembic import op
import sqlalchemy as sa


revision = "20260922_notification_foundation"
down_revision = "20260921_shipment_evidence_ownership"
branch_labels = None
depends_on = None

BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade():
    with op.batch_alter_table("operational_outbox") as batch_op:
        batch_op.create_unique_constraint(
            "uq_operational_outbox_tenant", ["id", "organization_id"]
        )

    op.create_table(
        "notification_action",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column(
            "organization_id",
            BIGINT,
            sa.ForeignKey("operational_organization.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("source_event_id", BIGINT, nullable=True),
        sa.Column("idempotency_key", sa.String(160), nullable=False),
        sa.Column("correlation_key", sa.String(160), nullable=True),
        sa.Column("purpose", sa.String(80), nullable=False),
        sa.Column(
            "status", sa.String(20), nullable=False, server_default="PENDING"
        ),
        sa.Column("recipient_reference", sa.String(255), nullable=True),
        sa.Column("channel", sa.String(32), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("public_id", name="uq_notification_action_public_id"),
        sa.UniqueConstraint(
            "id", "organization_id", name="uq_notification_action_tenant"
        ),
        sa.UniqueConstraint(
            "organization_id",
            "idempotency_key",
            name="uq_notification_action_idempotency",
        ),
        sa.ForeignKeyConstraint(
            ["source_event_id", "organization_id"],
            ["operational_outbox.id", "operational_outbox.organization_id"],
            name="fk_notification_action_source_event_tenant",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "status IN ('PENDING','IN_PROGRESS','COMPLETED','FAILED','CANCELLED')",
            name="ck_notification_action_status",
        ),
    )
    op.create_index(
        "ix_notification_action_org_status",
        "notification_action",
        ["organization_id", "status", "created_at"],
    )
    op.create_index(
        "ix_notification_action_correlation",
        "notification_action",
        ["organization_id", "correlation_key"],
    )

    op.create_table(
        "notification_attempt",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column(
            "organization_id",
            BIGINT,
            sa.ForeignKey("operational_organization.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("action_id", BIGINT, nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column(
            "status", sa.String(20), nullable=False, server_default="PENDING"
        ),
        sa.Column("channel", sa.String(32), nullable=True),
        sa.Column("provider", sa.String(80), nullable=True),
        sa.Column("provider_reference", sa.String(160), nullable=True),
        sa.Column("result_code", sa.String(80), nullable=True),
        sa.Column("failure_code", sa.String(80), nullable=True),
        sa.Column("failure_summary", sa.String(255), nullable=True),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("public_id", name="uq_notification_attempt_public_id"),
        sa.UniqueConstraint(
            "action_id",
            "attempt_number",
            name="uq_notification_attempt_number",
        ),
        sa.ForeignKeyConstraint(
            ["action_id", "organization_id"],
            ["notification_action.id", "notification_action.organization_id"],
            name="fk_notification_attempt_action_tenant",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "attempt_number >= 1", name="ck_notification_attempt_number_positive"
        ),
        sa.CheckConstraint(
            "status IN ('PENDING','IN_PROGRESS','SUCCEEDED','FAILED','UNKNOWN')",
            name="ck_notification_attempt_status",
        ),
    )
    op.create_index(
        "ix_notification_attempt_org_status",
        "notification_attempt",
        ["organization_id", "status", "created_at"],
    )


def downgrade():
    bind = op.get_bind()
    action_count = bind.execute(
        sa.text("SELECT COUNT(*) FROM notification_action")
    ).scalar_one()
    attempt_count = bind.execute(
        sa.text("SELECT COUNT(*) FROM notification_attempt")
    ).scalar_one()
    if action_count or attempt_count:
        raise RuntimeError(
            "Cannot downgrade while notification foundation history exists."
        )

    op.drop_index(
        "ix_notification_attempt_org_status", table_name="notification_attempt"
    )
    op.drop_table("notification_attempt")
    op.drop_index(
        "ix_notification_action_correlation", table_name="notification_action"
    )
    op.drop_index(
        "ix_notification_action_org_status", table_name="notification_action"
    )
    op.drop_table("notification_action")
    with op.batch_alter_table("operational_outbox") as batch_op:
        batch_op.drop_constraint("uq_operational_outbox_tenant", type_="unique")
