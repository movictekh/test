from datetime import date
from decimal import Decimal
from typing import List, Optional

from django.conf import settings
from django.core.exceptions import ValidationError
from system.messaging.email.services import send_text_email as send_mail
from django.db.models import F, Max, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Query, Router
from ninja.pagination import LimitOffsetPagination, paginate

from finance.api.schemas import (
    ReceivableOut,
    ReceivableReminderIn,
    ReceivableReminderOut,
    ReceivableSummaryOut,
)
from shared.api.schema import MessageSchema
from domains.service_operations.models import Invoice
from services.models.service import ServiceRequestActivity
from system.authorization import require_permission

router = Router(tags=["Finance Receivables"])

RECEIVABLE_REMINDER_MARKER = "Receivables reminder"


def _invoice_queryset():
    return Invoice.objects.select_related(
        "client",
        "client__user",
        "service",
        "service_request",
        "service_request__branch",
        "order",
        "order__branch",
    ).annotate(
        last_receivable_reminder_at=Max(
            "service_request__activities__created_at",
            filter=Q(
                service_request__activities__activity_type="email",
                service_request__activities__note__icontains=RECEIVABLE_REMINDER_MARKER,
            ),
        )
    )


def _apply_branch_scope(request, invoices):
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if getattr(request, "_perm_scope", "branches") == "company" or not branch_ids:
        return invoices
    return invoices.filter(
        Q(service_request__branch_id__in=branch_ids)
        | Q(order__branch_id__in=branch_ids)
    )


def _receivable_queryset(request):
    return (
        _apply_branch_scope(request, _invoice_queryset())
        .exclude(status__in=["draft", "cancelled"])
        .filter(total_amount__gt=F("amount_paid"))
    )


def _age_days(invoice, today=None):
    today = today or timezone.localdate()
    return max(0, (today - invoice.due_date).days)


def _ageing_bucket(age_days):
    if age_days <= 0:
        return "current"
    if age_days <= 30:
        return "1_30"
    if age_days <= 60:
        return "31_60"
    if age_days <= 90:
        return "61_90"
    return "90_plus"


def _decorate_receivable(invoice, today=None):
    age_days = _age_days(invoice, today=today)
    invoice.receivable_age_days = age_days
    invoice.receivable_ageing_bucket = _ageing_bucket(age_days)
    invoice.receivable_display_status = "overdue" if age_days > 0 else invoice.status
    return invoice


def _apply_filters(
    request,
    branch_id: Optional[int] = None,
    client_id: Optional[int] = None,
    service_id: Optional[int] = None,
    ageing_bucket: Optional[str] = None,
    due_from: Optional[date] = None,
    due_to: Optional[date] = None,
    search: Optional[str] = None,
):
    receivables = _receivable_queryset(request)
    if branch_id:
        receivables = receivables.filter(
            Q(service_request__branch_id=branch_id) | Q(order__branch_id=branch_id)
        )
    if client_id:
        receivables = receivables.filter(client_id=client_id)
    if service_id:
        receivables = receivables.filter(service_id=service_id)
    if due_from:
        receivables = receivables.filter(due_date__gte=due_from)
    if due_to:
        receivables = receivables.filter(due_date__lte=due_to)
    if search:
        q = search.strip()
        receivables = receivables.filter(
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

    today = timezone.localdate()
    decorated = [
        _decorate_receivable(invoice, today=today) for invoice in receivables.distinct()
    ]
    if ageing_bucket:
        decorated = [
            invoice
            for invoice in decorated
            if invoice.receivable_ageing_bucket == ageing_bucket
        ]
    return decorated


def _client_email(invoice):
    if invoice.service_request and invoice.service_request.contact_email:
        return invoice.service_request.contact_email
    return invoice.client.user.email


def _portal_invoice_url(invoice):
    base_url = getattr(settings, "FRONTEND_PRODUCTION_DOMAIN", "").strip().split()
    if not base_url:
        return ""
    url = base_url[0]
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    return f"{url.rstrip('/')}/service-requests/invoices/{invoice.id}"


@router.get("/receivables", response=List[ReceivableOut])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("service_invoices", "list")
def list_receivables(
    request,
    branch_id: Optional[int] = Query(None),
    client_id: Optional[int] = Query(None),
    service_id: Optional[int] = Query(None),
    ageing_bucket: Optional[str] = Query(None),
    due_from: Optional[date] = Query(None),
    due_to: Optional[date] = Query(None),
    search: Optional[str] = Query(None),
):
    receivables = _apply_filters(
        request,
        branch_id=branch_id,
        client_id=client_id,
        service_id=service_id,
        ageing_bucket=ageing_bucket,
        due_from=due_from,
        due_to=due_to,
        search=search,
    )
    return sorted(
        receivables, key=lambda invoice: (invoice.due_date, invoice.invoice_number)
    )


@router.get("/receivables/summary", response=ReceivableSummaryOut)
@require_permission("service_invoices", "list")
def receivables_summary(
    request,
    branch_id: Optional[int] = Query(None),
    client_id: Optional[int] = Query(None),
    service_id: Optional[int] = Query(None),
    ageing_bucket: Optional[str] = Query(None),
    due_from: Optional[date] = Query(None),
    due_to: Optional[date] = Query(None),
    search: Optional[str] = Query(None),
):
    receivables = _apply_filters(
        request,
        branch_id=branch_id,
        client_id=client_id,
        service_id=service_id,
        ageing_bucket=ageing_bucket,
        due_from=due_from,
        due_to=due_to,
        search=search,
    )
    buckets = {
        "current": Decimal("0.00"),
        "1_30": Decimal("0.00"),
        "31_60": Decimal("0.00"),
        "61_90": Decimal("0.00"),
        "90_plus": Decimal("0.00"),
    }
    bucket_counts = {key: 0 for key in buckets}
    total_invoiced = Decimal("0.00")
    total_paid = Decimal("0.00")

    for invoice in receivables:
        bucket = invoice.receivable_ageing_bucket
        balance = invoice.balance
        buckets[bucket] += balance
        bucket_counts[bucket] += 1
        total_invoiced += invoice.total_amount
        total_paid += invoice.amount_paid

    total_receivables = sum(buckets.values(), Decimal("0.00"))
    overdue_total = (
        buckets["1_30"] + buckets["31_60"] + buckets["61_90"] + buckets["90_plus"]
    )
    collection_rate = Decimal("0.00")
    if total_invoiced > 0:
        collection_rate = (total_paid / total_invoiced * Decimal("100")).quantize(
            Decimal("0.01")
        )

    return {
        "total_receivables": total_receivables,
        "current": buckets["current"],
        "bucket_1_30": buckets["1_30"],
        "bucket_31_60": buckets["31_60"],
        "bucket_61_90": buckets["61_90"],
        "bucket_90_plus": buckets["90_plus"],
        "overdue_total": overdue_total,
        "overdue_count": bucket_counts["1_30"]
        + bucket_counts["31_60"]
        + bucket_counts["61_90"]
        + bucket_counts["90_plus"],
        "receivable_count": len(receivables),
        "collection_rate": collection_rate,
        "bucket_counts": bucket_counts,
    }


@router.post(
    "/receivables/{invoice_id}/send-reminder",
    response={200: ReceivableReminderOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("service_invoices", "update")
def send_receivable_reminder(request, invoice_id: int, payload: ReceivableReminderIn):
    try:
        invoice = get_object_or_404(_receivable_queryset(request), id=invoice_id)
        recipient = _client_email(invoice)
        if not recipient:
            return 400, {"detail": "Client email is not available."}

        portal_url = _portal_invoice_url(invoice)
        client_name = (
            invoice.client.user.get_full_name()
            or invoice.client.company_name
            or invoice.client.user.email
        )
        body = (
            f"Hello {client_name},\n\n"
            f"This is a reminder that invoice {invoice.invoice_number} for {invoice.service.name} has an unpaid balance.\n\n"
            f"Total: {invoice.total_amount}\n"
            f"Amount paid: {invoice.amount_paid}\n"
            f"Outstanding balance: {invoice.balance}\n"
            f"Due date: {invoice.due_date}\n"
        )
        if payload.message:
            body += f"\nMessage from Bomach Finance:\n{payload.message}\n"
        if invoice.payment_instructions:
            body += f"\nPayment instructions:\n{invoice.payment_instructions}\n"
        if portal_url:
            body += f"\nView invoice: {portal_url}\n"
        body += "\nBomach Group"

        send_mail(
            subject=f"Payment reminder for invoice {invoice.invoice_number}",
            message=body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[recipient],
            fail_silently=False,
        )
        activity = None
        if invoice.service_request:
            activity = ServiceRequestActivity.objects.create(
                request=invoice.service_request,
                activity_type="email",
                outcome="successful",
                note=(
                    f"{RECEIVABLE_REMINDER_MARKER}: sent to {recipient} for invoice "
                    f"{invoice.invoice_number} with outstanding balance {invoice.balance}."
                ),
                next_action="Await payment",
                created_by=request.user,
            )
        return 200, {
            "detail": "Reminder sent successfully.",
            "invoice_id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "recipient": recipient,
            "sent": True,
            "activity_id": activity.id if activity else None,
        }
    except ValidationError as exc:
        return 400, {"detail": str(exc)}
    except Exception as exc:
        return 400, {"detail": f"Reminder could not be sent: {exc}"}
