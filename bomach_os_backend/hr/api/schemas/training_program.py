from ninja import Schema, Field
from typing import Optional
from datetime import date
from decimal import Decimal
from pydantic import validator


class TrainingProgramCreateSchema(Schema):
    program_name: str
    provider: str
    description: str
    start_date: date
    end_date: date
    cost: Decimal = Field(..., gt=0, decimal_places=2)
    target_audience: str
    status: str = "pending"

    @validator('end_date')
    def validate_dates(cls, v, values):
        if 'start_date' in values and v < values['start_date']:
            raise ValueError('End date must be after start date')
        return v

    @validator('status')
    def validate_status(cls, v):
        valid_statuses = ['pending', 'in_progress', 'completed', 'cancelled']
        if v not in valid_statuses:
            raise ValueError(f'Status must be one of: {", ".join(valid_statuses)}')
        return v

    @validator('target_audience')
    def validate_target_audience(cls, v):
        valid_audiences = [
            'all_employees', 'management', 'new_hires', 'department_specific',
            'leadership_team', 'technical_staff', 'sales_team', 'customer_service'
        ]
        if v not in valid_audiences:
            raise ValueError(f'Target audience must be one of: {", ".join(valid_audiences)}')
        return v


class TrainingProgramUpdateSchema(Schema):
    program_name: Optional[str] = None
    provider: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    cost: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    target_audience: Optional[str] = None
    status: Optional[str] = None

    @validator('status')
    def validate_status(cls, v):
        if v is not None:
            valid_statuses = ['pending', 'in_progress', 'completed', 'cancelled']
            if v not in valid_statuses:
                raise ValueError(f'Status must be one of: {", ".join(valid_statuses)}')
        return v

    @validator('target_audience')
    def validate_target_audience(cls, v):
        if v is not None:
            valid_audiences = [
                'all_employees', 'management', 'new_hires', 'department_specific',
                'leadership_team', 'technical_staff', 'sales_team', 'customer_service'
            ]
            if v not in valid_audiences:
                raise ValueError(f'Target audience must be one of: {", ".join(valid_audiences)}')
        return v


class TrainingProgramResponseSchema(Schema):
    id: int
    program_name: str
    provider: str
    description: str
    start_date: date
    end_date: date
    cost: Decimal
    target_audience: str
    status: str
    duration_days: int
    is_ongoing: bool
    is_upcoming: bool
    created_at: str
    updated_at: str

    @staticmethod
    def resolve_created_at(obj):
        return obj.created_at.isoformat()

    @staticmethod
    def resolve_updated_at(obj):
        return obj.updated_at.isoformat()


class TrainingProgramListSchema(Schema):
    """Simplified schema for list view"""
    id: int
    program_name: str
    start_date: date
    end_date: date
    status: str


class TrainingProgramFilterSchema(Schema):
    program_name: Optional[str] = None
    provider: Optional[str] = None
    status: Optional[str] = None
    target_audience: Optional[str] = None
    start_date_from: Optional[date] = None
    start_date_to: Optional[date] = None
    end_date_from: Optional[date] = None
    end_date_to: Optional[date] = None
    min_cost: Optional[Decimal] = None
    max_cost: Optional[Decimal] = None
