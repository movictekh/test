"""Client commercial and delivery portal endpoints under Service Requests."""

from typing import List, Optional
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Query, Router
from ninja.errors import HttpError
from ninja.pagination import LimitOffsetPagination, paginate
from services.api.schema.others import MessageSchema
from ..schemas.lifecycle import (
    InvoiceOut,
    QuoteClientActionIn,
    QuoteOut,
    ServiceClientExecutionTaskOut,
    ServiceDeliverableActionIn,
    ServiceDeliverableOut,
    ServiceOrderOut,
)
from domains.service_operations.models import Invoice
from domains.service_operations.models import ServiceOrderActivity
from user.api.schemas.client_service import ClientInvoiceSchema, PaymentSubmissionCreateSchema, PaymentSubmissionResponseSchema
from user.models.client_service import PaymentSubmission
from ._service_request_support import CLIENT_VISIBLE_INVOICE_STATUSES, CLIENT_VISIBLE_ORDER_STATUSES, CLIENT_VISIBLE_QUOTE_STATUSES, _client_deliverable_queryset, _client_order_queryset, _client_task_queryset, _get_client_profile, _invoice_queryset, _quote_queryset, _validation_detail

from domains.service_operations.services import quotes as quote_services
from domains.service_operations.services import invoices as invoice_services


router = Router(tags=["Service Requests"])


@router.get("/payments/", response=List[ClientInvoiceSchema])
def list_client_invoices(request):
    client = _get_client_profile(request.user)
    return Invoice.objects.filter(client=client).prefetch_related("service_requests")


@router.post("/payments/submit", response={201: PaymentSubmissionResponseSchema, 400: MessageSchema})
def submit_payment(request, data: PaymentSubmissionCreateSchema):
    client = _get_client_profile(request.user)
    invoice = get_object_or_404(Invoice, id=data.invoice_id, client=client)
    if data.amount > invoice.balance:
        raise HttpError(400, "Amount exceeds outstanding balance")
    if PaymentSubmission.objects.filter(invoice=invoice, client=client, status=PaymentSubmission.STATUS.PENDING).exists():
        raise HttpError(400, "You already have a pending submission for this invoice")
    submission = PaymentSubmission.objects.create(
        invoice=invoice,
        client=client,
        submitted_by=request.user,
        submitted_by_type=PaymentSubmission.SUBMITTED_BY_TYPE.CLIENT,
        **data.dict(exclude={"invoice_id"}),
    )
    return 201, submission


@router.get("/payments/{invoice_id}", response=List[PaymentSubmissionResponseSchema])
def list_invoice_submissions(request, invoice_id: int):
    client = _get_client_profile(request.user)
    return PaymentSubmission.objects.filter(invoice_id=invoice_id, client=client).select_related("invoice")


@router.get("/invoices", response=List[InvoiceOut])
@paginate(LimitOffsetPagination, page_size=10)
def list_my_invoices(
    request,
    status: Optional[str] = Query(None),
    service_request_id: Optional[int] = Query(None),
):
    client = _get_client_profile(request.user)
    qs = _invoice_queryset().filter(client=client, status__in=CLIENT_VISIBLE_INVOICE_STATUSES)
    if status:
        qs = qs.filter(status=status)
    if service_request_id:
        qs = qs.filter(service_request_id=service_request_id)
    return qs.order_by("-issue_date", "-created_at")


@router.get("/invoices/{invoice_id}", response={200: InvoiceOut, 404: MessageSchema})
def get_my_invoice(request, invoice_id: int):
    client = _get_client_profile(request.user)
    invoice = get_object_or_404(
        _invoice_queryset(),
        id=invoice_id,
        client=client,
        status__in=CLIENT_VISIBLE_INVOICE_STATUSES,
    )
    return 200, invoice


@router.post("/invoices/{invoice_id}/payment-submissions", response={201: PaymentSubmissionResponseSchema, 400: MessageSchema, 404: MessageSchema})
def submit_invoice_payment(request, invoice_id: int, payload: PaymentSubmissionCreateSchema):
    try:
        client=_get_client_profile(request.user); i=get_object_or_404(_invoice_queryset(),id=invoice_id,client=client,status__in=CLIENT_VISIBLE_INVOICE_STATUSES); s=invoice_services.submit_payment(i,payload,client=client,user=request.user); return 201,s
    except (ValidationError,IntegrityError) as e: return 400,{"detail":_validation_detail(e)}


@router.get("/quotes", response=List[QuoteOut])
@paginate(LimitOffsetPagination, page_size=10)
def list_my_quotes(
    request,
    status: Optional[str] = Query(None),
    service_request_id: Optional[int] = Query(None),
):
    client = _get_client_profile(request.user)
    qs = _quote_queryset().filter(client=client, status__in=CLIENT_VISIBLE_QUOTE_STATUSES)
    if status:
        qs = qs.filter(status=status)
    if service_request_id:
        qs = qs.filter(service_request_id=service_request_id)
    return qs.order_by("-sent_at", "-created_at")


@router.get("/quotes/{quote_id}", response={200: QuoteOut, 404: MessageSchema})
def get_my_quote(request, quote_id: int):
    client = _get_client_profile(request.user)
    quote = get_object_or_404(
        _quote_queryset(),
        id=quote_id,
        client=client,
        status__in=CLIENT_VISIBLE_QUOTE_STATUSES,
    )
    return 200, quote


@router.post("/quotes/{quote_id}/accept", response={200: QuoteOut, 400: MessageSchema, 404: MessageSchema})
def accept_my_quote(request, quote_id: int):
    try:
        client=_get_client_profile(request.user); q=get_object_or_404(_quote_queryset(),id=quote_id,client=client,status__in=CLIENT_VISIBLE_QUOTE_STATUSES); quote_services.client_accept(q,user=request.user); return 200,_quote_queryset().get(id=q.id)
    except (ValidationError,IntegrityError) as e: return 400,{"detail":_validation_detail(e)}


@router.post("/quotes/{quote_id}/reject", response={200: QuoteOut, 400: MessageSchema, 404: MessageSchema})
def reject_my_quote(request, quote_id: int, payload: QuoteClientActionIn):
    try:
        client=_get_client_profile(request.user); q=get_object_or_404(_quote_queryset(),id=quote_id,client=client,status__in=CLIENT_VISIBLE_QUOTE_STATUSES); quote_services.client_reject(q,reason=payload.reason,user=request.user); return 200,_quote_queryset().get(id=q.id)
    except (ValidationError,IntegrityError) as e: return 400,{"detail":_validation_detail(e)}


@router.get("/orders", response=List[ServiceOrderOut])
@paginate(LimitOffsetPagination, page_size=10)
def list_my_orders(
    request,
    order_status: Optional[str] = Query(None),
    service_request_id: Optional[int] = Query(None),
):
    client = _get_client_profile(request.user)
    qs = _client_order_queryset().filter(client=client, order_status__in=CLIENT_VISIBLE_ORDER_STATUSES)
    if order_status:
        qs = qs.filter(order_status=order_status)
    if service_request_id:
        qs = qs.filter(service_request_id=service_request_id)
    return qs.order_by("-created_at")


@router.get("/orders/{order_id}", response={200: ServiceOrderOut, 404: MessageSchema})
def get_my_order(request, order_id: int):
    client = _get_client_profile(request.user)
    order = get_object_or_404(
        _client_order_queryset(),
        id=order_id,
        client=client,
        order_status__in=CLIENT_VISIBLE_ORDER_STATUSES,
    )
    return 200, order


@router.get("/orders/{order_id}/tasks", response=List[ServiceClientExecutionTaskOut])
@paginate(LimitOffsetPagination, page_size=10)
def list_my_order_tasks(
    request,
    order_id: int,
    status: Optional[str] = Query(None),
    milestone_id: Optional[int] = Query(None),
):
    client = _get_client_profile(request.user)
    get_object_or_404(_client_order_queryset(), id=order_id, client=client, order_status__in=CLIENT_VISIBLE_ORDER_STATUSES)
    tasks = _client_task_queryset().filter(order_id=order_id)
    if status:
        tasks = tasks.filter(status=status)
    if milestone_id:
        tasks = tasks.filter(milestone_id=milestone_id)
    return tasks.order_by("due_date", "-created_at")


@router.get("/orders/{order_id}/deliverables", response=List[ServiceDeliverableOut])
@paginate(LimitOffsetPagination, page_size=10)
def list_my_order_deliverables(
    request,
    order_id: int,
    status: Optional[str] = Query(None),
    deliverable_type: Optional[str] = Query(None),
):
    client = _get_client_profile(request.user)
    get_object_or_404(_client_order_queryset(), id=order_id, client=client, order_status__in=CLIENT_VISIBLE_ORDER_STATUSES)
    deliverables = _client_deliverable_queryset().filter(order_id=order_id)
    if status:
        deliverables = deliverables.filter(status=status)
    if deliverable_type:
        deliverables = deliverables.filter(deliverable_type=deliverable_type)
    return deliverables.order_by("-created_at")


@router.get("/orders/{order_id}/deliverables/{deliverable_id}", response={200: ServiceDeliverableOut, 404: MessageSchema})
def get_my_order_deliverable(request, order_id: int, deliverable_id: int):
    client = _get_client_profile(request.user)
    get_object_or_404(_client_order_queryset(), id=order_id, client=client, order_status__in=CLIENT_VISIBLE_ORDER_STATUSES)
    deliverable = get_object_or_404(_client_deliverable_queryset(), id=deliverable_id, order_id=order_id)
    return 200, deliverable


@router.post("/orders/{order_id}/deliverables/{deliverable_id}/approve", response={200: ServiceDeliverableOut, 400: MessageSchema, 404: MessageSchema})
def approve_my_order_deliverable(request, order_id: int, deliverable_id: int):
    try:
        client = _get_client_profile(request.user)
        order = get_object_or_404(_client_order_queryset(), id=order_id, client=client, order_status__in=CLIENT_VISIBLE_ORDER_STATUSES)
        deliverable = get_object_or_404(_client_deliverable_queryset(), id=deliverable_id, order=order)
        if deliverable.approval_mode != "client":
            return 400, {"detail": "This deliverable does not require client approval."}
        if deliverable.status != "under_review":
            return 400, {"detail": "Only deliverables under review can be approved."}
        deliverable.status = "approved"
        deliverable.approved_by = request.user
        deliverable.approved_at = timezone.now()
        deliverable.rejected_by = None
        deliverable.rejected_at = None
        deliverable.rejection_reason = ""
        deliverable.save()
        ServiceOrderActivity.objects.create(
            order=order,
            activity_type="deliverable_approved",
            visibility="internal_client",
            note=f"Client approved deliverable {deliverable.deliverable_number}.",
            created_by=request.user,
        )
        return 200, _client_deliverable_queryset().get(id=deliverable.id)
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


@router.post("/orders/{order_id}/deliverables/{deliverable_id}/reject", response={200: ServiceDeliverableOut, 400: MessageSchema, 404: MessageSchema})
def reject_my_order_deliverable(request, order_id: int, deliverable_id: int, payload: ServiceDeliverableActionIn):
    try:
        client = _get_client_profile(request.user)
        order = get_object_or_404(_client_order_queryset(), id=order_id, client=client, order_status__in=CLIENT_VISIBLE_ORDER_STATUSES)
        deliverable = get_object_or_404(_client_deliverable_queryset(), id=deliverable_id, order=order)
        if deliverable.approval_mode != "client":
            return 400, {"detail": "This deliverable does not require client approval."}
        if deliverable.status != "under_review":
            return 400, {"detail": "Only deliverables under review can be rejected."}
        deliverable.status = "rejected"
        deliverable.rejected_by = request.user
        deliverable.rejected_at = timezone.now()
        deliverable.rejection_reason = payload.reason or ""
        deliverable.save()
        ServiceOrderActivity.objects.create(
            order=order,
            activity_type="deliverable_rejected",
            visibility="internal_client",
            note=f"Client rejected deliverable {deliverable.deliverable_number}.",
            created_by=request.user,
        )
        return 200, _client_deliverable_queryset().get(id=deliverable.id)
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}
