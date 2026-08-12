"""Service helpers for user-management delete cleanup."""
from __future__ import annotations

from typing import Any

from flask import current_app

from backend.extensions import db
from backend.models import (
    Activity,
    AssignmentLog,
    AssignmentRule,
    CRMCustomerLinkAudit,
    ExpertConsoleLog,
    ExpertConsoleMessage,
    ExpertConsoleNotification,
    ExpertQuote,
    ExpertSpecialization,
    ExpertUser,
    Opportunity,
    ReferralAssignmentLog,
    ReferralRule,
    ReferralRuleState,
    Report,
    ShipmentRequest,
    Task,
)
from backend.operational_models import OperationalMembership


class DeleteAuthenticationRequired(Exception):
    """Raised when delete is attempted without a current user."""


class SelfDeleteNotAllowed(Exception):
    """Raised when an admin attempts to delete their own account."""


class DeleteTargetNotFound(Exception):
    """Raised when the target user does not exist."""


class AdminDeleteNotAllowed(Exception):
    """Raised when the target user is an admin."""


def get_delete_target_user_or_none(user_id: int) -> ExpertUser | None:
    """Look up the target user using the current legacy query behavior."""
    return db.session.query(ExpertUser).get(user_id)


def validate_user_delete_allowed(target_user: ExpertUser | None, current_user: dict[str, Any] | None, user_id: int) -> ExpertUser:
    """Preserve current delete guards and their ordering."""
    if not current_user:
        raise DeleteAuthenticationRequired()

    if current_user["id"] == user_id:
        raise SelfDeleteNotAllowed()

    if not target_user:
        raise DeleteTargetNotFound()

    if target_user.role == "admin":
        raise AdminDeleteNotAllowed()

    return target_user


def cleanup_user_subordinates(target_user: ExpertUser) -> None:
    """Unset manager for direct subordinates of the deleted user."""
    db.session.query(ExpertUser).filter(ExpertUser.manager_id == target_user.id).update(
        {ExpertUser.manager_id: None}, synchronize_session=False
    )


def cleanup_user_related_records(target_user: ExpertUser) -> None:
    """Delete records that directly reference the target expert user."""
    expert_id = target_user.id

    protected_rows = [
        *db.session.query(ExpertConsoleNotification).filter(
            ExpertConsoleNotification.expert_user_id == expert_id
        ).all(),
        *db.session.query(ExpertConsoleLog).filter(
            ExpertConsoleLog.expert_user_id == expert_id
        ).all(),
        *db.session.query(AssignmentLog).filter(
            AssignmentLog.assigned_expert_id == expert_id
        ).all(),
        *db.session.query(ReferralAssignmentLog).filter(
            ReferralAssignmentLog.selected_expert_id == expert_id
        ).all(),
    ]
    for row in protected_rows:
        db.session.delete(row)
    db.session.query(ExpertQuote).filter(
        ExpertQuote.created_by_expert_id == expert_id
    ).delete(synchronize_session=False)
    db.session.query(ExpertConsoleMessage).filter(
        ExpertConsoleMessage.expert_user_id == expert_id
    ).delete(synchronize_session=False)
    db.session.query(ExpertSpecialization).filter(
        ExpertSpecialization.expert_user_id == expert_id
    ).delete(synchronize_session=False)
    db.session.query(Activity).filter(Activity.expert_user_id == expert_id).delete(
        synchronize_session=False
    )
    db.session.query(Task).filter(
        (Task.assigned_to == expert_id) | (Task.created_by == expert_id)
    ).delete(synchronize_session=False)
    db.session.query(Report).filter(Report.created_by == expert_id).delete(
        synchronize_session=False
    )


def cleanup_user_owned_rules(target_user: ExpertUser) -> None:
    """Delete rules owned by the user while preserving nullable history links."""
    expert_id = target_user.id

    assignment_rule_ids = db.session.query(AssignmentRule.id).filter(
        AssignmentRule.created_by == expert_id
    )
    assignment_logs = db.session.query(AssignmentLog).filter(
        AssignmentLog.assignment_rule_id.in_(assignment_rule_ids)
    ).all()
    for log in assignment_logs:
        log.assignment_rule_id = None
    db.session.query(AssignmentRule).filter(
        AssignmentRule.created_by == expert_id
    ).delete(synchronize_session=False)

    referral_rule_ids = db.session.query(ReferralRule.id).filter(
        ReferralRule.created_by == expert_id
    )
    referral_logs = db.session.query(ReferralAssignmentLog).filter(
        ReferralAssignmentLog.rule_id.in_(referral_rule_ids)
    ).all()
    for log in referral_logs:
        log.rule_id = None
    db.session.query(ReferralRuleState).filter(
        ReferralRuleState.rule_id.in_(referral_rule_ids)
    ).delete(synchronize_session=False)
    db.session.query(ReferralRule).filter(
        ReferralRule.created_by == expert_id
    ).delete(synchronize_session=False)


def unassign_user_shipments_and_opportunities(target_user: ExpertUser) -> None:
    """Clear current shipment and opportunity assignments for the target user."""
    expert_id = target_user.id

    db.session.query(ShipmentRequest).filter(
        ShipmentRequest.assigned_to == expert_id
    ).update({ShipmentRequest.assigned_to: None}, synchronize_session=False)
    db.session.query(Opportunity).filter(Opportunity.assigned_to == expert_id).update(
        {Opportunity.assigned_to: None}, synchronize_session=False
    )
    db.session.query(CRMCustomerLinkAudit).filter(
        CRMCustomerLinkAudit.performed_by_user_id == expert_id
    ).update({CRMCustomerLinkAudit.performed_by_user_id: None}, synchronize_session=False)


def build_delete_user_response_payload(target_user: ExpertUser) -> dict[str, str]:
    """Build the current delete user success response payload."""
    return {"message": "کاربر و تمام داده‌های مرتبط با موفقیت حذف شدند"}


def delete_user_with_cleanup(user_id: int, current_user: dict[str, Any] | None, context=None) -> dict[str, str]:
    """Permanently delete a user and all non-nullable owned dependencies."""
    if context is not None:
        target_user = (db.session.query(ExpertUser).join(OperationalMembership, OperationalMembership.user_id == ExpertUser.id).filter(ExpertUser.id == user_id, OperationalMembership.organization_id == context.organization_id, OperationalMembership.is_active.is_(True)).one_or_none())
    else:
        target_user = get_delete_target_user_or_none(user_id)
    target_user = validate_user_delete_allowed(target_user, current_user, user_id)
    if getattr(target_user, "authority", "EXPERT") == "PLATFORM_ADMIN":
        raise AdminDeleteNotAllowed()
    if context is not None:
        memberships = db.session.query(OperationalMembership).filter(OperationalMembership.user_id == target_user.id, OperationalMembership.is_active.is_(True)).all()
        if len(memberships) != 1 or memberships[0].organization_id != context.organization_id:
            raise DeleteTargetNotFound()
        target_user.is_active = False
        memberships[0].is_active = False
        from backend.services.auth_session_service import revoke_all_user_sessions
        revoke_all_user_sessions(target_user.id, "account_deactivated", commit=False)
        db.session.commit()
        return {"message": "User disabled safely."}

    expert_id = target_user.id
    expert_username = target_user.username

    cleanup_user_subordinates(target_user)
    cleanup_user_related_records(target_user)
    cleanup_user_owned_rules(target_user)
    unassign_user_shipments_and_opportunities(target_user)

    payload = build_delete_user_response_payload(target_user)
    db.session.delete(target_user)
    db.session.commit()

    current_app.logger.info(
        f"Admin {current_user.get('username')} deleted user id={expert_id} ({expert_username}) and related data."
    )
    return payload
