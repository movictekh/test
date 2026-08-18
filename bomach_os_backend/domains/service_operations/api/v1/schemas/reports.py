from decimal import Decimal

from ninja import Schema


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


class ServiceStatsOut(Schema):
    total_services: int
    total_orders: int
    total_quotes: int
    total_invoices: int
