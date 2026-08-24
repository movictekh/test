"""Mutation and producer boundary for System Notifications."""

from collections.abc import Iterable
from typing import Any

from system.notifications.models import Notification
from system.notifications.selectors import get_user_notification


def mark_user_notification_read(*, user, notification_id: int) -> Notification:
    """Mark one user-owned notification as read and return it."""
    notification = get_user_notification(
        user=user,
        notification_id=notification_id,
    )
    notification.is_read = True
    notification.save(update_fields=["is_read", "updated_at"])
    return notification


def mark_all_user_notifications_read(*, user) -> int:
    """Mark every unread notification for one user as read."""
    return Notification.objects.filter(
        user=user,
        is_read=False,
    ).update(is_read=True)


def notify_user(
    *,
    user_id: int,
    title: str,
    message: str,
    notification_type: str = "info",
    link: str = "",
    metadata: dict[str, Any] | None = None,
) -> Notification:
    """Create one in-app notification through the canonical producer boundary."""
    return Notification.objects.create(
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type,
        link=link,
        metadata=dict(metadata or {}),
    )


def notify_users(
    *,
    user_ids: Iterable[int],
    title: str,
    message: str,
    notification_type: str = "info",
    link: str = "",
    metadata: dict[str, Any] | None = None,
) -> list[Notification]:
    """Create the same in-app notification for each supplied user id.

    """
    return [
        notify_user(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            link=link,
            metadata=metadata,
        )
        for user_id in user_ids
    ]


__all__ = [
    "mark_all_user_notifications_read",
    "mark_user_notification_read",
    "notify_user",
    "notify_users",
]
