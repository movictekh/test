from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from user.models.base import BaseModel


class RoleCareerPath(BaseModel):
    from_role = models.ForeignKey(
        "Role",
        on_delete=models.CASCADE,
        related_name="career_paths_from",
    )
    to_role = models.ForeignKey(
        "Role",
        on_delete=models.CASCADE,
        related_name="career_paths_to",
    )
    description = models.TextField(blank=True, default="")
    requirements = models.TextField(blank=True, default="")
    estimated_duration_months = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
    )
    sequence = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = "user"
        ordering = ["sequence", "id"]
        indexes = [
            models.Index(fields=["from_role", "sequence"]),
            models.Index(fields=["from_role", "is_active"]),
            models.Index(fields=["from_role", "to_role"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["from_role", "to_role"],
                name="uniq_role_career_path_edge",
            )
        ]

    def clean(self):
        if (
            self.from_role_id
            and self.to_role_id
            and self.from_role_id == self.to_role_id
        ):
            raise ValidationError({"to_role": "A role cannot progress to itself."})

    def __str__(self):
        return f"{self.from_role.name} -> {self.to_role.name}"
