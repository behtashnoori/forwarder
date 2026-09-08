"""Grant the accepted Personal Dashboard capabilities to canonical tenant users."""
from alembic import op
import sqlalchemy as sa

revision = "20260916_personal_dashboard_permissions"
down_revision = "20260915_project_access_foundation"
branch_labels = None
depends_on = None

GRANTS = ("personal_dashboard.manage", "personal_dashboard.read")


def upgrade():
    op.create_table(
        "personal_dashboard_permission_grant",
        sa.Column("membership_id", sa.BigInteger(), nullable=False),
        sa.Column("permission", sa.String(80), nullable=False),
        sa.ForeignKeyConstraint(["membership_id"], ["operational_membership.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("membership_id", "permission"),
    )
    bind = op.get_bind()
    metadata = sa.MetaData()
    membership = sa.Table("operational_membership", metadata, autoload_with=bind)
    user = sa.Table("expert_user", metadata, autoload_with=bind)
    audit = sa.Table("personal_dashboard_permission_grant", metadata, autoload_with=bind)
    active_membership = membership.alias("active_membership")
    active_count = sa.select(sa.func.count()).where(
        active_membership.c.user_id == user.c.id,
        active_membership.c.is_active.is_(True),
    ).correlate(user).scalar_subquery()
    rows = bind.execute(
        sa.select(membership.c.id, membership.c.permissions)
        .join(user, user.c.id == membership.c.user_id)
        .where(
            membership.c.is_active.is_(True),
            user.c.is_active.is_(True),
            user.c.authority.in_(("ORGANIZATION_ADMIN", "EXPERT")),
            active_count == 1,
        )
    ).all()
    for membership_id, current in rows:
        permissions = list(current or [])
        introduced = [key for key in GRANTS if key not in permissions]
        if not introduced:
            continue
        bind.execute(audit.insert(), [{"membership_id": membership_id, "permission": key} for key in introduced])
        bind.execute(membership.update().where(membership.c.id == membership_id).values(permissions=sorted(set(permissions) | set(introduced))))


def downgrade():
    bind = op.get_bind()
    metadata = sa.MetaData()
    membership = sa.Table("operational_membership", metadata, autoload_with=bind)
    audit = sa.Table("personal_dashboard_permission_grant", metadata, autoload_with=bind)
    for membership_id, permission in bind.execute(sa.select(audit.c.membership_id, audit.c.permission)).all():
        current = bind.execute(sa.select(membership.c.permissions).where(membership.c.id == membership_id)).scalar_one_or_none()
        if current is not None:
            bind.execute(membership.update().where(membership.c.id == membership_id).values(permissions=[key for key in (current or []) if key != permission]))
    op.drop_table("personal_dashboard_permission_grant")
