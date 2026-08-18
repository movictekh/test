from datetime import date
from decimal import Decimal
from typing import Optional

from ninja import Schema


class ServiceOrderProfitabilityOut(Schema):
    order_id: int
    order_number: str
    source_reference: str
    client_id: int
    client_name: str
    service_id: int
    service_name: str
    branch_id: Optional[int] = None
    branch_name: str
    project_name: str
    contract_type: Optional[str] = None
    contract_value: Decimal
    cost_budget: Optional[Decimal] = None
    overhead_amount: Optional[Decimal] = None
    order_status: str
    order_status_display: str
    payment_status: str
    payment_status_display: str
    progress: int
    stage: str
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    owner_name: str
    invoiced_total: Decimal
    collected_total: Decimal
    outstanding_invoice_balance: Decimal
    paid_costs: Decimal
    committed_costs: Decimal
    expected_gross_profit: Optional[Decimal] = None
    expected_margin_pct: Optional[Decimal] = None
    cash_contribution: Decimal
    accrued_profit: Decimal
    wallet_id: Optional[int] = None
    wallet_funded: Decimal
    wallet_spent: Decimal
    wallet_committed: Decimal
    wallet_available: Decimal


class ServiceOrderProfitabilitySummaryOut(Schema):
    order_count: int
    total_contract_value: Decimal
    total_invoiced: Decimal
    total_collected: Decimal
    total_outstanding: Decimal
    total_paid_costs: Decimal
    total_committed_costs: Decimal
    total_cash_contribution: Decimal
    total_accrued_profit: Decimal
    profitable_order_count: int
    loss_making_order_count: int
    cash_positive_order_count: int
    cash_negative_order_count: int


class ServiceOrderCostOut(Schema):
    id: int
    source: str = "expense"
    source_display: str = "Expense"
    expense_number: str
    vendor_bill_id: Optional[int] = None
    vendor_bill_number: str = ""
    date: date
    category: str
    category_display: str
    cost_type: str
    cost_type_display: str
    stage: str
    description: str
    beneficiary: str
    vendor: Optional[str] = None
    amount: Decimal
    status: str
    status_display: str
    billable: bool
    client_visible: bool
    finance_account_id: Optional[int] = None
    finance_account_name: str
    attachment: Optional[str] = None
    paid_at: Optional[date] = None


class ServiceOrderTransactionOut(Schema):
    date: date
    reference: str
    source: str
    source_display: str
    description: str
    finance_account_id: Optional[int] = None
    finance_account_name: str
    money_in: Decimal
    money_out: Decimal
    running_contribution: Decimal
    status: str
