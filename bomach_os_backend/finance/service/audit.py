from datetime import date, datetime
from decimal import Decimal

from django.db.models import Q

from user.models import AuditLog


def _json_safe(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    return value


def _entity_branch(entity):
    if entity is None:
        return None

    branch = getattr(entity, "branch", None)
    if branch is not None:
        return branch

    service_order = getattr(entity, "service_order", None)
    if service_order is not None and getattr(service_order, "branch", None) is not None:
        return service_order.branch

    finance_account = getattr(entity, "finance_account", None)
    if (
        finance_account is not None
        and getattr(finance_account, "branch", None) is not None
    ):
        return finance_account.branch

    invoice = getattr(entity, "invoice", None)
    if invoice is not None:
        service_request = getattr(invoice, "service_request", None)
        if (
            service_request is not None
            and getattr(service_request, "branch", None) is not None
        ):
            return service_request.branch
        order = getattr(invoice, "order", None)
        if order is not None and getattr(order, "branch", None) is not None:
            return order.branch

    return None


def record_finance_audit(
    *,
    area,
    action,
    actor,
    entity=None,
    reference="",
    branch=None,
    amount=None,
    details=None,
    activity="",
):
    branch = branch or _entity_branch(entity)
    entity_type = type(entity).__name__ if entity is not None else ""
    entity_id = getattr(entity, "pk", None) if entity is not None else None

    metadata = {
        "area": area,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "reference": reference,
        "branch_id": getattr(branch, "id", None),
        "branch_name": getattr(branch, "branch_name", "") if branch else "",
    }
    if amount is not None:
        metadata["amount"] = str(amount)
    if details:
        metadata["details"] = _json_safe(details)

    if not activity:
        subject = reference or entity_type or "Finance record"
        activity = (
            f"{area.replace('_', ' ').title()}: "
            f"{action.replace('_', ' ')} — {subject}"
        )

    return AuditLog.objects.create(
        audit_type=AuditLog.AuditType.FINANCE_ACTION,
        audit_status=AuditLog.AuditStatus.SUCCESS,
        activity=activity,
        user=actor,
        metadata=_json_safe(metadata),
    )


def finance_audit_queryset(
    *,
    branch_ids=None,
    branch_id=None,
    area=None,
    action=None,
    user_id=None,
    date_from=None,
    date_to=None,
    search=None,
):
    queryset = AuditLog.objects.select_related("user").filter(
        audit_type=AuditLog.AuditType.FINANCE_ACTION
    )

    if branch_ids is not None:
        queryset = queryset.filter(metadata__branch_id__in=list(branch_ids))
    if branch_id is not None:
        queryset = queryset.filter(metadata__branch_id=branch_id)
    if area:
        queryset = queryset.filter(metadata__area=area)
    if action:
        queryset = queryset.filter(metadata__action=action)
    if user_id:
        queryset = queryset.filter(user_id=user_id)
    if date_from:
        queryset = queryset.filter(created_at__date__gte=date_from)
    if date_to:
        queryset = queryset.filter(created_at__date__lte=date_to)
    if search:
        value = search.strip()
        if value:
            queryset = queryset.filter(
                Q(activity__icontains=value)
                | Q(user__first_name__icontains=value)
                | Q(user__last_name__icontains=value)
                | Q(user__email__icontains=value)
            )

    return queryset.order_by("-created_at", "-id")
