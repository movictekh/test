from django.db import models

from user.models.base import BaseModel


class Notification(BaseModel):
    """
    In-app notification for a single user.
    """

    NOTIFICATION_TYPE_CHOICES = [
        ("info", "Informational"),
        ("warning", "Warning"),
        ("success", "Success"),
        ("error", "Error"),
        ("approval", "Approval Required"),
        ("task", "Task Assignment"),
        ("system", "System"),
    ]

    user = models.ForeignKey(
        "user.User",
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPE_CHOICES,
        default="info",
    )
    is_read = models.BooleanField(default=False)
    link = models.CharField(max_length=500, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read"]),
            models.Index(fields=["user", "-created_at"]),
        ]

    def __str__(self):
        return f"[{self.notification_type}] {self.title} → {self.user}"
