from django.db import models
from .base import BaseModel
from .applicant import Applicant


class Interview(BaseModel):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        NO_SHOW = "no_show", "No Show"

    applicant = models.ForeignKey(
        Applicant, on_delete=models.CASCADE, related_name="interviews"
    )
    interviewer = models.ForeignKey(
        "user.Employee",
        on_delete=models.CASCADE,
        related_name="interviews_conducted",
    )
    scheduled_at = models.DateTimeField()
    meeting_link = models.URLField(blank=True, null=True)
    feedback = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.SCHEDULED
    )

    class Meta:
        db_table = "interviews"
        ordering = ["-scheduled_at"]
        verbose_name = "Interview"
        verbose_name_plural = "Interviews"
        indexes = [
            models.Index(fields=["applicant"]),
            models.Index(fields=["status"]),
            models.Index(fields=["scheduled_at"]),
        ]

    def __str__(self):
        return f"Interview for {self.applicant.full_name} on {self.scheduled_at}"
