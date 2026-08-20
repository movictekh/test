from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError

from .base import BaseModel


class EmployeeEvaluation(BaseModel):
    employee = models.ForeignKey(
        "user.Employee",
        on_delete=models.CASCADE,
        related_name="evaluations_received",
    )
    evaluator = models.ForeignKey(
        "user.Employee",
        on_delete=models.CASCADE,
        related_name="evaluations_given",
    )
    month = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)]
    )
    year = models.IntegerField()
    scorecard = models.ForeignKey(
        "MonthlyScorecard",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="evaluations",
    )

    # Manager input fields
    manager_comments = models.TextField()

    # Recommendation & Decision
    promotion_required = models.BooleanField(default=False)
    training_required = models.BooleanField(default=False)
    salary_increase = models.BooleanField(default=False)

    class Meta:
        db_table = "employee_evaluations"
        unique_together = ["employee", "evaluator", "month", "year"]
        ordering = ["-year", "-month", "-created_at"]

    def __str__(self):
        return f"{self.employee_id} - {self.month}/{self.year} by {self.evaluator_id}"

    def clean(self):
        super().clean()
        if (
            self.employee_id
            and self.evaluator_id
            and self.employee_id == self.evaluator_id
        ):
            raise ValidationError(
                "Evaluator cannot be the same as the employee being evaluated"
            )
