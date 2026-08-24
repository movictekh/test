from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from ninja import Schema


class CartItemCreateSchema(Schema):
    """Schema for adding a property to the cart"""

    property_id: int


class CartItemSchema(Schema):
    """Schema for a cart item response"""

    id: int
    property_id: int
    property_name: str
    property_type: str
    property_type_display: str
    estate_id: int
    estate_name: str
    estate_code: str
    status: str
    status_display: str
    price: Decimal
    # Property-specific summary fields
    plot_size: Optional[Decimal] = None
    plot_size_unit: Optional[str] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    total_area: Optional[Decimal] = None
    floors: Optional[int] = None
    thumbnail: Optional[str] = None
    created_at: datetime

    @staticmethod
    def resolve_property_name(obj):
        return obj.property.property_name

    @staticmethod
    def resolve_property_type(obj):
        return obj.property.property_type

    @staticmethod
    def resolve_property_type_display(obj):
        return obj.property.get_property_type_display()

    @staticmethod
    def resolve_estate_id(obj):
        return obj.property.estate_id

    @staticmethod
    def resolve_estate_name(obj):
        return obj.property.estate.estate_name

    @staticmethod
    def resolve_estate_code(obj):
        return obj.property.estate.estate_code

    @staticmethod
    def resolve_status(obj):
        return obj.property.status

    @staticmethod
    def resolve_status_display(obj):
        return obj.property.get_status_display()

    @staticmethod
    def resolve_plot_size(obj):
        return obj.property.plot_size

    @staticmethod
    def resolve_plot_size_unit(obj):
        return obj.property.plot_size_unit or None

    @staticmethod
    def resolve_bedrooms(obj):
        return obj.property.bedrooms

    @staticmethod
    def resolve_bathrooms(obj):
        return obj.property.bathrooms

    @staticmethod
    def resolve_total_area(obj):
        return obj.property.total_area

    @staticmethod
    def resolve_floors(obj):
        return obj.property.floors

    @staticmethod
    def resolve_thumbnail(obj):
        first_image = obj.property.images.first()
        if first_image and first_image.image:
            return first_image.image.url
        return None


class CartSchema(Schema):
    """Schema for the full cart response"""

    id: int
    items: List[CartItemSchema]
    total_items: int
    total_price: Decimal
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_items(obj):
        return list(
            obj.items.select_related("property", "property__estate")
            .prefetch_related("property__images")
            .all()
        )

    @staticmethod
    def resolve_total_items(obj):
        return obj.total_items

    @staticmethod
    def resolve_total_price(obj):
        return obj.total_price
