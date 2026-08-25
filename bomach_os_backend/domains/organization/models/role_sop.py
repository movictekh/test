from django.db import models

from user.models.base import BaseModel


class RoleSOP(BaseModel):
    role = models.ForeignKey(
        "Role",
        on_delete=models.CASCADE,
        related_name="role_sops",
    )
    sop = models.ForeignKey(
        "SOP",
        on_delete=models.CASCADE,
        related_name="role_links",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = "user"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["role", "sop"]),
            models.Index(fields=["role", "is_active"]),
        ]
        unique_together = [("role", "sop")]

    def __str__(self):
        return f"{self.role.name}: {self.sop.title}"
