"""Read/query boundary for technical audit logs."""

from datetime import datetime, timedelta

from django.db.models import Q

from system.audit.models import AuditLog


def list_audit_logs(
    *,
    search=None,
    user_id=None,
    audit_type=None,
    audit_status=None,
    start_date=None,
    end_date=None,
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


__all__ = ["list_audit_logs"]
