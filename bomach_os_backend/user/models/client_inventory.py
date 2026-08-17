from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from user.models.base import BaseModel


class CLientInventoryItem(BaseModel):
    STATUS_AVAILABLE = "available"
    STATUS_LOW = "low"
    STATUS_PERCENTAGE = "percentage"

    STATUS_CHOICES = [
        (STATUS_AVAILABLE, "Available"),
        (STATUS_LOW, "Low"),
        (STATUS_PERCENTAGE, "Percentage"),
    ]

    UNIT_BAGS = "bags"
    UNIT_UNITS = "uni"
    UNIT_TONS = "tons"

    UNIT_CHOICES = [
        (UNIT_BAGS, "Bags"),
        (UNIT_UNITS, "Units"),
        (UNIT_TONS, "Tons"),
    ]

    item_name = models.CharField(
        max_length=200, verbose_name="Item Name", help_text="Name of the inventory item"
    )

    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="Quantity",
        help_text="Quantity available",
    )

    quantity_used = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="Quantity",
        help_text="Quantity available",
    )

    unit = models.CharField(
        max_length=10,
        choices=UNIT_CHOICES,
        verbose_name="Unit",
        help_text="Unit of measurement",
    )

    total_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="Total Value",
        help_text="Total value",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        verbose_name="Status",
        help_text="Current status of the item",
    )

    class Meta:
        verbose_name = "Inventory Item"
        verbose_name_plural = "Inventory Items"
        ordering = ["item_name"]
        indexes = [
            models.Index(fields=["item_name"]),
            models.Index(fields=["status"]),
        ]

    def clean(self):
        super().clean()
        if not self.item_name or not self.item_name.strip():
            raise ValidationError({"item_name": "Item name cannot be blank."})
        valid_units = [choice[0] for choice in self.UNIT_CHOICES]
        if self.unit and (self.unit not in valid_units):
            raise ValidationError(
                {"unit": f"Invalid unit. Must be one of: {', '.join(valid_units)}"}
            )
        valid_statuses = [choice[0] for choice in self.STATUS_CHOICES]
        if self.status and (self.status not in valid_statuses):
            raise ValidationError(
                {
                    "status": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
                }
            )
        if self.quantity is not None and self.quantity_used is not None:
            if self.quantity_used > self.quantity:
                raise ValidationError(
                    {"quantity_used": "Quantity used cannot exceed total quantity."}
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.item_name} - {self.quantity} {self.unit}"

    def get_unit_price(self):
        """Calculate unit price"""
        if self.quantity > 0:
            return self.total_value / self.quantity
        return Decimal("0.00")

    def is_low_stock(self):
        """Check if item is low in stock"""
        return self.status == self.STATUS_LOW

    def formatted_value(self):
        """Return formatted currency value"""
        return f"₦{self.total_value:,.2f}"
