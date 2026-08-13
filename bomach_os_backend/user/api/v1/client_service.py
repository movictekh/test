from ninja import Router, Query
from django.shortcuts import get_object_or_404
from ninja.pagination import paginate, LimitOffsetPagination
from django.http import Http404
from django.db.models import Q, Count
from django.core.exceptions import ValidationError
from user.api.schemas.client_service import (
    ClientServiceResponseSchema,
    ServiceRequestCreateSchema,
    ServiceRequestDashboardResponseSchema,
    ServiceRequestFullResponseSchema,
    ClientInvoiceSchema,
    PaymentSubmissionCreateSchema,
    PaymentSubmissionResponseSchema,
    ReviewPaymentSchema
)
from user.api.schemas.others import MessageSchema
from user.models.client_service import ClientService, ServiceRequest, PaymentSubmission
from finance.services import handle_payment_exception, review_payment_submission as review_submission_payment
from services.models.payment import Invoice
from typing import List, Optional
from ninja.errors import HttpError


client_service_api = Router(tags=["Client Services"])
service_request_api = Router(tags=["Service Requests"])


# ─── Browse Services (read-only) ─────────────────────────────────────
#
@service_request_api.get("/summary", response={200: dict, 400: MessageSchema})
def get_my_summary(request):
    try:
        qs = ServiceRequest.objects.filter(client=request.user)
        return 200, {
            "in_progress": qs.filter(status=ServiceRequest.STATUS.IN_PROGRESS).count(),
            "under_review": qs.filter(status=ServiceRequest.STATUS.UNDER_REVIEW).count(),
            "completed": qs.filter(status=ServiceRequest.STATUS.COMPLETED).count(),
            "total": qs.count(),
        }
    except Exception as e:
        return 400, {"detail": str(e)}

@client_service_api.get("", response={200: List[ClientServiceResponseSchema]})
@paginate(LimitOffsetPagination, page_size=10)
def list_services(
    request,
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    filters = Q(is_active=True)

    if category:
        filters &= Q(category=category)

    if search:
        filters &= (
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )

    return ClientService.objects.filter(filters).order_by('-is_featured', '-created_at')

@client_service_api.get("/recent-orders", response={200: List[ServiceRequestDashboardResponseSchema], 400: MessageSchema})
def recent_orders(request):
    try:
        recent_requests = ServiceRequest.objects.filter(
            client=request.user
        ).select_related(
            'service', 'client', 'invoice'
        ).order_by('-created_at')[:5]
        return 200, recent_requests
    except Exception as e:
        return 400, {"detail": str(e)}

@client_service_api.get("/{id}", response={200: ClientServiceResponseSchema, 404: MessageSchema})
def get_service(request, id: int):
    try:
        service = ClientService.objects.get(id=id, is_active=True)
        return 200, service
    except ClientService.DoesNotExist:
        return 404, {"detail": "Service not found."}


# ─── Service Requests ─────────────────────────────────────────────────

@service_request_api.post("", response={201: ServiceRequestFullResponseSchema, 400: MessageSchema})
def create_request(request, payload: ServiceRequestCreateSchema):
    try:
        service = get_object_or_404(ClientService, id=payload.service_id, is_active=True)

        service_request = ServiceRequest.objects.create(
            client=request.user,
            service=service,
            project_name=payload.project_name,
            location=payload.location,
            preferred_start_date=payload.preferred_start_date,
            project_details=payload.project_details,
            special_requirements=payload.special_requirements,
            attachment=payload.attachment,
        )

        service_request.full_clean()
        service_request.save()

        return 201, service_request
    except Http404:
        return 400, {"detail": "Service not found or is inactive."}
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
    except Exception as e:
        return 400, {"detail": str(e)}


@service_request_api.get("/{id}", response={200: ServiceRequestFullResponseSchema, 404: MessageSchema})
def get_request(request, id: int):
    try:
        service_request = ServiceRequest.objects.select_related('client', 'service', 'invoice').get(id=id)
        if service_request.client != request.user:
            return 404, {"detail": "Request not found."}
        return 200, service_request
    except ServiceRequest.DoesNotExist:
        return 404, {"detail": "Request not found."}


@service_request_api.get("", response={200: List[ServiceRequestDashboardResponseSchema], 400: MessageSchema})
@paginate(LimitOffsetPagination, page_size=10)
def list_my_requests(
    request,
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    filters = Q(client=request.user)

    if status:
        filters &= Q(status=status)

    if search:
        filters &= (
            Q(order_id__icontains=search) |
            Q(project_name__icontains=search) |
            Q(service__name__icontains=search) |
            Q(location__icontains=search)
        )

    return ServiceRequest.objects.filter(filters).select_related('service', 'invoice').order_by('-created_at')


@service_request_api.post("/{id}/approve", response={
    200: ServiceRequestFullResponseSchema,
    403: MessageSchema,
    404: MessageSchema,
    400: MessageSchema,
})
def approve_request(request, id: int):
    try:
        service_request = get_object_or_404(ServiceRequest, id=id)

        if service_request.status != ServiceRequest.STATUS.PENDING:
            return 400, {"detail": "Only pending requests can be approved."}

        service_request.status = ServiceRequest.STATUS.IN_PROGRESS
        service_request.save()

        return 200, service_request
    except Http404:
        return 404, {"detail": "Request not found."}
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
    except Exception as e:
        return 400, {"detail": str(e)}


@service_request_api.post("/{id}/reject", response={
    200: ServiceRequestFullResponseSchema,
    403: MessageSchema,
    404: MessageSchema,
    400: MessageSchema,
})
def reject_request(request, id: int):
    try:
        service_request = get_object_or_404(ServiceRequest, id=id)

        if service_request.status != ServiceRequest.STATUS.PENDING:
            return 400, {"detail": "Only pending requests can be rejected."}

        service_request.status = ServiceRequest.STATUS.REJECTED
        service_request.save()

        return 200, service_request
    except Http404:
        return 404, {"detail": "Request not found."}
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
    except Exception as e:
        return 400, {"detail": str(e)}


# ── Client endpoints ──

@service_request_api.get("/payments/", response=List[ClientInvoiceSchema])
def list_client_invoices(request):
    """All invoices for the logged-in client"""
    return Invoice.objects.filter(
        client=request.user.client_profile
    ).prefetch_related('service_requests')


@service_request_api.get("/payments/{invoice_id}", response=List[PaymentSubmissionResponseSchema])
def list_invoice_submissions(request, invoice_id: int):
    """All payment submissions for a specific invoice"""
    return PaymentSubmission.objects.filter(
        invoice_id=invoice_id,
        client=request.user.client_profile
    ).select_related('invoice')


@service_request_api.post("/payments/submit", response=PaymentSubmissionResponseSchema)
def submit_payment(request, data: PaymentSubmissionCreateSchema):
    """Client uploads proof of payment"""
    invoice = get_object_or_404(
        Invoice, id=data.invoice_id, client=request.user.client_profile
    )

    # Prevent submitting more than what's owed
    if data.amount > invoice.balance:
        raise HttpError(400, "Amount exceeds outstanding balance")

    # Prevent duplicate pending submissions
    has_pending = PaymentSubmission.objects.filter(
        invoice=invoice,
        client=request.user.client_profile,
        status=PaymentSubmission.STATUS.PENDING
    ).exists()

    if has_pending:
        raise HttpError(400, "You already have a pending submission for this invoice")

    submission = PaymentSubmission.objects.create(
        invoice=invoice,
        client=request.user.client_profile,
        submitted_by=request.user,
        submitted_by_type=PaymentSubmission.SUBMITTED_BY_TYPE.CLIENT,
        **data.dict(exclude={'invoice_id'})
    )
    return submission


# ── Admin endpoints ──

@service_request_api.get("/admin/payment-submissions", response=List[PaymentSubmissionResponseSchema])
def list_pending_submissions(request):
    """All submissions awaiting review"""
    return PaymentSubmission.objects.filter(
        status=PaymentSubmission.STATUS.PENDING
    ).select_related('invoice')


@service_request_api.post("/admin/payment-submissions/{submission_id}/review")
def review_submission(request, submission_id: int, data: ReviewPaymentSchema):
    """Admin confirms or rejects a payment submission"""
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

@service_request_api.get(
    "/admin/service-requests",
    response=List[ServiceRequestDashboardResponseSchema]
)
def list_all_service_requests(request, client_id: Optional[int] = None):
    qs = ServiceRequest.objects.select_related(
        'service', 'client', 'invoice'
    )
    if client_id:
        qs = qs.filter(client__client_profile__id=client_id)
    return qs


@service_request_api.get(
    "/admin/service-requests/{request_id}",
    response=ServiceRequestFullResponseSchema
)
def get_service_request_detail(request, request_id: int):
    return get_object_or_404(
        ServiceRequest.objects.select_related(
            'service', 'client', 'invoice'
        ).prefetch_related(
            'invoice__items', 'invoice__payments'
        ),
        id=request_id
    )
