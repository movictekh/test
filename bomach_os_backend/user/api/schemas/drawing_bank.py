from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from ninja import Schema

# --- Request Schemas ---


class DrawingBankCreateSchema(Schema):
    title: str
    building_category: str
    drawing_file: str
    file_name: Optional[str] = ""
    file_size_mb: Optional[Decimal] = None
    description: str
    tags: Optional[List[str]] = []


class DrawingBankUpdateSchema(Schema):
    title: Optional[str] = None
    building_category: Optional[str] = None
    drawing_file: Optional[str] = None
    file_name: Optional[str] = None
    file_size_mb: Optional[Decimal] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None


class DrawingBankRejectSchema(Schema):
    rejection_reason: str


# --- Response Schemas ---


class DrawingBankBaseResponse(Schema):
    id: int
    title: str
    building_category: str
    building_category_display: str
    status: str
    status_display: str
    employee_name: str
    tags: List[str]
    created_at: datetime

    @staticmethod
    def resolve_building_category_display(obj):
        return obj.get_building_category_display()

    @staticmethod
    def resolve_status_display(obj):
        return obj.get_status_display()

    @staticmethod
    def resolve_employee_name(obj):
        return (
            f"{obj.employee.first_name} {obj.employee.last_name}".strip()
            or obj.employee.username
        )


class DrawingBankListResponseSchema(DrawingBankBaseResponse):
    file_name: str
    file_size_mb: Optional[str] = None
    approved_by_name: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    download_count: int

    @staticmethod
    def resolve_file_size_mb(obj):
        if obj.file_size_mb is not None:
            return f"{obj.file_size_mb:.1f} MB"
        return None

    @staticmethod
    def resolve_approved_by_name(obj):
        if obj.approved_by:
            return (
                f"{obj.approved_by.first_name} {obj.approved_by.last_name}".strip()
                or obj.approved_by.username
            )
        return None


class DrawingBankFullResponseSchema(DrawingBankBaseResponse):
    drawing_file: str
    file_name: str
    file_size_mb: Optional[str] = None
    description: str
    approved_by_name: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    download_count: int

    @staticmethod
    def resolve_file_size_mb(obj):
        if obj.file_size_mb is not None:
            return f"{obj.file_size_mb:.1f} MB"
        return None

    @staticmethod
    def resolve_approved_by_name(obj):
        if obj.approved_by:
            return (
                f"{obj.approved_by.first_name} {obj.approved_by.last_name}".strip()
                or obj.approved_by.username
            )
        return None


class DrawingBankStatsSchema(Schema):
    total_submissions: int
    pending_approval: int
    approved: int
    rejected: int
