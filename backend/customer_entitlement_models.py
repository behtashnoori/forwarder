"""DN10 explicit grants; revocation closes a grant, regrant creates a new fact."""
from uuid import uuid4

from sqlalchemy import text

from backend.extensions import db
from backend.operational_models import BIGINT, utcnow


class CustomerEntitlement(db.Model):
    __tablename__ = "customer_entitlement"
    __table_args__ = (
        db.UniqueConstraint("organization_id", "command_key", name="uq_customer_entitlement_command"),
        db.ForeignKeyConstraint(
            ["portal_account_id", "organization_id"],
            ["customer_gamification.id", "customer_gamification.operational_organization_id"],
            name="fk_customer_entitlement_account_org", ondelete="RESTRICT",
        ),
        db.ForeignKeyConstraint(
            ["customer_id", "organization_id"],
            ["customer.id", "customer.operational_organization_id"],
            name="fk_customer_entitlement_customer_org", ondelete="RESTRICT",
        ),
        db.CheckConstraint(
            "(revoked_at IS NULL AND revoked_by IS NULL) OR "
            "(revoked_at IS NOT NULL AND revoked_by IS NOT NULL AND revoked_at >= granted_at)",
            name="ck_customer_entitlement_revocation",
        ),
        db.Index("uq_customer_entitlement_current", "organization_id", "portal_account_id", "customer_id",
                 unique=True, postgresql_where=text("revoked_at IS NULL"), sqlite_where=text("revoked_at IS NULL")),
    )
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, unique=True, default=lambda: str(uuid4()))
    organization_id = db.Column(BIGINT, db.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=False)
    portal_account_id = db.Column(BIGINT, nullable=False)
    customer_id = db.Column(BIGINT, nullable=False)
    command_key = db.Column(db.String(100), nullable=False)
    granted_by = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False)
    granted_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    revoked_by = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"))
    revoked_at = db.Column(db.DateTime(timezone=True))
