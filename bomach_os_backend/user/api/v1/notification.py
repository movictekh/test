"""Compatibility exports for the System Notifications API v1 router."""
from system.notifications.api.v1.routers.notification import (
    get_notification,
    get_notification_stats,
    list_notifications,
    mark_all_notifications_read,
    mark_notification_read,
    notification_router,
)
__all__ = [
    "notification_router",
    "get_notification_stats",
    "mark_all_notifications_read",
    "list_notifications",
    "get_notification",
    "mark_notification_read",
]
