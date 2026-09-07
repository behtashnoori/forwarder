"""Private personal Saved View persistence."""
from alembic import op
import sqlalchemy as sa

revision = "20260914_saved_view_persistence"
down_revision = "20260913_dashboard_persistence"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("saved_view", sa.Column("id", sa.BigInteger(), primary_key=True), sa.Column("public_id", sa.String(36), nullable=False, unique=True), sa.Column("organization_id", sa.BigInteger(), sa.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=False), sa.Column("owner_user_id", sa.BigInteger(), sa.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False), sa.Column("name", sa.String(120), nullable=False), sa.Column("description", sa.String(1000), nullable=False), sa.Column("visibility", sa.String(16), nullable=False), sa.Column("status", sa.String(16), nullable=False), sa.Column("semantic_version", sa.String(64), nullable=False), sa.Column("saved_view_schema_version", sa.String(64), nullable=False), sa.Column("definition_json", sa.JSON(), nullable=False), sa.Column("version", sa.Integer(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.Column("created_by", sa.BigInteger(), sa.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False), sa.Column("updated_by", sa.BigInteger(), sa.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False), sa.CheckConstraint("visibility = 'PRIVATE'", name="ck_saved_view_private_only"), sa.CheckConstraint("status IN ('ACTIVE','ARCHIVED')", name="ck_saved_view_status"), sa.CheckConstraint("version >= 1", name="ck_saved_view_version_positive"))
    op.create_index("ix_saved_view_org_owner_status", "saved_view", ["organization_id", "owner_user_id", "status"])
    op.create_table("saved_view_revision", sa.Column("id", sa.BigInteger(), primary_key=True), sa.Column("saved_view_id", sa.BigInteger(), sa.ForeignKey("saved_view.id", ondelete="RESTRICT"), nullable=False), sa.Column("revision_number", sa.Integer(), nullable=False), sa.Column("definition_json", sa.JSON(), nullable=False), sa.Column("semantic_version", sa.String(64), nullable=False), sa.Column("saved_view_schema_version", sa.String(64), nullable=False), sa.Column("name_snapshot", sa.String(120), nullable=False), sa.Column("description_snapshot", sa.String(1000), nullable=False), sa.Column("changed_by", sa.BigInteger(), sa.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False), sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False), sa.Column("change_reason", sa.String(255)), sa.UniqueConstraint("saved_view_id", "revision_number", name="uq_saved_view_revision_number"))
    op.create_index("ix_saved_view_revision_saved_view_id", "saved_view_revision", ["saved_view_id"])


def downgrade():
    op.drop_index("ix_saved_view_revision_saved_view_id", table_name="saved_view_revision"); op.drop_table("saved_view_revision")
    op.drop_index("ix_saved_view_org_owner_status", table_name="saved_view"); op.drop_table("saved_view")
