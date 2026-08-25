from datetime import datetime
from typing import List, Optional

from ninja import Schema


class AnnouncementBranchSchema(Schema):
    id: int
    branch_name: str
    branch_id: str


class AnnouncementDepartmentSchema(Schema):
    id: int
    name: str


class AnnouncementCreateSchema(Schema):
    title: str
    content: str
    announcement_type: str = "general"
    priority: str = "normal"
    branch_ids: List[int] = []
    department_ids: List[int] = []
    is_active: bool = True
    publish_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class AnnouncementUpdateSchema(Schema):
    title: Optional[str] = None
    content: Optional[str] = None
    announcement_type: Optional[str] = None
    priority: Optional[str] = None
    branch_ids: Optional[List[int]] = None
    department_ids: Optional[List[int]] = None
    is_active: Optional[bool] = None
    publish_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class AnnouncementSchema(Schema):
    id: int
    announcement_id: str
    title: str
    content: str
    announcement_type: str
    announcement_type_display: str
    priority: str
    priority_display: str
    branches: List[AnnouncementBranchSchema]
    departments: List[AnnouncementDepartmentSchema]
    targets_all_branches: bool
    targets_all_departments: bool
    created_by_id: Optional[int] = None
    created_by_name: Optional[str] = None
    is_active: bool
    publish_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_announcement_type_display(obj):
        return obj.get_announcement_type_display()

    @staticmethod
    def resolve_priority_display(obj):
        return obj.get_priority_display()

    @staticmethod
    def resolve_branches(obj):
        return list(obj.branches.all())

    @staticmethod
    def resolve_departments(obj):
        return list(obj.departments.all())

    @staticmethod
    def resolve_targets_all_branches(obj):
        return not obj.branches.exists()

    @staticmethod
    def resolve_targets_all_departments(obj):
        return not obj.departments.exists()

    @staticmethod
    def resolve_created_by_id(obj):
        return obj.created_by_id

    @staticmethod
    def resolve_created_by_name(obj):
        if obj.created_by:
            return (
                f"{obj.created_by.first_name} {obj.created_by.last_name}".strip()
                or obj.created_by.email
            )
        return None


class AnnouncementChoicesSchema(Schema):
    announcement_types: List[dict]
    priorities: List[dict]
