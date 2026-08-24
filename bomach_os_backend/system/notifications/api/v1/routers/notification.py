from ninja import Router
from ninja.pagination import LimitOffsetPagination, paginate

from system.notifications.api.v1.schemas import NotificationOut, NotificationStats
from system.notifications.selectors import (
    get_unread_notification_count,
    get_user_notification,
    list_user_notifications,
)
from system.notifications.services import (
    mark_all_user_notifications_read,
    mark_user_notification_read,
)
from user.utils.perm import require_permission

notification_router = Router(tags=["Notifications"])


@notification_router.get("/stats", response=NotificationStats)
@require_permission("notifications", "view")
def get_notification_stats(request):
    unread_count = get_unread_notification_count(user=request.user)
    return {"unread_count": unread_count}


@notification_router.post("/read-all", response={200: dict})
@require_permission("notifications", "mark_all_read")
def mark_all_notifications_read(request):
    updated = mark_all_user_notifications_read(user=request.user)
    return {"detail": f"Marked {updated} notifications as read"}


@notification_router.get("/", response=list[NotificationOut])
@paginate(LimitOffsetPagination, page_size=20)
@require_permission("notifications", "list")
def list_notifications(request, is_read: bool = None):
    return list_user_notifications(
        user=request.user,
        is_read=is_read,
    )


@notification_router.get("/{notification_id}", response=NotificationOut)
@require_permission("notifications", "view")
def get_notification(request, notification_id: int):
    return get_user_notification(
        user=request.user,
        notification_id=notification_id,
    )


@notification_router.patch("/{notification_id}/read", response=NotificationOut)
@require_permission("notifications", "mark_read")
def mark_notification_read(request, notification_id: int):
    return mark_user_notification_read(
        user=request.user,
        notification_id=notification_id,
    )
