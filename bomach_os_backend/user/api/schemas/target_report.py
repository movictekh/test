from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from ninja import Schema


class TargetReportCreateSchema(Schema):
    employee_target_id: int
    summary: str
    progress_value: Decimal


class TargetReportRejectSchema(Schema):
    rejection_reason: str


class TargetReportEmployeeSchema(Schema):
    id: int
    user_id: int
    employee_id: str


class TargetReportReviewerSchema(Schema):
    id: int
    email: str
    first_name: str
    last_name: str


class TargetReportTargetSchema(Schema):
    id: int
    title: str
    target_value: Decimal
    unit: str
    period: str
    period_start: date
    period_end: date


class TargetReportResponseSchema(Schema):
    id: int
    employee_target_id: int
    employee_target: TargetReportTargetSchema
    employee: TargetReportEmployeeSchema
    summary: str
    progress_value: Decimal
    status: str
    reviewed_by_id: Optional[int] = None
    reviewed_by: Optional[TargetReportReviewerSchema] = None
    reviewed_at: Optional[datetime] = None
    rejection_reason: str
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_employee_target(obj):
        return obj.employee_target

    @staticmethod
    def resolve_employee(obj):
        return obj.employee_target.employee

    @staticmethod
    def resolve_reviewed_by(obj):
        return obj.reviewed_by
