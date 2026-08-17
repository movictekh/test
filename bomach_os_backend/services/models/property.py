from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class Property(models.Model):
    PROPERTY_TYPE_CHOICES = [
        ("residential", "Residential"),
        ("commercial", "Commercial"),
        ("industrial", "Industrial"),
        ("land", "Land"),
    ]

    CATEGORY_CHOICES = [
        ("sale", "For Sale"),
        ("rent", "For Rent"),
        ("lease", "For Lease"),
    ]

    STATUS_CHOICES = [
        ("available", "Available"),
        ("sold", "Sold"),
        ("rented", "Rented"),
        ("reserved", "Reserved"),
        ("pending", "Pending"),
        ("off_market", "Off Market"),
    ]

    name = models.CharField(max_length=255, verbose_name="Property Name")
    property_type = models.CharField(
        max_length=50, choices=PROPERTY_TYPE_CHOICES, verbose_name="Property Type"
    )
    category = models.CharField(
        max_length=50, choices=CATEGORY_CHOICES, verbose_name="Category"
    )

    location = models.TextField(verbose_name="Location/Address")

    price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Price",
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    size = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Size (sqm)",
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    bedrooms = models.PositiveIntegerField(default=0)
    bathrooms = models.PositiveIntegerField(default=0)
    parking_spaces = models.PositiveIntegerField(default=0)

    description = models.TextField(blank=True)
    images = models.JSONField(
        default=list, blank=True, verbose_name="Property Images (URLs)"
    )

    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default="available",
        verbose_name="Status",
    )
    client = models.ForeignKey(
        "user.Client",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="properties",
        verbose_name="Owner",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Property"
        verbose_name_plural = "Properties"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "category"]),
            models.Index(fields=["client"]),
            models.Index(fields=["property_type"]),
        ]

    def __str__(self):
        return self.name
