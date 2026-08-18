from datetime import datetime
from decimal import Decimal
from typing import Optional

from ninja import Schema


class FinanceWalletIn(Schema):
    client_id: int
    wallet_type: str
    name: str
    service_order_id: Optional[int] = None
    purpose: str = ""
    status: str = "active"


class FinanceWalletUpdate(Schema):
    wallet_type: Optional[str] = None
    name: Optional[str] = None
    service_order_id: Optional[int] = None
    purpose: Optional[str] = None
    status: Optional[str] = None


class FinanceWalletEntryIn(Schema):
    entry_type: str
    amount: Decimal
    description: str
    status: str = "posted"
    reference: str = ""
    invoice_id: Optional[int] = None
    payment_id: Optional[int] = None
    expense_id: Optional[int] = None
    vendor_bill_id: Optional[int] = None
    service_order_id: Optional[int] = None


class FinanceWalletOut(Schema):
    id: int
    wallet_number: str
    client_id: int
    client_name: str
    service_order_id: Optional[int] = None
    service_order_number: str
    wallet_type: str
    wallet_type_display: str
    name: str
    purpose: str
    status: str
    status_display: str
    funded: Decimal
    spent: Decimal
    committed: Decimal
    available: Decimal
    created_by_id: int
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_client_name(obj):
        full_name = obj.client.user.get_full_name()
        return obj.client.company_name or full_name or obj.client.user.email

    @staticmethod
    def resolve_service_order_number(obj):
        return obj.service_order.order_number if obj.service_order else ""

    @staticmethod
    def resolve_wallet_type_display(obj):
        return obj.get_wallet_type_display()

    @staticmethod
    def resolve_status_display(obj):
        return obj.get_status_display()

    @staticmethod
    def resolve_funded(obj):
        return obj.balance_summary()["funded"]

    @staticmethod
    def resolve_spent(obj):
        return obj.balance_summary()["spent"]

    @staticmethod
    def resolve_committed(obj):
        return obj.balance_summary()["committed"]

    @staticmethod
    def resolve_available(obj):
        return obj.balance_summary()["available"]


class FinanceWalletEntryOut(Schema):
    id: int
    wallet_id: int
    wallet_number: str
    entry_type: str
    entry_type_display: str
    status: str
    status_display: str
    amount: Decimal
    invoice_id: Optional[int] = None
    invoice_number: str
    payment_id: Optional[int] = None
    payment_reference: str
    expense_id: Optional[int] = None
    expense_number: str
    vendor_bill_id: Optional[int] = None
    vendor_bill_number: str
    service_order_id: Optional[int] = None
    service_order_number: str
    description: str
    reference: str
    created_by_id: int
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_wallet_number(obj):
        return obj.wallet.wallet_number

    @staticmethod
    def resolve_entry_type_display(obj):
        return obj.get_entry_type_display()

    @staticmethod
    def resolve_status_display(obj):
        return obj.get_status_display()

    @staticmethod
    def resolve_invoice_number(obj):
        return obj.invoice.invoice_number if obj.invoice else ""

    @staticmethod
    def resolve_payment_reference(obj):
        return obj.payment.payment_reference if obj.payment else ""

    @staticmethod
    def resolve_expense_number(obj):
        return obj.expense.expense_number if obj.expense else ""

    @staticmethod
    def resolve_vendor_bill_number(obj):
        return obj.vendor_bill.bill_number if obj.vendor_bill else ""

    @staticmethod
    def resolve_service_order_number(obj):
        return obj.service_order.order_number if obj.service_order else ""
