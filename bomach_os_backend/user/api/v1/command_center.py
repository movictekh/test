from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count, F, Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from ninja import Router

from user.api.schemas.command_center import (
    ActionItem,
    ActivityFeedItem,
    ApprovalDomainSummary,
    FinancialSummary,
    PendingApprovalsSummary,
    PipelineStage,
    PipelineSummary,
)
from system.authorization import require_permission

command_center_router = Router(tags=["Command Center"])


def _days_since(dt):
    if dt is None:
        return 0
    delta = timezone.now() - dt
    return max(0, delta.days)


@command_center_router.get("/activity", response=list[ActivityFeedItem])
@require_permission("command_center", "view")
def get_activity_feed(request):
    """Recent activity across orders, approvals, invoices."""
    from services.models.payment import Invoice
    from services.models.service import Quote, ServiceOrder
    from system.approvals.models.approval import ApprovalRequest

    items = []

    # Recent orders
    for order in ServiceOrder.objects.order_by("-created_at")[:10]:
        items.append(
            ActivityFeedItem(
                id=order.id,
                type="order",
                title=f"Order {order.order_number}",
                description=f"Status: {order.get_order_status_display()}",
                timestamp=order.created_at,
                link=f"/orders/{order.id}",
            )
        )

    # Recent approval requests
    for req in ApprovalRequest.objects.order_by("-created_at")[:10]:
        items.append(
            ActivityFeedItem(
                id=req.id,
                type="approval",
                title=req.title,
                description=f"Status: {req.get_status_display()}",
                timestamp=req.created_at,
                link=f"/approvals/requests/{req.id}",
            )
        )

    # Recent invoices
    for inv in Invoice.objects.order_by("-created_at")[:10]:
        items.append(
            ActivityFeedItem(
                id=inv.id,
                type="invoice",
                title=f"Invoice {inv.invoice_number}",
                description=f"Amount: {inv.total_amount} ({inv.get_status_display()})",
                timestamp=inv.created_at,
                link=f"/invoices/{inv.id}",
            )
        )

    # Sort by timestamp descending, take top 20
    items.sort(key=lambda x: x.timestamp, reverse=True)
    return items[:20]


@command_center_router.get("/pending-approvals", response=PendingApprovalsSummary)
@require_permission("command_center", "view")
def get_pending_approvals(request):
    """Summary of pending approvals across domains."""
    from hr.models.leave_request import LeaveRequest
    from services.models.expenses import Expense
    from services.models.service import Quote, ServiceOrder

    items = []

    # Pending expenses
    expense_count = Expense.objects.filter(status="pending").count()
    if expense_count:
        oldest = Expense.objects.filter(status="pending").order_by("created_at").first()
        items.append(
            ApprovalDomainSummary(
                domain="expenses",
                count=expense_count,
                oldest_days=_days_since(oldest.created_at),
            )
        )

    # Pending leave requests
    leave_count = LeaveRequest.objects.filter(status="pending").count()
    if leave_count:
        oldest = (
            LeaveRequest.objects.filter(status="pending").order_by("created_at").first()
        )
        items.append(
            ApprovalDomainSummary(
                domain="leave_requests",
                count=leave_count,
                oldest_days=_days_since(oldest.created_at),
            )
        )

    # Quotes awaiting approval
    quote_count = Quote.objects.filter(status="awaiting_approval").count()
    if quote_count:
        oldest = (
            Quote.objects.filter(status="awaiting_approval")
            .order_by("created_at")
            .first()
        )
        items.append(
            ApprovalDomainSummary(
                domain="quotes",
                count=quote_count,
                oldest_days=_days_since(oldest.created_at),
            )
        )

    # Orders pending
    order_count = ServiceOrder.objects.filter(order_status="pending").count()
    if order_count:
        oldest = (
            ServiceOrder.objects.filter(order_status="pending")
            .order_by("created_at")
            .first()
        )
        items.append(
            ApprovalDomainSummary(
                domain="orders",
                count=order_count,
                oldest_days=_days_since(oldest.created_at),
            )
        )

    total = sum(i.count for i in items)
    return PendingApprovalsSummary(items=items, total_pending=total)


@command_center_router.get("/financials", response=FinancialSummary)
@require_permission("command_center", "view")
def get_financials(request):
    """Revenue, expenses, outstanding, and margin."""
    from services.models.expenses import Expense
    from services.models.payment import Invoice

    revenue = Invoice.objects.filter(
        status__in=["paid", "partially_paid"],
    ).aggregate(
        total=Coalesce(Sum("amount_paid"), Decimal("0"))
    )["total"]

    expenses = Expense.objects.filter(
        status="approved",
    ).aggregate(
        total=Coalesce(Sum("amount"), Decimal("0"))
    )["total"]

    outstanding = Invoice.objects.filter(
        status__in=["sent", "viewed", "overdue"],
    ).aggregate(
        total=Coalesce(
            Sum(F("total_amount") - F("amount_paid")),
            Decimal("0"),
        )
    )[
        "total"
    ]

    margin_pct = 0.0
    if revenue > 0:
        margin_pct = round(float((revenue - expenses) / revenue * 100), 2)

    return FinancialSummary(
        revenue=revenue,
        expenses=expenses,
        outstanding=outstanding,
        margin_pct=margin_pct,
    )


@command_center_router.get("/pipeline", response=PipelineSummary)
@require_permission("command_center", "view")
def get_pipeline(request):
    """Service pipeline status counts and conversion rate."""
    from services.models.service import Quote, ServiceOrder

    status_map = {
        "pending": "Pending",
        "accepted": "Accepted",
        "in_progress": "In Progress",
        "completed": "Completed",
        "cancelled": "Cancelled",
    }

    stages = []
    for status, label in status_map.items():
        count = ServiceOrder.objects.filter(order_status=status).count()
        value = ServiceOrder.objects.filter(
            order_status=status,
        ).aggregate(
            total=Coalesce(Sum("amount"), Decimal("0"))
        )["total"]
        stages.append(PipelineStage(name=label, count=count, value=value))

    total_quotes = Quote.objects.count()
    converted = Quote.objects.filter(orders__isnull=False).distinct().count()
    conversion_rate = (
        round((converted / total_quotes * 100), 2) if total_quotes else 0.0
    )

    return PipelineSummary(stages=stages, conversion_rate=conversion_rate)


@command_center_router.get("/action-items", response=list[ActionItem])
@require_permission("command_center", "view")
def get_action_items(request):
    """Pending items requiring user's attention."""
    from services.models.service import ServiceOrder
    from system.approvals.models.approval import ApprovalRequest

    items = []

    # My pending approval requests
    for req in ApprovalRequest.objects.filter(
        status="pending",
    ).order_by(
        "-created_at"
    )[:10]:
        items.append(
            ActionItem(
                id=req.id,
                type="approval",
                title=req.title,
                description=req.description or "",
                link=f"/approvals/requests/{req.id}",
                priority="high",
            )
        )

    # Active orders assigned to me
    if hasattr(request.user, "employee_profile"):
        emp = request.user.employee_profile
        for order in ServiceOrder.objects.filter(
            assigned_to=emp,
            order_status="in_progress",
        ).order_by("-created_at")[:10]:
            items.append(
                ActionItem(
                    id=order.id,
                    type="order",
                    title=f"Order {order.order_number}",
                    description=order.description[:100],
                    due_date=getattr(order, "due_date", None),
                    link=f"/orders/{order.id}",
                    priority="normal",
                )
            )

    return items
