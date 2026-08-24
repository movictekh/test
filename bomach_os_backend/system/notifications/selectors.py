"""Read boundary for System Notifications."""

from django.shortcuts import get_object_or_404

from system.notifications.models import Notification


def list_user_notifications(*, user, is_read: bool | None = None):
    """Return notifications belonging to one user, optionally filtered by read state."""
    queryset = Notification.objects.filter(user=user)
    if is_read is not None:
        queryset = queryset.filter(is_read=is_read)
    return queryset


def get_user_notification(*, user, notification_id: int) -> Notification:
    """Return one notification only when it belongs to the supplied user."""
    return get_object_or_404(
        Notification,
        id=notification_id,
        user=user,
    )


def get_unread_notification_count(*, user) -> int:
    """Return the unread in-app notification count for one user."""
    return Notification.objects.filter(
        user=user,
        is_read=False,
    ).count()


__all__ = [
    "get_unread_notification_count",
    "get_user_notification",
    "list_user_notifications",
]
