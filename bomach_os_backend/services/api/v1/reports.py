from datetime import date as date_type
from decimal import Decimal

from django.http import HttpResponse
from django.db.models import (
    Q,
    Count,
    Sum,
    Avg,
    Min,
    F,
    ExpressionWrapper,
    DateTimeField,
    DateField,
    DecimalField,
)
from django.db.models.functions import Coalesce, TruncDate
from ninja import Router

from services.api.schema.report_schemas import (
    KPISchema,
    ServicePerformanceItem,
    BranchPerformanceItem,
)
from services.models.service import (
    Quote,
    ServiceOrder,
    ServiceRequest,
    ServiceRequestActivity,
)
from services.models.payment import Invoice
from services.models.expenses import Expense
from services.models.feedback import ClientFeedback
from user.utils.perm import require_permission

router = Router(tags=["Reports"])


def _date_filters(date_from, date_to):
    """Build common Q objects for date range filtering on ServiceRequest."""
    q = Q()
    if date_from:
        q &= Q(created_at__date__gte=date_from)
    if date_to:
        q &= Q(created_at__date__lte=date_to)
    return q


@router.get("/kpis", response={200: KPISchema})
@require_permission("reports", "view")
def get_kpis(
    request,
    date_from: date_type = None,
    date_to: date_type = None,
):
    """Return the 4 KPI cards: conversion, response time, margin, on-time delivery."""

    # --- Quote-to-order conversion ---
    total_quotes = Quote.objects.count()
    converted_quotes = Quote.objects.filter(orders__isnull=False).distinct().count()
    conversion = (
        (Decimal(converted_quotes) / Decimal(total_quotes) * 100).quantize(
            Decimal("0.01")
        )
        if total_quotes
        else Decimal("0.00")
    )

    # --- Average response time (ServiceRequest → first activity) ---
    sr_filter = _date_filters(date_from, date_to)
    requests_with_activity = (
        ServiceRequest.objects.filter(
            sr_filter,
            activities__isnull=False,
        )
        .annotate(
            first_activity=Coalesce(
                Min("activities__created_at"),
                F("created_at"),
                output_field=DateTimeField(),
            )
        )
        .values_list("id", "created_at", "first_activity")
    )

    # Actually, let's use a simpler approach: for each request, get the
    # earliest activity created_at and compute the delta.
    response_times = []
    srs = ServiceRequest.objects.filter(sr_filter).prefetch_related("activities")
    for sr in srs:
        first_activity = sr.activities.order_by("created_at").first()
        if first_activity:
            delta = first_activity.created_at - sr.created_at
            response_times.append(delta.total_seconds() / 60.0)

    avg_response = sum(response_times) / len(response_times) if response_times else 0.0

    # --- Gross service margin ---
    total_revenue = Invoice.objects.filter(
        status__in=["paid", "partially_paid"],
    ).aggregate(total=Coalesce(Sum("amount_paid"), Decimal("0")))["total"]

    total_expenses = Expense.objects.filter(
        status="approved",
    ).aggregate(
        total=Coalesce(Sum("amount"), Decimal("0"))
    )["total"]

    if total_revenue > 0:
        margin = ((total_revenue - total_expenses) / total_revenue * 100).quantize(
            Decimal("0.01")
        )
    else:
        margin = Decimal("0.00")

    # --- On-time delivery ---
    completed_orders = ServiceOrder.objects.filter(
        completed_at__isnull=False,
    )
    total_completed = completed_orders.count()
    on_time = completed_orders.filter(
        completed_at__lte=F("due_date"),
    ).count()
    on_time_pct = (
        (Decimal(on_time) / Decimal(total_completed) * 100).quantize(Decimal("0.01"))
        if total_completed
        else Decimal("0.00")
    )

    return 200, KPISchema(
        quote_to_order_conversion=conversion,
        average_response_time_minutes=round(avg_response, 1),
        gross_service_margin=margin,
        on_time_delivery=on_time_pct,
    )


@router.get("/service-performance", response={200: list})
@require_permission("reports", "view")
def get_service_performance(
    request,
    date_from: date_type = None,
    date_to: date_type = None,
):
    """Return per-service completion rate and revenue."""
    if date_from or date_to:
        sr_date_q = Q()
        if date_from:
            sr_date_q &= Q(service_request__created_at__date__gte=date_from)
        if date_to:
            sr_date_q &= Q(service_request__created_at__date__lte=date_to)
        order_filter = Q(service_request__isnull=True) | sr_date_q
    else:
        order_filter = Q()

    orders = (
        ServiceOrder.objects.filter(
            order_filter,
        )
        .values("service__name")
        .annotate(
            total=Count("id"),
            completed=Count("id", filter=Q(order_status="completed")),
        )
        .order_by("service__name")
    )

    results = []
    for row in orders:
        name = row["service__name"] or "Unknown"
        total = row["total"]
        completed = row["completed"]
        completion_rate = (
            (Decimal(completed) / Decimal(total) * 100).quantize(Decimal("0.01"))
            if total
            else Decimal("0.00")
        )

        revenue = Invoice.objects.filter(
            order__service__name=row["service__name"],
            status__in=["paid", "partially_paid"],
        ).aggregate(total=Coalesce(Sum("amount_paid"), Decimal("0")))["total"]

        results.append(
            ServicePerformanceItem(
                service_name=name,
                completion_rate=completion_rate,
                revenue=revenue,
            )
        )

    return 200, results


@router.get("/service-performance/export")
@require_permission("reports", "view")
def export_service_performance(
    request,
    date_from: date_type = None,
    date_to: date_type = None,
):
    """Export service performance as CSV."""
    if date_from or date_to:
        sr_date_q = Q()
        if date_from:
            sr_date_q &= Q(service_request__created_at__date__gte=date_from)
        if date_to:
            sr_date_q &= Q(service_request__created_at__date__lte=date_to)
        order_filter = Q(service_request__isnull=True) | sr_date_q
    else:
        order_filter = Q()

    orders = (
        ServiceOrder.objects.filter(
            order_filter,
        )
        .values("service__name")
        .annotate(
            total=Count("id"),
            completed=Count("id", filter=Q(order_status="completed")),
        )
        .order_by("service__name")
    )

    rows = [["Service", "Completion Rate", "Revenue"]]
    for row in orders:
        name = row["service__name"] or "Unknown"
        total = row["total"]
        completed = row["completed"]
        rate = f"{(completed / total * 100):.1f}%" if total else "0.0%"
        revenue = Invoice.objects.filter(
            order__service__name=row["service__name"],
            status__in=["paid", "partially_paid"],
        ).aggregate(total=Coalesce(Sum("amount_paid"), Decimal("0")))["total"]
        rows.append([name, rate, str(revenue)])

    csv_content = "\n".join(",".join(f'"{c}"' for c in row) for row in rows)
    return HttpResponse(
        csv_content,
        content_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="service-performance.csv"'
        },
    )


@router.get("/branch-performance", response={200: list})
@require_permission("reports", "view")
def get_branch_performance(
    request,
    date_from: date_type = None,
    date_to: date_type = None,
):
    """Return per-branch metrics: requests, active orders, revenue, SLA, CSAT."""
    sr_filter = _date_filters(date_from, date_to)

    branches = (
        ServiceRequest.objects.filter(
            sr_filter,
            branch__isnull=False,
        )
        .values(
            "branch__branch_name",
        )
        .annotate(
            request_count=Count("id"),
        )
        .order_by("branch__branch_name")
    )

    results = []
    for row in branches:
        branch_name = row["branch__branch_name"]
        request_count = row["request_count"]

        # Active orders for this branch
        active_orders = ServiceOrder.objects.filter(
            service_request__branch__branch_name=branch_name,
            order_status="active",
        ).count()

        # Revenue for this branch
        revenue = Invoice.objects.filter(
            service_request__branch__branch_name=branch_name,
            status__in=["paid", "partially_paid"],
        ).aggregate(total=Coalesce(Sum("amount_paid"), Decimal("0")))["total"]

        # SLA: % of completed orders delivered on time
        completed = ServiceOrder.objects.filter(
            service_request__branch__branch_name=branch_name,
            completed_at__isnull=False,
        )
        total_completed = completed.count()
        on_time = completed.filter(completed_at__lte=F("due_date")).count()
        sla = (
            (Decimal(on_time) / Decimal(total_completed) * 100).quantize(
                Decimal("0.01")
            )
            if total_completed
            else Decimal("0.00")
        )

        # CSAT: average rating for feedback linked to orders of this branch
        csat_avg = ClientFeedback.objects.filter(
            order__service_request__branch__branch_name=branch_name,
        ).aggregate(
            avg=Coalesce(
                Avg("rating"),
                Decimal("0"),
                output_field=DecimalField(),
            )
        )[
            "avg"
        ]
        if isinstance(csat_avg, float):
            csat_avg = Decimal(str(csat_avg)).quantize(Decimal("0.01"))
        csat = (
            (csat_avg * 20).quantize(Decimal("0.01")) if csat_avg else Decimal("0.00")
        )

        results.append(
            BranchPerformanceItem(
                branch_name=branch_name,
                requests=request_count,
                active_orders=active_orders,
                revenue=revenue,
                sla=sla,
                csat=csat,
            )
        )

    return 200, results
