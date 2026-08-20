from datetime import datetime
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, Field


class OfferLetterCreateSchema(BaseModel):
    template: str = Field(..., description="Template: standard_full_time, standard_part_time, contract, internship")
    annual_salary: Decimal = Field(..., gt=0)
    letter_content: str
    start_date: datetime


class OfferLetterUpdateSchema(BaseModel):
    template: Optional[str] = None
    annual_salary: Optional[Decimal] = Field(None, gt=0)
    start_date: Optional[datetime] = None
    letter_content: Optional[str] = None
    status: Optional[str] = None


class OfferLetterResponseSchema(BaseModel):
    id: int
    applicant_id: int
    template: str
    annual_salary: Decimal
    start_date: datetime
    letter_content: str
    status: str
    sent_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OfferLetterListItemSchema(BaseModel):
    id: int
    applicant_id: int
    template: str
    annual_salary: Decimal
    start_date: datetime
    status: str
    sent_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
