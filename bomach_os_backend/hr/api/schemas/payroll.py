from datetime import date
from decimal import Decimal
from typing import List, Optional

from ninja import Field, Schema
from pydantic import validator


class EmployeeOut(Schema):
    id: int
    full_name: str
    designation: str

    @staticmethod
    def resolve_full_name(obj):
        full_name = f"{getattr(obj.user, 'first_name', '')} {getattr(obj.user, 'last_name', '')}".strip()

        return full_name if full_name else getattr(obj.user, "username", "N/A")


class PayrollOut(Schema):
    id: int
    employee: EmployeeOut
    period_display: str
    net_pay: Decimal
    base_salary: Optional[Decimal]
    commission_bonus: Decimal
    tax_deductions: Decimal
    status: str
    disbursement_date: Optional[date]

    @staticmethod
    def resolve_net_pay(obj):
        return obj.net_salary

    @staticmethod
    def resolve_base_salary(obj):
        return obj.gross_salary

    @staticmethod
    def resolve_employee_name(obj):
        return str(obj.employee)

    @staticmethod
    def resolve_tax_deductions(obj):
        return obj.total_deductions

    @staticmethod
    def resolve_commission_bonus(obj):
        return obj.total_allowances

    @staticmethod
    def resolve_period_display(obj):
        import calendar

        month_name = calendar.month_name[obj.period_month]
        return f"{month_name} {obj.period_year}"


class ProcessPayrollSchema(Schema):
    period_date: date


class PayrollFilterSchema(Schema):
    employee_id: Optional[int] = None
    period_date_from: Optional[date] = None
    period_date_to: Optional[date] = None
    status: Optional[str] = None
    disbursement_date_from: Optional[date] = None
    disbursement_date_to: Optional[date] = None
    min_net_salary: Optional[Decimal] = None
    max_net_salary: Optional[Decimal] = None


class PayrollSummaryOut(Schema):
    month: str
    total_net_salary: Decimal
    total_allowances: Decimal
    total_deductions: Decimal
    employee_count: int
