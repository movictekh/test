from ninja import Schema
from typing import Optional
from datetime import datetime
from decimal import Decimal


class EvaluationCreateSchema(Schema):
    employee_id: int
    evaluator_id: int
    month: int
    year: int
    manager_comments: str
    promotion_required: bool = False
    training_required: bool = False
    salary_increase: bool = False


class EvaluationUpdateSchema(Schema):
    manager_comments: Optional[str] = None
    promotion_required: Optional[bool] = None
    training_required: Optional[bool] = None
    salary_increase: Optional[bool] = None


class EvaluationResponseSchema(Schema):
    id: int
    employee_id: int
    evaluator_id: int
    month: int
    year: int
    manager_comments: str
    promotion_required: bool
    training_required: bool
    salary_increase: bool

    # Employee info from gRPC
    employee_name: Optional[str] = None
    employee_level: Optional[str] = None

    # Scorecard metrics
    attendance_score: Optional[Decimal] = None
    task_delivery_score: Optional[Decimal] = None
    report_accuracy_score: Optional[Decimal] = None
    training_progress_score: Optional[Decimal] = None
    brand_contribution_score: Optional[Decimal] = None
    overall_score: Optional[Decimal] = None
    target_score: Optional[Decimal] = None
    target_achievement: Optional[Decimal] = None
    ranking: Optional[int] = None

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EvaluationListItemSchema(Schema):
    id: int
    employee_id: int
    evaluator_id: int
    month: int
    year: int
    promotion_required: bool
    training_required: bool
    salary_increase: bool
    overall_score: Optional[Decimal] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
