from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from ninja import Schema


class FinanceCommandCenterKPIOut(Schema):
    money_received: Decimal
    money_spent: Decimal
    net_cash_movement: Decimal
    outstanding_receivables: Decimal
    overdue_receivable_count: int
    cash_and_bank_position: Decimal


class FinanceCommandCenterAlertSummaryOut(Schema):
    total_count: int
    critical_count: int
    warning_count: int
    info_count: int


class FinanceCommandCenterAlertOut(Schema):
    key: str
    severity: str
    category: str
    title: str
    detail: str
    reference: str
    action_path: str
    relevant_date: date
    amount: Optional[Decimal] = None


class FinanceCommandCenterApprovalItemOut(Schema):
    key: str
    label: str
    count: int


class FinanceCommandCenterProfitabilityPreviewOut(Schema):
    order_id: int
    order_number: str
    client_name: str
    service_name: str
    branch_name: str
    contract_value: Decimal
    collected_total: Decimal
    paid_costs: Decimal
    accrued_profit: Decimal
    cash_contribution: Decimal
    outstanding_invoice_balance: Decimal


class FinanceCommandCenterServicePerformanceOut(Schema):
    service_id: int
    service_name: str
    order_count: int
    contract_value: Decimal
    collected_total: Decimal
    accrued_profit: Decimal
    outstanding_invoice_balance: Decimal


class FinanceCommandCenterMovementOut(Schema):
    date: date
    reference: str
    source: str
    source_display: str
    description: str
    client_name: str
    service: str
    project: str
    money_in: Decimal
    money_out: Decimal
    running_balance: Decimal
    status: str


class FinanceCommandCenterFeatureAvailabilityOut(Schema):
    key: str
    label: str
    availability: str
    detail: str
    endpoint: str = ""


class FinanceCommandCenterOut(Schema):
    generated_at: datetime
    currency: str
    date_from: date
    date_to: date
    as_of: date
    kpis: FinanceCommandCenterKPIOut
    approvals: List[FinanceCommandCenterApprovalItemOut]
    alerts_summary: FinanceCommandCenterAlertSummaryOut
    alerts: List[FinanceCommandCenterAlertOut]
    profitability_preview: List[FinanceCommandCenterProfitabilityPreviewOut]
    service_performance: List[FinanceCommandCenterServicePerformanceOut]
    recent_money_movement: List[FinanceCommandCenterMovementOut]
    feature_availability: List[FinanceCommandCenterFeatureAvailabilityOut]
