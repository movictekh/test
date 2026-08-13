from datetime import date, datetime
from decimal import Decimal
from typing import Dict, Optional

from django.utils import timezone
from ninja import Schema


FINAL_INVOICE_STATUSES = {"paid", "cancelled"}


def finance_invoice_status(invoice) -> str:
    if invoice.status not in FINAL_INVOICE_STATUSES and invoice.balance > 0 and invoice.due_date < timezone.localdate():
        return "overdue"
    return invoice.status


class FinanceInvoiceOut(Schema):
    id: int
    invoice_number: str
    client_id: int
    client_name: str
    client_email: str
    service_id: int
    service_name: str
    branch_id: Optional[int] = None
    branch_name: str
    quote_id: Optional[int] = None
    service_request_id: Optional[int] = None
    service_request_number: str
    order_id: Optional[int] = None
    order_number: str
    issue_date: date
    due_date: date
    subtotal: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    amount_paid: Decimal
    balance: Decimal
    payment_progress: float
    status: str
    display_status: str
    is_overdue: bool
    can_record_payment: bool
    payment_schedule: str
    activation_threshold_amount: Decimal
    activation_threshold_met_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    created_by_id: int

    @staticmethod
    def resolve_client_name(obj):
        full_name = obj.client.user.get_full_name()
        return obj.client.company_name or full_name or obj.client.user.email

    @staticmethod
    def resolve_client_email(obj):
        return obj.client.user.email

    @staticmethod
    def resolve_service_name(obj):
        return obj.service.name

    @staticmethod
    def resolve_branch_id(obj):
        branch = invoice_branch(obj)
        return branch.id if branch else None

    @staticmethod
    def resolve_branch_name(obj):
        branch = invoice_branch(obj)
        return branch.branch_name if branch else ""

    @staticmethod
    def resolve_service_request_number(obj):
        return obj.service_request.request_number if obj.service_request else ""

    @staticmethod
    def resolve_order_number(obj):
        return obj.order.order_number if obj.order else ""

    @staticmethod
    def resolve_display_status(obj):
        return finance_invoice_status(obj)

    @staticmethod
    def resolve_is_overdue(obj):
        return finance_invoice_status(obj) == "overdue"

    @staticmethod
    def resolve_can_record_payment(obj):
        return (
            obj.balance > 0
            and finance_invoice_status(obj) in {"sent", "viewed", "partially_paid", "overdue"}
        )


class FinanceInvoiceSummaryOut(Schema):
    total_invoiced: Decimal
    total_paid: Decimal
    outstanding_balance: Decimal
    current_balance: Decimal
    overdue_balance: Decimal
    overdue_count: int
    invoice_count: int
    status_counts: Dict[str, int]


def invoice_branch(invoice):
    if invoice.service_request and invoice.service_request.branch:
        return invoice.service_request.branch
    if invoice.order and invoice.order.branch:
        return invoice.order.branch
    return None
