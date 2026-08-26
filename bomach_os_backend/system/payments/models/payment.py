import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from user.models.base import BaseModel


class PaymentIntent(BaseModel):
    class STATUS(models.TextChoices):
        CREATED = "created", "Created"
        PROCESSING = "processing", "Processing"
        CONFIRMED = "confirmed", "Confirmed"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"

    reference = models.CharField(max_length=50, unique=True, editable=False)
    idempotency_key = models.CharField(max_length=160, unique=True)
    purpose_type = models.CharField(max_length=80)
    purpose_id = models.CharField(max_length=80)
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    currency = models.CharField(max_length=3, default="NGN")
    status = models.CharField(max_length=20, choices=STATUS.choices, default=STATUS.CREATED)
    description = models.CharField(max_length=255, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    branch = models.ForeignKey(
        "user.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_intents",
    )
    created_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_payment_intents",
    )

    # Immutable accounting snapshot, consumed only after money is verified.
    accounting_total_due = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    accounting_total_tax = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    accounting_prior_paid = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    revenue_account_code = models.CharField(max_length=30)

    class Meta:
        app_label = "user"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["purpose_type", "purpose_id"]),
            models.Index(fields=["status", "expires_at"]),
            models.Index(fields=["currency", "status"]),
        ]

    @property
    def outstanding_at_creation(self):
        return self.accounting_total_due - self.accounting_prior_paid

    def clean(self):
        super().clean()
        errors = {}
        if self.accounting_total_tax > self.accounting_total_due:
            errors["accounting_total_tax"] = "Tax cannot exceed the accounting total due."
        if self.accounting_prior_paid >= self.accounting_total_due:
            errors["accounting_prior_paid"] = (
                "Prior paid must be less than the accounting total due."
            )
        if self.amount > self.outstanding_at_creation:
            errors["amount"] = (
                "Payment intent amount exceeds the snapshotted outstanding balance."
            )
        if not (self.purpose_type or "").strip():
            errors["purpose_type"] = "Purpose type is required."
        if not (self.purpose_id or "").strip():
            errors["purpose_id"] = "Purpose id is required."
        if not (self.revenue_account_code or "").strip():
            errors["revenue_account_code"] = "A Finance revenue account code is required."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = f"PI-{uuid.uuid4().hex[:16].upper()}"
        self.currency = (self.currency or "NGN").upper()
        self.purpose_type = (self.purpose_type or "").strip()
        self.purpose_id = (self.purpose_id or "").strip()
        self.revenue_account_code = (self.revenue_account_code or "").strip().upper()
        if not kwargs.get("update_fields"):
            self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reference} · {self.amount} {self.currency}"


class PaymentAttempt(BaseModel):
    class STATUS(models.TextChoices):
        CREATED = "created", "Created"
        PENDING = "pending", "Pending"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"

    reference = models.CharField(max_length=50, unique=True, editable=False)
    intent = models.ForeignKey(PaymentIntent, on_delete=models.PROTECT, related_name="attempts")
    provider = models.CharField(max_length=50)
    idempotency_key = models.CharField(max_length=160)
    provider_reference = models.CharField(max_length=160, blank=True, default="")
    checkout_url = models.URLField(max_length=1000, blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS.choices, default=STATUS.CREATED)
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    currency = models.CharField(max_length=3)
    provider_metadata = models.JSONField(default=dict, blank=True)
    failure_code = models.CharField(max_length=80, blank=True, default="")
    failure_message = models.TextField(blank=True, default="")
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = "user"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["intent", "status"]),
            models.Index(fields=["provider", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "idempotency_key"],
                name="uniq_pay_attempt_provider_idem",
            ),
            models.UniqueConstraint(
                fields=["provider", "provider_reference"],
                condition=~Q(provider_reference=""),
                name="uniq_pay_attempt_provider_ref",
            ),
        ]

    def clean(self):
        super().clean()
        errors = {}
        if self.intent_id:
            if self.amount != self.intent.amount:
                errors["amount"] = "Attempt amount must exactly match its payment intent."
            if self.currency.upper() != self.intent.currency:
                errors["currency"] = "Attempt currency must exactly match its payment intent."
        if not (self.provider or "").strip():
            errors["provider"] = "Provider is required."
        if not (self.idempotency_key or "").strip():
            errors["idempotency_key"] = "Attempt idempotency key is required."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = f"PA-{uuid.uuid4().hex[:16].upper()}"
        self.provider = (self.provider or "").strip().lower()
        self.currency = (self.currency or "").upper()
        if not kwargs.get("update_fields"):
            self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reference} · {self.provider} · {self.status}"


class PaymentProviderEvent(BaseModel):
    class STATUS(models.TextChoices):
        RECEIVED = "received", "Received"
        PROCESSED = "processed", "Processed"
        FAILED = "failed", "Failed"
        IGNORED = "ignored", "Ignored"

    provider = models.CharField(max_length=50)
    event_key = models.CharField(max_length=180)
    event_type = models.CharField(max_length=100, blank=True, default="")
    payload = models.JSONField(default=dict)
    payload_digest = models.CharField(max_length=64)
    is_verified = models.BooleanField(default=False)
    verification_metadata = models.JSONField(default=dict, blank=True)
    intent = models.ForeignKey(
        PaymentIntent,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="provider_events",
    )
    attempt = models.ForeignKey(
        PaymentAttempt,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="provider_events",
    )
    receipt = models.ForeignKey(
        "ConfirmedReceipt",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="provider_events",
    )
    status = models.CharField(max_length=20, choices=STATUS.choices, default=STATUS.RECEIVED)
    processed_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True, default="")

    class Meta:
        app_label = "user"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["provider", "status"]),
            models.Index(fields=["intent", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "event_key"],
                name="uniq_pay_event_provider_key",
            )
        ]

    def save(self, *args, **kwargs):
        self.provider = (self.provider or "").strip().lower()
        self.event_key = (self.event_key or "").strip()
        if not self.provider:
            raise ValidationError({"provider": "Provider is required."})
        if not self.event_key:
            raise ValidationError({"event_key": "Provider event key is required."})
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.provider}:{self.event_key} · {self.status}"


class ConfirmedReceipt(BaseModel):
    reference = models.CharField(max_length=50, unique=True, editable=False)
    intent = models.OneToOneField(
        PaymentIntent,
        on_delete=models.PROTECT,
        related_name="confirmed_receipt",
    )
    attempt = models.OneToOneField(
        PaymentAttempt,
        on_delete=models.PROTECT,
        related_name="confirmed_receipt",
    )
    provider = models.CharField(max_length=50)
    provider_transaction_reference = models.CharField(max_length=180)
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    currency = models.CharField(max_length=3)
    paid_at = models.DateTimeField()
    payment_method = models.CharField(max_length=50, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    finance_account = models.ForeignKey(
        "finance.FinanceAccount",
        on_delete=models.PROTECT,
        related_name="central_confirmed_receipts",
    )
    finance_journal = models.OneToOneField(
        "finance.JournalEntry",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="central_confirmed_receipt",
    )
    finance_posted_at = models.DateTimeField(null=True, blank=True)
    application_reference = models.CharField(max_length=180, blank=True, default="")
    applied_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = "user"
        ordering = ["-paid_at", "-created_at"]
        indexes = [
            models.Index(fields=["provider", "paid_at"]),
            models.Index(fields=["applied_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "provider_transaction_reference"],
                name="uniq_confirmed_receipt_provider_ref",
            )
        ]

    def clean(self):
        super().clean()
        errors = {}
        if self.intent_id and self.attempt_id:
            if self.attempt.intent_id != self.intent_id:
                errors["attempt"] = "Receipt attempt must belong to the receipt intent."
            if self.provider != self.attempt.provider:
                errors["provider"] = "Receipt provider must match the payment attempt."
            if self.amount != self.intent.amount:
                errors["amount"] = "Confirmed receipt amount must match the payment intent."
            if self.currency.upper() != self.intent.currency:
                errors["currency"] = "Confirmed receipt currency must match the payment intent."
        if not (self.provider_transaction_reference or "").strip():
            errors["provider_transaction_reference"] = (
                "Provider transaction reference is required."
            )
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = f"CR-{uuid.uuid4().hex[:16].upper()}"
        self.provider = (self.provider or "").strip().lower()
        self.provider_transaction_reference = (
            self.provider_transaction_reference or ""
        ).strip()
        self.currency = (self.currency or "").upper()
        if not kwargs.get("update_fields"):
            self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reference} · {self.amount} {self.currency}"
