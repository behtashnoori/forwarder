"""DN10 explicit auditable account-to-CRM entitlement, without inferred backfill."""
from alembic import op
import sqlalchemy as sa

revision = "20261006_customer_entitlement"
down_revision = "20261005_phase3_contextual_documents"
branch_labels = None
depends_on = None
BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade():
    op.create_unique_constraint("uq_customer_portal_id_org", "customer_gamification", ["id", "operational_organization_id"])
    op.create_table(
        "customer_entitlement",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False, unique=True),
        sa.Column("organization_id", BIGINT, sa.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("portal_account_id", BIGINT, nullable=False),
        sa.Column("customer_id", BIGINT, nullable=False),
        sa.Column("command_key", sa.String(100), nullable=False),
        sa.UniqueConstraint("organization_id", "command_key", name="uq_customer_entitlement_command"),
        sa.Column("granted_by", BIGINT, sa.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("revoked_by", BIGINT, sa.ForeignKey("expert_user.id", ondelete="RESTRICT")),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["portal_account_id", "organization_id"],
                                ["customer_gamification.id", "customer_gamification.operational_organization_id"],
                                name="fk_customer_entitlement_account_org", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["customer_id", "organization_id"],
                                ["customer.id", "customer.operational_organization_id"],
                                name="fk_customer_entitlement_customer_org", ondelete="RESTRICT"),
        sa.CheckConstraint("(revoked_at IS NULL AND revoked_by IS NULL) OR "
                           "(revoked_at IS NOT NULL AND revoked_by IS NOT NULL AND revoked_at >= granted_at)",
                           name="ck_customer_entitlement_revocation"),
    )
    op.create_index("uq_customer_entitlement_current", "customer_entitlement",
                    ["organization_id", "portal_account_id", "customer_id"], unique=True,
                    postgresql_where=sa.text("revoked_at IS NULL"), sqlite_where=sa.text("revoked_at IS NULL"))


def downgrade():
    if op.get_bind().execute(sa.text("SELECT 1 FROM customer_entitlement LIMIT 1")).first():
        raise RuntimeError("DN10 entitlement history exists; downgrade would erase authorization evidence")
    op.drop_table("customer_entitlement")
    op.drop_constraint("uq_customer_portal_id_org", "customer_gamification", type_="unique")
