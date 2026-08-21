from datetime import date
from decimal import Decimal
from typing import List, Optional

from ninja import Schema


class FinancialReportLineOut(Schema):
    ledger_account_id: int
    ledger_account_code: str
    ledger_account_name: str
    account_type: str
    normal_balance: str
    amount: Decimal


class ProfitAndLossOut(Schema):
    date_from: date
    date_to: date
    currency: str
    revenue: List[FinancialReportLineOut]
    expenses: List[FinancialReportLineOut]
    total_revenue: Decimal
    total_expenses: Decimal
    net_profit: Decimal


class AccountActivityReportOut(Schema):
    date_from: date
    date_to: date
    currency: str
    account_type: str
    rows: List[FinancialReportLineOut]
    total: Decimal


class BalanceSheetOut(Schema):
    as_of: date
    currency: str
    assets: List[FinancialReportLineOut]
    liabilities: List[FinancialReportLineOut]
    equity: List[FinancialReportLineOut]
    total_assets: Decimal
    total_liabilities: Decimal
    posted_equity: Decimal
    cumulative_earnings: Decimal
    total_equity: Decimal
    equation_difference: Decimal
    balanced: bool


class ReportCatalogItemOut(Schema):
    key: str
    name: str
    description: str
    availability: str
    endpoint: Optional[str] = None
    method: Optional[str] = None
    required_resource: Optional[str] = None
    required_action: Optional[str] = None
    export_endpoint: Optional[str] = None
    export_format: Optional[str] = None
    note: str = ""


class ReportCatalogOut(Schema):
    reports: List[ReportCatalogItemOut]


class PayablesAgeingRowOut(Schema):
    vendor_bill_id: int
    bill_number: str
    vendor_id: int
    vendor_name: str
    service_order_id: Optional[int] = None
    service_order_number: str
    branch_id: Optional[int] = None
    branch_name: str
    bill_date: date
    due_date: date
    age_days: int
    ageing_bucket: str
    status: str
    net_amount: Decimal


class PayablesAgeingOut(Schema):
    as_of: date
    currency: str
    currency_basis: str
    total_payables: Decimal
    current: Decimal
    bucket_1_30: Decimal
    bucket_31_60: Decimal
    bucket_61_90: Decimal
    bucket_90_plus: Decimal
    overdue_total: Decimal
    payable_count: int
    overdue_count: int
    bucket_counts: dict
    rows: List[PayablesAgeingRowOut]
