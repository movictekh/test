from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models

from user.models.base import BaseModel
from user.models.user import User


class DrawingBank(BaseModel):
    class STATUS(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    class BUILDING_CATEGORY(models.TextChoices):
        DUPLEX = "duplex", "Duplex"
        BUNGALOW = "bungalow", "Bungalow"
        BLOCK_OF_FLATS = "block_of_flats", "Block of Flats"
        SEMI_DETACHED = "semi_detached", "Semi Detached"
        TERRACE = "terrace", "Terrace"
        PLAZA = "plaza", "Plaza"
        EVENT_CENTERS = "event_centers", "Event Centers"
        CHURCH = "church", "Church"

    title = models.CharField(max_length=255)
    building_category = models.CharField(
        max_length=30, choices=BUILDING_CATEGORY.choices
    )
    drawing_file = models.URLField(help_text="URL to the uploaded PDF drawing file")
    file_name = models.CharField(max_length=255, blank=True, default="")
    file_size_mb = models.DecimalField(
        decimal_places=2,
        max_digits=8,
        null=True,
        blank=True,
        help_text="File size in MB",
    )
    description = models.TextField(max_length=1000)
    tags = models.JSONField(
        default=list, blank=True, help_text="List of tags for categorization"
    )
    employee = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="drawing_submissions"
    )
    status = models.CharField(
        max_length=20, choices=STATUS.choices, default=STATUS.PENDING
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_drawings",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(max_length=500, blank=True, default="")
    download_count = models.PositiveIntegerField(default=0)

    def clean(self):
        super().clean()
        if not self.title or not self.title.strip():
            raise ValidationError({"title": "Drawing title is required."})

        if not self.drawing_file:
            raise ValidationError({"drawing_file": "A drawing file URL is required."})

        if not self.description or not self.description.strip():
            raise ValidationError({"description": "Description is required."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

    class Meta:
        ordering = ["-created_at"]
