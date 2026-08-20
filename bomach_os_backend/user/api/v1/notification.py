from ninja import Router
from ninja.pagination import paginate, LimitOffsetPagination
from django.shortcuts import get_object_or_404

from user.api.schemas.notification import NotificationOut, NotificationStats
from user.models.notification import Notification
from user.utils.perm import require_permission

notification_router = Router(tags=["Notifications"])


@notification_router.get("/stats", response=NotificationStats)
@require_permission("notifications", "view")
def get_notification_stats(request):
    unread_count = Notification.objects.filter(
        user=request.user,
        is_read=False,
    ).count()
    return {"unread_count": unread_count}


@notification_router.post("/read-all", response={200: dict})
@require_permission("notifications", "mark_all_read")
def mark_all_notifications_read(request):
    updated = Notification.objects.filter(
        user=request.user,
        is_read=False,
    ).update(is_read=True)
    return {"detail": f"Marked {updated} notifications as read"}


@notification_router.get("/", response=list[NotificationOut])
@paginate(LimitOffsetPagination, page_size=20)
@require_permission("notifications", "list")
def list_notifications(request, is_read: bool = None):
    qs = Notification.objects.filter(user=request.user)
    if is_read is not None:
        qs = qs.filter(is_read=is_read)
    return qs


@notification_router.get("/{notification_id}", response=NotificationOut)
@require_permission("notifications", "view")
def get_notification(request, notification_id: int):
    return get_object_or_404(
        Notification,
        id=notification_id,
        user=request.user,
    )


@notification_router.patch("/{notification_id}/read", response=NotificationOut)
@require_permission("notifications", "mark_read")
def mark_notification_read(request, notification_id: int):
    notification = get_object_or_404(
        Notification,
        id=notification_id,
        user=request.user,
    )
    notification.is_read = True
    notification.save(update_fields=["is_read", "updated_at"])
    return notification
