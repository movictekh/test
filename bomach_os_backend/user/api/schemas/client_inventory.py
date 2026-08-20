from ninja import Schema
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

# ============== Inventory Item Schemas ==============


class CreateInventoryItemRequest(Schema):
    """Schema for creating a new inventory item"""

    item_name: str
    quantity: Decimal
    quantity_used: Optional[Decimal] = None
    unit: str  # "bags", "uni", "tons"
    total_value: Decimal
    status: str  # "available", "low", "percentage"


class UpdateInventoryItemRequest(Schema):
    """Schema for updating an inventory item"""

    item_name: Optional[str] = None
    quantity: Optional[Decimal] = None
    quantity_used: Optional[Decimal] = None
    unit: Optional[str] = None
    total_value: Optional[Decimal] = None
    status: Optional[str] = None


class InventoryItemResponse(Schema):
    """Schema for inventory item response"""

    id: int
    item_name: str
    quantity: Decimal
    quantity_used: Decimal

    unit: str
    unit_display: str
    total_value: Decimal
    formatted_value: str
    unit_price: Decimal
    status: str
    status_display: str
    is_low_stock: bool
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_unit_display(obj):
        """Get human-readable unit name"""
        return dict(obj.UNIT_CHOICES).get(obj.unit, obj.unit)

    @staticmethod
    def resolve_status_display(obj):
        """Get human-readable status name"""
        return dict(obj.STATUS_CHOICES).get(obj.status, obj.status)

    @staticmethod
    def resolve_formatted_value(obj):
        """Get formatted currency value"""
        return obj.formatted_value()

    @staticmethod
    def resolve_unit_price(obj):
        """Calculate unit price"""
        return obj.get_unit_price()

    @staticmethod
    def resolve_is_low_stock(obj):
        """Check if item is low in stock"""
        return obj.is_low_stock()
