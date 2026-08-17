import uuid

from django.core.exceptions import ValidationError
from django.db import models

from user.models.base import BaseModel
from user.models.user import User


class BoardResolution(BaseModel):

    TYPE_CHOICES = [
        ("financial", "Financial"),
        ("operational", "Operational"),
        ("strategic", "Strategic"),
        ("legal", "Legal & Compliance"),
        ("hr", "Human Resources"),
        ("investment", "Investment"),
        ("governance", "Governance"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("archived", "Archived"),
    ]

    resolution_id = models.CharField(
        max_length=50, unique=True, verbose_name="Resolution ID"
    )
    title = models.CharField(max_length=255, verbose_name="Title")
    description = models.TextField(verbose_name="Description")
    resolution_type = models.CharField(
        max_length=50, choices=TYPE_CHOICES, verbose_name="Type"
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending", verbose_name="Status"
    )
    resolution_date = models.DateField(
        verbose_name="Resolution Date",
        help_text="Date the resolution was created or passed",
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="resolutions_created",
        verbose_name="Created By",
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolutions_approved",
        verbose_name="Approved By",
    )
    approved_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Approved At"
    )
    attachment_url = models.URLField(
        max_length=500,
        blank=True,
        verbose_name="Attachment URL",
        help_text="Optional link to the full resolution document",
    )
    notes = models.TextField(blank=True, verbose_name="Notes")

    class Meta:
        verbose_name = "Board Resolution"
        verbose_name_plural = "Board Resolutions"
        ordering = ["-resolution_date", "-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["resolution_type"]),
            models.Index(fields=["resolution_date"]),
        ]

    def __str__(self):
        return f"[{self.get_resolution_type_display()}] {self.title} — {self.get_status_display()}"

    def clean(self):
        super().clean()
        if not self.title or not self.title.strip():
            raise ValidationError({"title": "Title cannot be blank."})
        if not self.description or not self.description.strip():
            raise ValidationError({"description": "Description cannot be blank."})

    def save(self, *args, **kwargs):
        if not self.resolution_id:
            self.resolution_id = f"RES-{uuid.uuid4().hex[:12].upper()}"
        self.full_clean()
        super().save(*args, **kwargs)
