from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from ninja import Schema

# ─── ClientService Schemas ───────────────────────────────────────────


class ClientServiceResponseSchema(Schema):
    id: int
    name: str
    description: str
    category: str
    category_display: str
    starting_price: str
    estimated_duration: str
    is_featured: bool

    @staticmethod
    def resolve_starting_price(obj):
        return f"{obj.starting_price:,.2f}"

    @staticmethod
    def resolve_category_display(obj):
        return obj.get_category_display()


# ─── ServiceRequest Schemas ──────────────────────────────────────────


class ServiceRequestCreateSchema(Schema):
    service_id: int
    project_name: str
    location: str
    preferred_start_date: Optional[date] = None
    project_details: str
    special_requirements: Optional[str] = ""
    attachment: Optional[str] = ""


class InvoiceSummarySchema(Schema):
    id: int
    invoice_number: str
    status: str
    total_amount: Decimal
    amount_paid: Decimal
    balance: Decimal
    due_date: date

    @staticmethod
    def resolve_status(obj):
        return obj.get_status_display()


class ServiceRequestDashboardResponseSchema(Schema):
    id: int
    order_id: str
    project_name: str
    service_name: str
    category: str
    status: str
    progress: int
    location: str
    invoice: Optional[InvoiceSummarySchema] = None
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_status(obj):
        return obj.get_status_display()

    @staticmethod
    def resolve_service_name(obj):
        return obj.service.name

    @staticmethod
    def resolve_category(obj):
        return obj.service.get_category_display()


class ServiceRequestFullResponseSchema(ServiceRequestDashboardResponseSchema):
    client_name: str
    preferred_start_date: Optional[date]
    project_details: str
    special_requirements: str
    attachment: str

    @staticmethod
    def resolve_client_name(obj):
        return (
            f"{obj.client.first_name} {obj.client.last_name}".strip()
            or obj.client.username
        )


# Client-facing: what they see on the payments page
class ClientInvoiceSchema(Schema):
    id: int
    invoice_number: str
    service_request_name: str
    total_amount: Decimal
    amount_paid: Decimal
    balance: Decimal
    status: str
    due_date: Optional[date] = None
    created_at: datetime

    @staticmethod
    def resolve_status(obj):
        return obj.get_status_display()

    @staticmethod
    def resolve_service_request_name(obj):
        sr = (
            obj.service_requests.first()
        )  # reverse FK is a manager, not a single object
        return sr.project_name if sr else ""


# Submission schemas
class PaymentSubmissionCreateSchema(Schema):
    invoice_id: int
    amount: Decimal
    payment_method: str
    payment_date: date
    proof_of_payment: str  # URL from file upload
    receiving_account_text: str = ""
    transaction_reference: str = ""
    notes: str = ""


class PaymentSubmissionResponseSchema(Schema):
    id: int
    reference: str
    invoice_number: str
    amount: Decimal
    payment_method: str
    payment_date: date
    proof_of_payment: str
    receiving_account_text: str
    finance_account_id: Optional[int] = None
    transaction_reference: str
    submitted_by_id: Optional[int] = None
    submitted_by_type: str
    status: str
    rejection_reason: str
    confirmed_payment_id: Optional[int] = None
    created_at: datetime

    @staticmethod
    def resolve_status(obj):
        return obj.get_status_display()

    @staticmethod
    def resolve_invoice_number(obj):
        return obj.invoice.invoice_number


# Admin review
class ReviewPaymentSchema(Schema):
    status: str  # 'confirmed' or 'rejected'
    finance_account_id: Optional[int] = None
    rejection_reason: str = ""
