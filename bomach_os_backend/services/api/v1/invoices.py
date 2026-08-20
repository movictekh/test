from typing import List, Optional

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import IntegrityError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from ninja import Query, Router
from ninja.errors import HttpError
from ninja.pagination import LimitOffsetPagination, paginate

from services.api.schema.others import MessageSchema
from services.api.schema.schemas import InvoiceIn, InvoiceOut, InvoiceSendIn, InvoiceUpdate, ServiceOrderFromInvoiceIn, ServiceOrderOut
from services.models.payment import Invoice, InvoiceItem
from services.models.service import ServiceRequestActivity
from services.utils.service_orders import create_order_from_invoice
from user.api.schemas.client_service import PaymentSubmissionResponseSchema, ReviewPaymentSchema
from user.models.client_service import PaymentSubmission
from user.utils.perm import require_permission, scope_queryset
from finance.service import handle_payment_exception, review_payment_submission as review_submission_payment


router = Router(tags=["Invoices"])

EDITABLE_STATUSES = {"draft", "sent"}
ACTIVE_INVOICE_STATUSES = {"draft", "sent", "viewed", "partially_paid", "paid", "overdue"}


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


def _log_request_activity(service_request, activity_type, note, created_by=None, next_action=""):
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


def _send_invoice_email(invoice):
    recipient = _client_email(invoice)
    if not recipient:
        raise ValidationError("Client email is not available.")

    portal_url = _portal_invoice_url(invoice)
    body = (
        f"Hello {invoice.client.user.get_full_name() or invoice.client.user.email},\n\n"
        f"Invoice {invoice.invoice_number} for {invoice.service.name} has been issued.\n\n"
        f"Total: {invoice.total_amount}\n"
        f"Amount paid: {invoice.amount_paid}\n"
        f"Balance: {invoice.balance}\n"
        f"Due date: {invoice.due_date}\n"
    )
    if invoice.activation_threshold_amount:
        body += f"Required mobilisation/payment threshold: {invoice.activation_threshold_amount}\n"
    if invoice.payment_instructions:
        body += f"\nPayment instructions:\n{invoice.payment_instructions}\n"
    if portal_url:
        body += f"\nView and pay this invoice here: {portal_url}\n"
    body += "\nBomach Group"

    send_mail(
        subject=f"Invoice {invoice.invoice_number} from Bomach Group",
        message=body,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        recipient_list=[recipient],
        fail_silently=False,
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
    invoices = scope_queryset(request, _invoice_queryset(), branch_field="service_request__branch_id")
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
        data = payload.dict()
        items_data = data.pop("items", [])
        data["created_by"] = request.user
        data.pop("created_by_id", None)
        invoice = Invoice.objects.create(**data)
        _create_invoice_items(invoice, items_data)
        return 201, _invoice_queryset().get(id=invoice.id)
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
    submissions = scope_queryset(request, submissions, branch_field="invoice__service_request__branch_id")
    if status:
        submissions = submissions.filter(status=status)
    if invoice_id:
        submissions = submissions.filter(invoice_id=invoice_id)
    return submissions.order_by("-created_at")


@router.post("/payment-submissions/{submission_id}/review", response={200: PaymentSubmissionResponseSchema, 400: MessageSchema, 404: MessageSchema})
@require_permission("payments", "create")
def review_payment_submission(request, submission_id: int, payload: ReviewPaymentSchema):
    try:
        submission = get_object_or_404(
            PaymentSubmission.objects.select_related("invoice", "invoice__service_request"),
            id=submission_id,
        )
        reviewed = review_submission_payment(
            submission,
            reviewed_by=request.user,
            status=payload.status,
            finance_account_id=payload.finance_account_id,
            rejection_reason=payload.rejection_reason,
        )
        return 200, PaymentSubmission.objects.select_related("invoice").get(id=reviewed.id)
    except Exception as e:
        return 400, handle_payment_exception(e)


@router.post("/{invoice_id}/send", response={200: InvoiceOut, 400: MessageSchema, 404: MessageSchema})
@require_permission("service_invoices", "update")
def send_invoice(request, invoice_id: int, payload: InvoiceSendIn):
    try:
        invoice = get_object_or_404(_invoice_queryset(), id=invoice_id)
        if invoice.status not in {"draft", "sent"}:
            return 400, {"detail": "Only draft or sent invoices can be sent."}
        if payload and payload.payment_instructions is not None:
            invoice.payment_instructions = payload.payment_instructions
        invoice.status = "sent"
        invoice.save(update_fields=["payment_instructions", "status", "updated_at"])
        _log_request_activity(
            invoice.service_request,
            "invoice_issued",
            f"Invoice {invoice.invoice_number} issued for {invoice.total_amount}.",
            created_by=request.user,
            next_action="Await payment",
        )
        try:
            _send_invoice_email(invoice)
        except Exception as exc:
            _log_request_activity(
                invoice.service_request,
                "internal_note",
                f"Invoice email delivery failed for {invoice.invoice_number}: {exc}",
                created_by=request.user,
                next_action="Follow up with client manually",
            )
        return 200, _invoice_queryset().get(id=invoice.id)
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


@router.post("/{invoice_id}/cancel", response={200: InvoiceOut, 400: MessageSchema, 404: MessageSchema})
@require_permission("service_invoices", "update")
def cancel_invoice(request, invoice_id: int):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    if invoice.amount_paid > 0:
        return 400, {"detail": "Invoices with confirmed payments cannot be cancelled."}
    if invoice.status == "cancelled":
        return 400, {"detail": "Invoice is already cancelled."}
    invoice.status = "cancelled"
    invoice.save(update_fields=["status", "updated_at"])
    return 200, _invoice_queryset().get(id=invoice.id)


@router.post("/{invoice_id}/service-order", response={201: ServiceOrderOut, 400: MessageSchema, 404: MessageSchema})
@require_permission("orders", "create")
def create_service_order_from_invoice(request, invoice_id: int, payload: ServiceOrderFromInvoiceIn):
    try:
        invoice = get_object_or_404(
            _invoice_queryset(),
            id=invoice_id,
        )
        branch_ids = getattr(request, "_perm_branch_ids", [])
        if branch_ids:
            branch_id = invoice.service_request.branch_id if invoice.service_request_id else None
            if branch_id not in branch_ids:
                raise HttpError(403, "You do not have permission to create an order for this invoice.")
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


@router.patch("/{invoice_id}", response={200: InvoiceOut, 400: MessageSchema, 404: MessageSchema})
@require_permission("service_invoices", "update")
def update_invoice(request, invoice_id: int, payload: InvoiceUpdate):
    try:
        invoice = get_object_or_404(Invoice, id=invoice_id)
        if invoice.status not in EDITABLE_STATUSES:
            return 400, {"detail": "Only draft or sent invoices can be edited."}
        for attr, value in payload.dict(exclude_unset=True).items():
            setattr(invoice, attr, value)
        invoice.save()
        return 200, _invoice_queryset().get(id=invoice.id)
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


@router.put("/{invoice_id}", response={200: InvoiceOut, 400: MessageSchema, 404: MessageSchema})
@require_permission("service_invoices", "update")
def replace_invoice(request, invoice_id: int, payload: InvoiceUpdate):
    return update_invoice(request, invoice_id, payload)


@router.delete("/{invoice_id}", response={200: MessageSchema, 400: MessageSchema, 404: MessageSchema})
@require_permission("service_invoices", "delete")
def delete_invoice(request, invoice_id: int):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    if invoice.payments.exists():
        return 400, {"detail": "Invoices with recorded payments cannot be deleted; preserve the payment and accounting audit trail."}
    if invoice.quote_id or invoice.service_request_id:
        return 400, {"detail": "Commercial flow invoices cannot be deleted. Cancel them instead."}
    invoice.delete()
    return 200, {"detail": "Invoice deleted successfully"}
