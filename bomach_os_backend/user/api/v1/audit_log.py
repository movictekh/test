from ninja import Router
from django.http import HttpRequest
from django.db.models import Q
from typing import List, Optional
from datetime import datetime, timedelta
from ninja.pagination import paginate, LimitOffsetPagination

from user.api.schemas.audit_log import AuditLogResponse
from user.models import AuditLog
from user.utils.perm import require_permission
from user.api.schemas import (
    ErrorResponse,
)

audit_log_api = Router(tags=["Audit Logs"])


@audit_log_api.get("", response={200: List[AuditLogResponse], 401: ErrorResponse})
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("audit_logs", "list")
def list_audit_logs(
    request: HttpRequest,
    search: Optional[str] = None,
    user_id: Optional[int] = None,
    audit_type: Optional[str] = None,
    audit_status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    queryset = AuditLog.objects.select_related("user").all()

    if search:
        queryset = queryset.filter(
            Q(activity__icontains=search)
            | Q(user__first_name__icontains=search)
            | Q(user__last_name__icontains=search)
            | Q(user__email__icontains=search)
        )

    if user_id:
        queryset = queryset.filter(user_id=user_id)

    if audit_type:
        queryset = queryset.filter(audit_type=audit_type)

    if audit_status:
        queryset = queryset.filter(audit_status=audit_status)

    if start_date:
        try:
            queryset = queryset.filter(
                created_at__gte=datetime.fromisoformat(start_date)
            )
        except ValueError:
            pass

    if end_date:
        try:
            end_datetime = datetime.fromisoformat(end_date) + timedelta(days=1)
            queryset = queryset.filter(created_at__lt=end_datetime)
        except ValueError:
            pass

    return queryset
