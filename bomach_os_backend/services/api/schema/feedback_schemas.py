from ninja import Schema
from typing import Optional
from datetime import datetime
from decimal import Decimal


class FeedbackIn(Schema):
    order_id: int
    feedback_type: str
    rating: int
    comment: str
    status: str = "open"
    internal_note: Optional[str] = None


class FeedbackUpdate(Schema):
    feedback_type: Optional[str] = None
    rating: Optional[int] = None
    comment: Optional[str] = None
    status: Optional[str] = None
    internal_note: Optional[str] = None


class RecordedByOut(Schema):
    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: str

    class Config:
        from_attributes = True


class FeedbackOut(Schema):
    id: int
    order_id: int
    order_number: str
    client_name: str
    service_name: str
    feedback_type: str
    rating: int
    comment: str
    internal_note: Optional[str] = None
    status: str
    recorded_by: RecordedByOut
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FeedbackStatsSchema(Schema):
    total: int
    average_rating: Decimal
    client_satisfaction: Decimal
    rework_rate: Decimal
    repeat_clients: Decimal
