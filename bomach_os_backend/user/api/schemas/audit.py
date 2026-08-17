from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from ninja import Schema

# ============== Audit Schemas ==============


class CreateAuditRequest(Schema):
    """Request schema for creating a new audit"""

    audit_name: str
    audit_type: str  # external, regulatory, internal, customer, financial, operational, compliance
    auditor_name: str
    auditor_title: Optional[str] = ""
    status: Optional[str] = (
        "scheduled"  # completed, in_progress, scheduled, draft, cancelled, failed
    )
    score: Optional[int] = None  # 0-100
    audit_date: date
    audit_number: Optional[str] = None
    description: Optional[str] = ""
    findings: Optional[str] = ""
    recommendations: Optional[str] = ""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    auditor_organization: Optional[str] = ""
    department: Optional[str] = ""


class UpdateAuditRequest(Schema):
    """Request schema for updating an audit"""

    audit_name: Optional[str] = None
    audit_type: Optional[str] = None
    auditor_name: Optional[str] = None
    auditor_title: Optional[str] = None
    status: Optional[str] = None
    score: Optional[int] = None
    audit_date: Optional[date] = None
    audit_number: Optional[str] = None
    description: Optional[str] = None
    findings: Optional[str] = None
    recommendations: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    auditor_organization: Optional[str] = None
    department: Optional[str] = None


class UpdateAuditStatusRequest(Schema):
    """Request schema for updating audit status"""

    status: str  # completed, in_progress, scheduled, draft, cancelled, failed


class UpdateAuditScoreRequest(Schema):
    """Request schema for updating audit score"""

    score: int  # 0-100


class AuditResponse(Schema):
    """Response schema for audit details"""

    id: int
    audit_name: str
    audit_type: str
    audit_type_display: str
    auditor_name: str
    auditor_title: str
    status: str
    status_display: str
    score: Optional[int]
    score_percentage: str
    is_passed: Optional[bool]
    score_category: str
    audit_date: date
    audit_number: Optional[str]
    description: str
    findings: str
    recommendations: str
    start_date: Optional[date]
    end_date: Optional[date]
    auditor_organization: str
    department: str
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_audit_type_display(obj):
        return obj.get_audit_type_display()

    @staticmethod
    def resolve_status_display(obj):
        return obj.get_status_display()

    @staticmethod
    def resolve_score_percentage(obj):
        return obj.score_percentage

    @staticmethod
    def resolve_is_passed(obj):
        return obj.is_passed

    @staticmethod
    def resolve_score_category(obj):
        return obj.score_category


class AuditStatisticsResponse(Schema):
    """Response schema for audit statistics"""

    total_audits: int
    completed_audits: int
    in_progress_audits: int
    scheduled_audits: int
    cancelled_audits: int
    failed_audits: int
    average_score: Optional[float]
    pass_rate: Optional[float]
    audits_by_type: dict
    audits_by_score_category: dict
    upcoming_audits_count: int


class AuditPerformanceTrendsResponse(Schema):
    """Response schema for audit performance trends"""

    period: str  # month, quarter, year
    trends: list  # List of {period: str, average_score: float, total_audits: int, pass_rate: float}
    overall_improvement: Optional[float]


class AuditorSummaryResponse(Schema):
    """Response schema for auditor summary"""

    auditor_name: str
    total_audits: int
    average_score: Optional[float]


class DepartmentAuditSummaryResponse(Schema):
    """Response schema for department audit summary"""

    department: str
    total_audits: int
    average_score: Optional[float]
    latest_audit_date: Optional[date]
    pass_rate: Optional[float]
