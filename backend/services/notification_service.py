"""Service helpers for expert console notifications."""
from typing import Any, Optional

from sqlalchemy import and_, desc, func

from backend.extensions import db
from backend.models import ExpertConsoleNotification


def list_notifications_for_expert(
    expert_id: int,
    filters: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Return the current expert notification list response payload."""
    filters = filters or {}
    unread_only = bool(filters.get("unread_only", False))
    limit = min(int(filters.get("limit", 50)), 200)

    query = db.session.query(ExpertConsoleNotification).filter(
        ExpertConsoleNotification.expert_user_id == expert_id
    )

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
    return {
        "id": notification.id,
        "type": notification.notification_type,
        "title": notification.title,
        "message": notification.message,
        "is_read": notification.is_read,
        "created_at": notification.created_at.isoformat(),
        "shipment_request_id": notification.shipment_request_id,
    }


def get_unread_count(expert_id: int) -> int:
    """Return the current unread count for an expert."""
    return db.session.query(func.count(ExpertConsoleNotification.id)).filter(
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
        notifications = db.session.query(ExpertConsoleNotification).filter(
            and_(
                ExpertConsoleNotification.expert_user_id == expert_id,
                ExpertConsoleNotification.is_read.is_(False),
            )
        ).all()
    elif notification_ids:
        notifications = db.session.query(ExpertConsoleNotification).filter(
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
