from datetime import date, datetime
from decimal import Decimal
from typing import Dict, Optional

from ninja import Schema


class ReceivableOut(Schema):
    invoice_id: int
    invoice_number: str
    client_id: int
    client_name: str
    client_email: str
    service_id: int
    service_name: str
    branch_id: Optional[int] = None
    branch_name: str
    total_amount: Decimal
    amount_paid: Decimal
    balance: Decimal
    due_date: date
    age_days: int
    ageing_bucket: str
    status: str
    display_status: str
    last_reminder_at: Optional[datetime] = None

    @staticmethod
    def resolve_invoice_id(obj):
        return obj.id

    @staticmethod
    def resolve_client_name(obj):
        full_name = obj.client.user.get_full_name()
        return obj.client.company_name or full_name or obj.client.user.email

    @staticmethod
    def resolve_client_email(obj):
        return obj.service_request.contact_email if obj.service_request and obj.service_request.contact_email else obj.client.user.email

    @staticmethod
    def resolve_service_name(obj):
        return obj.service.name

    @staticmethod
    def resolve_branch_id(obj):
        branch = _invoice_branch(obj)
        return branch.id if branch else None

    @staticmethod
    def resolve_branch_name(obj):
        branch = _invoice_branch(obj)
        return branch.branch_name if branch else ""

    @staticmethod
    def resolve_age_days(obj):
        return getattr(obj, "receivable_age_days", 0)

    @staticmethod
    def resolve_ageing_bucket(obj):
        return getattr(obj, "receivable_ageing_bucket", "current")

    @staticmethod
    def resolve_display_status(obj):
        return getattr(obj, "receivable_display_status", obj.status)

    @staticmethod
    def resolve_last_reminder_at(obj):
        return getattr(obj, "last_receivable_reminder_at", None)


class ReceivableSummaryOut(Schema):
    total_receivables: Decimal
    current: Decimal
    bucket_1_30: Decimal
    bucket_31_60: Decimal
    bucket_61_90: Decimal
    bucket_90_plus: Decimal
    overdue_total: Decimal
    overdue_count: int
    receivable_count: int
    collection_rate: Decimal
    bucket_counts: Dict[str, int]


class ReceivableReminderIn(Schema):
    message: str = ""


class ReceivableReminderOut(Schema):
    detail: str
    invoice_id: int
    invoice_number: str
    recipient: str
    sent: bool
    activity_id: Optional[int] = None


def _invoice_branch(invoice):
    if invoice.service_request and invoice.service_request.branch:
        return invoice.service_request.branch
    if invoice.order and invoice.order.branch:
        return invoice.order.branch
    return None
