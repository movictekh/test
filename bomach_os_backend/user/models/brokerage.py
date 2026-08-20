from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import (
    FileExtensionValidator,
    MaxValueValidator,
    MinValueValidator,
)
from decimal import Decimal

from user.models.base import BaseModel


class BrokerageListing(BaseModel):
    """Third-party property listing managed on a commission basis."""

    VERIFICATION_STATUS_CHOICES = [
        ("pending", "Pending Verification"),
        ("verified", "Verified"),
        ("inspection_due", "Inspection Due"),
    ]

    LISTING_STATUS_CHOICES = [
        ("available", "Available"),
        ("sold", "Sold"),
        ("off_market", "Off Market"),
    ]

    PROPERTY_TYPE_CHOICES = [
        ("residential", "Residential"),
        ("commercial", "Commercial"),
        ("land", "Land"),
    ]

    # Basic Information
    title = models.CharField(
        max_length=255,
        verbose_name="Title",
    )
    description = models.TextField(
        blank=True,
        default="",
        verbose_name="Description",
    )
    location = models.CharField(
        max_length=500,
        verbose_name="Location",
    )
    price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name="Price",
    )
    property_type = models.CharField(
        max_length=50,
        choices=PROPERTY_TYPE_CHOICES,
        verbose_name="Property Type",
    )

    # Owner / Mandate Giver
    owner_name = models.CharField(
        max_length=255,
        verbose_name="Owner / Mandate Giver",
    )
    owner_phone = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name="Owner Phone",
    )
    owner_email = models.EmailField(
        blank=True,
        default="",
        verbose_name="Owner Email",
    )

    # Commission
    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
        default=Decimal("5.00"),
        verbose_name="Commission Rate (%)",
        help_text="Commission percentage, e.g. 5.00",
    )

    # Status
    verification_status = models.CharField(
        max_length=20,
        choices=VERIFICATION_STATUS_CHOICES,
        default="pending",
        verbose_name="Verification Status",
    )
    status = models.CharField(
        max_length=20,
        choices=LISTING_STATUS_CHOICES,
        default="available",
        verbose_name="Status",
    )

    # Assignment
    assigned_agent = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="brokerage_listings",
        verbose_name="Assigned Agent",
    )

    # Optional link to an estate
    estate = models.ForeignKey(
        "user.Estate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="brokerage_listings",
        verbose_name="Estate",
    )

    # Metadata
    tags = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Tags",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Is Active",
    )

    class Meta:
        verbose_name = "Brokerage Listing"
        verbose_name_plural = "Brokerage Listings"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["verification_status"]),
            models.Index(fields=["property_type"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.location})"

    def clean(self):
        super().clean()
        if not self.title or not self.title.strip():
            raise ValidationError({"title": "Title cannot be blank."})
        if not self.location or not self.location.strip():
            raise ValidationError({"location": "Location cannot be blank."})
        valid_verification = [c[0] for c in self.VERIFICATION_STATUS_CHOICES]
        if (
            self.verification_status
            and self.verification_status not in valid_verification
        ):
            raise ValidationError(
                {
                    "verification_status": f"Invalid status. Must be one of: {', '.join(valid_verification)}"
                }
            )
        valid_statuses = [c[0] for c in self.LISTING_STATUS_CHOICES]
        if self.status and self.status not in valid_statuses:
            raise ValidationError(
                {
                    "status": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
                }
            )

    def save(self, *args, **kwargs):
        if not kwargs.get("update_fields"):
            self.full_clean()
        super().save(*args, **kwargs)


class BrokerageListingImage(BaseModel):
    """Images for a brokerage listing."""

    listing = models.ForeignKey(
        BrokerageListing,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name="Listing",
    )
    image = models.FileField(
        upload_to="brokerage/images/",
        validators=[FileExtensionValidator(allowed_extensions=["png", "jpg", "jpeg"])],
        verbose_name="Image",
        help_text="PNG, JPG up to 10MB",
    )
    caption = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Caption",
    )

    class Meta:
        verbose_name = "Brokerage Listing Image"
        verbose_name_plural = "Brokerage Listing Images"
        ordering = ["created_at"]

    def __str__(self):
        return f"Image for {self.listing.title}"
