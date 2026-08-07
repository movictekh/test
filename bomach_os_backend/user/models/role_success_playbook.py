from django.core.validators import MinValueValidator
from django.db import models

from user.models.base import BaseModel


class RoleSuccessPlaybookItem(BaseModel):
    class Kind(models.TextChoices):
        BEST_PRACTICE = "best_practice", "Best Practice"
        COMMON_MISTAKE = "common_mistake", "Common Mistake"
        WINNING_STRATEGY = "winning_strategy", "Winning Strategy"
        LESSON_LEARNED = "lesson_learned", "Lesson Learned"

    role = models.ForeignKey(
        "Role",
        on_delete=models.CASCADE,
        related_name="success_playbook_items",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    kind = models.CharField(max_length=30, choices=Kind.choices)
    sequence = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sequence", "id"]
        indexes = [
            models.Index(fields=["role", "sequence"]),
            models.Index(fields=["role", "kind"]),
        ]

    def __str__(self):
        return f"{self.role.name}: {self.title}"
