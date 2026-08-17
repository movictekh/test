from datetime import datetime
from typing import Optional

from ninja import Schema
from pydantic import Field


class JobPostingCreateSchema(Schema):
    """Schema for creating a new job posting"""

    job_title: str = Field(..., min_length=1, max_length=255)
    department_id: Optional[int] = Field(
        None, description="Department ID from department microservice"
    )
    branch_id: int = Field(..., description="Branch ID")
    job_type: str = Field(
        ...,
        description="Job type: Full-Time, Part-Time, Contract, Internship, Temporary",
    )
    status: Optional[str] = Field(
        default="draft", description="Status: draft, pending, active, closed, cancelled"
    )
    description: Optional[str] = None
    requirements: Optional[str] = None
    responsibilities: Optional[str] = None

    salary_min: Optional[float] = None
    salary_max: Optional[float] = None

    deadline: Optional[datetime] = None
    is_active: Optional[bool] = True


class JobPostingUpdateSchema(Schema):
    """Schema for updating a job posting"""

    job_title: Optional[str] = Field(None, min_length=1, max_length=255)
    department_id: Optional[int] = Field(
        None, description="Department ID from department microservice"
    )
    branch_id: Optional[int] = Field(None, description="Branch ID")
    job_type: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    responsibilities: Optional[str] = None

    salary_min: Optional[float] = None
    salary_max: Optional[float] = None

    deadline: Optional[datetime] = None
    is_active: Optional[bool] = None


class JobPostingStatusUpdateSchema(Schema):
    """Schema for updating only the status of a job posting"""

    status: str = Field(
        ..., description="Status: draft, pending, active, closed, cancelled"
    )


class JobPostingResponseSchema(Schema):
    """Schema for job posting response"""

    id: int
    job_title: str
    department_id: Optional[int] = None
    branch_id: int
    job_type: str
    status: str
    description: Optional[str] = None
    requirements: Optional[str] = None
    responsibilities: Optional[str] = None

    salary_min: Optional[float] = None
    salary_max: Optional[float] = None

    vacancy_count: int
    applicants_count: int
    deadline: Optional[datetime] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_applicants_count(obj):
        return obj.applicants.count()


class JobPostingListItemSchema(Schema):
    """Schema for job posting in list view (minimal data)"""

    id: int
    job_title: str
    department_id: Optional[int] = None
    branch_id: int
    job_type: str
    status: str
    applicants_count: int
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_applicants_count(obj):
        return obj.applicants.count()


class MessageSchema(Schema):
    """Generic message response schema"""

    detail: str
