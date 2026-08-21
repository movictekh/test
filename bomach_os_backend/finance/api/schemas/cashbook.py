from datetime import date
from decimal import Decimal
from typing import Dict, Optional

from ninja import Schema


class CashbookRowOut(Schema):
    date: date
    reference: str
    source: str
    source_display: str
    description: str
    service: str
    project: str
    service_order_id: Optional[int] = None
    service_order_number: str
    client_id: Optional[int] = None
    client_name: str
    finance_account_id: Optional[int] = None
    finance_account_name: str
    branch_id: Optional[int] = None
    branch_name: str
    money_in: Decimal
    money_out: Decimal
    running_balance: Decimal
    status: str


class CashbookSummaryOut(Schema):
    opening_balance: Decimal
    period_inflow: Decimal
    period_outflow: Decimal
    net_movement: Decimal
    closing_balance: Decimal
    posted_count: int
    pending_count: int
    inflow_by_source: Dict[str, Decimal]
    outflow_by_source: Dict[str, Decimal]
