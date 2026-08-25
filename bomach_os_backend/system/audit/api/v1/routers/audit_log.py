"""Technical audit-log HTTP boundary."""

from typing import List, Optional

from django.http import HttpRequest
from ninja import Router
from ninja.pagination import LimitOffsetPagination, paginate

from system.audit.api.v1.schemas import AuditLogResponse
from system.audit.selectors import list_audit_logs as select_audit_logs
from system.authorization import require_permission
from user.api.schemas import ErrorResponse

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
    return select_audit_logs(
        search=search,
        user_id=user_id,
        audit_type=audit_type,
        audit_status=audit_status,
        start_date=start_date,
        end_date=end_date,
    )


__all__ = ["audit_log_api", "list_audit_logs"]
