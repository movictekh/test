from django.db import models
from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from .base import BaseModel


class DailyWorkReport(BaseModel):
    """Model for tracking daily work reports from employees"""

    # MOOD_CHOICES = [
    #    ('happy', 'Happy'),
    #   ('neutral', 'Neutral'),
    #    ('sad', 'Sad'),
    #    ('stressed', 'Stressed'),
    #    ('tired', 'Tired'),
    #    ('frustrated', 'Frustrated'),
    # ]

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    # Employee Information
    employee = models.ForeignKey(
        "user.Employee",
        on_delete=models.CASCADE,
        related_name="reports",
    )

    # Report Details
    day = models.DateField(db_index=True)
    hours_worked = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        validators=[MinValueValidator(Decimal("0.0"))],
        default=Decimal("0.0"),
        help_text="Total hours worked for the day",
    )
    # mood = models.CharField(
    #    max_length=20,
    #    choices=MOOD_CHOICES,
    #    default='neutral'
    # )

    # Content
    operational_base = models.CharField(
        max_length=500, blank=True, null=True, help_text="Challenges faced today"
    )
    work_activities = models.TextField(
        blank=True, null=True, help_text="Accomplishments today"
    )
    task_details = models.TextField(
        blank=True, null=True, help_text="Details about tasks worked on"
    )
    plan_next_day = models.TextField(
        blank=True, null=True, help_text="Plan for tomorrow"
    )

    rating = models.DecimalField(
        max_digits=1,
        decimal_places=0,
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    feedback = models.TextField(blank=True, null=True, help_text="Feedback")

    # Status
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="draft", db_index=True
    )
    reviewed_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_work_reports",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "daily_work_reports"
        ordering = ["-day", "-created_at"]
        verbose_name = "Daily Work Report"
        verbose_name_plural = "Daily Work Reports"
        indexes = [
            models.Index(fields=["employee", "day"]),
            models.Index(fields=["status"]),
        ]
        unique_together = ["employee", "day"]

    def __str__(self):
        return f"{self.employee} - {self.day}"

    def clean(self):
        super().clean()
        if self.status in ("approved", "rejected"):
            if not self.reviewed_by_id or not self.reviewed_at:
                raise ValidationError(
                    "Decided work reports must include reviewer details."
                )
        elif self.reviewed_by_id or self.reviewed_at:
            raise ValidationError(
                "Undecided work reports cannot include reviewer details."
            )

        if self.status == "rejected" and not (self.feedback or "").strip():
            raise ValidationError(
                {"feedback": "Feedback is required when rejecting a work report."}
            )


class ReportAttachment(models.Model):
    report = models.ForeignKey(
        DailyWorkReport, related_name="attachments", on_delete=models.CASCADE
    )
    file_url = models.URLField(max_length=1000)

    def __str__(self):
        return f"Attachment for {self.report.day}"
