from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid
from services.models.service import Quote, Service, ServiceLead, ServiceOrder, ServiceRequest


class Invoice(models.Model):
    INVOICE_STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('viewed', 'Viewed'),
        ('partially_paid', 'Partially Paid'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]

    invoice_number = models.CharField(max_length=50, unique=True, editable=False)

    client = models.ForeignKey(
        'user.Client',
        on_delete=models.PROTECT,
        related_name='svc_invoices',
    )

    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name='invoices')
    quote = models.ForeignKey(Quote, on_delete=models.PROTECT, null=True, blank=True, related_name='invoices')
    service_request = models.ForeignKey(
        ServiceRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoices',
    )
    order = models.ForeignKey(ServiceOrder, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    lead = models.ForeignKey(ServiceLead, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')

    issue_date = models.DateField()
    due_date = models.DateField()

    subtotal = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('7.50'), validators=[MinValueValidator(Decimal('0.00'))])
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    amount_paid = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'), validators=[MinValueValidator(Decimal('0.00'))])

    status = models.CharField(max_length=20, choices=INVOICE_STATUS_CHOICES, default='draft')
    payment_schedule = models.CharField(max_length=80, blank=True)
    payment_instructions = models.TextField(blank=True)
    activation_threshold_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    activation_threshold_met_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'user.User',
        on_delete=models.PROTECT,
        related_name='created_invoices',
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['client']),
            models.Index(fields=['status']),
            models.Index(fields=['quote', 'status']),
            models.Index(fields=['service_request', 'status']),
        ]

    def save(self, *args, **kwargs):
        # Auto-generate invoice_number
        if not self.invoice_number:
            from datetime import datetime
            year = datetime.now().year
            month = datetime.now().month
            random_id = uuid.uuid4().hex[:12].upper()
            self.invoice_number = f"SRV-{year}-{month:02d}-{random_id}"

        # Calculate tax and total
        self.tax_amount = (self.subtotal * self.tax_rate) / Decimal('100')
        self.total_amount = self.subtotal + self.tax_amount

        super().save(*args, **kwargs)

    @property
    def balance(self):
        return self.total_amount - self.amount_paid

    @property
    def payment_progress(self):
        if self.total_amount == 0:
            return 0
        return (self.amount_paid / self.total_amount) * 100

    def __str__(self):
        return f"{self.invoice_number}"


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    unit_price = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    total = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['id']

    def save(self, *args, **kwargs):
        self.total = self.quantity * self.unit_price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.invoice.invoice_number} - {self.description}"


class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('cheque', 'Cheque'),
        ('card', 'Card'),
        ('mobile_money', 'Mobile Money'),
        ('other', 'Other'),
    ]

    payment_reference = models.CharField(max_length=100, unique=True, editable=False)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    payment_date = models.DateField()
    transaction_reference = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'user.User',
        on_delete=models.PROTECT,
        related_name='created_payments',
    )

    class Meta:
        ordering = ['-payment_date']

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
            total_paid = invoice.payments.aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
            invoice.amount_paid = total_paid

            # Update invoice status based on payment
            if total_paid >= invoice.total_amount:
                invoice.status = 'paid'
            elif total_paid > 0:
                invoice.status = 'partially_paid'

            if (
                invoice.activation_threshold_amount
                and total_paid >= invoice.activation_threshold_amount
                and not invoice.activation_threshold_met_at
            ):
                invoice.activation_threshold_met_at = timezone.now()

            invoice.save(update_fields=['amount_paid', 'status', 'activation_threshold_met_at', 'updated_at'])

    def __str__(self):
        return f"{self.payment_reference} - {self.invoice.invoice_number}"
