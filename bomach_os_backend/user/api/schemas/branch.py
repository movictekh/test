from ninja import Schema, File
from ninja.files import UploadedFile
from typing import Optional, List
from datetime import datetime, time
from pydantic import field_validator


# Business Hours Schemas
class BusinessHoursInputSchema(Schema):
    """Schema for creating/updating a single day's business hours"""

    day_of_week: int  # 0=Monday, 6=Sunday
    open_time: Optional[time] = None  # e.g. "09:00:00"
    close_time: Optional[time] = None  # e.g. "17:00:00"
    is_open: bool = True

    @field_validator("open_time", "close_time", mode="before")
    @classmethod
    def parse_time(cls, v):
        if isinstance(v, str):
            if v.endswith("Z"):
                v = v[:-1]  # remove Z
            try:
                dt = datetime.fromisoformat(v)
                return dt.time().replace(tzinfo=None)
            except ValueError:
                pass
        if isinstance(v, time) and v.tzinfo:
            return v.replace(tzinfo=None)
        return v


class BusinessHoursSchema(Schema):
    """Schema for business hours response"""

    id: int
    day_of_week: int
    day_name: str
    open_time: Optional[str] = None
    close_time: Optional[str] = None
    is_open: bool

    @staticmethod
    def resolve_day_name(obj):
        return obj.get_day_of_week_display()

    @staticmethod
    def resolve_open_time(obj):
        return obj.open_time.strftime("%H:%M") if obj.open_time else None

    @staticmethod
    def resolve_close_time(obj):
        return obj.close_time.strftime("%H:%M") if obj.close_time else None


# Branch Schemas
class BranchCreateSchema(Schema):
    """Schema for creating a branch"""

    branch_name: str
    branch_id: Optional[str] = None  # Optional, will auto-generate if not provided
    default_currency: Optional[str] = None
    language_preference: Optional[str] = None
    country: str
    country_code: Optional[str] = None
    state: str
    state_code: Optional[str] = None
    city: Optional[str] = None
    lga: Optional[str] = None
    office_address: str
    operational_status: str = "active"
    branch_role: str = "branch"
    contact_email: str
    contact_phone: str
    manager_id: Optional[int] = None
    branch_file: Optional[str] = None  # URL from upload endpoint
    notes: Optional[str] = None
    business_hours: Optional[List[BusinessHoursInputSchema]] = None


class BranchUpdateSchema(Schema):
    """Schema for updating a branch"""

    branch_name: Optional[str] = None
    default_currency: Optional[str] = None
    language_preference: Optional[str] = None

    country: Optional[str] = None
    country_code: Optional[str] = None
    state: Optional[str] = None
    state_code: Optional[str] = None
    city: Optional[str] = None
    lga: Optional[str] = None
    office_address: Optional[str] = None
    operational_status: Optional[str] = None
    branch_role: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    manager_id: Optional[int] = None
    branch_file: Optional[str] = None  # URL from upload endpoint
    is_active: Optional[bool] = None
    notes: Optional[str] = None
    business_hours: Optional[List[BusinessHoursInputSchema]] = None


class BranchSchema(Schema):
    """Schema for branch response"""

    id: int
    branch_name: str
    branch_id: str
    default_currency: Optional[str] = None
    language_preference: Optional[str] = None
    country: str
    country_code: Optional[str] = None
    state: str
    state_code: Optional[str] = None
    city: Optional[str] = None
    lga: Optional[str] = None
    office_address: str
    full_address: str
    operational_status: str
    operational_status_display: str
    branch_role: str
    branch_role_display: str
    contact_email: str
    contact_phone: str
    manager_id: Optional[int] = None
    manager_name: Optional[str] = None
    branch_file: Optional[str] = None
    is_active: bool
    is_operational: bool
    notes: Optional[str] = None
    business_hours: List[BusinessHoursSchema] = []
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_business_hours(obj):
        return list(obj.business_hours.all())

    @staticmethod
    def resolve_full_address(obj):
        return obj.full_address

    @staticmethod
    def resolve_operational_status_display(obj):
        return obj.get_operational_status_display()

    @staticmethod
    def resolve_branch_role_display(obj):
        return obj.get_branch_role_display()

    @staticmethod
    def resolve_manager_name(obj):
        if obj.manager:
            return (
                f"{obj.manager.first_name} {obj.manager.last_name}".strip()
                or obj.manager.email
            )
        return None

    @staticmethod
    def resolve_branch_file(obj):
        if obj.branch_file:
            return obj.branch_file.url
        return None

    @staticmethod
    def resolve_is_operational(obj):
        return obj.is_operational


# Additional schema for operational status and branch role choices
class ChoiceSchema(Schema):
    """Schema for choice options"""

    value: str
    label: str


class BranchChoicesSchema(Schema):
    """Schema for branch choice fields"""

    operational_status: List[ChoiceSchema]
    branch_role: List[ChoiceSchema]


# Branch Performance Analysis Schemas
class KeyInsightSchema(Schema):
    """Schema for individual key insight"""

    title: str
    value: str
    status: str  # 'high', 'medium', 'low'
    recommendation: str


class RevenueTrendPointSchema(Schema):
    """Schema for revenue trend data point"""

    month: str
    actual_revenue: float
    projected_revenue: float


class BranchPerformanceMetricsSchema(Schema):
    """Schema for top-level performance metrics"""

    revenue_generated: str
    operational_efficiency: str
    customer_satisfaction: str
    total_employees: int


class BranchDetailsSchema(Schema):
    """Schema for branch detail information"""

    branch_name: str
    location: str
    status: str
    revenue: str
    revenue_percentage: str
    employees: int
    employee_productivity: str
    projects: int
    active_projects: int
    customer_satisfaction_percentage: str
    customer_count: int


class BranchPerformanceAnalysisSchema(Schema):
    """Schema for complete branch performance analysis"""

    metrics: BranchPerformanceMetricsSchema
    key_insights: List[KeyInsightSchema]
    revenue_trend: List[RevenueTrendPointSchema]
    branch_details: BranchDetailsSchema
