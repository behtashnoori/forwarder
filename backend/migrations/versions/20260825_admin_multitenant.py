"""Explicit admin authority and tenant-scoped policy. Revision ID: 20260825_admin_multitenant"""
from alembic import op
import sqlalchemy as sa
revision="20260825_admin_multitenant"; down_revision="20260824_mt1_graph"; branch_labels=None; depends_on=None
BIGINT=sa.BigInteger()
def upgrade():
    op.add_column("expert_user",sa.Column("authority",sa.String(32),nullable=False,server_default="EXPERT"))
    op.create_check_constraint("ck_expert_user_authority","expert_user","authority IN ('PLATFORM_ADMIN','ORGANIZATION_ADMIN','EXPERT')")
    op.execute("UPDATE expert_user SET authority='ORGANIZATION_ADMIN' WHERE role='admin' AND id IN (SELECT user_id FROM operational_membership WHERE is_active=true GROUP BY user_id HAVING count(*)=1)")
    for table in ("assignment_rule","referral_rule","referral_rule_state","referral_auto_assign_state"):
        op.add_column(table,sa.Column("operational_organization_id",BIGINT,nullable=True)); op.create_index(f"ix_{table}_operational_organization_id",table,["operational_organization_id"]); op.create_foreign_key(f"fk_{table}_operational_organization_id",table,"operational_organization",["operational_organization_id"],["id"],ondelete="RESTRICT")
    op.execute("UPDATE assignment_rule r SET operational_organization_id=(SELECT min(m.organization_id) FROM operational_membership m WHERE m.user_id=r.created_by AND m.is_active=true HAVING count(*)=1)")
    op.execute("UPDATE referral_rule r SET operational_organization_id=(SELECT min(m.organization_id) FROM operational_membership m WHERE m.user_id=r.created_by AND m.is_active=true HAVING count(*)=1)")
    op.execute("UPDATE referral_rule_state s SET operational_organization_id=(SELECT r.operational_organization_id FROM referral_rule r WHERE r.id=s.rule_id)")
    op.create_unique_constraint("uq_referral_auto_assign_state_org","referral_auto_assign_state",["operational_organization_id"])
def downgrade():
    op.drop_constraint("uq_referral_auto_assign_state_org","referral_auto_assign_state",type_="unique")
    for table in reversed(("assignment_rule","referral_rule","referral_rule_state","referral_auto_assign_state")):
        op.drop_constraint(f"fk_{table}_operational_organization_id",table,type_="foreignkey"); op.drop_index(f"ix_{table}_operational_organization_id",table_name=table); op.drop_column(table,"operational_organization_id")
    op.drop_constraint("ck_expert_user_authority","expert_user",type_="check"); op.drop_column("expert_user","authority")
