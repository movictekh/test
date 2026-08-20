from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from decimal import Decimal
import uuid
from django.utils import timezone

from user.models.base import BaseModel
from user.models.estate import Property


class EstatePropertyInvoice(BaseModel):
    """Invoice for estate properties — a user can add multiple properties to one invoice."""

    INVOICE_STATUS_CHOICES = [
        ("draft", "Draft"),
        ("approved", "Approved"),
        ("sent", "Sent"),
        ("partially_paid", "Partially Paid"),
        ("paid", "Paid"),
        ("overdue", "Overdue"),
        ("cancelled", "Cancelled"),
    ]

    INVOICE_TYPE_CHOICES = [
        ("full-payment", "Full Payment"),
        ("installment", "Installment Plan"),
        ("reserve-fee", "Reserve Fee"),
    ]

    invoice_number = models.CharField(max_length=50, unique=True, editable=False)

    invoice_type = models.CharField(
        max_length=20,
        choices=INVOICE_TYPE_CHOICES,
        default="full-payment",
    )

    installment_spread_months = models.IntegerField(
        null=True,
        blank=True,
    )

    reserve_fee_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    client = models.ForeignKey(
        "user.User",
        on_delete=models.PROTECT,
        related_name="estate_invoices",
    )

    issue_date = models.DateField()
    due_date = models.DateField()

    subtotal = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("7.50"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    tax_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    total_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    amount_paid = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    status = models.CharField(
        max_length=20, choices=INVOICE_STATUS_CHOICES, default="draft"
    )
    payment_completed_date = models.DateField(null=True, blank=True)

    notes = models.TextField(blank=True)

    sort_code = models.CharField(max_length=255, blank=True, null=True)
    bank_code = models.CharField(max_length=255, blank=True, null=True)
    bank_name = models.CharField(max_length=255, blank=True, null=True)
    account_number = models.CharField(max_length=255, blank=True, null=True)
    account_name = models.CharField(max_length=255, blank=True, null=True)
    bank_details_expires_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        "user.User",
        on_delete=models.PROTECT,
        related_name="created_estate_invoices",
    )

    class Meta:
        verbose_name = "Estate Property Invoice"
        verbose_name_plural = "Estate Property Invoices"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["client"]),
            models.Index(fields=["status"]),
            models.Index(fields=["due_date"]),
        ]

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            from datetime import datetime

            year = datetime.now().year
            month = datetime.now().month
            random_id = uuid.uuid4().hex[:12].upper()
            self.invoice_number = f"EST-{year}-{month:02d}-{random_id}"

        self.tax_amount = (self.subtotal * self.tax_rate) / Decimal("100")
        self.total_amount = self.subtotal + self.tax_amount

        super().save(*args, **kwargs)

    def generate_payment_details(self):
        """Regenerate payment details based on client's default payment info."""
        if (
            self.bank_details_expires_at
            and self.bank_details_expires_at > timezone.now()
        ):
            return  # Still valid, no need to regenerate

        self.sort_code = "000000"  # Placeholder sort code
        self.bank_code = "000000"  # Placeholder bank code
        self.bank_name = "Placeholder Bank Name"  # Placeholder bank name
        self.account_number = "00000000"  # Placeholder account number
        self.account_name = "Placeholder Account Name"  # Placeholder account name
        self.save()

    def recalculate_subtotal(self):
        """Recalculate subtotal from invoice items and save."""
        self.subtotal = self.estate_invoice_items.aggregate(total=models.Sum("total"))[
            "total"
        ] or Decimal("0.00")
        self.save()

    def clean(self):
        super().clean()
        # Calculate expected total from items
        items_total = self.estate_invoice_items.aggregate(total=models.Sum("total"))[
            "total"
        ] or Decimal("0.00")
        expected_tax = (items_total * self.tax_rate) / Decimal("100")
        expected_total = items_total + expected_tax

        if self.total_amount < expected_total:
            raise ValidationError(
                {
                    "total_amount": f"Total amount cannot be less than the sum of items ({items_total}) plus tax ({expected_tax}). Expected minimum: {expected_total}."
                }
            )

        if self.invoice_type == "installment" and not self.installment_spread_months:
            raise ValidationError(
                {
                    "installment_spread_months": "Installment spread months must be set for installment invoices."
                }
            )

        if self.due_date and self.issue_date and self.due_date < self.issue_date:
            raise ValidationError({"due_date": "Due date cannot be before issue date."})

    @property
    def balance(self):
        return self.total_amount - self.amount_paid

    @property
    def payment_progress(self):
        if self.total_amount == 0:
            return 0
        return (self.amount_paid / self.total_amount) * 100

    @property
    def property_count(self):
        return self.estate_invoice_items.count()

    def __str__(self):
        return f"{self.invoice_number}"


class EstatePropertyInvoiceItem(BaseModel):
    """Line item linking a property to an invoice."""

    invoice = models.ForeignKey(
        EstatePropertyInvoice,
        on_delete=models.CASCADE,
        related_name="estate_invoice_items",
    )
    property = models.ForeignKey(
        Property,
        on_delete=models.PROTECT,
        related_name="invoice_items",
    )
    description = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Optional override description. Defaults to property name.",
    )
    quantity = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(1)],
        help_text="Quantity is fixed at 1 since each item represents a single property.",
    )
    unit_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Defaults to property price if not provided.",
    )
    total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    class Meta:
        verbose_name = "Invoice Item"
        verbose_name_plural = "Invoice Items"
        ordering = ["created_at"]

    def save(self, *args, **kwargs):
        if not self.description:
            self.description = (
                f"{self.property.property_name} - {self.property.estate.estate_name}"
            )
        if not self.unit_price:
            self.unit_price = self.property.price
        self.total = self.quantity * self.unit_price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.invoice.invoice_number} - {self.description}"


class InvoiceApproval(BaseModel):
    """Tracks each approval step for an estate property invoice.
    Flow: Step 1 (Manager) → Step 2 (CEO) → Invoice marked 'sent'.
    """

    STEP_CHOICES = [
        (1, "Manager Approval"),
        (2, "CEO Approval"),
    ]

    DECISION_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    invoice = models.ForeignKey(
        EstatePropertyInvoice,
        on_delete=models.CASCADE,
        related_name="approvals",
    )
    step = models.PositiveIntegerField(choices=STEP_CHOICES)
    step_name = models.CharField(max_length=50)
    required_level = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text="Minimum employee level needed for this step.",
    )
    assigned_to = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_invoice_approvals",
        help_text="Specific user assigned to approve this step.",
    )
    decision = models.CharField(
        max_length=10,
        choices=DECISION_CHOICES,
        default="pending",
    )
    decided_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoice_approval_decisions",
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    comment = models.TextField(blank=True)

    class Meta:
        verbose_name = "Invoice Approval"
        verbose_name_plural = "Invoice Approvals"
        unique_together = ("invoice", "step")
        ordering = ["step"]

    def __str__(self):
        return f"{self.invoice.invoice_number} — Step {self.step}: {self.get_decision_display()}"
