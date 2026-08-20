from ninja import Router, Query
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
from typing import Optional, List, Dict, Any

from services.models.service import Quote, ServiceDeliverable
from services.models.expenses import Expense

from user.api.schemas.approval_queue import (
    ApprovalQueueChoicesSchema,
    ApprovalQueueItemSchema,
    ApprovalQueueResponseSchema,
    ApprovalQueueStatsSchema,
)

approval_queue_api = Router(tags=["Approval Queue"])

DEFAULT_HIGH_VALUE_THRESHOLD = Decimal("1000000")
DEFAULT_SLA_TARGET_HOURS = 48
DEFAULT_SLA_WINDOW_DAYS = 30

SOURCE_LABELS = {
    "quotation": "Quotation",
    "deliverable": "Deliverable",
    "expense": "Expense",
}

STATUS_LABELS = {
    "pending": "Pending",
    "approved": "Approved",
    "rejected": "Rejected",
}


def _user_name(user) -> Optional[str]:
    if not user:
        return None
    return f"{user.first_name} {user.last_name}".strip() or user.email


def _quote_items(approval_status: str = "pending") -> List[Dict[str, Any]]:
    if approval_status == "pending":
        qs = Quote.objects.select_related(
            "service", "created_by", "required_approver_role"
        ).filter(status="awaiting_approval")
    elif approval_status == "approved":
        qs = Quote.objects.select_related(
            "service", "created_by", "required_approver_role"
        ).filter(status__in=["sent", "accepted"])
    elif approval_status == "rejected":
        qs = Quote.objects.select_related(
            "service", "created_by", "required_approver_role"
        ).filter(status="rejected")
    else:
        return []

    items = []
    for q in qs:
        subject = (
            f"{q.service.name} quotation"
            if q.service
            else f"Quotation {q.quote_number}"
        )
        items.append(
            {
                "id": f"quotation-{q.id}",
                "source": "quotation",
                "source_display": "Quotation",
                "ref_number": q.quote_number,
                "subject": subject,
                "requester_name": _user_name(q.created_by),
                "approver_name": (
                    q.required_approver_role.name if q.required_approver_role else None
                ),
                "amount": q.amount,
                "created_at": q.created_at,
                "status": approval_status,
                "action_label": (
                    "Approve & Send" if approval_status == "pending" else "—"
                ),
                "approve_url": (
                    f"/api/v1/quotes/{q.id}/approve"
                    if approval_status == "pending"
                    else None
                ),
                "reject_url": None,
            }
        )
    return items


def _deliverable_items(approval_status: str = "pending") -> List[Dict[str, Any]]:
    if approval_status == "pending":
        qs = ServiceDeliverable.objects.select_related("order", "created_by").filter(
            status="under_review", approval_mode__in=["supervisor", "client"]
        )
    elif approval_status == "approved":
        qs = ServiceDeliverable.objects.select_related("order", "created_by").filter(
            status="approved"
        )
    elif approval_status == "rejected":
        qs = ServiceDeliverable.objects.select_related("order", "created_by").filter(
            status="rejected"
        )
    else:
        return []

    items = []
    for d in qs:
        approver = "Client" if d.approval_mode == "client" else "Supervisor"
        items.append(
            {
                "id": f"deliverable-{d.id}",
                "source": "deliverable",
                "source_display": "Deliverable",
                "ref_number": d.deliverable_number,
                "subject": d.title,
                "requester_name": _user_name(d.created_by),
                "approver_name": approver,
                "amount": None,
                "created_at": d.created_at,
                "status": approval_status,
                "action_label": "Approve" if approval_status == "pending" else "—",
                "approve_url": (
                    f"/api/v1/orders/{d.order_id}/deliverables/{d.id}/approve"
                    if approval_status == "pending"
                    else None
                ),
                "reject_url": (
                    f"/api/v1/orders/{d.order_id}/deliverables/{d.id}/reject"
                    if approval_status == "pending"
                    else None
                ),
            }
        )
    return items


def _expense_items(approval_status: str = "pending") -> List[Dict[str, Any]]:
    if approval_status == "pending":
        qs = Expense.objects.select_related("user").filter(status="pending")
    elif approval_status == "approved":
        qs = Expense.objects.select_related("user").filter(status="approved")
    elif approval_status == "rejected":
        qs = Expense.objects.select_related("user").filter(status="rejected")
    else:
        return []

    items = []
    for e in qs:
        items.append(
            {
                "id": f"expense-{e.id}",
                "source": "expense",
                "source_display": "Expense",
                "ref_number": f"EXP-{e.id}",
                "subject": e.description,
                "requester_name": _user_name(e.user),
                "approver_name": "Manager",
                "amount": e.amount,
                "created_at": e.created_at,
                "status": approval_status,
                "action_label": "Approve" if approval_status == "pending" else "—",
                "approve_url": (
                    f"/api/v1/expenses/{e.id}/approve"
                    if approval_status == "pending"
                    else None
                ),
                "reject_url": (
                    f"/api/v1/expenses/{e.id}/reject"
                    if approval_status == "pending"
                    else None
                ),
            }
        )
    return items


def _apply_search(
    items: List[Dict[str, Any]], search: Optional[str]
) -> List[Dict[str, Any]]:
    if not search:
        return items
    needle = search.lower()
    return [
        it
        for it in items
        if needle
        in " ".join(
            [
                it["ref_number"] or "",
                it["subject"] or "",
                it["requester_name"] or "",
                it["approver_name"] or "",
            ]
        ).lower()
    ]


def _resolved_records(window_start) -> List[Any]:
    """Return (created_at, resolved_at) tuples for approvals resolved within the window."""
    records = []
    records.extend(
        (q.created_at, q.approved_at)
        for q in Quote.objects.filter(
            status__in=["sent", "accepted"], approved_at__gte=window_start
        )
    )
    records.extend(
        (q.created_at, q.client_responded_at)
        for q in Quote.objects.filter(
            status="rejected", client_responded_at__gte=window_start
        )
    )
    records.extend(
        (d.created_at, d.approved_at)
        for d in ServiceDeliverable.objects.filter(
            status="approved", approved_at__gte=window_start
        )
    )
    records.extend(
        (d.created_at, d.rejected_at)
        for d in ServiceDeliverable.objects.filter(
            status="rejected", rejected_at__gte=window_start
        )
    )
    records.extend(
        (e.created_at, e.updated_at)
        for e in Expense.objects.filter(status="approved", updated_at__gte=window_start)
    )
    records.extend(
        (e.created_at, e.updated_at)
        for e in Expense.objects.filter(status="rejected", updated_at__gte=window_start)
    )
    return records


@approval_queue_api.get("/choices", response=ApprovalQueueChoicesSchema, auth=None)
def get_approval_queue_choices(request):
    """Get available filter choices for the approval queue."""
    return {
        "sources": [{"value": v, "label": l} for v, l in SOURCE_LABELS.items()],
        "statuses": [{"value": v, "label": l} for v, l in STATUS_LABELS.items()],
    }


@approval_queue_api.get("/stats", response=ApprovalQueueStatsSchema)
def approval_queue_stats(
    request,
    high_value_threshold: Optional[Decimal] = Query(DEFAULT_HIGH_VALUE_THRESHOLD),
    sla_target_hours: Optional[int] = Query(DEFAULT_SLA_TARGET_HOURS),
):
    """Summary statistics for the approval queue (pending count, high value, oldest waiting, SLA)."""
    now = timezone.now()

    pending_items = []
    pending_items += _quote_items("pending")
    pending_items += _deliverable_items("pending")
    pending_items += _expense_items("pending")

    pending_count = len(pending_items)

    threshold = high_value_threshold or DEFAULT_HIGH_VALUE_THRESHOLD
    high_value_count = len(
        [
            it
            for it in pending_items
            if it["amount"] is not None and it["amount"] > threshold
        ]
    )

    oldest_waiting_days = 0
    if pending_items:
        oldest = min(it["created_at"] for it in pending_items)
        oldest_waiting_days = max((now - oldest).days, 0)

    window_start = now - timedelta(days=DEFAULT_SLA_WINDOW_DAYS)
    resolved = _resolved_records(window_start)
    total_resolved = len(resolved)
    target_seconds = (sla_target_hours or DEFAULT_SLA_TARGET_HOURS) * 3600
    within_target = sum(
        1
        for created_at, resolved_at in resolved
        if resolved_at and (resolved_at - created_at).total_seconds() <= target_seconds
    )

    if total_resolved > 0:
        sla_percent = (
            Decimal(within_target) / Decimal(total_resolved) * Decimal("100")
        ).quantize(Decimal("0.01"))
    else:
        sla_percent = Decimal("100.00")

    return {
        "pending_count": pending_count,
        "high_value_count": high_value_count,
        "oldest_waiting_days": oldest_waiting_days,
        "sla_percent": sla_percent,
    }


@approval_queue_api.get("/", response=ApprovalQueueResponseSchema)
def list_approval_queue(
    request,
    status: Optional[str] = Query("pending"),
    source: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    high_value: Optional[bool] = Query(None),
    high_value_threshold: Optional[Decimal] = Query(DEFAULT_HIGH_VALUE_THRESHOLD),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List approvals across quotations, deliverables and expenses. Defaults to pending."""
    if status not in STATUS_LABELS:
        status = "pending"

    items = []
    if source is None or source == "quotation":
        items += _quote_items(status)
    if source is None or source == "deliverable":
        items += _deliverable_items(status)
    if source is None or source == "expense":
        items += _expense_items(status)

    if high_value:
        threshold = high_value_threshold or DEFAULT_HIGH_VALUE_THRESHOLD
        items = [
            it for it in items if it["amount"] is not None and it["amount"] > threshold
        ]

    items = _apply_search(items, search)
    items.sort(key=lambda it: it["created_at"], reverse=True)

    total = len(items)
    page = items[offset : offset + limit]
    return {"count": total, "results": page}
