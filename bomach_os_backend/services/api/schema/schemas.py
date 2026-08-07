from ninja import Schema
from typing import Optional, List, Dict
from datetime import date, datetime
from decimal import Decimal


# ServiceCategory Schemas
class ServiceCategoryIn(Schema):
    name: str
    description: Optional[str] = ""


class ServiceCategoryOut(Schema):
    id: int
    name: str
    description: str
    created_at: datetime
    updated_at: datetime


# Service Schemas
class ServiceIn(Schema):
    name: str
    category_id: int
    description: str
    base_price: Decimal
    delivery_time: str
    status: str = "active"
    created_by_id: int


class ServiceUpdate(Schema):
    name: Optional[str] = None
    category_id: Optional[int] = None
    description: Optional[str] = None
    base_price: Optional[Decimal] = None
    delivery_time: Optional[str] = None
    status: Optional[str] = None


class ServiceOut(Schema):
    id: int
    name: str
    category: ServiceCategoryOut
    description: str
    base_price: Decimal
    delivery_time: str
    status: str
    created_at: datetime
    updated_at: datetime
    created_by_id: int


# ServiceLead Schemas
class ServiceLeadIn(Schema):
    client_id: int  # Reference to main backend client
    service_id: Optional[int] = None
    estimated_value: Decimal
    status: str = "new"
    notes: Optional[str] = ""
    created_by_id: int


class ServiceLeadUpdate(Schema):
    client_id: Optional[int] = None
    service_id: Optional[int] = None
    estimated_value: Optional[Decimal] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class ServiceLeadOut(Schema):
    id: int
    client_id: int
    service: Optional[ServiceOut] = None
    estimated_value: Decimal
    status: str
    notes: str
    created_at: datetime
    updated_at: datetime
    created_by_id: int


# Quote Schemas
class QuoteIn(Schema):
    client_id: int  # Reference to main backend client
    service_id: int
    service_request_id: Optional[int] = None
    previous_quote_id: Optional[int] = None
    required_approver_role_id: Optional[int] = None
    description: str
    scope_summary: str = ""
    terms: str = ""
    service_fee: Optional[Decimal] = None
    other_charges: Decimal = Decimal("0.00")
    discount: Decimal = Decimal("0.00")
    tax_rate: Decimal = Decimal("0.00")
    deposit_percent: Decimal = Decimal("0.00")
    amount: Optional[Decimal] = None
    valid_until: date
    status: str = "awaiting_approval"


class QuoteUpdate(Schema):
    description: Optional[str] = None
    scope_summary: Optional[str] = None
    terms: Optional[str] = None
    service_fee: Optional[Decimal] = None
    other_charges: Optional[Decimal] = None
    discount: Optional[Decimal] = None
    tax_rate: Optional[Decimal] = None
    deposit_percent: Optional[Decimal] = None
    valid_until: Optional[date] = None


class QuoteOut(Schema):
    id: int
    quote_number: str
    client_id: int
    service_request_id: Optional[int] = None
    previous_quote_id: Optional[int] = None
    required_approver_role_id: Optional[int] = None
    required_approver_role_name: str
    version: int
    service: ServiceOut
    description: str
    scope_summary: str
    terms: str
    service_fee: Decimal
    other_charges: Decimal
    discount: Decimal
    subtotal: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    deposit_percent: Decimal
    deposit_amount: Decimal
    amount: Decimal
    valid_until: date
    status: str
    approved_by_id: Optional[int] = None
    approved_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    client_responded_at: Optional[datetime] = None
    client_rejection_reason: str
    created_at: datetime
    updated_at: datetime
    created_by_id: int

    @staticmethod
    def resolve_required_approver_role_name(obj):
        return obj.required_approver_role.name if obj.required_approver_role else ""


class QuoteClientActionIn(Schema):
    reason: Optional[str] = ""


# ServiceOrder Schemas
class ServiceOrderIn(Schema):
    client_id: int  # Reference to main backend client
    service_id: int
    quote_id: Optional[int] = None
    service_request_id: Optional[int] = None
    invoice_id: Optional[int] = None
    description: str
    amount: Decimal
    order_status: str = "pending_mobilisation"
    valid_until: date
    due_date: Optional[date] = None
    progress: int = 0
    stage: Optional[str] = ""
    next_action: Optional[str] = ""
    created_by_id: Optional[int] = None
    assigned_to_id: Optional[int] = None
    branch_id: Optional[int] = None


class ServiceOrderUpdate(Schema):
    client_id: Optional[int] = None
    service_id: Optional[int] = None
    quote_id: Optional[int] = None
    service_request_id: Optional[int] = None
    invoice_id: Optional[int] = None
    description: Optional[str] = None
    amount: Optional[Decimal] = None
    order_status: Optional[str] = None
    valid_until: Optional[date] = None
    due_date: Optional[date] = None
    progress: Optional[int] = None
    stage: Optional[str] = None
    next_action: Optional[str] = None
    assigned_to_id: Optional[int] = None
    branch_id: Optional[int] = None


class ServiceOrderFromInvoiceIn(Schema):
    assigned_to_id: Optional[int] = None
    due_date: Optional[date] = None
    description: Optional[str] = ""
    stage: Optional[str] = ""
    next_action: str = "Confirm team and mobilisation"


class ServiceOrderMilestoneIn(Schema):
    name: str
    status: str = "pending"
    sort_order: int = 0
    owner_role_id: Optional[int] = None
    client_visible: bool = True
    due_date: Optional[date] = None


class ServiceOrderActivityIn(Schema):
    activity_type: str = "progress_update"
    visibility: str = "internal_client"
    note: str
    progress: Optional[int] = None
    next_action: Optional[str] = ""


class ServiceOrderMilestoneOut(Schema):
    id: int
    workflow_stage_id: Optional[int] = None
    name: str
    status: str
    sort_order: int
    owner_role_id: Optional[int] = None
    client_visible: bool
    due_date: Optional[date] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class ServiceOrderActivityOut(Schema):
    id: int
    activity_type: str
    visibility: str
    note: str
    progress: Optional[int] = None
    next_action: str
    created_by_id: Optional[int] = None
    created_at: datetime


class ServiceExecutionTaskIn(Schema):
    milestone_id: Optional[int] = None
    title: str
    description: Optional[str] = ""
    instructions: Optional[str] = ""
    acceptance_criteria: Optional[str] = ""
    status: str = "to_do"
    priority: str = "normal"
    evidence_required: bool = False
    owner_id: Optional[int] = None
    assignee_ids: List[int] = []
    due_date: Optional[date] = None


class ServiceExecutionTaskUpdate(Schema):
    milestone_id: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    instructions: Optional[str] = None
    acceptance_criteria: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    evidence_required: Optional[bool] = None
    owner_id: Optional[int] = None
    assignee_ids: Optional[List[int]] = None
    due_date: Optional[date] = None


class ServiceExecutionTaskOut(Schema):
    id: int
    task_number: str
    order_id: int
    milestone_id: Optional[int] = None
    title: str
    description: str
    instructions: str
    acceptance_criteria: str
    status: str
    priority: str
    evidence_required: bool
    owner_id: Optional[int] = None
    assignee_ids: List[int] = []
    due_date: Optional[date] = None
    completed_at: Optional[datetime] = None
    created_by_id: int
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_assignee_ids(obj):
        return list(obj.assignees.values_list("id", flat=True))


class ServiceClientExecutionTaskOut(Schema):
    id: int
    task_number: str
    order_id: int
    milestone_id: Optional[int] = None
    title: str
    status: str
    priority: str
    evidence_required: bool
    due_date: Optional[date] = None
    completed_at: Optional[datetime] = None
    updated_at: datetime


class ServiceDeliverableIn(Schema):
    milestone_id: Optional[int] = None
    task_id: Optional[int] = None
    title: str
    deliverable_type: str = "report"
    version: str = "v1"
    file_url: str
    file_name: Optional[str] = ""
    content_type: Optional[str] = ""
    file_size_bytes: int = 0
    description: Optional[str] = ""
    client_visible: bool = False
    approval_mode: str = "none"
    status: Optional[str] = None
    owner_id: Optional[int] = None


class ServiceDeliverableUpdate(Schema):
    milestone_id: Optional[int] = None
    task_id: Optional[int] = None
    title: Optional[str] = None
    deliverable_type: Optional[str] = None
    version: Optional[str] = None
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    content_type: Optional[str] = None
    file_size_bytes: Optional[int] = None
    description: Optional[str] = None
    client_visible: Optional[bool] = None
    approval_mode: Optional[str] = None
    status: Optional[str] = None
    owner_id: Optional[int] = None


class ServiceDeliverableActionIn(Schema):
    reason: Optional[str] = ""


class ServiceDeliverableOut(Schema):
    id: int
    deliverable_number: str
    order_id: int
    milestone_id: Optional[int] = None
    task_id: Optional[int] = None
    title: str
    deliverable_type: str
    version: str
    file_url: str
    file_name: str
    content_type: str
    file_size_bytes: int
    description: str
    client_visible: bool
    status: str
    approval_mode: str
    owner_id: Optional[int] = None
    approved_by_id: Optional[int] = None
    approved_at: Optional[datetime] = None
    rejected_by_id: Optional[int] = None
    rejected_at: Optional[datetime] = None
    rejection_reason: str
    created_by_id: int
    created_at: datetime
    updated_at: datetime


class ServiceOrderOut(Schema):
    id: int
    order_number: str
    client_id: int
    service: ServiceOut
    quote: Optional[QuoteOut] = None
    service_request_id: Optional[int] = None
    invoice_id: Optional[int] = None
    description: str
    amount: Decimal
    order_status: str
    payment_status: str
    valid_until: date
    due_date: Optional[date] = None
    progress: int
    stage: str
    next_action: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    created_by_id: int
    assigned_to_id: Optional[int] = None
    branch_id: Optional[int] = None
    payment_link: Optional[str] = None
    task_counts: Dict[str, int] = {}
    deliverable_counts: Dict[str, int] = {}
    milestones: List[ServiceOrderMilestoneOut] = []
    activities: List[ServiceOrderActivityOut] = []

    @staticmethod
    def resolve_task_counts(obj):
        counts = {status: 0 for status, _label in obj.tasks.model.STATUS_CHOICES}
        for task in obj.tasks.all():
            counts[task.status] = counts.get(task.status, 0) + 1
        return counts

    @staticmethod
    def resolve_deliverable_counts(obj):
        counts = {status: 0 for status, _label in obj.deliverables.model.STATUS_CHOICES}
        for deliverable in obj.deliverables.all():
            counts[deliverable.status] = counts.get(deliverable.status, 0) + 1
        return counts

    @staticmethod
    def resolve_milestones(obj):
        visible = getattr(obj, "client_visible_milestones", None)
        return visible if visible is not None else obj.milestones.all()

    @staticmethod
    def resolve_activities(obj):
        visible = getattr(obj, "client_visible_activities", None)
        return visible if visible is not None else obj.activities.all()


# InvoiceItem Schemas
class InvoiceItemIn(Schema):
    description: str
    quantity: Decimal
    unit_price: Decimal


class InvoiceItemOut(Schema):
    id: int
    description: str
    quantity: Decimal
    unit_price: Decimal
    total: Decimal
    created_at: datetime
    updated_at: datetime


# Invoice Schemas
class InvoiceIn(Schema):
    client_id: int  # Reference to main backend client
    service_id: int
    quote_id: Optional[int] = None
    service_request_id: Optional[int] = None
    order_id: Optional[int] = None
    lead_id: Optional[int] = None
    issue_date: date
    due_date: date
    subtotal: Decimal
    tax_rate: Decimal = Decimal("7.50")
    status: str = "draft"
    payment_schedule: Optional[str] = ""
    payment_instructions: Optional[str] = ""
    activation_threshold_amount: Decimal = Decimal("0.00")
    notes: Optional[str] = ""
    created_by_id: int
    items: List[InvoiceItemIn] = []


class InvoiceUpdate(Schema):
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    subtotal: Optional[Decimal] = None
    tax_rate: Optional[Decimal] = None
    payment_schedule: Optional[str] = None
    payment_instructions: Optional[str] = None
    notes: Optional[str] = None


class InvoiceFromQuoteIn(Schema):
    due_date: date
    payment_schedule: str = "Deposit / mobilisation"
    payment_instructions: str = "Pay through client wallet, payment gateway, bank transfer or approved POS."
    notes: Optional[str] = ""


class InvoiceSendIn(Schema):
    payment_instructions: Optional[str] = None


class InvoiceOut(Schema):
    id: int
    invoice_number: str
    client_id: int
    quote_id: Optional[int] = None
    service_request_id: Optional[int] = None
    service: ServiceOut
    order: Optional[ServiceOrderOut] = None
    lead: Optional[ServiceLeadOut] = None
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
    payment_schedule: str
    payment_instructions: str
    activation_threshold_amount: Decimal
    activation_threshold_met_at: Optional[datetime] = None
    notes: str
    items: List[InvoiceItemOut]
    created_at: datetime
    updated_at: datetime
    created_by_id: int


# Payment Schemas
class PaymentIn(Schema):
    invoice_id: int
    amount: Decimal
    payment_method: str
    payment_date: date
    transaction_reference: Optional[str] = ""
    notes: Optional[str] = ""
    created_by_id: int


class PaymentOut(Schema):
    id: int
    payment_reference: str
    invoice_id: int
    amount: Decimal
    payment_method: str
    payment_date: date
    transaction_reference: str
    notes: str
    created_at: datetime
    updated_at: datetime
    created_by_id: int


# List/Pagination Schemas
class PaginatedResponse(Schema):
    count: int
    results: List


class ServiceListOut(Schema):
    count: int
    results: List[ServiceOut]


class ServiceLeadListOut(Schema):
    count: int
    results: List[ServiceLeadOut]


class QuoteListOut(Schema):
    count: int
    results: List[QuoteOut]


class ServiceOrderListOut(Schema):
    count: int
    results: List[ServiceOrderOut]


class InvoiceListOut(Schema):
    count: int
    results: List[InvoiceOut]


class PaymentListOut(Schema):
    count: int
    results: List[PaymentOut]


# Stats Schemas
class ServiceStatsOut(Schema):
    total_services: int
    total_orders: int
    total_quotes: int
    total_invoices: int


# Error Schemas
class ErrorOut(Schema):
    detail: str
