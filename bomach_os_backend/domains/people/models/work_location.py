from django.db import models
from django.utils import timezone

from user.models.base import BaseModel


class WorkLocation(BaseModel):
    """
    Whitelisted work locations for attendance verification.

    Employees submit proposals (status=PENDING); an admin approves or rejects them.
    Only approved, active, non-expired locations can be used for clock-in.
    `allowed_radius_meters` is an admin-only field.
    """

    class LocationType(models.TextChoices):
        BRANCH = "branch", "Branch Location"
        REMOTE = "remote", "Remote Location"
        SITE = "site", "On-Site Location"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending Approval"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    name = models.CharField(
        max_length=255,
        help_text="Name of the work location (e.g., 'Home Office', 'Branch HQ')",
    )

    location_type = models.CharField(
        max_length=20,
        choices=LocationType.choices,
        default=LocationType.REMOTE,
        help_text="Type of work location",
    )

    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, help_text="GPS latitude coordinate"
    )

    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, help_text="GPS longitude coordinate"
    )

    allowed_radius_meters = models.PositiveIntegerField(
        default=100, help_text="Allowed radius in meters. Admin-only field."
    )

    branch = models.ForeignKey(
        "Branch",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="work_locations",
        help_text="Associated branch (optional)",
    )

    employee = models.ForeignKey(
        "Employee",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="work_locations",
        help_text="Employee who owns this location (for personal remote locations)",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        help_text="Approval status — set by admin via approve/reject endpoints",
    )

    rejection_reason = models.TextField(
        blank=True,
        default="",
        help_text="Reason provided by admin when rejecting a proposal",
    )

    verified_by = models.ForeignKey(
        "Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_locations",
        help_text="Admin who approved or rejected this location",
    )

    verified_at = models.DateTimeField(
        null=True, blank=True, help_text="When the approval decision was made"
    )

    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this location expires (for temporary locations)",
    )

    is_active = models.BooleanField(
        default=True, help_text="Whether this location is active"
    )

    notes = models.TextField(
        blank=True, help_text="Additional notes about this location"
    )

    class Meta:
        app_label = "user"
        verbose_name = "Work Location"
        verbose_name_plural = "Work Locations"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["employee", "is_active"]),
            models.Index(fields=["branch", "is_active"]),
            models.Index(fields=["location_type", "status"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_location_type_display()})"

    def is_expired(self):
        if self.expires_at:
            return self.expires_at < timezone.now()
        return False

    def is_pending(self):
        return self.status == self.Status.PENDING

    def is_approved(self):
        return self.status == self.Status.APPROVED

    def can_be_used(self):
        """Location is usable for attendance verification only when approved,
        active, and not expired."""
        return self.is_approved() and self.is_active and not self.is_expired()
