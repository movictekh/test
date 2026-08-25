from typing import Any, Dict, Optional

from django.http import HttpRequest


def _get_client_ip(request: HttpRequest) -> Optional[str]:
    x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded:
        return x_forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR") or None


def log_activity(
    audit_type: str,
    activity: str,
    user=None,
    request: Optional[HttpRequest] = None,
    audit_status: str = "info",
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    try:
        from system.audit.models import AuditLog

        AuditLog.objects.create(
            audit_type=audit_type,
            audit_status=audit_status,
            activity=activity,
            user=user,
            ip_address=_get_client_ip(request) if request else None,
            metadata=metadata or {},
        )
    except Exception:
        pass
