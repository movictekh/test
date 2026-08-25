"""Transitional Finance-owned payment model.

Invoice and InvoiceItem model source is owned by Service Operations.
Payment remains here so Finance-owned endpoint/business implementation is untouched.
"""

import uuid
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from domains.service_operations.models import Invoice, InvoiceItem


class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ("cash", "Cash"),
        ("bank_transfer", "Bank Transfer"),
        ("cheque", "Cheque"),
        ("card", "Card"),
        ("mobile_money", "Mobile Money"),
        ("other", "Other"),
    ]

    payment_reference = models.CharField(max_length=100, unique=True, editable=False)
    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name="payments"
    )
    amount = models.DecimalField(
        max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    payment_date = models.DateField()
    transaction_reference = models.CharField(max_length=255, blank=True)
    finance_account = models.ForeignKey(
        "finance.FinanceAccount",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="confirmed_payments",
    )
    proof_of_payment = models.URLField(blank=True, default="")
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        "user.User",
        on_delete=models.PROTECT,
        related_name="created_payments",
    )

    class Meta:
        app_label = "services"
        ordering = ["-payment_date"]

    def save(self, *args, **kwargs):
        from django.db import transaction

        # Auto-generate payment_reference
        if not self.payment_reference:
            self.payment_reference = f"PAY-{uuid.uuid4().hex[:12].upper()}"

        # Use atomic transaction with select_for_update to prevent race conditions
        with transaction.atomic():
            super().save(*args, **kwargs)

            # Lock the invoice row for update to prevent concurrent modifications
            invoice = Invoice.objects.select_for_update().get(pk=self.invoice_id)

            # Update invoice amount_paid with atomic calculation
            total_paid = invoice.payments.aggregate(total=models.Sum("amount"))[
                "total"
            ] or Decimal("0.00")
            invoice.amount_paid = total_paid

            # Update invoice status based on payment
            if total_paid >= invoice.total_amount:
                invoice.status = "paid"
            elif total_paid > 0:
                invoice.status = "partially_paid"

            if (
                invoice.activation_threshold_amount
                and total_paid >= invoice.activation_threshold_amount
                and not invoice.activation_threshold_met_at
            ):
                invoice.activation_threshold_met_at = timezone.now()

            invoice.save(
                update_fields=[
                    "amount_paid",
                    "status",
                    "activation_threshold_met_at",
                    "updated_at",
                ]
            )

    def __str__(self):
        return f"{self.payment_reference} - {self.invoice.invoice_number}"


__all__ = ["Invoice", "InvoiceItem", "Payment"]
