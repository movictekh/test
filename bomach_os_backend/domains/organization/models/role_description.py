from django.db import models

from user.models.base import BaseModel


class RoleDescription(BaseModel):
    role = models.OneToOneField(
        "Role",
        on_delete=models.CASCADE,
        related_name="role_description",
    )
    purpose = models.TextField(blank=True, default="")
    responsibilities = models.TextField(blank=True, default="")
    job_description = models.TextField(blank=True, default="")

    class Meta:
        app_label = "user"
        verbose_name = "Role Description"
        verbose_name_plural = "Role Descriptions"
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"Role description for {self.role.name}"

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
