from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from ninja import Schema


class FinancePaymentSubmissionIn(Schema):
    invoice_id: int
    finance_account_id: int
    amount: Decimal
    payment_method: str
    payment_date: date
    transaction_reference: str
    proof_of_payment: str
    notes: str = ""


class FinancePaymentSubmissionReviewIn(Schema):
    status: str
    finance_account_id: Optional[int] = None
    rejection_reason: str = ""


class FinancePaymentSubmissionOut(Schema):
    id: int
    reference: str
    invoice_id: int
    invoice_number: str
    client_id: int
    client_name: str
    amount: Decimal
    payment_method: str
    payment_date: date
    proof_of_payment: str
    receiving_account_text: str
    finance_account_id: Optional[int] = None
    finance_account_name: str
    transaction_reference: str
    submitted_by_id: Optional[int] = None
    submitted_by_type: str
    status: str
    status_display: str
    reviewed_by_id: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    rejection_reason: str
    confirmed_payment_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_invoice_number(obj):
        return obj.invoice.invoice_number

    @staticmethod
    def resolve_client_name(obj):
        full_name = obj.client.user.get_full_name()
        return obj.client.company_name or full_name or obj.client.user.email

    @staticmethod
    def resolve_finance_account_name(obj):
        return obj.finance_account.display_name if obj.finance_account else ""

    @staticmethod
    def resolve_status_display(obj):
        return obj.get_status_display()


class ConfirmedFinancePaymentOut(Schema):
    id: int
    payment_reference: str
    invoice_id: int
    invoice_number: str
    client_id: int
    client_name: str
    service_id: int
    service_name: str
    branch_id: Optional[int] = None
    branch_name: str
    finance_account_id: Optional[int] = None
    finance_account_name: str
    amount: Decimal
    payment_method: str
    payment_date: date
    transaction_reference: str
    proof_of_payment: str
    notes: str
    created_at: datetime
    updated_at: datetime
    created_by_id: int

    @staticmethod
    def resolve_invoice_number(obj):
        return obj.invoice.invoice_number

    @staticmethod
    def resolve_client_id(obj):
        return obj.invoice.client_id

    @staticmethod
    def resolve_client_name(obj):
        full_name = obj.invoice.client.user.get_full_name()
        return (
            obj.invoice.client.company_name
            or full_name
            or obj.invoice.client.user.email
        )

    @staticmethod
    def resolve_service_id(obj):
        return obj.invoice.service_id

    @staticmethod
    def resolve_service_name(obj):
        return obj.invoice.service.name

    @staticmethod
    def resolve_branch_id(obj):
        branch = _invoice_branch(obj.invoice)
        return branch.id if branch else None

    @staticmethod
    def resolve_branch_name(obj):
        branch = _invoice_branch(obj.invoice)
        return branch.branch_name if branch else ""

    @staticmethod
    def resolve_finance_account_name(obj):
        return obj.finance_account.display_name if obj.finance_account else ""


def _invoice_branch(invoice):
    if invoice.service_request and invoice.service_request.branch:
        return invoice.service_request.branch
    if invoice.order and invoice.order.branch:
        return invoice.order.branch
    return None
