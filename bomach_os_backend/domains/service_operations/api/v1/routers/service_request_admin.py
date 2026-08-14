"""Staff/admin Service Request HTTP endpoints."""

from typing import List, Optional
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from ninja import Query, Router
from ninja.pagination import LimitOffsetPagination, paginate
from services.api.schema.others import MessageSchema
from ..schemas.service_requests import ServiceRequestActivityCreateSchema, ServiceRequestActivityOut, ServiceRequestAttachmentCreateSchema, ServiceRequestAttachmentOut, ServiceRequestDetailOut, ServiceRequestListOut, ServiceRequestQuoteCreateSchema, ServiceRequestUpdateSchema, StaffServiceRequestCreateSchema
from user.api.schemas.client_service import PaymentSubmissionResponseSchema, ReviewPaymentSchema
from user.models.client import Client as CustomerClient
from user.models.client_service import PaymentSubmission
from finance.services import handle_payment_exception, review_payment_submission as review_submission_payment
from user.utils.perm import require_permission, scope_queryset
from ._service_request_support import _apply_filters, _get_staff_object_or_404, _request_queryset, _serialize_activity, _serialize_attachment, _serialize_request, _validation_detail

from domains.service_operations.services import requests as request_services
from domains.service_operations.services import quotes as quote_services


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
        client=get_object_or_404(CustomerClient,id=payload.client_id); obj=request_services.create_service_request(payload,client=client,created_by=request.user,staff=True); obj=_request_queryset().get(id=obj.id); return 201,_serialize_request(obj,include_detail=True)
    except (ValidationError,IntegrityError) as e: return 400,{"detail":_validation_detail(e)}


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
        obj=_get_staff_object_or_404(request,request_id); request_services.update_staff_request(obj,payload,updated_by=request.user); obj=_request_queryset().get(id=obj.id); return 200,_serialize_request(obj,include_detail=True)
    except (ValidationError,IntegrityError) as e: return 400,{"detail":_validation_detail(e)}


@router.post("/admin/{request_id}/activities", response={201: ServiceRequestActivityOut, 400: MessageSchema, 404: MessageSchema})
@require_permission("service_requests", "update")
def create_admin_activity(request, request_id: int, payload: ServiceRequestActivityCreateSchema):
    try:
        obj=_get_staff_object_or_404(request,request_id); a=request_services.create_request_activity(obj,payload,created_by=request.user); return 201,_serialize_activity(a)
    except ValidationError as e: return 400,{"detail":_validation_detail(e)}


@router.post("/admin/{request_id}/attachments", response={201: ServiceRequestAttachmentOut, 400: MessageSchema, 404: MessageSchema})
@require_permission("service_requests", "update")
def create_admin_attachment(request, request_id: int, payload: ServiceRequestAttachmentCreateSchema):
    try:
        obj=_get_staff_object_or_404(request,request_id); x=request_services.create_request_attachment(obj,payload,uploaded_by=request.user); return 201,_serialize_attachment(x)
    except ValidationError as e: return 400,{"detail":_validation_detail(e)}


@router.post("/admin/{request_id}/quote", response={201: ServiceRequestDetailOut, 400: MessageSchema, 404: MessageSchema})
@require_permission("quotes", "create")
def create_or_link_request_quote(request, request_id: int, payload: ServiceRequestQuoteCreateSchema):
    try:
        obj=_get_staff_object_or_404(request,request_id); quote_services.create_request_quote(obj,payload,created_by=request.user); obj=_request_queryset().get(id=obj.id); return 201,_serialize_request(obj,include_detail=True)
    except (ValidationError,IntegrityError) as e: return 400,{"detail":_validation_detail(e)}
