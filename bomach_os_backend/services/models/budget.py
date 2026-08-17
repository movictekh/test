from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from services.models.payment import Invoice


class Budget(models.Model):
    class FISCAL_PERIOD(models.TextChoices):
        Q1_2026 = "Q1 2026"
        Q2_2026 = "Q2 2026"
        Q3_2026 = "Q3 2026"
        Q4_2026 = "Q4 2026"

    branch = models.ForeignKey("user.Branch", on_delete=models.CASCADE)

    department = models.ForeignKey("user.Department", on_delete=models.CASCADE)

    fiscal_period = models.CharField(
        max_length=20, choices=FISCAL_PERIOD.choices, null=True, blank=True
    )

    current_spend = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        blank=True,
        default=Decimal("0.00"),
        help_text="Amount of the budget that has been spent",
    )

    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Budget amount",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["fiscal_period"]),
        ]
        unique_together = [["branch", "department", "fiscal_period"]]

    def __str__(self):
        return f"Budget amount - {self.amount}"

    @property
    def amount_display(self):
        return f"{self.amount:,.2f}"
