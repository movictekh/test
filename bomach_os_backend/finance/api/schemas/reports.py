from datetime import date
from decimal import Decimal
from typing import List

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
