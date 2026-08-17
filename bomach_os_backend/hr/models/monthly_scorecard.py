from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from .base import BaseModel


class MonthlyScorecard(BaseModel):
    employee = models.ForeignKey(
        "user.Employee",
        on_delete=models.CASCADE,
        related_name="monthly_scorecards",
    )
    month = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)]
    )
    year = models.IntegerField()

    # 5 metric scores (0-100)
    attendance_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
    )
    task_delivery_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
    )
    report_accuracy_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
    )
    brand_contribution_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
    )
    training_progress_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
    )

    # Summary
    overall_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
    )
    target_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("75.00"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
    )
    target_achievement = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    ranking = models.IntegerField(null=True, blank=True)

    is_auto_generated = models.BooleanField(default=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "monthly_scorecards"
        ordering = ["-year", "-month", "-overall_score"]
        unique_together = ["employee", "month", "year"]
        indexes = [
            models.Index(fields=["employee", "year", "month"]),
            models.Index(fields=["-overall_score"]),
        ]

    def __str__(self):
        return f"{self.employee_id} - {self.month}/{self.year} ({self.overall_score})"
