"""Organization closure policy and immutable completed-to-closed decisions."""
from uuid import uuid4
from sqlalchemy import event, inspect
from backend.extensions import db
from backend.operational_models import BIGINT, utcnow

MODES = ("GENERAL", "road", "rail", "sea", "air", "multimodal_transfer", "customs_handling")
CRITERIA = ("ACTUAL_QUANTITY_KNOWN", "ALL_CARGO_DELIVERED", "REQUIRED_DOCUMENTS_READY",
            "NO_OPEN_EXCEPTIONS", "NO_OPEN_FOLLOW_UPS", "NO_OPEN_OPERATIONAL_WORK")


class ClosurePolicy(db.Model):
    __tablename__ = "closure_policy"
    __table_args__ = (db.UniqueConstraint("id", "organization_id", name="uq_closure_policy_org"),)
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, unique=True, default=lambda: str(uuid4()))
    organization_id = db.Column(BIGINT, db.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=False, unique=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class ClosurePolicyVersion(db.Model):
    __tablename__ = "closure_policy_version"
    __table_args__ = (
        db.UniqueConstraint("id", "organization_id", name="uq_closure_version_org"),
        db.UniqueConstraint("policy_id", "version", name="uq_closure_version_number"),
        db.UniqueConstraint("policy_id", "effective_from", name="uq_closure_version_effective"),
        db.ForeignKeyConstraint(["policy_id", "organization_id"], ["closure_policy.id", "closure_policy.organization_id"], name="fk_closure_version_policy", ondelete="RESTRICT"),
        db.CheckConstraint("version >= 1", name="ck_closure_version_positive"),
    )
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, unique=True, default=lambda: str(uuid4()))
    organization_id = db.Column(BIGINT, nullable=False)
    policy_id = db.Column(BIGINT, nullable=False)
    version = db.Column(db.Integer, nullable=False)
    effective_from = db.Column(db.DateTime(timezone=True), nullable=False)
    actor_user_id = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False)
    recorded_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class ClosurePolicyCriterion(db.Model):
    __tablename__ = "closure_policy_criterion"
    __table_args__ = (
        db.ForeignKeyConstraint(["policy_version_id", "organization_id"], ["closure_policy_version.id", "closure_policy_version.organization_id"], name="fk_closure_criterion_version", ondelete="RESTRICT"),
        db.UniqueConstraint("policy_version_id", "scope", "code", name="uq_closure_criterion_identity"),
        db.CheckConstraint("scope IN ('GENERAL','road','rail','sea','air','multimodal_transfer','customs_handling')", name="ck_closure_criterion_scope"),
        db.CheckConstraint("code IN ('ACTUAL_QUANTITY_KNOWN','ALL_CARGO_DELIVERED','REQUIRED_DOCUMENTS_READY','NO_OPEN_EXCEPTIONS','NO_OPEN_FOLLOW_UPS','NO_OPEN_OPERATIONAL_WORK')", name="ck_closure_criterion_code"),
    )
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, unique=True, default=lambda: str(uuid4()))
    organization_id = db.Column(BIGINT, nullable=False)
    policy_version_id = db.Column(BIGINT, nullable=False)
    scope = db.Column(db.String(24), nullable=False)
    code = db.Column(db.String(40), nullable=False)
    mandatory = db.Column(db.Boolean, nullable=False)


class ClosureDecision(db.Model):
    __tablename__ = "shipment_closure_decision"
    __table_args__ = (
        db.ForeignKeyConstraint(["operational_shipment_id", "organization_id"], ["operational_shipment.id", "operational_shipment.organization_id"], name="fk_closure_decision_shipment", ondelete="RESTRICT"),
        db.ForeignKeyConstraint(["policy_version_id", "organization_id"], ["closure_policy_version.id", "closure_policy_version.organization_id"], name="fk_closure_decision_policy", ondelete="RESTRICT"),
        db.CheckConstraint("previous_state = 'completed'", name="ck_closure_completed_predecessor"),
        db.CheckConstraint("kind IN ('NORMAL','EXCEPTIONAL')", name="ck_closure_decision_kind"),
        db.CheckConstraint("kind != 'EXCEPTIONAL' OR (reason IS NOT NULL AND length(trim(reason)) > 0)", name="ck_closure_exception_reason"),
    )
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, unique=True, default=lambda: str(uuid4()))
    organization_id = db.Column(BIGINT, nullable=False)
    operational_shipment_id = db.Column(BIGINT, nullable=False, unique=True)
    policy_version_id = db.Column(BIGINT, nullable=False)
    previous_state = db.Column(db.String(20), nullable=False, default="completed")
    kind = db.Column(db.String(12), nullable=False)
    actor_user_id = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False)
    actor_label = db.Column(db.String(200), nullable=False)
    reason = db.Column(db.String(1000))
    shipment_version = db.Column(db.Integer, nullable=False)
    assessment_fingerprint = db.Column(db.String(64), nullable=False)
    assessment = db.Column(db.JSON, nullable=False)
    missing_items = db.Column(db.JSON, nullable=False)
    occurred_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    recorded_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


def immutable(_mapper, _connection, target):
    if any(inspect(target).attrs[column.key].history.has_changes() for column in target.__table__.columns):
        raise ValueError("Closure policy/decision history is immutable")


def no_delete(_mapper, _connection, _target):
    raise ValueError("Closure policy/decision history cannot be deleted")


for model in (ClosurePolicy, ClosurePolicyVersion, ClosurePolicyCriterion, ClosureDecision):
    event.listen(model, "before_update", immutable)
    event.listen(model, "before_delete", no_delete)
