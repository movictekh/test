from django.db import models
from django.utils import timezone


class BaseModel(models.Model):
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="When this record was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True, help_text="When this record was last updated"
    )

    class Meta:
        abstract = True
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.__class__.__name__} ({self.pk})"


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="When this record was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True, help_text="When this record was last updated"
    )

    class Meta:
        abstract = True
