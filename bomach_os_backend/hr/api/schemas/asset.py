from datetime import date, datetime
from decimal import Decimal
from typing import List, Literal, Optional

from ninja import Schema
from pydantic import Field, field_validator

from hr.models.asset import Asset

ASSET_TYPE_MAP = {value.lower(): value for value, _label in Asset.ASSET_TYPE_CHOICES}
ASSET_TYPE_MAP.update(
    {label.lower(): value for value, label in Asset.ASSET_TYPE_CHOICES}
)


class AssetDocument(Schema):
    name: str
    type: Literal["Document", "Image"]
    url: Optional[str] = None


def normalize_asset_type(value: Optional[str]) -> Optional[str]:
    if value is None:
        return value

    if not isinstance(value, str):
        return value

    normalized = ASSET_TYPE_MAP.get(value.lower())
    if not normalized:
        valid_types = ", ".join(sorted(ASSET_TYPE_MAP))
        raise ValueError(f"Invalid asset_type. Must be one of: {valid_types}")
    return normalized


class AssetCreate(Schema):
    name: str
    asset_type: str
    branch: str
    assigned_to_id: Optional[int] = None
    department_id: Optional[int] = None
    purchase_date: Optional[date] = None
    value: Optional[Decimal] = None
    vendor: Optional[str] = None
    invoice_number: Optional[str] = None
    status: Optional[str] = "available"
    warranty_expiry_date: Optional[date] = None
    documents: List[AssetDocument] = Field(default_factory=list)
    notes: Optional[str] = None
    serial_number: Optional[str] = None
    imei: Optional[str] = None
    manufacturer: Optional[str] = None

    @field_validator("asset_type", mode="before")
    @classmethod
    def validate_asset_type(cls, value):
        return normalize_asset_type(value)


class AssetUpdate(Schema):
    name: Optional[str] = None
    asset_type: Optional[str] = None
    branch: Optional[str] = None
    assigned_to_id: Optional[int] = None
    department_id: Optional[int] = None
    purchase_date: Optional[date] = None
    value: Optional[Decimal] = None
    vendor: Optional[str] = None
    invoice_number: Optional[str] = None
    status: Optional[str] = None
    warranty_expiry_date: Optional[date] = None
    documents: List[AssetDocument] = None
    notes: Optional[str] = None
    serial_number: Optional[str] = None
    imei: Optional[str] = None
    manufacturer: Optional[str] = None

    @field_validator("asset_type", mode="before")
    @classmethod
    def validate_asset_type(cls, value):
        return normalize_asset_type(value)


class AssetOut(Schema):
    name: str
    asset_type: str
    branch: str
    assigned_to_id: Optional[int] = None
    department_id: Optional[int] = None
    purchase_date: Optional[date] = None
    value: Optional[Decimal] = None
    vendor: Optional[str] = None
    invoice_number: Optional[str] = None
    status: str
    warranty_expiry_date: Optional[date] = None
    notes: Optional[str] = None
    serial_number: Optional[str] = None
    imei: Optional[str] = None
    manufacturer: Optional[str] = None
    documents: List[AssetDocument] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
