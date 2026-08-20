from ninja import Schema
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class PropertyIn(Schema):
    name: str
    property_type: str
    category: str
    location: str
    price: Decimal
    size: Decimal
    bedrooms: int = 0
    bathrooms: int = 0
    parking_spaces: int = 0
    description: Optional[str] = ""
    images: Optional[List[str]] = []
    status: str = "available"
    client_id: Optional[int] = None


class PropertyUpdate(Schema):
    name: Optional[str] = None
    property_type: Optional[str] = None
    category: Optional[str] = None
    location: Optional[str] = None
    price: Optional[Decimal] = None
    size: Optional[Decimal] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    parking_spaces: Optional[int] = None
    description: Optional[str] = None
    images: Optional[List[str]] = None
    status: Optional[str] = None
    client_id: Optional[int] = None


class PropertyOut(Schema):
    id: int
    name: str
    property_type: str
    category: str
    location: str
    price: Decimal
    size: Decimal
    bedrooms: int
    bathrooms: int
    parking_spaces: int
    description: str
    images: List[str]
    status: str
    client_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_images(obj):
        """Ensure images are always returned as a list of strings."""
        images = obj.images if isinstance(obj.images, list) else []
        result = []
        for img in images:
            if isinstance(img, str):
                result.append(img)
            elif isinstance(img, dict):
                result.append(img.get("url", img.get("image", str(img))))
            else:
                result.append(str(img))
        return result


class PropertyStatsOut(Schema):
    total_properties: int
    available: int
    reserved: int
    sold_rented: int
    for_sale: int
    for_rent: int
    for_lease: int
