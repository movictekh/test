from datetime import date
from decimal import Decimal
from typing import List, Optional

from django.db.models import Q
from django.utils import timezone
from ninja import Query, Router
from ninja.pagination import LimitOffsetPagination, paginate

from finance.api.schemas import (
    FinanceInvoiceOut,
    FinanceInvoiceSummaryOut,
    finance_invoice_status,
)
from services.models.payment import Invoice
from user.utils.perm import require_permission

router = Router(tags=["Finance Invoices"])


def _invoice_queryset():
    return Invoice.objects.select_related(
        "client",
        "client__user",
        "service",
        "quote",
        "service_request",
        "service_request__branch",
        "order",
        "order__branch",
        "created_by",
    )


def _apply_branch_scope(request, invoices):
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if getattr(request, "_perm_scope", "branches") == "company" or not branch_ids:
        return invoices
    return invoices.filter(
        Q(service_request__branch_id__in=branch_ids)
        | Q(order__branch_id__in=branch_ids)
    )


def _apply_filters(
    request,
    status: Optional[str] = None,
    branch_id: Optional[int] = None,
    client_id: Optional[int] = None,
    service_id: Optional[int] = None,
    order_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    due_from: Optional[date] = None,
    due_to: Optional[date] = None,
    overdue_only: bool = False,
    search: Optional[str] = None,
):
    invoices = _apply_branch_scope(request, _invoice_queryset())

    if status:
        normalized_status = status.strip().lower()
        if normalized_status == "overdue":
            today = timezone.localdate()
            invoices = invoices.filter(due_date__lt=today).exclude(
                status__in=["paid", "cancelled"]
            )
        else:
            invoices = invoices.filter(status=normalized_status)
    if branch_id:
        invoices = invoices.filter(
            Q(service_request__branch_id=branch_id) | Q(order__branch_id=branch_id)
        )
    if client_id:
        invoices = invoices.filter(client_id=client_id)
    if service_id:
        invoices = invoices.filter(service_id=service_id)
    if order_id:
        invoices = invoices.filter(order_id=order_id)
    if date_from:
        invoices = invoices.filter(issue_date__gte=date_from)
    if date_to:
        invoices = invoices.filter(issue_date__lte=date_to)
    if due_from:
        invoices = invoices.filter(due_date__gte=due_from)
    if due_to:
        invoices = invoices.filter(due_date__lte=due_to)
    if overdue_only:
        today = timezone.localdate()
        invoices = invoices.filter(due_date__lt=today).exclude(
            status__in=["paid", "cancelled"]
        )
    if search:
        q = search.strip()
        invoices = invoices.filter(
            Q(invoice_number__icontains=q)
            | Q(client__company_name__icontains=q)
            | Q(client__user__first_name__icontains=q)
            | Q(client__user__last_name__icontains=q)
            | Q(client__user__email__icontains=q)
            | Q(service__name__icontains=q)
            | Q(service_request__request_number__icontains=q)
            | Q(service_request__contact_name__icontains=q)
            | Q(service_request__contact_email__icontains=q)
            | Q(order__order_number__icontains=q)
        )

    return invoices.distinct()


@router.get("/invoices", response=List[FinanceInvoiceOut])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("service_invoices", "list")
def list_finance_invoices(
    request,
    status: Optional[str] = Query(None),
    branch_id: Optional[int] = Query(None),
    client_id: Optional[int] = Query(None),
    service_id: Optional[int] = Query(None),
    order_id: Optional[int] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    due_from: Optional[date] = Query(None),
    due_to: Optional[date] = Query(None),
    overdue_only: bool = Query(False),
    search: Optional[str] = Query(None),
):
    return _apply_filters(
        request,
        status=status,
        branch_id=branch_id,
        client_id=client_id,
        service_id=service_id,
        order_id=order_id,
        date_from=date_from,
        date_to=date_to,
        due_from=due_from,
        due_to=due_to,
        overdue_only=overdue_only,
        search=search,
    ).order_by("-issue_date", "-created_at")


@router.get("/invoices/summary", response=FinanceInvoiceSummaryOut)
@require_permission("service_invoices", "list")
def finance_invoice_summary(
    request,
    status: Optional[str] = Query(None),
    branch_id: Optional[int] = Query(None),
    client_id: Optional[int] = Query(None),
    service_id: Optional[int] = Query(None),
    order_id: Optional[int] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    due_from: Optional[date] = Query(None),
    due_to: Optional[date] = Query(None),
    overdue_only: bool = Query(False),
    search: Optional[str] = Query(None),
):
    invoices = _apply_filters(
        request,
        status=status,
        branch_id=branch_id,
        client_id=client_id,
        service_id=service_id,
        order_id=order_id,
        date_from=date_from,
        date_to=date_to,
        due_from=due_from,
        due_to=due_to,
        overdue_only=overdue_only,
        search=search,
    )

    total_invoiced = Decimal("0.00")
    total_paid = Decimal("0.00")
    outstanding_balance = Decimal("0.00")
    current_balance = Decimal("0.00")
    overdue_balance = Decimal("0.00")
    overdue_count = 0
    status_counts = {}

    for invoice in invoices:
        balance = invoice.balance
        display_status = finance_invoice_status(invoice)
        total_invoiced += invoice.total_amount
        total_paid += invoice.amount_paid
        outstanding_balance += balance
        status_counts[display_status] = status_counts.get(display_status, 0) + 1
        if display_status == "overdue":
            overdue_count += 1
            overdue_balance += balance
        elif invoice.status != "cancelled":
            current_balance += balance

    return {
        "total_invoiced": total_invoiced,
        "total_paid": total_paid,
        "outstanding_balance": outstanding_balance,
        "current_balance": current_balance,
        "overdue_balance": overdue_balance,
        "overdue_count": overdue_count,
        "invoice_count": invoices.count(),
        "status_counts": status_counts,
    }
