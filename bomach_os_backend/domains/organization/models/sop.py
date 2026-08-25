"""Organization-owned standard operating procedure model."""

from django.core.exceptions import ValidationError
from django.db import models

from user.models.base import TimeStampedModel
from domains.organization.models.roles import Department, Unit


class SOP(TimeStampedModel):
    title = models.CharField(max_length=200, help_text="SOP title / name")
    version = models.CharField(
        max_length=20, default="v1.0", help_text="e.g. v1.2, 2025-03"
    )
    description = models.TextField(blank=True, help_text="Full procedure / content")

    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="department_sops",
    )
    unit = models.ForeignKey(
        Unit, on_delete=models.SET_NULL, null=True, blank=True, related_name="unit_sops"
    )

    priority = models.CharField(
        max_length=20,
        choices=[
            ("Critical", "Critical"),
            ("High", "High"),
            ("Medium", "Medium"),
            ("Low", "Low"),
        ],
        default="Medium",
    )
    is_up_to_date = models.BooleanField(default=True, help_text="Still current")

    class Meta:
        app_label = "user"
        verbose_name = "SOP"
        verbose_name_plural = "SOPs"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["department", "unit"]),
            models.Index(fields=["priority", "is_up_to_date"]),
        ]

    def __str__(self):
        parts = [self.title]
        if self.version:
            parts.append(f"({self.version})")
        if self.department:
            parts.append(f"– {self.department}")
        elif self.unit:
            parts.append(f"– {self.unit}")
        return " ".join(parts)

    def clean(self):
        super().clean()
        if not self.department and not self.unit:
            raise ValidationError("SOP must belong to a Department or a Unit.")
