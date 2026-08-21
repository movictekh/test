from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from ninja import Schema


class PayrollRunIn(Schema):
    period_month: int
    period_year: int
    scheduled_payment_date: date
    branch_id: Optional[int] = None
    notes: str = ""


class PayrollRunUpdate(Schema):
    scheduled_payment_date: Optional[date] = None
    notes: Optional[str] = None


class PayrollManualLineItemIn(Schema):
    item_type: str
    category: str
    name: str
    amount: Decimal
    is_taxable: Optional[bool] = None
    is_statutory: bool = False
    notes: str = ""


class PayrollManualItemsReplaceIn(Schema):
    items: List[PayrollManualLineItemIn]


class PayrollRejectIn(Schema):
    reason: str


class PayrollCancelIn(Schema):
    reason: str


class PayrollPayIn(Schema):
    finance_account_id: int
    paid_at: Optional[datetime] = None
    payment_reference: str = ""


class PayrollLineItemOut(Schema):
    id: int
    item_type: str
    category: str
    name: str
    amount: Decimal
    source_type: str
    source_reference: str
    is_taxable: Optional[bool]
    is_statutory: bool
    notes: str
    sort_order: int


class PayrollLineOut(Schema):
    id: int
    employee_id: Optional[int] = None
    employee_number: str
    employee_name: str
    designation: str
    branch_name: str
    department_name: str
    salary_frequency: str
    bank_name: str
    account_number_masked: str
    missing_bank_details: bool
    gross_salary_snapshot: Decimal
    gross_pay: Decimal
    total_deductions: Decimal
    net_pay: Decimal
    items: List[PayrollLineItemOut]


class PayrollRunOut(Schema):
    id: int
    run_number: str
    period_month: int
    period_year: int
    period_display: str
    scheduled_payment_date: date
    branch_id: Optional[int] = None
    branch_name: str
    finance_account_id: Optional[int] = None
    finance_account_name: str
    status: str
    status_display: str
    employee_count: int
    missing_bank_details_count: int
    gross_pay: Decimal
    total_deductions: Decimal
    net_pay: Decimal
    notes: str
    calculated_by_name: str
    calculated_at: Optional[datetime] = None
    submitted_by_name: str
    submitted_at: Optional[datetime] = None
    approved_by_name: str
    approved_at: Optional[datetime] = None
    rejected_by_name: str
    rejected_at: Optional[datetime] = None
    rejection_reason: str
    paid_by_name: str
    paid_at: Optional[datetime] = None
    payment_reference: str
    cancelled_by_name: str
    cancelled_at: Optional[datetime] = None
    cancellation_reason: str
    created_by_name: str
    created_at: datetime
    updated_at: datetime


class PayrollRunDetailOut(PayrollRunOut):
    lines: List[PayrollLineOut]
