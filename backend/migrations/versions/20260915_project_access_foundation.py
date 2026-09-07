"""Explicit tenant-consistent Project user access."""
from alembic import op
import sqlalchemy as sa

revision = "20260915_project_access_foundation"
down_revision = "20260914_saved_view_persistence"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "project_access",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False, unique=True),
        sa.Column("organization_id", sa.BigInteger(), nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("created_by_user_id", sa.BigInteger(), sa.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id", "organization_id"], ["project.id", "project.organization_id"], name="fk_project_access_project_org", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id", "user_id"], ["operational_membership.organization_id", "operational_membership.user_id"], name="fk_project_access_membership_org_user", ondelete="CASCADE"),
        sa.UniqueConstraint("organization_id", "project_id", "user_id", name="uq_project_access_org_project_user"),
    )
    op.create_index("ix_project_access_org_user", "project_access", ["organization_id", "user_id"])
    op.create_index("ix_project_access_project", "project_access", ["project_id"])


def downgrade():
    op.drop_index("ix_project_access_project", table_name="project_access")
    op.drop_index("ix_project_access_org_user", table_name="project_access")
    op.drop_table("project_access")
