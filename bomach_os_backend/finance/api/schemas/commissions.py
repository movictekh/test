from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from ninja import Schema


class CommissionRuleIn(Schema):
    name: str
    service_id: int
    branch_id: Optional[int] = None
    rate_percent: Decimal
    minimum_verified_revenue: Decimal = Decimal("0.00")
    effective_from: date
    effective_to: Optional[date] = None
    notes: str = ""


class CommissionRuleUpdate(Schema):
    name: Optional[str] = None
    branch_id: Optional[int] = None
    rate_percent: Optional[Decimal] = None
    minimum_verified_revenue: Optional[Decimal] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    notes: Optional[str] = None


class CommissionRuleOut(Schema):
    id: int
    rule_number: str
    name: str
    service_id: int
    service_name: str
    branch_id: Optional[int] = None
    branch_name: str
    rate_percent: Decimal
    minimum_verified_revenue: Decimal
    effective_from: date
    effective_to: Optional[date] = None
    status: str
    notes: str
    created_at: datetime
    updated_at: datetime


class CommissionCalculateIn(Schema):
    employee_id: int
    payment_id: int
    commission_rule_id: int
    payout_month: int
    payout_year: int
    notes: str = ""


class BonusIn(Schema):
    employee_id: int
    amount: Decimal
    payout_month: int
    payout_year: int
    reason: str
    notes: str = ""


class IncentiveRejectIn(Schema):
    reason: str


class IncentiveAwardOut(Schema):
    id: int
    award_number: str
    award_type: str
    employee_id: int
    employee_number: str
    employee_name: str
    branch_id: Optional[int] = None
    branch_name: str
    service_id: Optional[int] = None
    service_name: str
    payment_id: Optional[int] = None
    payment_reference: str
    commission_rule_id: Optional[int] = None
    commission_rule_number: str
    revenue_source: str
    verified_revenue: Decimal
    rate_percent: Decimal
    amount: Decimal
    payout_month: int
    payout_year: int
    payout_period_display: str
    status: str
    status_display: str
    payroll_run_id: Optional[int] = None
    payroll_run_number: str
    reason: str
    notes: str
    approved_by_name: str
    approved_at: Optional[datetime] = None
    rejected_by_name: str
    rejected_at: Optional[datetime] = None
    rejection_reason: str
    paid_by_name: str
    paid_at: Optional[datetime] = None
    created_by_name: str
    created_at: datetime
    updated_at: datetime
