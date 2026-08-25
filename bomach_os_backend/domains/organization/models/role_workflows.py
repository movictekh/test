from django.core.validators import MinValueValidator
from django.db import models

from user.models.base import BaseModel


class RoleTaskTemplate(BaseModel):
    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
    ]

    role = models.ForeignKey(
        "Role",
        on_delete=models.CASCADE,
        related_name="task_templates",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    sequence = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    default_priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default="medium",
    )
    estimated_minutes = models.PositiveIntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(1)],
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = "user"
        ordering = ["sequence", "id"]
        indexes = [
            models.Index(fields=["role", "sequence"]),
        ]

    def __str__(self):
        return f"{self.role.name}: {self.title}"


class RoleDailyRoutineItem(BaseModel):
    role = models.ForeignKey(
        "Role",
        on_delete=models.CASCADE,
        related_name="daily_routine_items",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    sequence = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    time_of_day = models.TimeField(blank=True, null=True)
    estimated_minutes = models.PositiveIntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(1)],
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = "user"
        ordering = ["sequence", "id"]
        indexes = [
            models.Index(fields=["role", "sequence"]),
        ]

    def __str__(self):
        return f"{self.role.name}: {self.title}"
