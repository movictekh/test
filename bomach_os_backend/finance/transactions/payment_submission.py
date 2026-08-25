"""Finance-owned payment evidence / review model."""

import uuid
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from domains.service_operations.models import Invoice
from finance.transactions.payment import Payment


class PaymentSubmission(models.Model):
    class Meta:
        app_label = "user"

    class STATUS(models.TextChoices):
        PENDING = "pending", "Pending Review"
        CONFIRMED = "confirmed", "Confirmed"
        REJECTED = "rejected", "Rejected"

    class SUBMITTED_BY_TYPE(models.TextChoices):
        CLIENT = "client", "Client"
        STAFF = "staff", "Staff"

    reference = models.CharField(max_length=100, unique=True, editable=False)
    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name="submissions"
    )
    client = models.ForeignKey(
        "user.Client", on_delete=models.CASCADE, related_name="payment_submissions"
    )
    amount = models.DecimalField(
        max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    payment_method = models.CharField(
        max_length=20, choices=Payment.PAYMENT_METHOD_CHOICES
    )
    payment_date = models.DateField()
    proof_of_payment = models.URLField()  # uploaded file URL
    receiving_account_text = models.CharField(max_length=255, blank=True, default="")
    finance_account = models.ForeignKey(
        "finance.FinanceAccount",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_submissions",
    )
    transaction_reference = models.CharField(max_length=255, blank=True, default="")
    notes = models.TextField(blank=True)

    status = models.CharField(
        max_length=20, choices=STATUS.choices, default=STATUS.PENDING
    )
    submitted_by = models.ForeignKey(
        "user.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="payment_submissions_created",
    )
    submitted_by_type = models.CharField(
        max_length=20,
        choices=SUBMITTED_BY_TYPE.choices,
        default=SUBMITTED_BY_TYPE.CLIENT,
    )
    reviewed_by = models.ForeignKey(
        "user.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_submissions",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default="")
    confirmed_payment = models.OneToOneField(
        Payment,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="source_submission",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = f"SUB-{uuid.uuid4().hex[:12].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reference} - {self.invoice.invoice_number}"
