from ninja import Schema, Field
from typing import Optional, List
from datetime import date
from pydantic import validator


class PerformanceReviewCreateSchema(Schema):
    employee_id: int
    reviewer_id: int
    review_date: date
    review_period: str
    overall_rating: int = Field(..., ge=1, le=5)
    strengths: str
    areas_for_improvement: str
    feedback: Optional[str] = None
    employee_comment: Optional[str] = None

    @validator("overall_rating")
    def validate_rating(cls, v):
        if not 1 <= v <= 5:
            raise ValueError("Rating must be between 1 and 5")
        return v


class PerformanceReviewUpdateSchema(Schema):
    review_date: Optional[date] = None
    review_period: Optional[str] = None
    overall_rating: Optional[int] = Field(None, ge=1, le=5)
    strengths: Optional[str] = None
    areas_for_improvement: Optional[str] = None
    feedback: Optional[str] = None
    employee_comment: Optional[str] = None

    @validator("overall_rating")
    def validate_rating(cls, v):
        if v is not None and not 1 <= v <= 5:
            raise ValueError("Rating must be between 1 and 5")
        return v


class PerformanceReviewResponseSchema(Schema):
    employee_id: int
    reviewer_id: int
    review_date: date
    review_period: str
    overall_rating: int
    rating_display: str
    strengths: str
    areas_for_improvement: str
    feedback: Optional[str] = None
    employee_comment: Optional[str] = None
    created_at: str
    updated_at: str

    @staticmethod
    def resolve_created_at(obj):
        return obj.created_at.isoformat()

    @staticmethod
    def resolve_updated_at(obj):
        return obj.updated_at.isoformat()


class PerformanceReviewFilterSchema(Schema):
    employee_id: Optional[int] = None
    reviewer_id: Optional[int] = None
    review_period: Optional[str] = None
    min_rating: Optional[int] = None
    max_rating: Optional[int] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
