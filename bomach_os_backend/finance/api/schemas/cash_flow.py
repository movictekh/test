from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional

from ninja import Schema


class CashFlowForecastItemOut(Schema):
    source: str
    direction: str
    reference: str
    description: str
    due_date: date
    forecast_date: date
    amount: Decimal
    status: str
    is_overdue: bool
    branch_id: Optional[int] = None
    branch_name: str
    client_id: Optional[int] = None
    client_name: str
    service_order_id: Optional[int] = None
    service_order_number: str


class CashFlowForecastWeekOut(Schema):
    week_number: int
    date_from: date
    date_to: date
    opening_balance: Decimal
    expected_inflows: Decimal
    expected_outflows: Decimal
    net_movement: Decimal
    closing_balance: Decimal
    inflow_count: int
    outflow_count: int


class CashFlowForecastOut(Schema):
    as_of: date
    horizon_weeks: int
    horizon_end: date
    thirty_day_end: date
    opening_cash: Decimal
    expected_inflows_30d: Decimal
    expected_outflows_30d: Decimal
    forecast_closing_30d: Decimal
    forecast_closing_horizon: Decimal
    inflow_by_source_30d: Dict[str, Decimal]
    outflow_by_source_30d: Dict[str, Decimal]
    weeks: List[CashFlowForecastWeekOut]
    upcoming_obligations: List[CashFlowForecastItemOut]
    items: List[CashFlowForecastItemOut]
