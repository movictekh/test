from ninja import Schema
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class ScorecardGenerateSchema(Schema):
    employee_id: int
    month: int
    year: int
    # employee_name: Optional[str] = None
    # employee_position: Optional[str] = None
    # branch_id: Optional[str] = None


class ScorecardUpdateSchema(Schema):
    attendance_score: Optional[Decimal] = None
    task_delivery_score: Optional[Decimal] = None
    report_accuracy_score: Optional[Decimal] = None
    brand_contribution_score: Optional[Decimal] = None
    training_progress_score: Optional[Decimal] = None
    target_score: Optional[Decimal] = None
    notes: Optional[str] = None
    # employee_name: Optional[str] = None
    # employee_position: Optional[str] = None
    # branch_id: Optional[str] = None


class ScorecardResponseSchema(Schema):
    id: int
    employee_id: int
    employee_name: Optional[str] = None
    employee_level: Optional[str] = None
    month: int
    year: int
    attendance_score: Decimal
    task_delivery_score: Decimal
    report_accuracy_score: Decimal
    brand_contribution_score: Decimal
    training_progress_score: Decimal
    overall_score: Decimal
    target_score: Decimal
    target_achievement: Decimal
    ranking: Optional[int] = None
    is_auto_generated: bool
    notes: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScorecardListItemSchema(Schema):
    id: int
    employee_id: int
    # employee_name: str
    # employee_position: str
    # branch_id: str
    month: int
    year: int
    overall_score: Decimal
    target_score: Decimal
    target_achievement: Decimal
    ranking: Optional[int] = None
    is_auto_generated: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScorecardCompareSchema(Schema):
    scorecards: List[ScorecardResponseSchema]


class LeaderboardEntrySchema(Schema):
    rank: int
    employee_id: int
    employee_name: Optional[str] = None
    branch: Optional[str] = None
    score: Decimal
    award: Optional[str] = None


class LeaderboardResponseSchema(Schema):
    month: int
    year: int
    entries: List[LeaderboardEntrySchema]
    avg_score: Decimal
    total_participants: int
