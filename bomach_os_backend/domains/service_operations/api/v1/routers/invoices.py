from typing import List, Optional

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from ninja import Query, Router
from ninja.errors import HttpError
from ninja.pagination import LimitOffsetPagination, paginate

from domains.service_operations.models import (
    Invoice,
    InvoiceItem,
    ServiceRequestActivity,
)
from domains.service_operations.services import invoices as invoice_services
from domains.service_operations.services.orders import create_order_from_invoice
from finance.services import (
    handle_payment_exception,
)
from finance.services import review_payment_submission as review_submission_payment
from shared.api.schema.others import MessageSchema
from user.api.schemas.client_service import (
    PaymentSubmissionResponseSchema,
    ReviewPaymentSchema,
)
from finance.transactions.payment_submission import PaymentSubmission
from system.authorization import require_permission, scope_queryset

from ..schemas.lifecycle import (
    InvoiceIn,
    InvoiceOut,
    InvoiceSendIn,
    InvoiceUpdate,
    ServiceOrderFromInvoiceIn,
    ServiceOrderOut,
)

router = Router(tags=["Invoices"])

EDITABLE_STATUSES = {"draft", "sent"}
ACTIVE_INVOICE_STATUSES = {
    "draft",
    "sent",
    "viewed",
    "partially_paid",
    "paid",
    "overdue",
}


def _validation_detail(exc):
    if hasattr(exc, "message_dict"):
        return "; ".join(
            f"{field}: {', '.join(messages)}"
            for field, messages in exc.message_dict.items()
        )
    return exc.messages[0] if getattr(exc, "messages", None) else str(exc)


def _invoice_queryset():
    return Invoice.objects.select_related(
        "client",
        "client__user",
        "service",
        "service__category",
        "quote",
        "service_request",
        "service_request__branch",
        "order",
        "lead",
        "created_by",
    ).prefetch_related("items", "payments", "submissions")


def _log_request_activity(
    service_request, activity_type, note, created_by=None, next_action=""
):
    if not service_request:
        return
    ServiceRequestActivity.objects.create(
        request=service_request,
        activity_type=activity_type,
        outcome="not_applicable",
        note=note,
        next_action=next_action,
        created_by=created_by,
    )


def _create_invoice_items(invoice, items_data):
    for item_data in items_data:
        InvoiceItem.objects.create(invoice=invoice, **item_data)


@router.get("", response=List[InvoiceOut])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("service_invoices", "list")
def list_invoices(
    request,
    status: Optional[str] = Query(None),
    client_id: Optional[int] = Query(None),
    quote_id: Optional[int] = Query(None),
    service_request_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
):
    invoices = scope_queryset(
        request, _invoice_queryset(), branch_field="service_request__branch_id"
    )
    if status:
        invoices = invoices.filter(status=status)
    if client_id:
        invoices = invoices.filter(client_id=client_id)
    if quote_id:
        invoices = invoices.filter(quote_id=quote_id)
    if service_request_id:
        invoices = invoices.filter(service_request_id=service_request_id)
    if search:
        invoices = invoices.filter(Q(invoice_number__icontains=search))
    return invoices.order_by("-created_at")


@router.post("", response={201: InvoiceOut, 400: MessageSchema})
@require_permission("service_invoices", "create")
def create_invoice(request, payload: InvoiceIn):
    try:
        i = invoice_services.create_invoice(payload, user=request.user)
        return 201, _invoice_queryset().get(id=i.id)
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get("/payment-submissions", response=List[PaymentSubmissionResponseSchema])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("payments", "list")
def list_payment_submissions(
    request,
    status: Optional[str] = Query(PaymentSubmission.STATUS.PENDING),
    invoice_id: Optional[int] = Query(None),
):
    submissions = PaymentSubmission.objects.select_related(
        "invoice",
        "invoice__service_request",
        "invoice__service_request__branch",
    )
    submissions = scope_queryset(
        request, submissions, branch_field="invoice__service_request__branch_id"
    )
    if status:
        submissions = submissions.filter(status=status)
    if invoice_id:
        submissions = submissions.filter(invoice_id=invoice_id)
    return submissions.order_by("-created_at")


@router.post(
    "/payment-submissions/{submission_id}/review",
    response={
        200: PaymentSubmissionResponseSchema,
        400: MessageSchema,
        404: MessageSchema,
    },
)
@require_permission("payments", "create")
def review_payment_submission(
    request, submission_id: int, payload: ReviewPaymentSchema
):
    try:
        submission = get_object_or_404(
            PaymentSubmission.objects.select_related(
                "invoice", "invoice__service_request"
            ),
            id=submission_id,
        )
        reviewed = review_submission_payment(
            submission,
            reviewed_by=request.user,
            status=payload.status,
            finance_account_id=payload.finance_account_id,
            rejection_reason=payload.rejection_reason,
        )
        return 200, PaymentSubmission.objects.select_related("invoice").get(
            id=reviewed.id
        )
    except Exception as e:
        return 400, handle_payment_exception(e)


@router.post(
    "/{invoice_id}/send",
    response={200: InvoiceOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("service_invoices", "update")
def send_invoice(request, invoice_id: int, payload: InvoiceSendIn):
    try:
        i = get_object_or_404(_invoice_queryset(), id=invoice_id)
        invoice_services.send_invoice(i, payload, user=request.user)
        return 200, _invoice_queryset().get(id=i.id)
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


@router.post(
    "/{invoice_id}/cancel",
    response={200: InvoiceOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("service_invoices", "update")
def cancel_invoice(request, invoice_id: int):
    i = get_object_or_404(Invoice, id=invoice_id)
    try:
        invoice_services.cancel_invoice(i)
        return 200, _invoice_queryset().get(id=i.id)
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}


@router.post(
    "/{invoice_id}/service-order",
    response={201: ServiceOrderOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("orders", "create")
def create_service_order_from_invoice(
    request, invoice_id: int, payload: ServiceOrderFromInvoiceIn
):
    try:
        invoice = get_object_or_404(
            _invoice_queryset(),
            id=invoice_id,
        )
        branch_ids = getattr(request, "_perm_branch_ids", [])
        if branch_ids:
            branch_id = (
                invoice.service_request.branch_id
                if invoice.service_request_id
                else None
            )
            if branch_id not in branch_ids:
                raise HttpError(
                    403,
                    "You do not have permission to create an order for this invoice.",
                )
        order = create_order_from_invoice(
            invoice,
            created_by=request.user,
            assigned_to_id=payload.assigned_to_id,
            due_date=payload.due_date,
            description=payload.description or "",
            stage=payload.stage or "",
            next_action=payload.next_action,
        )
        _log_request_activity(
            invoice.service_request,
            "order_created",
            f"Service order {order.order_number} created from invoice {invoice.invoice_number}.",
            created_by=request.user,
            next_action=f"Track {order.order_number}",
        )
        return 201, order
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


@router.get("/{invoice_id}", response=InvoiceOut)
@require_permission("service_invoices", "view")
def get_invoice(request, invoice_id: int):
    return get_object_or_404(_invoice_queryset(), id=invoice_id)


@router.patch(
    "/{invoice_id}", response={200: InvoiceOut, 400: MessageSchema, 404: MessageSchema}
)
@require_permission("service_invoices", "update")
def update_invoice(request, invoice_id: int, payload: InvoiceUpdate):
    try:
        i = get_object_or_404(Invoice, id=invoice_id)
        invoice_services.update_invoice(i, payload)
        return 200, _invoice_queryset().get(id=i.id)
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


@router.put(
    "/{invoice_id}", response={200: InvoiceOut, 400: MessageSchema, 404: MessageSchema}
)
@require_permission("service_invoices", "update")
def replace_invoice(request, invoice_id: int, payload: InvoiceUpdate):
    return update_invoice(request, invoice_id, payload)


@router.delete(
    "/{invoice_id}",
    response={200: MessageSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("service_invoices", "delete")
def delete_invoice(request, invoice_id: int):
    i = get_object_or_404(Invoice, id=invoice_id)
    try:
        invoice_services.delete_invoice(i)
        return 200, {"detail": "Invoice deleted successfully"}
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
