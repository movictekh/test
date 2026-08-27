from django.conf import settings
from django.db import models
from django.utils import timezone

from user.models.base import BaseModel


class MessageOutbox(BaseModel):
    CHANNEL_IN_APP = "in_app"
    CHANNEL_EMAIL = "email"
    CHANNEL_CHOICES = [(CHANNEL_IN_APP, "In app"), (CHANNEL_EMAIL, "Email")]

    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_SENT = "sent"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PROCESSING, "Processing"),
        (STATUS_SENT, "Sent"),
        (STATUS_FAILED, "Failed"),
    ]

    event_key = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=100, db_index=True)
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    recipient_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="message_outbox_entries",
    )
    recipient_address = models.CharField(max_length=320, blank=True, default="")
    subject = models.CharField(max_length=255)
    body = models.TextField()
    link = models.CharField(max_length=500, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True
    )
    attempts = models.PositiveSmallIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=5)
    available_at = models.DateTimeField(default=timezone.now, db_index=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True, default="")

    class Meta:
        app_label = "user"
        db_table = "user_message_outbox"
        ordering = ["available_at", "created_at"]
        indexes = [
            models.Index(
                fields=["status", "available_at"],
                name="user_msgout_status_avail_idx",
            )
        ]

    def __str__(self):
        return f"{self.event_type}:{self.channel}:{self.event_key}"
