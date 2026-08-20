from ninja import Schema
from typing import Optional
from datetime import date, datetime
from decimal import Decimal

# ============== Legal Case Schemas ==============


class CreateLegalCaseRequest(Schema):
    """Request schema for creating a new legal case"""

    case_name: str
    case_type: str  # contract_dispute, employment, regulatory, civil, criminal, corporate, intellectual_property
    status: Optional[str] = (
        "open"  # in_progress, settled, open, closed, pending, dismissed, won, lost
    )
    exposure: Optional[Decimal] = None
    next_hearing: Optional[date] = None
    case_number: Optional[str] = None
    description: Optional[str] = ""
    date_filed: Optional[date] = None
    date_closed: Optional[date] = None


class UpdateLegalCaseRequest(Schema):
    """Request schema for updating a legal case"""

    case_name: Optional[str] = None
    case_type: Optional[str] = None
    status: Optional[str] = None
    exposure: Optional[Decimal] = None
    next_hearing: Optional[date] = None
    case_number: Optional[str] = None
    description: Optional[str] = None
    date_filed: Optional[date] = None
    date_closed: Optional[date] = None


class UpdateCaseStatusRequest(Schema):
    """Request schema for updating case status"""

    status: str


class LegalCaseResponse(Schema):
    """Response schema for legal case details"""

    id: int
    case_name: str
    case_type: str
    case_type_display: str
    status: str
    status_display: str
    exposure: Optional[Decimal]
    next_hearing: Optional[date]
    case_number: Optional[str]
    description: str
    date_filed: Optional[date]
    date_closed: Optional[date]
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_case_type_display(obj):
        return obj.get_case_type_display()

    @staticmethod
    def resolve_status_display(obj):
        return obj.get_status_display()


class LegalCaseStatisticsResponse(Schema):
    """Response schema for legal case statistics"""

    total_cases: int
    open_cases: int
    in_progress_cases: int
    settled_cases: int
    closed_cases: int
    won_cases: int
    lost_cases: int
    dismissed_cases: int
    pending_cases: int
    total_exposure: Decimal
    upcoming_hearings: int
    cases_by_type: dict
