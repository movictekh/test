from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from decimal import Decimal

from user.models.base import BaseModel
from user.models.estate import Property


class Cart(BaseModel):
    """Shopping cart for a user to hold properties before checkout"""

    user = models.OneToOneField(
        "User",
        on_delete=models.CASCADE,
        related_name="cart",
        verbose_name="User",
    )

    class Meta:
        verbose_name = "Cart"
        verbose_name_plural = "Carts"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Cart for {self.user.get_full_name() or self.user.email}"

    @property
    def total_items(self):
        return self.items.count()

    @property
    def total_price(self):
        total = self.items.aggregate(total=models.Sum("price"))["total"]
        return total or Decimal("0.00")


class CartItem(BaseModel):
    """Individual property item in a cart"""

    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Cart",
    )
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="cart_items",
        verbose_name="Property",
    )
    price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name="Price at time of adding",
        help_text="Snapshot of the property price when added to cart",
    )

    class Meta:
        verbose_name = "Cart Item"
        verbose_name_plural = "Cart Items"
        unique_together = ["cart", "property"]
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["cart", "property"]),
        ]

    def __str__(self):
        return f"{self.property.property_name} in cart"

    def clean(self):
        super().clean()
        if hasattr(self, "property") and self.property_id:
            if self.property.status == "sold":
                raise ValidationError(
                    {"property": "Cannot add a sold property to cart."}
                )

    def save(self, *args, **kwargs):
        # Snapshot the price from the property if not explicitly set
        if not self.price and self.property_id:
            self.price = self.property.price
        if not kwargs.get("update_fields"):
            self.full_clean()
        super().save(*args, **kwargs)
