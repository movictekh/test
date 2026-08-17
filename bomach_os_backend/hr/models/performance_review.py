from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from .base import BaseModel


class PerformanceReview(BaseModel):
    """Model for employee performance reviews"""

    # Rating Choices (1-5 stars)
    RATING_CHOICES = [
        (1, "1 Star"),
        (2, "2 Stars"),
        (3, "3 Stars"),
        (4, "4 Stars"),
        (5, "5 Stars"),
    ]

    REVIEW_PERIOD_CHOICES = [("q1", "Q1"), ("q2", "Q2"), ("q3", "Q3"), ("q4", "Q4")]

    # Employee Information
    employee = models.ForeignKey(
        "user.Employee",
        on_delete=models.CASCADE,
        related_name="performance_reviews",
    )

    # Reviewer Information
    reviewer = models.ForeignKey(
        "user.Employee",
        on_delete=models.CASCADE,
        related_name="reviews_given",
    )

    # Review Details
    review_date = models.DateField()
    review_period = models.CharField(
        max_length=50,
        choices=REVIEW_PERIOD_CHOICES,
        help_text="e.g., Q1 2025, H1 2025, 2025, etc.",
    )

    # Rating and Feedback
    overall_rating = models.IntegerField(
        choices=RATING_CHOICES, validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    strengths = models.TextField(
        help_text="Employee's key strengths and accomplishments"
    )
    areas_for_improvement = models.TextField(
        help_text="Areas where the employee can improve"
    )
    feedback = models.TextField(
        blank=True, null=True, help_text="Additional feedback and comments"
    )

    employee_comment = models.TextField(
        blank=True, null=True, help_text="Additional feedback and comments"
    )

    class Meta:
        db_table = "performance_reviews"
        ordering = ["-review_date", "-created_at"]
        verbose_name = "Performance Review"
        verbose_name_plural = "Performance Reviews"
        indexes = [
            models.Index(fields=["employee", "review_date"]),
            models.Index(fields=["reviewer", "review_date"]),
            models.Index(fields=["review_period"]),
        ]
        unique_together = [["employee", "review_period"]]

    def __str__(self):
        return f"{self.review_period} ({self.overall_rating} stars)"

    @property
    def rating_display(self):
        """Get the rating as a display string"""
        return f"{self.overall_rating} Star{'s' if self.overall_rating != 1 else ''}"

    def clean(self):
        super().clean()
        # Validate that reviewer is not the same as employee
        if (
            self.employee_id
            and self.reviewer_id
            and self.employee_id == self.reviewer_id
        ):
            raise ValidationError(
                "Reviewer cannot be the same as the employee being reviewed"
            )
