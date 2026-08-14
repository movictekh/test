from ninja import Schema
from decimal import Decimal


class KPISchema(Schema):
    quote_to_order_conversion: Decimal
    average_response_time_minutes: float
    gross_service_margin: Decimal
    on_time_delivery: Decimal


class ServicePerformanceItem(Schema):
    service_name: str
    completion_rate: Decimal
    revenue: Decimal


class BranchPerformanceItem(Schema):
    branch_name: str
    requests: int
    active_orders: int
    revenue: Decimal
    sla: Decimal
    csat: Decimal
