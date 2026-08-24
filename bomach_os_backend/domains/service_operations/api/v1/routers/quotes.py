from decimal import Decimal
from typing import List, Optional

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from ninja import Query, Router
from ninja.errors import HttpError
from ninja.pagination import LimitOffsetPagination, paginate

from domains.service_operations.models import (
    Invoice,
    Quote,
    ServiceRequest,
    ServiceRequestActivity,
)
from domains.service_operations.services import quotes as quote_services
from shared.api.schema.others import MessageSchema
from user.utils.perm import require_permission, scope_queryset

from ..schemas.lifecycle import (
    InvoiceFromQuoteIn,
    InvoiceOut,
    QuoteIn,
    QuoteOut,
    QuoteUpdate,
)

router = Router(tags=["Quotes"])


EDITABLE_STATUSES = {"awaiting_approval"}
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


def _quote_queryset():
    return Quote.objects.select_related(
        "client",
        "client__user",
        "service",
        "service__category",
        "service_request",
        "service_request__branch",
        "previous_quote",
        "required_approver_role",
        "approved_by",
        "created_by",
    )


def _quote_payload_data(payload):
    data = payload.dict(exclude_unset=True)
    if not data.get("required_approver_role_id"):
        raise ValidationError(
            {"required_approver_role_id": "Required approver role is required."}
        )
    service_fee = data.get("service_fee")
    amount = data.get("amount")
    if service_fee is None:
        if amount is None:
            raise ValidationError({"service_fee": "Service fee is required."})
        data["service_fee"] = amount
    if amount is None:
        data["amount"] = Decimal("0.00")
    data["status"] = "awaiting_approval"
    return data


def _ensure_required_approver(quote, employee):
    if not quote.required_approver_role_id:
        raise HttpError(400, "Quote has no required approver role.")
    if employee.role_id != quote.required_approver_role_id:
        raise HttpError(403, "This quote requires approval from a different role.")


def _latest_rejected_quote(service_request):
    return (
        service_request.quotes.filter(status="rejected")
        .order_by("-version", "-created_at", "-id")
        .first()
    )


def _ensure_no_active_request_quote(service_request):
    if service_request.quotes.exclude(status__in=["rejected", "expired"]).exists():
        raise ValidationError("This service request already has an active quote.")


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


def _invoice_queryset():
    return Invoice.objects.select_related(
        "client",
        "client__user",
        "service",
        "service__category",
        "quote",
        "service_request",
        "order",
        "lead",
        "created_by",
    ).prefetch_related("items")


def _create_quote_from_data(data, created_by):
    service_request = None
    previous_quote = None
    if data.get("service_request_id"):
        service_request = get_object_or_404(
            ServiceRequest, id=data["service_request_id"]
        )
        _ensure_no_active_request_quote(service_request)
        data["client_id"] = service_request.client_id
        data["service_id"] = service_request.service_id
        previous = _latest_rejected_quote(service_request)
        if previous:
            previous_quote = previous
            data["version"] = previous.version + 1
        else:
            data.setdefault("version", 1)
    elif data.get("previous_quote_id"):
        previous_quote = get_object_or_404(Quote, id=data["previous_quote_id"])
        data["version"] = previous_quote.version + 1

    data.pop("previous_quote_id", None)
    quote = Quote.objects.create(
        previous_quote=previous_quote,
        created_by=created_by,
        **data,
    )
    if service_request:
        service_request.quote = quote
        service_request.status = "under_review"
        service_request.next_action = f"Approve quotation {quote.quote_number}"
        service_request.save(
            update_fields=["quote", "status", "next_action", "updated_at"]
        )
        _log_request_activity(
            service_request,
            "quote_prepared",
            f"Quotation {quote.quote_number} prepared for {quote.amount} and awaiting approval.",
            created_by=created_by,
            next_action="Await quote approval",
        )
    return quote


@router.get("", response=List[QuoteOut])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("quotes", "list")
def list_quotes(
    request,
    status: Optional[str] = Query(None),
    client_id: Optional[int] = Query(None),
    service_request_id: Optional[int] = Query(None),
):
    quotes = scope_queryset(
        request, _quote_queryset(), branch_field="service_request__branch_id"
    )
    if status:
        quotes = quotes.filter(status=status)
    if client_id:
        quotes = quotes.filter(client_id=client_id)
    if service_request_id:
        quotes = quotes.filter(service_request_id=service_request_id)
    return quotes.order_by("-created_at")


@router.post("", response={201: QuoteOut, 400: MessageSchema})
@require_permission("quotes", "create")
def create_quote(request, payload: QuoteIn):
    try:
        q = quote_services.create_quote(payload, created_by=request.user)
        return 201, _quote_queryset().get(id=q.id)
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


@router.post(
    "/{quote_id}/approve",
    response={200: QuoteOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("quotes", "approve")
def approve_quote(request, quote_id: int):
    try:
        q = get_object_or_404(_quote_queryset(), id=quote_id)
        quote_services.approve_quote(
            q, employee=request._perm_employee, user=request.user
        )
        return 200, _quote_queryset().get(id=q.id)
    except PermissionError as e:
        raise HttpError(403, str(e))
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


@router.post(
    "/{quote_id}/invoice",
    response={201: InvoiceOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("service_invoices", "create")
def create_invoice_from_quote(request, quote_id: int, payload: InvoiceFromQuoteIn):
    try:
        q = get_object_or_404(_quote_queryset(), id=quote_id)
        i = quote_services.create_invoice_from_quote(q, payload, user=request.user)
        return 201, _invoice_queryset().get(id=i.id)
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


@router.get("/{quote_id}", response=QuoteOut)
@require_permission("quotes", "view")
def get_quote(request, quote_id: int):
    return get_object_or_404(_quote_queryset(), id=quote_id)


@router.patch(
    "/{quote_id}", response={200: QuoteOut, 400: MessageSchema, 404: MessageSchema}
)
@require_permission("quotes", "update")
def update_quote(request, quote_id: int, payload: QuoteUpdate):
    try:
        q = get_object_or_404(Quote, id=quote_id)
        quote_services.update_quote(q, payload)
        return 200, _quote_queryset().get(id=q.id)
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


@router.put(
    "/{quote_id}", response={200: QuoteOut, 400: MessageSchema, 404: MessageSchema}
)
@require_permission("quotes", "update")
def replace_quote(request, quote_id: int, payload: QuoteUpdate):
    return update_quote(request, quote_id, payload)


@router.delete(
    "/{quote_id}", response={200: MessageSchema, 400: MessageSchema, 404: MessageSchema}
)
@require_permission("quotes", "delete")
def delete_quote(request, quote_id: int):
    q = get_object_or_404(Quote, id=quote_id)
    try:
        quote_services.delete_quote(q)
        return 200, {"detail": "Quote deleted successfully"}
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
