from datetime import date, datetime
from decimal import Decimal
from typing import Dict, Optional

from django.utils import timezone
from ninja import Schema


class FinanceVendorIn(Schema):
    name: str
    email: str = ""
    phone: str = ""
    address: str = ""
    tax_id: str = ""
    default_category: str = "other"
    status: str = "active"
    partner_id: Optional[int] = None


class FinanceVendorUpdate(Schema):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    tax_id: Optional[str] = None
    default_category: Optional[str] = None
    status: Optional[str] = None
    partner_id: Optional[int] = None


class FinanceVendorOut(Schema):
    id: int
    vendor_number: str
    name: str
    email: str
    phone: str
    address: str
    tax_id: str
    default_category: str
    default_category_display: str
    status: str
    status_display: str
    partner_id: Optional[int] = None
    created_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_default_category_display(obj):
        return obj.get_default_category_display()

    @staticmethod
    def resolve_status_display(obj):
        return obj.get_status_display()


class VendorBillIn(Schema):
    vendor_id: int
    service_order_id: Optional[int] = None
    branch_id: Optional[int] = None
    category: str
    description: str
    gross_amount: Decimal
    withholding_tax: Decimal = Decimal("0.00")
    bill_date: date
    due_date: date
    attachment: Optional[str] = None


class VendorBillUpdate(Schema):
    vendor_id: Optional[int] = None
    service_order_id: Optional[int] = None
    branch_id: Optional[int] = None
    category: Optional[str] = None
    description: Optional[str] = None
    gross_amount: Optional[Decimal] = None
    withholding_tax: Optional[Decimal] = None
    bill_date: Optional[date] = None
    due_date: Optional[date] = None
    status: Optional[str] = None
    attachment: Optional[str] = None


class VendorBillRejectIn(Schema):
    rejection_reason: str = ""


class VendorBillPayIn(Schema):
    finance_account_id: int
    paid_at: Optional[datetime] = None
    payment_reference: str = ""


class VendorBillOut(Schema):
    id: int
    bill_number: str
    vendor_id: int
    vendor_name: str
    service_order_id: Optional[int] = None
    service_order_number: str
    service_name: str
    project_name: str
    branch_id: Optional[int] = None
    branch_name: str
    finance_account_id: Optional[int] = None
    finance_account_name: str
    category: str
    description: str
    gross_amount: Decimal
    withholding_tax: Decimal
    net_amount: Decimal
    bill_date: date
    due_date: date
    is_overdue: bool
    status: str
    status_display: str
    attachment: Optional[str] = None
    approved_by_id: Optional[int] = None
    approved_by_name: str
    approved_at: Optional[datetime] = None
    rejected_by_id: Optional[int] = None
    rejected_by_name: str
    rejected_at: Optional[datetime] = None
    rejection_reason: str
    paid_by_id: Optional[int] = None
    paid_by_name: str
    paid_at: Optional[datetime] = None
    payment_reference: str
    created_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_vendor_name(obj):
        return obj.vendor.name

    @staticmethod
    def resolve_service_order_number(obj):
        return obj.service_order.order_number if obj.service_order else ""

    @staticmethod
    def resolve_service_name(obj):
        return obj.service_order.service.name if obj.service_order else ""

    @staticmethod
    def resolve_project_name(obj):
        return obj.service_order.description if obj.service_order else ""

    @staticmethod
    def resolve_branch_name(obj):
        return obj.branch.branch_name if obj.branch else ""

    @staticmethod
    def resolve_finance_account_name(obj):
        return obj.finance_account.display_name if obj.finance_account else ""

    @staticmethod
    def resolve_is_overdue(obj):
        return (
            obj.status not in {"paid", "rejected", "void"}
            and obj.due_date < timezone.localdate()
        )

    @staticmethod
    def resolve_status_display(obj):
        return obj.get_status_display()

    @staticmethod
    def resolve_approved_by_name(obj):
        return (
            (obj.approved_by.get_full_name() or obj.approved_by.email)
            if obj.approved_by
            else ""
        )

    @staticmethod
    def resolve_rejected_by_name(obj):
        return (
            (obj.rejected_by.get_full_name() or obj.rejected_by.email)
            if obj.rejected_by
            else ""
        )

    @staticmethod
    def resolve_paid_by_name(obj):
        return (obj.paid_by.get_full_name() or obj.paid_by.email) if obj.paid_by else ""


class VendorBillSummaryOut(Schema):
    total_payable: Decimal
    overdue_payable: Decimal
    due_soon_payable: Decimal
    approved_unpaid: Decimal
    scheduled_unpaid: Decimal
    paid_total: Decimal
    bill_count: int
    overdue_count: int
    due_soon_count: int
    status_counts: Dict[str, int]
