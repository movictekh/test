from datetime import date, datetime
from decimal import Decimal
from typing import Any, List, Optional

from ninja import Schema


class ServiceRequestCreateSchema(Schema):
    service_id: int
    subservice_id: Optional[int] = None
    branch_id: Optional[int] = None
    contact_name: str
    contact_phone: Optional[str] = ""
    contact_email: Optional[str] = ""
    customer_type: str = "individual"
    source: str = "client_portal"
    source_reference: Optional[str] = ""
    priority: str = "normal"
    budget: Optional[Decimal] = None
    estimated_value: Decimal = Decimal("0.00")
    preferred_date: Optional[date] = None
    due_date: Optional[date] = None
    next_action: Optional[str] = ""
    scope_summary: Optional[str] = ""
    answers: dict[str, Any]


class StaffServiceRequestCreateSchema(ServiceRequestCreateSchema):
    client_id: int
    service_lead_id: Optional[int] = None
    crm_lead_id: Optional[int] = None
    owner_id: Optional[int] = None
    source: str = "sales_crm"


class ServiceRequestUpdateSchema(Schema):
    status: Optional[str] = None
    priority: Optional[str] = None
    branch_id: Optional[int] = None
    owner_id: Optional[int] = None
    service_lead_id: Optional[int] = None
    crm_lead_id: Optional[int] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    customer_type: Optional[str] = None
    source: Optional[str] = None
    source_reference: Optional[str] = None
    budget: Optional[Decimal] = None
    estimated_value: Optional[Decimal] = None
    preferred_date: Optional[date] = None
    due_date: Optional[date] = None
    next_action: Optional[str] = None
    scope_summary: Optional[str] = None


class ServiceRequestActivityCreateSchema(Schema):
    activity_type: str
    outcome: str = "not_applicable"
    note: str
    next_action: Optional[str] = ""
    next_follow_up_at: Optional[datetime] = None


class ServiceRequestAttachmentCreateSchema(Schema):
    field_key: Optional[str] = ""
    label: Optional[str] = ""
    file_name: Optional[str] = ""
    file_url: str
    content_type: Optional[str] = ""
    file_size_bytes: int = 0


class ServiceRequestQuoteCreateSchema(Schema):
    required_approver_role_id: Optional[int] = None
    description: Optional[str] = None
    scope_summary: Optional[str] = ""
    terms: Optional[str] = ""
    service_fee: Optional[Decimal] = None
    other_charges: Decimal = Decimal("0.00")
    discount: Decimal = Decimal("0.00")
    tax_rate: Decimal = Decimal("0.00")
    deposit_percent: Decimal = Decimal("0.00")
    amount: Optional[Decimal] = None
    valid_until: Optional[date] = None


class ServiceRequestSummaryOut(Schema):
    new: int
    under_review: int
    awaiting_client: int
    site_assessment: int
    quoted: int
    converted: int
    rejected: int
    total: int


class ServiceRequestAnswerOut(Schema):
    id: int
    field_key: str
    label: str
    field_type: str
    value: Any = None
    sort_order: int


class ServiceRequestAttachmentOut(Schema):
    id: int
    field_key: str
    label: str
    file_name: str
    file_url: str
    content_type: str
    file_size_bytes: int
    uploaded_by_id: Optional[int] = None
    created_at: datetime


class ServiceRequestActivityOut(Schema):
    id: int
    activity_type: str
    activity_type_display: str
    outcome: str
    outcome_display: str
    note: str
    next_action: str
    next_follow_up_at: Optional[datetime] = None
    created_by_id: Optional[int] = None
    created_by_name: str
    created_at: datetime


class ServiceRequestListOut(Schema):
    id: int
    request_number: str
    client_id: int
    client_name: str
    service_id: int
    service_name: str
    subservice_id: Optional[int] = None
    subservice_name: str
    branch_id: Optional[int] = None
    branch_name: str
    quote_id: Optional[int] = None
    quote_number: str
    contact_name: str
    contact_phone: str
    contact_email: str
    customer_type: str
    source: str
    source_reference: str
    status: str
    status_display: str
    priority: str
    budget: Optional[Decimal] = None
    estimated_value: Decimal
    preferred_date: Optional[date] = None
    due_date: Optional[date] = None
    next_action: str
    scope_summary: str
    owner_id: Optional[int] = None
    owner_name: str
    created_at: datetime
    updated_at: datetime


class ServiceRequestDetailOut(ServiceRequestListOut):
    service_lead_id: Optional[int] = None
    crm_lead_id: Optional[int] = None
    request_form_id: int
    request_form_version: int
    pricing_config_id: Optional[int] = None
    pricing_config_version: Optional[int] = None
    workflow_id: Optional[int] = None
    workflow_version: Optional[int] = None
    answers_snapshot: dict[str, Any]
    form_snapshot: dict[str, Any]
    answers: List[ServiceRequestAnswerOut]
    attachments: List[ServiceRequestAttachmentOut]
    activities: List[ServiceRequestActivityOut]
