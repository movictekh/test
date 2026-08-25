import uuid

from django.core.exceptions import ValidationError
from django.db import models

from user.models.base import BaseModel
from system.identity.models.user import User


class Announcement(BaseModel):

    TYPE_CHOICES = [
        ("general", "General"),
        ("urgent", "Urgent"),
        ("event", "Event"),
        ("policy", "Policy Update"),
        ("reminder", "Reminder"),
    ]

    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("normal", "Normal"),
        ("high", "High"),
    ]

    announcement_id = models.CharField(
        max_length=50, unique=True, verbose_name="Announcement ID"
    )
    title = models.CharField(max_length=255, verbose_name="Title")
    content = models.TextField(verbose_name="Content")
    announcement_type = models.CharField(
        max_length=20, choices=TYPE_CHOICES, default="general", verbose_name="Type"
    )
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default="normal",
        verbose_name="Priority",
    )
    branches = models.ManyToManyField(
        "Branch",
        blank=True,
        related_name="announcements",
        verbose_name="Target Branches",
        help_text="Leave empty to target all branches",
    )
    departments = models.ManyToManyField(
        "Department",
        blank=True,
        related_name="announcements",
        verbose_name="Target Departments",
        help_text="Leave empty to target all departments",
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="announcements",
        verbose_name="Created By",
    )
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    publish_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Publish At",
        help_text="Schedule a future publish time. Leave blank to publish immediately.",
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Expires At",
        help_text="Optional expiry date/time after which the announcement is no longer shown.",
    )

    class Meta:
        app_label = "user"
        verbose_name = "Announcement"
        verbose_name_plural = "Announcements"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["announcement_type"]),
            models.Index(fields=["priority"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"[{self.get_announcement_type_display()}] {self.title}"

    def clean(self):
        super().clean()
        if not self.title or not self.title.strip():
            raise ValidationError({"title": "Title cannot be blank."})
        if not self.content or not self.content.strip():
            raise ValidationError({"content": "Content cannot be blank."})
        if self.publish_at and self.expires_at and self.publish_at >= self.expires_at:
            raise ValidationError(
                {"expires_at": "Expiry time must be after publish time."}
            )

    def save(self, *args, **kwargs):
        if not self.announcement_id:
            self.announcement_id = f"ANN-{uuid.uuid4().hex[:12].upper()}"
        self.full_clean()
        super().save(*args, **kwargs)
