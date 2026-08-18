from ninja import Schema
from datetime import date, datetime
from typing import Optional
from decimal import Decimal
from pydantic import Field


class DisciplinaryCaseSchema(Schema):
    id: int
    employee_id: int
    # employee_name: Optional[str]
    action_type: str
    violation_category: str
    violation_title: str
    violation_description: str
    date_of_violation: date
    action_date: date
    investigation_details: Optional[str]
    severance_payment_due: bool
    severance_amount: Optional[Decimal]
    created_at: datetime
    updated_at: datetime
    days_since_violation: Optional[int]
    is_severance_applicable: bool
    action_type_color: str

    class Config:
        from_attributes = True


class DisciplinaryCaseCreateSchema(Schema):
    employee_id: int
    # employee_name: Optional[str] = None
    action_type: str
    violation_category: str
    violation_title: str
    violation_description: str
    date_of_violation: date
    action_date: Optional[date] = None
    investigation_details: Optional[str] = None
    severance_payment_due: bool = False
    severance_amount: Optional[Decimal] = None


class DisciplinaryCaseUpdateSchema(Schema):
    employee_id: Optional[int] = None
    # employee_name: Optional[str] = None
    action_type: Optional[str] = None
    violation_category: Optional[str] = None
    violation_title: Optional[str] = None
    violation_description: Optional[str] = None
    date_of_violation: Optional[date] = None
    action_date: Optional[date] = None
    investigation_details: Optional[str] = None
    severance_payment_due: Optional[bool] = None
    severance_amount: Optional[Decimal] = None
