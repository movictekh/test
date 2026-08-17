from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class Expense(models.Model):

    class STATUS(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    class CATEGORY_CHOICES(models.TextChoices):
        TRAVEL = "travel", "Travel"
        FOOD = "food", "Food"
        ACCOMODATION = "accommodation", "Accommodation"
        EQUIPMENT = "equipment", "Equipment"
        UTILITIES = "utilities", "Utilities"
        OTHER = "other", "Other"

    user = models.ForeignKey(
        "user.User",
        on_delete=models.CASCADE,
        related_name="expenses",
    )

    department = models.ForeignKey(
        "user.Department",
        on_delete=models.CASCADE,
        related_name="expenses",
        null=True,
        blank=True,
    )

    date = models.DateField()
    description = models.CharField(max_length=255)
    amount = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))]
    )

    vendor = models.CharField(max_length=100, null=True, blank=True)

    category = models.CharField(
        max_length=50, choices=CATEGORY_CHOICES, default=CATEGORY_CHOICES.OTHER
    )

    status = models.CharField(max_length=20, choices=STATUS, default=STATUS.PENDING)

    attachment = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        verbose_name = "Expense"
        verbose_name_plural = "Expenses"
        indexes = [
            models.Index(fields=["user", "-date"]),
            models.Index(fields=["status"]),
            models.Index(fields=["category"]),
        ]

    def __str__(self):
        return f"{self.date} - {self.description} - {self.amount}"
