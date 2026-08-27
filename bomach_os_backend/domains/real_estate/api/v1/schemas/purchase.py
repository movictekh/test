from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from django.utils import timezone
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


class ChoiceItemSchema(Schema):
    value: str
    label: str


class PropertyPurchaseChoicesSchema(Schema):
    mode: list[ChoiceItemSchema]
    status: list[ChoiceItemSchema]


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
    mode_display: str
    agreed_price: Decimal
    reservation_threshold_percent: Optional[Decimal]
    reservation_amount: Optional[Decimal]
    installment_months: Optional[int]
    payment_window_hours: int
    payment_window_expires_at: Optional[datetime]
    approved_at: Optional[datetime]
    next_payment_due_at: Optional[datetime]
    status: str
    status_display: str
    amount_paid: Decimal
    outstanding_balance: Decimal
    payment_progress_percent: Decimal
    can_request_payment: bool
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

    @staticmethod
    def resolve_mode_display(obj):
        return obj.get_mode_display()

    @staticmethod
    def resolve_status_display(obj):
        return obj.get_status_display()

    @staticmethod
    def resolve_outstanding_balance(obj):
        return max(Decimal("0.00"), obj.agreed_price - obj.amount_paid)

    @staticmethod
    def resolve_payment_progress_percent(obj):
        if obj.agreed_price <= Decimal("0.00"):
            return Decimal("0.00")
        return (
            (obj.amount_paid / obj.agreed_price) * Decimal("100")
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def resolve_can_request_payment(obj):
        if obj.status not in {
            obj.STATUS_AWAITING_PAYMENT,
            obj.STATUS_RESERVED,
            obj.STATUS_INSTALLMENT_ACTIVE,
        }:
            return False
        if obj.amount_paid >= obj.agreed_price:
            return False
        now = timezone.now()
        if (
            obj.status == obj.STATUS_AWAITING_PAYMENT
            and obj.payment_window_expires_at
            and obj.payment_window_expires_at <= now
        ):
            return False
        if (
            obj.status == obj.STATUS_INSTALLMENT_ACTIVE
            and obj.next_payment_due_at is not None
            and obj.next_payment_due_at + timedelta(hours=obj.payment_window_hours)
            <= now
        ):
            return False
        return True


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


class PropertyPurchasePaymentHistoryAttemptSchema(Schema):
    reference: str
    provider: str
    provider_reference: str
    status: str
    amount: Decimal
    currency: str
    checkout_url: str
    failure_message: str
    completed_at: Optional[datetime]
    created_at: datetime


class PropertyPurchasePaymentHistorySchema(Schema):
    intent_reference: str
    intent_status: str
    amount: Decimal
    currency: str
    expires_at: Optional[datetime]
    confirmed_at: Optional[datetime]
    created_at: datetime
    attempts: list[PropertyPurchasePaymentHistoryAttemptSchema]
    receipt_reference: Optional[str]
    receipt_amount: Optional[Decimal]
    receipt_paid_at: Optional[datetime]
    payment_method: Optional[str]
