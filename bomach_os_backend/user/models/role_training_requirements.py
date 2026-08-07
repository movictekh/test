from django.core.validators import MinValueValidator
from django.db import models

from user.models.base import BaseModel


class RoleTrainingRequirement(BaseModel):
    class RequirementType(models.TextChoices):
        MANDATORY = "mandatory", "Mandatory"
        CONTINUOUS = "continuous", "Continuous"

    role = models.ForeignKey(
        "Role",
        on_delete=models.CASCADE,
        related_name="training_requirements",
    )
    training_program = models.ForeignKey(
        "hr.TrainingProgram",
        on_delete=models.CASCADE,
        related_name="role_requirements",
    )
    requirement_type = models.CharField(max_length=20, choices=RequirementType.choices)
    sequence = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sequence", "id"]
        indexes = [
            models.Index(fields=["role", "sequence"]),
            models.Index(fields=["role", "requirement_type"]),
            models.Index(fields=["role", "training_program"]),
        ]

    def __str__(self):
        return f"{self.role.name}: {self.training_program.program_name}"
