from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from user.models.base import BaseModel


class Transaction(BaseModel):
    """Model to track all wallet transactions"""

    TRANSACTION_TYPE_CHOICES = [
        ("credit", "Credit"),
        ("debit", "Debit"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]

    user = models.ForeignKey(
        "User", on_delete=models.CASCADE, related_name="transactions"
    )

    date = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=255)
    amount = models.DecimalField(
        max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPE_CHOICES)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="pending")
    reference = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        null=True,
        help_text="Unique reference for the transaction (e.g., invoice number)",
    )

    def clean(self):
        super().clean()
        valid_types = [choice[0] for choice in self.TRANSACTION_TYPE_CHOICES]
        if self.transaction_type and (self.transaction_type not in valid_types):
            raise ValidationError(
                {
                    "transaction_type": f"Invalid transaction type. Must be one of: {', '.join(valid_types)}"
                }
            )
        valid_statuses = [choice[0] for choice in self.STATUS_CHOICES]
        if self.status and (self.status not in valid_statuses):
            raise ValidationError(
                {
                    "status": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
                }
            )
        if self.amount is not None and self.amount <= Decimal("0.00"):
            raise ValidationError({"amount": "Amount must be greater than zero."})
        if not self.description or not self.description.strip():
            raise ValidationError({"description": "Description cannot be blank."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.transaction_type.upper()} - {self.amount} - {self.description}"

    class Meta:
        db_table = "transactions"
        ordering = ["-date"]
        indexes = [
            models.Index(fields=["-date"]),
            models.Index(fields=["user", "status"]),
            models.Index(fields=["transaction_type"]),
        ]
