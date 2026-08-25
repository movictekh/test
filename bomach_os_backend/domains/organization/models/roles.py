from django.core.exceptions import ValidationError
from django.db import models

from user.models.base import BaseModel, TimeStampedModel


class Department(BaseModel):
    class DepartmentChoices(models.TextChoices):
        OPERATIONS = "operations", "Operations"
        MARKETING = "marketing", "Marketing"
        FINANCE = "finance", "Finance"
        IT = "it", "Information Technology"
        HR = "hr", "Human Resources"
        LEGAL = "legal", "Legal"

    name = models.CharField(
        max_length=50,
        choices=DepartmentChoices.choices,
        unique=True,
        help_text="Department name",
    )
    description = models.TextField(blank=True, help_text="Department description")

    class Meta:
        app_label = "user"
        verbose_name = "Department"
        verbose_name_plural = "Departments"
        ordering = ["name"]

    def clean(self):
        super().clean()
        valid_names = [choice[0] for choice in self.DepartmentChoices.choices]
        if self.name and (self.name not in valid_names):
            raise ValidationError(
                {
                    "name": f"Invalid department name. Must be one of: {', '.join(valid_names)}"
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_name_display()}"


class Unit(BaseModel):
    name = models.CharField(max_length=100, help_text="Unit/Team name")
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name="units",
        help_text="Parent department",
    )
    description = models.TextField(blank=True, help_text="Unit description")

    class Meta:
        app_label = "user"
        verbose_name = "Unit"
        verbose_name_plural = "Units"
        unique_together = ["name", "department"]
        ordering = ["department", "name"]

    def clean(self):
        super().clean()
        if not self.name or not self.name.strip():
            raise ValidationError({"name": "Unit name cannot be blank."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.department.name})"
