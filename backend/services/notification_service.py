"""Service helpers for expert console notifications."""
from typing import Any, Optional

from sqlalchemy import and_, desc, func

from backend.extensions import db
from backend.models import ExpertConsoleNotification


def _visible_query(expert_id):
    """Keep legacy inbox semantics; new response attention follows live authority."""
    from sqlalchemy import select, or_
    from backend.models import ShipmentRequest, ExpertUser
    from backend.operational_models import OperationalMembership, OperationalOrganization
    from backend.quote_response_models import QuoteResponseFact
    from backend.services.assigned_work_authorization import assigned_request_scope
    db.session.scalar(select(ExpertUser).where(ExpertUser.id == expert_id).execution_options(populate_existing=True))
    owner_scope = assigned_request_scope({'id':expert_id}, 'request.read')
    active_member = select(func.min(OperationalMembership.id)).join(OperationalOrganization,
        OperationalOrganization.id == OperationalMembership.organization_id).where(
        OperationalMembership.user_id == expert_id, OperationalMembership.is_active.is_(True),
        OperationalOrganization.is_active.is_(True)).correlate(None).scalar_subquery()
    active_count = select(func.count(OperationalMembership.id)).join(OperationalOrganization,
        OperationalOrganization.id == OperationalMembership.organization_id).where(
        OperationalMembership.user_id == expert_id, OperationalMembership.is_active.is_(True),
        OperationalOrganization.is_active.is_(True)).correlate(None).scalar_subquery()
    # Correlated exact root/fact plus current membership prevents retained inbox
    # IDs and old cached expert assignment from remaining disclosure authority.
    response_visible = select(ShipmentRequest.id).join(QuoteResponseFact,
        QuoteResponseFact.request_id == ShipmentRequest.id).join(ExpertUser,
        ExpertUser.id == ShipmentRequest.assigned_to).join(OperationalMembership,
        and_(OperationalMembership.user_id == ExpertUser.id,
             OperationalMembership.organization_id == ShipmentRequest.operational_organization_id)).where(
        ShipmentRequest.id == ExpertConsoleNotification.shipment_request_id,
        ShipmentRequest.ownership_scope == 'TENANT', ShipmentRequest.assigned_to == expert_id,
        ShipmentRequest.operational_organization_id == ExpertConsoleNotification.operational_organization_id,
        QuoteResponseFact.id == ExpertConsoleNotification.quote_response_fact_id,
        QuoteResponseFact.organization_id == ShipmentRequest.operational_organization_id,
        ExpertUser.is_active.is_(True), ExpertUser.authority.in_(['EXPERT','ORGANIZATION_ADMIN']), owner_scope,
        OperationalMembership.is_active.is_(True), active_count == 1,
        OperationalMembership.id == active_member).exists()
    return db.session.query(ExpertConsoleNotification).filter(
        ExpertConsoleNotification.expert_user_id == expert_id,
        or_(ExpertConsoleNotification.quote_response_fact_id.is_(None), response_visible))


def list_notifications_for_expert(
    expert_id: int,
    filters: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Return the current expert notification list response payload."""
    filters = filters or {}
    unread_only = bool(filters.get("unread_only", False))
    limit = min(int(filters.get("limit", 50)), 200)

    query = _visible_query(expert_id)

    if unread_only:
        query = query.filter(ExpertConsoleNotification.is_read.is_(False))

    notifications = query.order_by(
        desc(ExpertConsoleNotification.created_at)
    ).limit(limit).all()

    return build_notifications_response_payload(notifications, expert_id)


def build_notifications_response_payload(
    notifications: list[ExpertConsoleNotification],
    expert_id: int,
) -> dict[str, Any]:
    """Build the notification list response payload without changing its shape."""
    return {
        "notifications": [
            build_notification_payload(notification)
            for notification in notifications
        ],
        "unread_count": get_unread_count(expert_id),
    }


def build_notification_payload(notification: ExpertConsoleNotification) -> dict[str, Any]:
    """Build the current single-notification JSON payload."""
    if notification.quote_response_fact_id is not None and not _visible_query(notification.expert_user_id).filter(
            ExpertConsoleNotification.id == notification.id).first():
        raise ValueError('QUOTE_RESPONSE_ATTENTION_UNAVAILABLE')
    payload = {
        "id": notification.id,
        "type": notification.notification_type,
        "title": notification.title,
        "message": notification.message,
        "is_read": notification.is_read,
        "created_at": notification.created_at.isoformat(),
        "shipment_request_id": notification.shipment_request_id,
    }
    if notification.quote_response_fact_id is not None:
        from backend.quote_response_models import QuoteResponseFact
        from backend.services.quote_response_authorization import aware
        fact = db.session.get(QuoteResponseFact, notification.quote_response_fact_id)
        payload.update(fact_id=fact.id, response_received_at=aware(fact.response_received_at).isoformat(),
            created_at=aware(fact.recorded_at).isoformat(),
            message=f'{fact.response}; quote={fact.snapshot["quote_public_id"]}; sequence={fact.sequence}')
    return payload


def get_unread_count(expert_id: int) -> int:
    """Return the current unread count for an expert."""
    return _visible_query(expert_id).with_entities(func.count(ExpertConsoleNotification.id)).filter(
        and_(
            ExpertConsoleNotification.expert_user_id == expert_id,
            ExpertConsoleNotification.is_read.is_(False),
        )
    ).scalar() or 0


def mark_notifications_read(
    expert_id: int,
    payload: Optional[dict[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    """Mark matching notifications as read and return the current success payload."""
    payload = payload or {}
    notification_ids = payload.get("notification_ids", [])
    mark_all = payload.get("mark_all", False)

    if mark_all:
        notifications = _visible_query(expert_id).filter(
            and_(
                ExpertConsoleNotification.expert_user_id == expert_id,
                ExpertConsoleNotification.is_read.is_(False),
            )
        ).all()
    elif notification_ids:
        notifications = _visible_query(expert_id).filter(
            and_(
                ExpertConsoleNotification.id.in_(notification_ids),
                ExpertConsoleNotification.expert_user_id == expert_id,
            )
        ).all()
    else:
        return None

    # Use mapped instances so the quarantine flush boundary can validate each
    # notification's ShipmentRequest reference under the pinned census.
    for notification in notifications:
        notification.is_read = True
    updated = len(notifications)
    db.session.commit()

    return {
        "message": f"{updated} اعلان به عنوان خوانده شده علامت‌گذاری شد",
        "marked_count": updated,
    }
