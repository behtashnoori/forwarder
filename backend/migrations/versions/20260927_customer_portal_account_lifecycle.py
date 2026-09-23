"""Add optional Customer Portal credentials, lifecycle, and recovery core.

Revision ID: 20260927_customer_portal_account_lifecycle
Revises: 20260926_fixed_shipment_responsible_expert
"""

from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision = "20260927_customer_portal_account_lifecycle"
down_revision = "20260926_fixed_shipment_responsible_expert"
branch_labels = None
depends_on = None

BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade():
    with op.batch_alter_table("customer_gamification", schema=None) as batch_op:
        batch_op.add_column(sa.Column("public_id", sa.String(36), nullable=True))
        batch_op.add_column(sa.Column("password_hash", sa.String(256), nullable=True))
        batch_op.add_column(
            sa.Column(
                "account_status",
                sa.String(16),
                nullable=False,
                server_default="ACTIVE",
            )
        )
        batch_op.add_column(
            sa.Column(
                "session_generation",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )
        batch_op.add_column(sa.Column("password_changed_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("disabled_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("disabled_by_user_id", BIGINT, nullable=True))
        batch_op.add_column(
            sa.Column("operational_organization_id", BIGINT, nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_customer_portal_disabled_by_user",
            "expert_user",
            ["disabled_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_customer_portal_operational_organization",
            "operational_organization",
            ["operational_organization_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_index(
            "ix_customer_gamification_operational_organization_id",
            ["operational_organization_id"],
            unique=False,
        )

    bind = op.get_bind()
    customer = sa.table(
        "customer_gamification",
        sa.column("id", BIGINT),
        sa.column("public_id", sa.String(36)),
    )
    for customer_id in bind.execute(
        sa.select(customer.c.id).where(customer.c.public_id.is_(None)).order_by(customer.c.id)
    ).scalars():
        bind.execute(
            customer.update()
            .where(customer.c.id == customer_id)
            .values(public_id=str(uuid4()))
        )

    with op.batch_alter_table("customer_gamification", schema=None) as batch_op:
        batch_op.alter_column(
            "public_id", existing_type=sa.String(36), nullable=False
        )
        batch_op.create_unique_constraint(
            "uq_customer_gamification_public_id", ["public_id"]
        )
        batch_op.create_check_constraint(
            "ck_customer_portal_account_status",
            "account_status IN ('ACTIVE', 'DISABLED')",
        )
        batch_op.create_check_constraint(
            "ck_customer_portal_session_generation_nonnegative",
            "session_generation >= 0",
        )

    op.create_table(
        "customer_portal_recovery_request",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column("customer_id", BIGINT, nullable=False),
        sa.Column("requested_at", sa.DateTime(), nullable=False),
        sa.Column("handled_at", sa.DateTime(), nullable=True),
        sa.Column("purpose", sa.String(16), server_default="RESET", nullable=False),
        sa.Column("delivery_channel", sa.String(16), server_default="EMAIL", nullable=False),
        sa.Column("delivery_status", sa.String(24), server_default="PENDING", nullable=False),
        sa.Column("delivery_attempted_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "purpose IN ('RESET', 'ENROLLMENT')",
            name="ck_customer_portal_recovery_request_purpose",
        ),
        sa.CheckConstraint(
            "delivery_channel IN ('EMAIL', 'MANUAL_LINK')",
            name="ck_customer_portal_recovery_request_channel",
        ),
        sa.CheckConstraint(
            "delivery_status IN ('PENDING', 'SENT', 'FAILED', 'SUPPRESSED', 'MANUAL_ISSUED')",
            name="ck_customer_portal_recovery_request_status",
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"], ["customer_gamification.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "public_id", name="uq_customer_portal_recovery_request_public_id"
        ),
    )
    op.create_index(
        "ix_customer_portal_recovery_request_customer_id",
        "customer_portal_recovery_request",
        ["customer_id"],
        unique=False,
    )

    op.create_table(
        "customer_portal_recovery_token",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("token_digest", sa.String(64), nullable=False),
        sa.Column("customer_id", BIGINT, nullable=False),
        sa.Column("purpose", sa.String(16), nullable=False),
        sa.Column("recovery_request_id", BIGINT, nullable=True),
        sa.Column("created_by_user_id", BIGINT, nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "purpose IN ('RESET', 'ENROLLMENT')",
            name="ck_customer_portal_recovery_token_purpose",
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"], ["customer_gamification.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["recovery_request_id"],
            ["customer_portal_recovery_request.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["expert_user.id"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint(
            "token_digest", name="uq_customer_portal_recovery_token_digest"
        ),
    )
    op.create_index(
        "ix_customer_portal_recovery_token_customer_id",
        "customer_portal_recovery_token",
        ["customer_id"],
        unique=False,
    )
    op.create_index(
        "ix_customer_portal_recovery_token_expires_at",
        "customer_portal_recovery_token",
        ["expires_at"],
        unique=False,
    )

    op.create_table(
        "customer_portal_account_audit",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("customer_id", BIGINT, nullable=True),
        sa.Column("operational_organization_id", BIGINT, nullable=True),
        sa.Column("actor_user_id", BIGINT, nullable=True),
        sa.Column("action", sa.String(48), nullable=False),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("detail", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["customer_id"], ["customer_gamification.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["operational_organization_id"],
            ["operational_organization.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"], ["expert_user.id"], ondelete="SET NULL"
        ),
    )
    op.create_index(
        "ix_customer_portal_account_audit_customer_id",
        "customer_portal_account_audit",
        ["customer_id"],
        unique=False,
    )
    op.create_index(
        "ix_customer_portal_account_audit_operational_organization_id",
        "customer_portal_account_audit",
        ["operational_organization_id"],
        unique=False,
    )

    with op.batch_alter_table("expert_quote", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "response_version", sa.Integer(), nullable=False, server_default="0"
            )
        )
        batch_op.create_check_constraint(
            "ck_expert_quote_response_version_nonnegative",
            "response_version >= 0",
        )


def downgrade():
    bind = op.get_bind()
    customer_evidence = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM customer_gamification "
            "WHERE password_hash IS NOT NULL OR account_status <> 'ACTIVE' "
            "OR session_generation <> 0 OR password_changed_at IS NOT NULL "
            "OR disabled_at IS NOT NULL OR disabled_by_user_id IS NOT NULL "
            "OR operational_organization_id IS NOT NULL"
        )
    ).scalar_one()
    recovery_evidence = bind.execute(
        sa.text(
            "SELECT "
            "(SELECT COUNT(*) FROM customer_portal_recovery_request) + "
            "(SELECT COUNT(*) FROM customer_portal_recovery_token) + "
            "(SELECT COUNT(*) FROM customer_portal_account_audit)"
        )
    ).scalar_one()
    response_evidence = bind.execute(
        sa.text("SELECT COUNT(*) FROM expert_quote WHERE response_version <> 0")
    ).scalar_one()
    if customer_evidence or recovery_evidence or response_evidence:
        raise RuntimeError(
            "Cannot downgrade while Customer Portal account, recovery, enrollment, "
            "or versioned Quote-response evidence exists."
        )

    with op.batch_alter_table("expert_quote", schema=None) as batch_op:
        batch_op.drop_constraint(
            "ck_expert_quote_response_version_nonnegative", type_="check"
        )
        batch_op.drop_column("response_version")

    op.drop_index(
        "ix_customer_portal_account_audit_operational_organization_id",
        table_name="customer_portal_account_audit",
    )
    op.drop_index(
        "ix_customer_portal_account_audit_customer_id",
        table_name="customer_portal_account_audit",
    )
    op.drop_table("customer_portal_account_audit")

    op.drop_index(
        "ix_customer_portal_recovery_token_expires_at",
        table_name="customer_portal_recovery_token",
    )
    op.drop_index(
        "ix_customer_portal_recovery_token_customer_id",
        table_name="customer_portal_recovery_token",
    )
    op.drop_table("customer_portal_recovery_token")
    op.drop_index(
        "ix_customer_portal_recovery_request_customer_id",
        table_name="customer_portal_recovery_request",
    )
    op.drop_table("customer_portal_recovery_request")

    with op.batch_alter_table("customer_gamification", schema=None) as batch_op:
        batch_op.drop_constraint(
            "ck_customer_portal_session_generation_nonnegative", type_="check"
        )
        batch_op.drop_constraint("ck_customer_portal_account_status", type_="check")
        batch_op.drop_constraint(
            "uq_customer_gamification_public_id", type_="unique"
        )
        batch_op.drop_constraint(
            "fk_customer_portal_disabled_by_user", type_="foreignkey"
        )
        batch_op.drop_index(
            "ix_customer_gamification_operational_organization_id"
        )
        batch_op.drop_constraint(
            "fk_customer_portal_operational_organization", type_="foreignkey"
        )
        batch_op.drop_column("operational_organization_id")
        batch_op.drop_column("disabled_by_user_id")
        batch_op.drop_column("disabled_at")
        batch_op.drop_column("password_changed_at")
        batch_op.drop_column("session_generation")
        batch_op.drop_column("account_status")
        batch_op.drop_column("password_hash")
        batch_op.drop_column("public_id")
