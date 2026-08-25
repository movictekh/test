"""Client request intake and self-service Service Request HTTP endpoints."""

from typing import Any, Dict, List, Optional

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from ninja import Query, Router
from ninja.pagination import LimitOffsetPagination, paginate

from domains.service_operations.api.v1.schemas.catalogue import FieldTypeOut
from domains.service_operations.models import (
    Service,
    ServiceFieldType,
    ServiceRequest,
    ServiceRequestActivity,
)
from domains.service_operations.services import requests as request_services
from shared.api.schema.others import MessageSchema

from ..schemas.service_requests import (
    ServiceRequestActivityCreateSchema,
    ServiceRequestActivityOut,
    ServiceRequestAttachmentCreateSchema,
    ServiceRequestAttachmentOut,
    ServiceRequestCreateSchema,
    ServiceRequestDetailOut,
    ServiceRequestListOut,
    ServiceRequestSummaryOut,
)
from ._service_request_support import (
    CLIENT_ACTIVITY_TYPES,
    _apply_filters,
    _choice_rows,
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


@router.get(
    "/services/{service_id}/intake-form",
    response={200: Dict[str, Any], 404: MessageSchema},
)
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
    qs = _apply_filters(
        qs, status=status, priority=priority, service_id=service_id, search=search
    )
    return [_serialize_request(item) for item in qs.order_by("-created_at")]


@router.post("", response={201: ServiceRequestDetailOut, 400: MessageSchema})
def create_my_request(request, payload: ServiceRequestCreateSchema):
    try:
        client = _get_client_profile(request.user)
        obj = request_services.create_service_request(
            payload, client=client, created_by=request.user, submitted_by=request.user
        )
        obj = _request_queryset().get(id=obj.id)
        return 201, _serialize_request(obj, include_detail=True)
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


@router.get(
    "/{request_id}", response={200: ServiceRequestDetailOut, 404: MessageSchema}
)
def get_my_request(request, request_id: int):
    client = _get_client_profile(request.user)
    obj = get_object_or_404(_request_queryset(), id=request_id, client=client)
    return 200, _serialize_request(obj, include_detail=True)


@router.post(
    "/{request_id}/activities",
    response={201: ServiceRequestActivityOut, 400: MessageSchema, 404: MessageSchema},
)
def create_my_activity(
    request, request_id: int, payload: ServiceRequestActivityCreateSchema
):
    try:
        if payload.activity_type not in CLIENT_ACTIVITY_TYPES:
            return 400, {
                "detail": "This activity type is not available from the client portal."
            }
        client = _get_client_profile(request.user)
        obj = get_object_or_404(ServiceRequest, id=request_id, client=client)
        a = request_services.create_request_activity(
            obj, payload, created_by=request.user
        )
        return 201, _serialize_activity(a)
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}


@router.post(
    "/{request_id}/attachments",
    response={201: ServiceRequestAttachmentOut, 400: MessageSchema, 404: MessageSchema},
)
def create_my_attachment(
    request, request_id: int, payload: ServiceRequestAttachmentCreateSchema
):
    try:
        client = _get_client_profile(request.user)
        obj = get_object_or_404(ServiceRequest, id=request_id, client=client)
        x = request_services.create_request_attachment(
            obj, payload, uploaded_by=request.user
        )
        return 201, _serialize_attachment(x)
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}


# --------------------------------------------------------------------------
# Staff / admin service-request endpoints
# --------------------------------------------------------------------------

"""Staff/admin Service Request HTTP endpoints."""

from typing import List, Optional

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from ninja import Query, Router
from ninja.pagination import LimitOffsetPagination, paginate

from domains.service_operations.services import quotes as quote_services
from domains.service_operations.services import requests as request_services
from finance.services import (
    handle_payment_exception,
)
from finance.services import review_payment_submission as review_submission_payment
from shared.api.schema.others import MessageSchema
from user.api.schemas.client_service import (
    PaymentSubmissionResponseSchema,
    ReviewPaymentSchema,
)
from user.models.client import Client as CustomerClient
from finance.transactions.payment_submission import PaymentSubmission
from system.authorization import require_permission, scope_queryset

from ..schemas.service_requests import (
    ServiceRequestActivityCreateSchema,
    ServiceRequestActivityOut,
    ServiceRequestAttachmentCreateSchema,
    ServiceRequestAttachmentOut,
    ServiceRequestDetailOut,
    ServiceRequestListOut,
    ServiceRequestQuoteCreateSchema,
    ServiceRequestUpdateSchema,
    StaffServiceRequestCreateSchema,
)
from ._service_request_support import (
    _apply_filters,
    _get_staff_object_or_404,
    _request_queryset,
    _serialize_activity,
    _serialize_attachment,
    _serialize_request,
    _validation_detail,
)

admin_router = Router(tags=["Service Requests"])


@admin_router.get("/admin", response=List[ServiceRequestListOut])
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
    qs = _apply_filters(
        qs,
        status,
        priority,
        service_id,
        branch_id,
        owner_id,
        client_id,
        source,
        date_from,
        date_to,
        due_from,
        due_to,
        search,
    )
    return [_serialize_request(item) for item in qs.order_by("-created_at")]


@admin_router.post(
    "/admin",
    response={201: ServiceRequestDetailOut, 400: MessageSchema, 403: MessageSchema},
)
@require_permission("service_requests", "create")
def create_admin_service_request(request, payload: StaffServiceRequestCreateSchema):
    try:
        client = get_object_or_404(CustomerClient, id=payload.client_id)
        obj = request_services.create_service_request(
            payload, client=client, created_by=request.user, staff=True
        )
        obj = _request_queryset().get(id=obj.id)
        return 201, _serialize_request(obj, include_detail=True)
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


@admin_router.get(
    "/admin/payment-submissions", response=List[PaymentSubmissionResponseSchema]
)
@require_permission("payments", "list")
def list_pending_submissions(request):
    return PaymentSubmission.objects.filter(
        status=PaymentSubmission.STATUS.PENDING
    ).select_related("invoice")


@admin_router.post("/admin/payment-submissions/{submission_id}/review")
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


@admin_router.get(
    "/admin/{request_id}", response={200: ServiceRequestDetailOut, 404: MessageSchema}
)
@require_permission("service_requests", "view")
def get_admin_service_request(request, request_id: int):
    obj = _get_staff_object_or_404(request, request_id)
    return 200, _serialize_request(obj, include_detail=True)


@admin_router.patch(
    "/admin/{request_id}",
    response={200: ServiceRequestDetailOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("service_requests", "update")
def update_admin_service_request(
    request, request_id: int, payload: ServiceRequestUpdateSchema
):
    try:
        obj = _get_staff_object_or_404(request, request_id)
        request_services.update_staff_request(obj, payload, updated_by=request.user)
        obj = _request_queryset().get(id=obj.id)
        return 200, _serialize_request(obj, include_detail=True)
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


@admin_router.post(
    "/admin/{request_id}/activities",
    response={201: ServiceRequestActivityOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("service_requests", "update")
def create_admin_activity(
    request, request_id: int, payload: ServiceRequestActivityCreateSchema
):
    try:
        obj = _get_staff_object_or_404(request, request_id)
        a = request_services.create_request_activity(
            obj, payload, created_by=request.user
        )
        return 201, _serialize_activity(a)
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}


@admin_router.post(
    "/admin/{request_id}/attachments",
    response={201: ServiceRequestAttachmentOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("service_requests", "update")
def create_admin_attachment(
    request, request_id: int, payload: ServiceRequestAttachmentCreateSchema
):
    try:
        obj = _get_staff_object_or_404(request, request_id)
        x = request_services.create_request_attachment(
            obj, payload, uploaded_by=request.user
        )
        return 201, _serialize_attachment(x)
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}


@admin_router.post(
    "/admin/{request_id}/quote",
    response={201: ServiceRequestDetailOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("quotes", "create")
def create_or_link_request_quote(
    request, request_id: int, payload: ServiceRequestQuoteCreateSchema
):
    try:
        obj = _get_staff_object_or_404(request, request_id)
        quote_services.create_request_quote(obj, payload, created_by=request.user)
        obj = _request_queryset().get(id=obj.id)
        return 201, _serialize_request(obj, include_detail=True)
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}
