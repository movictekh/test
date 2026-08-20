from datetime import datetime
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, Field
from .job_posting import JobPostingListItemSchema


class ApplicantCreateSchema(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: str
    phone: str = Field(..., min_length=1, max_length=20)
    job_posting_id: int = Field(..., description="ID of the job posting")
    status: Optional[str] = "applied"
    cover_letter: Optional[str] = None
    resume: Optional[str] = None
    linkedin_url: Optional[str] = None
    portolio_url: Optional[str] = None
    notes: Optional[str] = None

    address: Optional[str] = None
    current_job_title: Optional[str] = None
    years_of_experience: Optional[int] = None
    highest_education: Optional[str] = None
    institution_name: Optional[str] = None
    source: Optional[str] = None
    expected_salary: Optional[Decimal] = None


class ApplicantUpdateSchema(BaseModel):
    """Schema for updating an applicant"""

    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[str] = None
    phone: Optional[str] = Field(None, min_length=1, max_length=20)
    job_posting_id: Optional[int] = Field(None, description="ID of the job posting")
    status: Optional[str] = None
    cover_letter: Optional[str] = None
    resume: Optional[str] = None
    linkedin_url: Optional[str] = None
    portolio_url: Optional[str] = None
    notes: Optional[str] = None

    address: Optional[str] = None
    current_job_title: Optional[str] = None
    years_of_experience: Optional[int] = None
    highest_education: Optional[str] = None
    institution_name: Optional[str] = None
    source: Optional[str] = None
    expected_salary: Optional[Decimal] = None


class ApplicantStatusUpdateSchema(BaseModel):
    """Schema for updating applicant status"""

    status: str


class ApplicantMinimalSchema(BaseModel):
    """Minimal schema for applicant (used in nested responses)"""

    id: int
    first_name: str
    last_name: str
    email: str

    class Config:
        from_attributes = True


class ApplicantResponseSchema(BaseModel):
    """Schema for applicant response"""

    id: int
    first_name: str
    last_name: str
    email: str
    phone: str
    job_posting: JobPostingListItemSchema
    status: str
    resume: Optional[str] = None
    cover_letter: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    address: Optional[str] = None
    current_job_title: Optional[str] = None
    years_of_experience: Optional[int] = None
    highest_education: Optional[str] = None
    institution_name: Optional[str] = None
    source: Optional[str] = None
    expected_salary: Optional[Decimal] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class ApplicantListItemSchema(BaseModel):
    """Schema for applicant in list view (minimal data)"""

    id: int
    first_name: str
    last_name: str
    email: str
    phone: str
    job_posting: JobPostingListItemSchema
    status: str
    created_at: datetime
    updated_at: datetime
    address: Optional[str] = None
    current_job_title: Optional[str] = None
    years_of_experience: Optional[int] = None
    highest_education: Optional[str] = None
    institution_name: Optional[str] = None
    source: Optional[str] = None
    expected_salary: Optional[Decimal] = None

    class Config:
        from_attributes = True
