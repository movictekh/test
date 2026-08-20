from ninja import Schema
from decimal import Decimal
from datetime import date, datetime
from typing import Optional

class LoanCreateSchema(Schema):
    loan_amount: Decimal
    repayment_date: date
    reason: str
    emergency_contact_name: str
    emergency_contact_phone: str
    attachment: str

class LoanUpdateSchema(Schema):
    loan_amount: Optional[Decimal] = None
    repayment_date: Optional[date] = None
    reason: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    attachment: Optional[str] = None

class LoanBaseResponse(Schema):
    loan_amount: str
    repayment_date: date
    reason: str
    employee_name: str
    job_title: str
    status: str

    @staticmethod
    def resolve_loan_amount(obj):
        return f"{obj.loan_amount:,.2f}"

    @staticmethod
    def resolve_status(obj):
        return obj.get_status_display()

    @staticmethod
    def resolve_employee_name(obj):
        # user = obj.employee
        return f"{obj.employee.first_name} {obj.employee.last_name}".strip() or obj.employee.username

    @staticmethod
    def resolve_job_title(obj):
        user = obj.employee
        profile = getattr(user, 'employee_profile', None)
        return profile.designation if profile else "N/A"


class LoanDashboardResponseSchema(LoanBaseResponse):
    created_at: datetime


class LoanFullResponseSchema(LoanBaseResponse):
    id: int
    emergency_contact_name: str
    emergency_contact_phone: str
    attachment: str
    created_at: datetime

