"""Service helpers for user-management delete cleanup."""
from __future__ import annotations

from typing import Any

from flask import current_app

from backend.extensions import db
from backend.models import (
    Activity,
    AssignmentLog,
    AssignmentRule,
    ExpertConsoleLog,
    ExpertConsoleMessage,
    ExpertConsoleNotification,
    ExpertSpecialization,
    ExpertUser,
    Opportunity,
    Report,
    ShipmentRequest,
    Task,
)


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

    db.session.query(ExpertConsoleNotification).filter(
        ExpertConsoleNotification.expert_user_id == expert_id
    ).delete(synchronize_session=False)
    db.session.query(ExpertConsoleMessage).filter(
        ExpertConsoleMessage.expert_user_id == expert_id
    ).delete(synchronize_session=False)
    db.session.query(ExpertConsoleLog).filter(
        ExpertConsoleLog.expert_user_id == expert_id
    ).delete(synchronize_session=False)
    db.session.query(AssignmentLog).filter(
        AssignmentLog.assigned_expert_id == expert_id
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


def reassign_assignment_rules_created_by(target_user: ExpertUser, current_user: dict[str, Any]) -> None:
    """Reassign assignment rules created by the target user to the current admin."""
    db.session.query(AssignmentRule).filter(
        AssignmentRule.created_by == target_user.id
    ).update({AssignmentRule.created_by: int(current_user["id"])}, synchronize_session=False)


def unassign_user_shipments_and_opportunities(target_user: ExpertUser) -> None:
    """Clear current shipment and opportunity assignments for the target user."""
    expert_id = target_user.id

    db.session.query(ShipmentRequest).filter(
        ShipmentRequest.assigned_to == expert_id
    ).update({ShipmentRequest.assigned_to: None}, synchronize_session=False)
    db.session.query(Opportunity).filter(Opportunity.assigned_to == expert_id).update(
        {Opportunity.assigned_to: None}, synchronize_session=False
    )


def build_delete_user_response_payload(target_user: ExpertUser) -> dict[str, str]:
    """Build the current delete user success response payload."""
    return {"message": "کاربر و تمام داده‌های مرتبط با موفقیت حذف شدند"}


def delete_user_with_cleanup(user_id: int, current_user: dict[str, Any] | None) -> dict[str, str]:
    """Delete a user and preserve the current cleanup, flush, and commit ordering."""
    target_user = get_delete_target_user_or_none(user_id)
    target_user = validate_user_delete_allowed(target_user, current_user, user_id)

    expert_id = target_user.id
    expert_username = target_user.username

    cleanup_user_subordinates(target_user)
    cleanup_user_related_records(target_user)
    db.session.flush()

    reassign_assignment_rules_created_by(target_user, current_user)
    db.session.flush()

    unassign_user_shipments_and_opportunities(target_user)
    db.session.flush()

    payload = build_delete_user_response_payload(target_user)
    db.session.delete(target_user)
    db.session.commit()

    current_app.logger.info(
        f"Admin {current_user.get('username')} deleted user id={expert_id} ({expert_username}) and related data."
    )
    return payload
