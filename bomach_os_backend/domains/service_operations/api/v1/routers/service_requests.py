"""Client request intake and self-service Service Request HTTP endpoints."""

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
    CLIENT_ACTIVITY_TYPES,
    _apply_filters,
    _choice_rows,
    _create_service_request,
    _ensure_choice,
    _get_client_profile,
    _request_queryset,
    _serialize_activity,
    _serialize_attachment,
    _serialize_request,
    _serialize_request_form,
    _validation_detail,
)


router = Router(tags=["Service Requests"])


@router.get("/choices", response=Dict[str, Any])
def get_service_request_choices(request):
    field_type_supports_options = {
        ServiceFieldType.SELECT,
        ServiceFieldType.MULTISELECT,
    }
    return {
        "statuses": _choice_rows(ServiceRequest.STATUS_CHOICES),
        "priorities": _choice_rows(ServiceRequest.PRIORITY_CHOICES),
        "sources": _choice_rows(ServiceRequest.SOURCE_CHOICES),
        "customer_types": _choice_rows(ServiceRequest.CUSTOMER_TYPE_CHOICES),
        "activity_types": _choice_rows(ServiceRequestActivity.ACTIVITY_TYPE_CHOICES),
        "activity_outcomes": _choice_rows(ServiceRequestActivity.OUTCOME_CHOICES),
        "field_types": [
            FieldTypeOut(
                value=value,
                label=label,
                supports_options=value in field_type_supports_options,
                supports_validation=True,
            ).dict()
            for value, label in ServiceFieldType.choices
        ],
    }


@router.get("/services/{service_id}/intake-form", response={200: Dict[str, Any], 404: MessageSchema})
def get_service_intake_form(request, service_id: int):
    service = get_object_or_404(
        Service.objects.select_related("active_request_form").prefetch_related(
            "active_request_form__fields",
            "subservices",
        ),
        id=service_id,
        status="active",
        client_visibility="visible",
    )
    form = service.active_request_form
    if not form:
        return 404, {"detail": "Service has no active intake form."}
    return 200, {
        "service": {
            "id": service.id,
            "code": service.code,
            "name": service.name,
            "division": service.division,
            "default_sla_days": service.default_sla_days,
            "fulfillment_mode": service.fulfillment_mode,
        },
        "active_request_form": _serialize_request_form(form),
        "subservices": [
            {
                "id": item.id,
                "code": item.code,
                "name": item.name,
                "description": item.description,
                "status": item.status,
            }
            for item in service.subservices.filter(status="active")
        ],
    }


@router.get("/summary", response={200: ServiceRequestSummaryOut, 400: MessageSchema})
def get_my_summary(request):
    client = _get_client_profile(request.user)
    qs = ServiceRequest.objects.filter(client=client)
    return 200, {
        "new": qs.filter(status="new").count(),
        "under_review": qs.filter(status="under_review").count(),
        "awaiting_client": qs.filter(status="awaiting_client").count(),
        "site_assessment": qs.filter(status="site_assessment").count(),
        "quoted": qs.filter(status="quoted").count(),
        "converted": qs.filter(status="converted").count(),
        "rejected": qs.filter(status="rejected").count(),
        "total": qs.count(),
    }


@router.get("", response=List[ServiceRequestListOut])
@paginate(LimitOffsetPagination, page_size=10)
def list_my_requests(
    request,
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    service_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
):
    client = _get_client_profile(request.user)
    qs = _request_queryset().filter(client=client)
    qs = _apply_filters(qs, status=status, priority=priority, service_id=service_id, search=search)
    return [_serialize_request(item) for item in qs.order_by("-created_at")]


@router.post("", response={201: ServiceRequestDetailOut, 400: MessageSchema})
def create_my_request(request, payload: ServiceRequestCreateSchema):
    try:
        client = _get_client_profile(request.user)
        obj = _create_service_request(payload, client=client, created_by=request.user, submitted_by=request.user)
        return 201, _serialize_request(obj, include_detail=True)
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


@router.get("/{request_id}", response={200: ServiceRequestDetailOut, 404: MessageSchema})
def get_my_request(request, request_id: int):
    client = _get_client_profile(request.user)
    obj = get_object_or_404(_request_queryset(), id=request_id, client=client)
    return 200, _serialize_request(obj, include_detail=True)


@router.post("/{request_id}/activities", response={201: ServiceRequestActivityOut, 400: MessageSchema, 404: MessageSchema})
def create_my_activity(request, request_id: int, payload: ServiceRequestActivityCreateSchema):
    try:
        if payload.activity_type not in CLIENT_ACTIVITY_TYPES:
            return 400, {"detail": "This activity type is not available from the client portal."}
        client = _get_client_profile(request.user)
        obj = get_object_or_404(ServiceRequest, id=request_id, client=client)
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


@router.post("/{request_id}/attachments", response={201: ServiceRequestAttachmentOut, 400: MessageSchema, 404: MessageSchema})
def create_my_attachment(request, request_id: int, payload: ServiceRequestAttachmentCreateSchema):
    try:
        client = _get_client_profile(request.user)
        obj = get_object_or_404(ServiceRequest, id=request_id, client=client)
        attachment = ServiceRequestAttachment(request=obj, uploaded_by=request.user, **payload.dict())
        attachment.full_clean()
        attachment.save()
        return 201, _serialize_attachment(attachment)
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
