"""People-owned workforce responsibility model."""

from django.db import models

from user.models.base import TimeStampedModel
from system.identity.models.user import User


class Responsibility(TimeStampedModel):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="core_responsibilities"
    )

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    priority = models.CharField(
        max_length=20,
        choices=[("High", "High"), ("Medium", "Medium"), ("Low", "Low")],
        default="Medium",
    )
    frequency = models.CharField(max_length=80, blank=True)
    kpi_target = models.CharField(max_length=120, blank=True)

    class Meta:
        app_label = "user"
        verbose_name = "Core Responsibility"
        verbose_name_plural = "Core Responsibilities"
        ordering = ["priority", "title"]
        indexes = [models.Index(fields=["user", "priority"])]

    def __str__(self):
        return f"{self.title} – {self.user.get_full_name() or self.user.username}"
