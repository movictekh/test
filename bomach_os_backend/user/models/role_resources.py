from django.core.validators import MinValueValidator
from django.db import models

from user.models.base import BaseModel


class RoleResource(BaseModel):
    class Kind(models.TextChoices):
        PHYSICAL = "physical", "Physical"
        SOFTWARE = "software", "Software"
        DOCUMENT = "document", "Document"
        SKILL = "skill", "Skill"

    role = models.ForeignKey(
        "Role",
        on_delete=models.CASCADE,
        related_name="resources",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    sequence = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sequence", "id"]
        indexes = [
            models.Index(fields=["role", "sequence"]),
            models.Index(fields=["role", "kind"]),
        ]

    def __str__(self):
        return f"{self.role.name}: {self.name}"
