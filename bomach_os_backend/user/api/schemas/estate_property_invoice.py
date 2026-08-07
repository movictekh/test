from ninja import Schema
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal


# ============== Choice Schema ==============

class ChoiceSchema(Schema):
    value: str
    label: str


class EstateInvoiceChoicesSchema(Schema):
    invoice_status: List[ChoiceSchema]
    invoice_type: List[ChoiceSchema]


# ============== Invoice Item Schemas ==============

class InvoiceItemCreateSchema(Schema):
    property_id: int
    quantity: Optional[int] = 1
    description: Optional[str] = None
    unit_price: Optional[Decimal] = None


class InvoiceItemUpdateSchema(Schema):
    description: Optional[str] = None
    unit_price: Optional[Decimal] = None


class InvoiceItemSchema(Schema):
    id: int
    property_id: int
    property_name: str
    estate_name: str
    description: str
    quantity: int
    unit_price: Decimal
    total: Decimal
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_property_name(obj):
        return obj.property.property_name

    @staticmethod
    def resolve_estate_name(obj):
        return obj.property.estate.estate_name


# ============== Invoice Schemas ==============

class ApproverCreateSchema(Schema):
    """Schema for specifying an approver when creating an invoice."""
    user_id: int
    step: int
    step_name: str


class InvoiceCreateSchema(Schema):
    client_id: int
    invoice_type: str = 'full-payment'
    installment_spread_months: Optional[int] = None
    reserve_fee_amount: Optional[Decimal] = None
    issue_date: date
    due_date: date
    tax_rate: Decimal = Decimal('7.50')
    notes: Optional[str] = ''
    items: List[InvoiceItemCreateSchema] = []
    # approvers: Optional[List[ApproverCreateSchema]] = None


class InvoiceUpdateSchema(Schema):
    invoice_type: Optional[str] = None
    installment_spread_months: Optional[int] = None
    reserve_fee_amount: Optional[Decimal] = None
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    tax_rate: Optional[Decimal] = None
    status: Optional[str] = None
    payment_completed_date: Optional[date] = None
    notes: Optional[str] = None


class InvoiceSchema(Schema):
    id: int
    invoice_number: str
    invoice_type: str
    invoice_type_display: str
    installment_spread_months: Optional[int] = None
    reserve_fee_amount: Optional[Decimal] = None

    client_id: int
    client_name: str

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
    status_display: str
    payment_completed_date: Optional[date] = None
    notes: str

    property_count: int
    items: List[InvoiceItemSchema] = []
    approvals: List['ApprovalSchema'] = []

    sort_code: Optional[str] = None
    bank_name: Optional[str] = None
    bank_code: Optional[str] = None
    account_number: Optional[str] = None
    account_name: Optional[str] = None

    created_by_id: int
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_invoice_type_display(obj):
        return obj.get_invoice_type_display()

    @staticmethod
    def resolve_status_display(obj):
        return obj.get_status_display()

    @staticmethod
    def resolve_client_name(obj):
        return str(obj.client)

    @staticmethod
    def resolve_items(obj):
        return list(obj.estate_invoice_items.select_related('property', 'property__estate').all())

    @staticmethod
    def resolve_approvals(obj):
        return list(obj.approvals.select_related('decided_by').all())


# ============== Approval Schemas ==============

class ApprovalSchema(Schema):
    id: int
    step: int
    step_name: str
    required_level: str
    assigned_to_id: Optional[int] = None
    assigned_to_name: Optional[str] = None
    decision: str
    decided_by_id: Optional[int] = None
    decided_by_name: Optional[str] = None
    decided_at: Optional[datetime] = None
    comment: str
    created_at: datetime

    @staticmethod
    def resolve_assigned_to_name(obj):
        if obj.assigned_to:
            return obj.assigned_to.get_full_name() or str(obj.assigned_to)
        return None

    @staticmethod
    def resolve_decided_by_name(obj):
        if obj.decided_by:
            return obj.decided_by.get_full_name() or str(obj.decided_by)
        return None


class ApprovalDecisionSchema(Schema):
    decision: str  # 'approved' or 'rejected'
    comment: Optional[str] = ''


# ============== Payment Schema ==============

class RecordPaymentSchema(Schema):
    amount: Decimal
