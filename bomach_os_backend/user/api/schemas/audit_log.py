from ninja import Schema
from typing import Optional, Any, Dict
from datetime import datetime

from user.models.user import User


class UserInfo(Schema):
    """User information for audit log entries"""

    id: Optional[int] = None
    email: Optional[str] = None
    full_name: Optional[str] = None

    @staticmethod
    def resolve_full_name(obj: User, context):
        return f"{obj.first_name or ''} {obj.last_name or ''}".strip()

    class Config:
        from_attributes = True


class AuditLogResponse(Schema):
    """Schema for a single audit log entry"""

    id: int
    activity: str
    audit_type: str
    audit_type_display: str
    audit_status: str
    audit_status_display: str
    ip_address: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    user: Optional[UserInfo] = None
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_audit_type_display(obj):
        return obj.get_audit_type_display()

    @staticmethod
    def resolve_audit_status_display(obj):
        return obj.get_audit_status_display()

    class Config:
        from_attributes = True
