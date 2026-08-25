from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from user.models.base import BaseModel
from system.identity.models.user import User


class Loan(BaseModel):
    class STATUS(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    loan_amount = models.DecimalField(
        decimal_places=2, max_digits=10, validators=[MinValueValidator(Decimal("0.01"))]
    )

    employee = models.ForeignKey(User, on_delete=models.CASCADE)

    repayment_date = models.DateField()

    reason = models.TextField(max_length=500)

    emergency_contact_name = models.CharField(max_length=255)

    emergency_contact_phone = models.CharField(max_length=20)

    attachment = models.URLField()

    status = models.CharField(
        max_length=20, choices=STATUS.choices, default=STATUS.PENDING
    )

    def clean(self):
        super().clean()
        if self.loan_amount is not None and self.loan_amount <= Decimal("0.00"):
            raise ValidationError(
                {"loan_amount": "Loan amount must be greater than zero."}
            )

        if self.repayment_date and self.repayment_date <= timezone.now().date():
            raise ValidationError(
                {"repayment_date": "Repayment date must be in the future."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
