from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from domains.real_estate.models.estate import Property
from user.models.base import BaseModel


class PropertyPurchase(BaseModel):
    MODE_FULL_PAYMENT = "full_payment"
    MODE_RESERVATION = "reservation"
    MODE_INSTALLMENT = "installment"
    MODE_CHOICES = [
        (MODE_FULL_PAYMENT, "Full Payment"),
        (MODE_RESERVATION, "Reservation"),
        (MODE_INSTALLMENT, "Installment"),
    ]

    STATUS_AWAITING_APPROVAL = "awaiting_approval"
    STATUS_AWAITING_PAYMENT = "awaiting_payment"
    STATUS_RESERVED = "reserved"
    STATUS_INSTALLMENT_ACTIVE = "installment_active"
    STATUS_FULLY_PAID = "fully_paid"
    STATUS_CANCELLED = "cancelled"
    STATUS_EXPIRED = "expired"
    STATUS_DEFAULTED = "defaulted"
    STATUS_CHOICES = [
        (STATUS_AWAITING_APPROVAL, "Awaiting Approval"),
        (STATUS_AWAITING_PAYMENT, "Awaiting Payment"),
        (STATUS_RESERVED, "Reserved"),
        (STATUS_INSTALLMENT_ACTIVE, "Installment Active"),
        (STATUS_FULLY_PAID, "Fully Paid"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_EXPIRED, "Expired"),
        (STATUS_DEFAULTED, "Defaulted"),
    ]
    ACTIVE_STATUSES = (
        STATUS_AWAITING_APPROVAL,
        STATUS_AWAITING_PAYMENT,
        STATUS_RESERVED,
        STATUS_INSTALLMENT_ACTIVE,
    )

    property = models.ForeignKey(Property, on_delete=models.PROTECT, related_name="purchases")
    client = models.ForeignKey("user.Client", on_delete=models.PROTECT, related_name="property_purchases")
    invoice = models.ForeignKey(
        "user.EstatePropertyInvoice",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="property_purchases",
    )
    mode = models.CharField(max_length=20, choices=MODE_CHOICES)
    agreed_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    reservation_threshold_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.01")), MaxValueValidator(Decimal("100.00"))],
    )
    reservation_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    installment_months = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
    )
    payment_window_expires_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_AWAITING_APPROVAL)
    amount_paid = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    reserved_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        "user.User",
        on_delete=models.PROTECT,
        related_name="created_property_purchases",
    )

    class Meta:
        app_label = "user"
        verbose_name = "Property Purchase"
        verbose_name_plural = "Property Purchases"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["property", "status"]),
            models.Index(fields=["client", "status"]),
            models.Index(fields=["payment_window_expires_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["property"],
                condition=models.Q(
                    status__in=[
                        "awaiting_approval",
                        "awaiting_payment",
                        "reserved",
                        "installment_active",
                    ]
                ),
                name="unique_active_property_purchase",
            )
        ]

    def clean(self):
        super().clean()
        if self.amount_paid > self.agreed_price:
            raise ValidationError({"amount_paid": "Amount paid cannot exceed the agreed purchase price."})
        has_percent = self.reservation_threshold_percent is not None
        has_amount = self.reservation_amount is not None
        if has_percent != has_amount:
            raise ValidationError(
                {"reservation_amount": "Reservation percentage and amount must be snapshotted together."}
            )
        if self.mode == self.MODE_FULL_PAYMENT:
            if has_percent or self.installment_months is not None:
                raise ValidationError(
                    {"mode": "Full-payment purchases cannot carry reservation or installment terms."}
                )
        elif self.mode == self.MODE_RESERVATION:
            if not has_percent:
                raise ValidationError(
                    {"reservation_threshold_percent": "Reservation purchases require a policy snapshot."}
                )
            if self.installment_months is not None:
                raise ValidationError(
                    {"installment_months": "Reservation purchases cannot carry installment months."}
                )
        elif self.mode == self.MODE_INSTALLMENT and self.installment_months is None:
            raise ValidationError(
                {"installment_months": "Installment purchases require an installment duration."}
            )

    def save(self, *args, **kwargs):
        if not kwargs.get("update_fields"):
            self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.property} - {self.client} ({self.status})"
