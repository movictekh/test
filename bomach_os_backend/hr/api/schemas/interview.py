from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class InterviewCreateSchema(BaseModel):
    interviewer_id: int
    scheduled_at: datetime
    meeting_link: Optional[str] = None


class InterviewUpdateSchema(BaseModel):
    interviewer_id: Optional[int] = None
    scheduled_at: Optional[datetime] = None
    meeting_link: Optional[str] = None
    status: Optional[str] = None


class InterviewFeedbackSchema(BaseModel):
    feedback: str = Field(..., min_length=1)
    status: Optional[str] = Field(default="completed")


class InterviewResponseSchema(BaseModel):
    id: int
    applicant_id: int
    interviewer_id: int
    scheduled_at: datetime
    meeting_link: Optional[str] = None
    feedback: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InterviewListItemSchema(BaseModel):
    id: int
    applicant_id: int
    interviewer_id: int
    scheduled_at: datetime
    meeting_link: Optional[str] = None
    status: str
    feedback: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
