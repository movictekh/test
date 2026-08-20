from ninja import Schema
from typing import Optional, List
from datetime import date, datetime


class BoardResolutionCreateSchema(Schema):
    title: str
    description: str
    resolution_type: str
    resolution_date: date
    status: Optional[str] = None
    attachment_url: Optional[str] = None
    notes: Optional[str] = None


class BoardResolutionUpdateSchema(Schema):
    title: Optional[str] = None
    description: Optional[str] = None
    resolution_type: Optional[str] = None
    resolution_date: Optional[date] = None
    status: Optional[str] = None
    attachment_url: Optional[str] = None
    notes: Optional[str] = None


class BoardResolutionSchema(Schema):
    id: int
    resolution_id: str
    title: str
    description: str
    resolution_type: str
    resolution_type_display: str
    status: str
    status_display: str
    resolution_date: date
    attachment_url: Optional[str] = None
    notes: Optional[str] = None
    created_by_id: Optional[int] = None
    created_by_name: Optional[str] = None
    approved_by_id: Optional[int] = None
    approved_by_name: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_resolution_type_display(obj):
        return obj.get_resolution_type_display()

    @staticmethod
    def resolve_status_display(obj):
        return obj.get_status_display()

    @staticmethod
    def resolve_created_by_name(obj):
        if obj.created_by:
            return (
                f"{obj.created_by.first_name} {obj.created_by.last_name}".strip()
                or obj.created_by.email
            )
        return None

    @staticmethod
    def resolve_approved_by_name(obj):
        if obj.approved_by:
            return (
                f"{obj.approved_by.first_name} {obj.approved_by.last_name}".strip()
                or obj.approved_by.email
            )
        return None


class BoardResolutionChoicesSchema(Schema):
    types: List[dict]
    statuses: List[dict]
