from datetime import datetime
from decimal import Decimal
from typing import Optional

from ninja import Schema
from pydantic import EmailStr


class PurchaseClientSchema(Schema):
    id: int
    user_id: int
    full_name: str
    email: str
    phone: str
    company_name: str

    @staticmethod
    def resolve_user_id(obj):
        return obj.user_id

    @staticmethod
    def resolve_full_name(obj):
        return obj.user.get_full_name() or obj.user.email

    @staticmethod
    def resolve_email(obj):
        return obj.user.email

    @staticmethod
    def resolve_phone(obj):
        return obj.phone or obj.user.phone_number or ""

    @staticmethod
    def resolve_company_name(obj):
        return obj.company_name or ""


class PurchaseClientCreateSchema(Schema):
    email: EmailStr
    first_name: str
    last_name: str
    phone_number: Optional[str] = None
    company_name: Optional[str] = None
    send_portal_invite: bool = False


class PropertyPurchaseCreateSchema(Schema):
    property_id: int
    client_id: int
    mode: str
    agreed_price: Optional[Decimal] = None
    installment_months: Optional[int] = None


class PropertyPurchaseSchema(Schema):
    id: int
    property_id: int
    property_name: str
    estate_id: int
    estate_name: str
    client_id: int
    client_user_id: int
    client_name: str
    client_email: str
    invoice_id: Optional[int]
    mode: str
    agreed_price: Decimal
    reservation_threshold_percent: Optional[Decimal]
    reservation_amount: Optional[Decimal]
    installment_months: Optional[int]
    payment_window_hours: int
    payment_window_expires_at: Optional[datetime]
    approved_at: Optional[datetime]
    next_payment_due_at: Optional[datetime]
    status: str
    amount_paid: Decimal
    reserved_at: Optional[datetime]
    completed_at: Optional[datetime]
    cancelled_at: Optional[datetime]
    created_by_id: int
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_property_name(obj):
        return obj.property.property_name

    @staticmethod
    def resolve_estate_id(obj):
        return obj.property.estate_id

    @staticmethod
    def resolve_estate_name(obj):
        return obj.property.estate.estate_name

    @staticmethod
    def resolve_client_user_id(obj):
        return obj.client.user_id

    @staticmethod
    def resolve_client_name(obj):
        return obj.client.user.get_full_name() or obj.client.user.email

    @staticmethod
    def resolve_client_email(obj):
        return obj.client.user.email


class PropertyPurchasePaymentAttemptSchema(Schema):
    intent_reference: str
    attempt_reference: str
    provider: str
    provider_reference: str
    amount: Decimal
    currency: str
    checkout_url: str
    expires_at: Optional[datetime]
    provider_metadata: dict
