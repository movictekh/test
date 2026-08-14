"""Staff/admin Service Request HTTP endpoints."""

from datetime import timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Prefetch, Q
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
from domains.service_operations.api.v1.schemas.catalogue import FieldTypeOut
from ..schemas.service_requests import (
    ServiceRequestActivityCreateSchema,
    ServiceRequestActivityOut,
    ServiceRequestAttachmentCreateSchema,
    ServiceRequestAttachmentOut,
    ServiceRequestCreateSchema,
    ServiceRequestDetailOut,
    ServiceRequestListOut,
    ServiceRequestQuoteCreateSchema,
    ServiceRequestSummaryOut,
    ServiceRequestUpdateSchema,
    StaffServiceRequestCreateSchema,
)
from domains.service_operations.models import Invoice
from domains.service_operations.models import (
    Quote,
    Service,
    ServiceFieldType,
    ServiceLead,
    ServiceDeliverable,
    ServiceExecutionTask,
    ServiceOrder,
    ServiceOrderActivity,
    ServiceOrderMilestone,
    ServiceRequest,
    ServiceRequestActivity,
    ServiceRequestAnswer,
    ServiceRequestAttachment,
    ServiceRequestForm,
    ServiceSubService,
)
from user.api.schemas.client_service import (
    ClientInvoiceSchema,
    PaymentSubmissionCreateSchema,
    PaymentSubmissionResponseSchema,
    ReviewPaymentSchema,
)
from user.models.client import Client as CustomerClient
from user.models.client_service import PaymentSubmission
from finance.services import handle_payment_exception, review_payment_submission as review_submission_payment
from user.models.employee import Employee
from user.utils.perm import require_permission, scope_queryset
from ._service_request_support import (
    _apply_filters,
    _create_service_request,
    _ensure_choice,
    _ensure_no_active_quote,
    _get_staff_object_or_404,
    _latest_rejected_quote,
    _log_activity,
    _quote_payload_data,
    _request_queryset,
    _serialize_activity,
    _serialize_attachment,
    _serialize_request,
    _validation_detail,
)


router = Router(tags=["Service Requests"])


@router.get("/admin", response=List[ServiceRequestListOut])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("service_requests", "list")
def list_admin_service_requests(
    request,
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    service_id: Optional[int] = Query(None),
    branch_id: Optional[int] = Query(None),
    owner_id: Optional[int] = Query(None),
    client_id: Optional[int] = Query(None),
    source: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    due_from: Optional[str] = Query(None),
    due_to: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    qs = scope_queryset(request, _request_queryset(), branch_field="branch_id")
    qs = _apply_filters(qs, status, priority, service_id, branch_id, owner_id, client_id, source, date_from, date_to, due_from, due_to, search)
    return [_serialize_request(item) for item in qs.order_by("-created_at")]


@router.post("/admin", response={201: ServiceRequestDetailOut, 400: MessageSchema, 403: MessageSchema})
@require_permission("service_requests", "create")
def create_admin_service_request(request, payload: StaffServiceRequestCreateSchema):
    try:
        client = get_object_or_404(CustomerClient, id=payload.client_id)
        obj = _create_service_request(payload, client=client, created_by=request.user, staff=True)
        return 201, _serialize_request(obj, include_detail=True)
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


@router.get("/admin/payment-submissions", response=List[PaymentSubmissionResponseSchema])
@require_permission("payments", "list")
def list_pending_submissions(request):
    return PaymentSubmission.objects.filter(status=PaymentSubmission.STATUS.PENDING).select_related("invoice")


@router.post("/admin/payment-submissions/{submission_id}/review")
@require_permission("payments", "create")
def review_submission(request, submission_id: int, data: ReviewPaymentSchema):
    try:
        submission = get_object_or_404(PaymentSubmission, id=submission_id)
        review_submission_payment(
            submission,
            reviewed_by=request.user,
            status=data.status,
            finance_account_id=data.finance_account_id,
            rejection_reason=data.rejection_reason,
        )
        return {"status": "ok"}
    except Exception as exc:
        return handle_payment_exception(exc)


@router.get("/admin/{request_id}", response={200: ServiceRequestDetailOut, 404: MessageSchema})
@require_permission("service_requests", "view")
def get_admin_service_request(request, request_id: int):
    obj = _get_staff_object_or_404(request, request_id)
    return 200, _serialize_request(obj, include_detail=True)


@router.patch("/admin/{request_id}", response={200: ServiceRequestDetailOut, 400: MessageSchema, 404: MessageSchema})
@require_permission("service_requests", "update")
def update_admin_service_request(request, request_id: int, payload: ServiceRequestUpdateSchema):
    try:
        obj = _get_staff_object_or_404(request, request_id)
        data = payload.dict(exclude_unset=True)
        relation_map = {
            "branch_id": "branch_id",
            "owner_id": "owner_id",
            "service_lead_id": "service_lead_id",
            "crm_lead_id": "crm_lead_id",
        }
        old_status = obj.status
        for payload_key, model_attr in relation_map.items():
            if payload_key in data:
                setattr(obj, model_attr, data.pop(payload_key))
        for attr, value in data.items():
            setattr(obj, attr, value)
        obj.save()
        activity_type = "status_change" if old_status != obj.status else "control_update"
        _log_activity(
            obj,
            activity_type,
            f"Service request updated. Status: {obj.status}; next action: {obj.next_action}",
            created_by=request.user,
        )
        obj = _request_queryset().get(id=obj.id)
        return 200, _serialize_request(obj, include_detail=True)
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


@router.post("/admin/{request_id}/activities", response={201: ServiceRequestActivityOut, 400: MessageSchema, 404: MessageSchema})
@require_permission("service_requests", "update")
def create_admin_activity(request, request_id: int, payload: ServiceRequestActivityCreateSchema):
    try:
        obj = _get_staff_object_or_404(request, request_id)
        _ensure_choice(payload.activity_type, ServiceRequestActivity.ACTIVITY_TYPE_CHOICES, "activity_type")
        _ensure_choice(payload.outcome, ServiceRequestActivity.OUTCOME_CHOICES, "outcome")
        activity = ServiceRequestActivity.objects.create(
            request=obj,
            activity_type=payload.activity_type,
            outcome=payload.outcome,
            note=payload.note,
            next_action=payload.next_action or "",
            next_follow_up_at=payload.next_follow_up_at,
            created_by=request.user,
        )
        return 201, _serialize_activity(activity)
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}


@router.post("/admin/{request_id}/attachments", response={201: ServiceRequestAttachmentOut, 400: MessageSchema, 404: MessageSchema})
@require_permission("service_requests", "update")
def create_admin_attachment(request, request_id: int, payload: ServiceRequestAttachmentCreateSchema):
    try:
        obj = _get_staff_object_or_404(request, request_id)
        attachment = ServiceRequestAttachment(
            request=obj,
            uploaded_by=request.user,
            **payload.dict(),
        )
        attachment.full_clean()
        attachment.save()
        return 201, _serialize_attachment(attachment)
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}


@router.post("/admin/{request_id}/quote", response={201: ServiceRequestDetailOut, 400: MessageSchema, 404: MessageSchema})
@require_permission("quotes", "create")
def create_or_link_request_quote(request, request_id: int, payload: ServiceRequestQuoteCreateSchema):
    try:
        obj = _get_staff_object_or_404(request, request_id)
        with transaction.atomic():
            _ensure_no_active_quote(obj)
            previous_quote = _latest_rejected_quote(obj)
            quote = Quote.objects.create(
                client=obj.client,
                service=obj.service,
                service_request=obj,
                previous_quote=previous_quote,
                version=(previous_quote.version + 1) if previous_quote else 1,
                created_by=request.user,
                **_quote_payload_data(payload, obj),
            )
            obj.quote = quote
            obj.status = "under_review"
            obj.next_action = f"Approve quotation {quote.quote_number}"
            obj.save(update_fields=["quote", "status", "next_action", "updated_at"])
            _log_activity(
                obj,
                "quote_prepared",
                f"Quotation {quote.quote_number} prepared for {quote.amount} and awaiting approval.",
                created_by=request.user,
                next_action="Await quote approval",
            )
        obj = _request_queryset().get(id=obj.id)
        return 201, _serialize_request(obj, include_detail=True)
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}
