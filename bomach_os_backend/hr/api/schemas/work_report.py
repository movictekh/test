from datetime import date, datetime
from decimal import Decimal
from typing import List, Literal, Optional

from ninja import Schema


class AttachmentOut(Schema):
    file_url: str


class WorkReportCreate(Schema):
    day: date
    hours_worked: Optional[Decimal] = Decimal("0.0")
    # mood: Optional[Literal['happy', 'neutral', 'sad', 'stressed', 'tired', 'frustrated']] = 'neutral'
    operational_base: Optional[str] = None
    work_activities: Optional[str] = None
    task_details: Optional[str] = None
    plan_next_day: Optional[str] = None
    status: Optional[Literal["draft", "submitted"]] = "draft"
    attachments: List[str] = []


class WorkReportUpdate(Schema):
    day: Optional[date] = None
    hours_worked: Optional[Decimal] = None
    # mood: Optional[Literal['happy', 'neutral', 'sad', 'stressed', 'tired', 'frustrated']] = None
    operational_base: Optional[str] = None
    work_activities: Optional[str] = None
    task_details: Optional[str] = None
    plan_next_day: Optional[str] = None
    status: Optional[Literal["draft", "submitted"]] = None
    attachments: Optional[List[str]] = None


class WorkReportApprove(Schema):
    rating: Optional[int] = None
    feedback: Optional[str] = None


class WorkReportReject(Schema):
    feedback: str


class WorkReportReviewer(Schema):
    id: int
    email: str
    first_name: str
    last_name: str


class WorkReportOut(Schema):
    id: int
    employee_id: int
    day: date
    hours_worked: Decimal
    # mood: str
    operational_base: Optional[str] = None
    work_activities: Optional[str] = None
    task_details: Optional[str] = None
    plan_next_day: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
    feedback: Optional[str] = None
    rating: Optional[int] = None
    reviewed_by_id: Optional[int] = None
    reviewed_by: Optional[WorkReportReviewer] = None
    reviewed_at: Optional[datetime] = None
    attachments: Optional[List[AttachmentOut]] = None

    @staticmethod
    def resolve_reviewed_by(obj):
        return obj.reviewed_by


class WorkReportListItem(Schema):
    id: int
    employee_id: int
    day: date
    hours_worked: Decimal
    # mood: str
    status: str
    created_at: datetime
    updated_at: datetime
    feedback: Optional[str] = None
    rating: Optional[int] = None
    reviewed_by_id: Optional[int] = None
    reviewed_by: Optional[WorkReportReviewer] = None
    reviewed_at: Optional[datetime] = None
    attachments: Optional[List[AttachmentOut]] = None

    @staticmethod
    def resolve_reviewed_by(obj):
        return obj.reviewed_by
