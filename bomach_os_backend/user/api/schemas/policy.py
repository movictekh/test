from ninja import Schema
from typing import Optional, List
from datetime import date, datetime


class PolicyDepartmentSchema(Schema):
    id: int
    name: str


class PolicyCreateSchema(Schema):
    title: str
    category: str
    content: str
    version: str = '1.0'
    status: str = 'draft'
    effective_date: date
    review_date: Optional[date] = None
    # IDs of applicable departments — omit or pass [] to apply to all departments
    department_ids: List[int] = []
    attachment_url: Optional[str] = None


class PolicyUpdateSchema(Schema):
    title: Optional[str] = None
    category: Optional[str] = None
    content: Optional[str] = None
    version: Optional[str] = None
    status: Optional[str] = None
    effective_date: Optional[date] = None
    review_date: Optional[date] = None
    department_ids: Optional[List[int]] = None
    attachment_url: Optional[str] = None


class PolicySchema(Schema):
    id: int
    policy_id: str
    title: str
    category: str
    category_display: str
    content: str
    version: str
    status: str
    status_display: str
    effective_date: date
    review_date: Optional[date] = None
    departments: List[PolicyDepartmentSchema]
    applies_to_all_departments: bool
    attachment_url: Optional[str] = None
    created_by_id: Optional[int] = None
    created_by_name: Optional[str] = None
    last_updated_by_id: Optional[int] = None
    last_updated_by_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_category_display(obj):
        return obj.get_category_display()

    @staticmethod
    def resolve_status_display(obj):
        return obj.get_status_display()

    @staticmethod
    def resolve_departments(obj):
        return list(obj.departments.all())

    @staticmethod
    def resolve_applies_to_all_departments(obj):
        return not obj.departments.exists()

    @staticmethod
    def resolve_created_by_name(obj):
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}".strip() or obj.created_by.email
        return None

    @staticmethod
    def resolve_last_updated_by_name(obj):
        if obj.last_updated_by:
            return f"{obj.last_updated_by.first_name} {obj.last_updated_by.last_name}".strip() or obj.last_updated_by.email
        return None


class PolicyChoicesSchema(Schema):
    categories: List[dict]
    statuses: List[dict]
