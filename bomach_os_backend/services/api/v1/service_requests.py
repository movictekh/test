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
from services.api.schema.schemas import (
    InvoiceOut,
    QuoteClientActionIn,
    QuoteOut,
    ServiceClientExecutionTaskOut,
    ServiceDeliverableActionIn,
    ServiceDeliverableOut,
    ServiceOrderOut,
)
from services.api.schema.service_catalogue_schemas import FieldTypeOut
from services.api.schema.service_request_schemas import (
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
from services.models.payment import Invoice
from services.models.service import (
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
from finance.service import handle_payment_exception, review_payment_submission as review_submission_payment
from user.models.employee import Employee
from user.utils.perm import require_permission, scope_queryset


router = Router(tags=["Service Requests"])

CLIENT_ACTIVITY_TYPES = {"document_received", "email", "whatsapp", "internal_note"}
CLIENT_VISIBLE_QUOTE_STATUSES = {"sent", "accepted", "rejected"}
CLIENT_VISIBLE_INVOICE_STATUSES = {"sent", "viewed", "partially_paid", "paid", "overdue"}
CLIENT_VISIBLE_ORDER_STATUSES = {"pending_mobilisation", "active", "quality_review", "awaiting_client", "completed", "on_hold"}


def _validation_detail(exc):
    if hasattr(exc, "message_dict"):
        return "; ".join(
            f"{field}: {', '.join(messages)}"
            for field, messages in exc.message_dict.items()
        )
    return exc.messages[0] if getattr(exc, "messages", None) else str(exc)


def _choice_values(choices):
    return {choice[0] for choice in choices}


def _ensure_choice(value, choices, field_name):
    if value and value not in _choice_values(choices):
        raise ValidationError({field_name: f"Invalid {field_name}: {value}."})


def _choice_rows(choices):
    return [{"value": value, "label": label} for value, label in choices]


def _user_name(user):
    if not user:
        return ""
    return user.get_full_name() or user.email or user.username


def _client_name(client):
    if not client:
        return ""
    company_name = getattr(client, "company_name", "")
    return company_name or _user_name(client.user)


def _employee_name(employee):
    if not employee:
        return ""
    return _user_name(employee.user)


def _branch_name(branch):
    return branch.branch_name if branch else ""


def _request_queryset():
    return ServiceRequest.objects.select_related(
        "client",
        "client__user",
        "service",
        "service__category",
        "subservice",
        "branch",
        "owner",
        "owner__user",
        "quote",
        "service_lead",
        "crm_lead",
        "request_form",
        "pricing_config",
        "workflow",
    ).prefetch_related(
        "answers",
        "attachments",
        "activities",
        "activities__created_by",
    )


def _client_order_queryset():
    return ServiceOrder.objects.select_related(
        "client",
        "client__user",
        "service",
        "service__category",
        "quote",
        "service_request",
        "invoice",
        "created_by",
        "assigned_to",
    ).prefetch_related(
        Prefetch(
            "milestones",
            queryset=ServiceOrderMilestone.objects.filter(client_visible=True).order_by("sort_order", "id"),
            to_attr="client_visible_milestones",
        ),
        Prefetch(
            "activities",
            queryset=ServiceOrderActivity.objects.filter(visibility="internal_client").order_by("-created_at"),
            to_attr="client_visible_activities",
        ),
    )


def _client_task_queryset():
    return ServiceExecutionTask.objects.select_related(
        "order",
        "order__client",
        "milestone",
    )


def _client_deliverable_queryset():
    return ServiceDeliverable.objects.select_related(
        "order",
        "order__client",
        "milestone",
        "task",
        "owner",
        "approved_by",
        "rejected_by",
        "created_by",
    ).filter(client_visible=True)


def _serialize_answer(answer):
    return {
        "id": answer.id,
        "field_key": answer.field_key,
        "label": answer.label,
        "field_type": answer.field_type,
        "value": answer.value,
        "sort_order": answer.sort_order,
    }


def _serialize_attachment(attachment):
    return {
        "id": attachment.id,
        "field_key": attachment.field_key,
        "label": attachment.label,
        "file_name": attachment.file_name,
        "file_url": attachment.file_url,
        "content_type": attachment.content_type,
        "file_size_bytes": attachment.file_size_bytes,
        "uploaded_by_id": attachment.uploaded_by_id,
        "created_at": attachment.created_at,
    }


def _serialize_activity(activity):
    return {
        "id": activity.id,
        "activity_type": activity.activity_type,
        "activity_type_display": activity.get_activity_type_display(),
        "outcome": activity.outcome,
        "outcome_display": activity.get_outcome_display(),
        "note": activity.note,
        "next_action": activity.next_action,
        "next_follow_up_at": activity.next_follow_up_at,
        "created_by_id": activity.created_by_id,
        "created_by_name": _user_name(activity.created_by),
        "created_at": activity.created_at,
    }


def _serialize_request(obj, include_detail=False):
    row = {
        "id": obj.id,
        "request_number": obj.request_number,
        "client_id": obj.client_id,
        "client_name": _client_name(obj.client),
        "service_id": obj.service_id,
        "service_name": obj.service.name if obj.service else "",
        "subservice_id": obj.subservice_id,
        "subservice_name": obj.subservice.name if obj.subservice else "",
        "branch_id": obj.branch_id,
        "branch_name": _branch_name(obj.branch),
        "quote_id": obj.quote_id,
        "quote_number": obj.quote.quote_number if obj.quote else "",
        "contact_name": obj.contact_name,
        "contact_phone": obj.contact_phone,
        "contact_email": obj.contact_email,
        "customer_type": obj.customer_type,
        "source": obj.source,
        "source_reference": obj.source_reference,
        "status": obj.status,
        "status_display": obj.get_status_display(),
        "priority": obj.priority,
        "budget": obj.budget,
        "estimated_value": obj.estimated_value,
        "preferred_date": obj.preferred_date,
        "due_date": obj.due_date,
        "next_action": obj.next_action,
        "scope_summary": obj.scope_summary,
        "owner_id": obj.owner_id,
        "owner_name": _employee_name(obj.owner),
        "created_at": obj.created_at,
        "updated_at": obj.updated_at,
    }
    if include_detail:
        row.update({
            "service_lead_id": obj.service_lead_id,
            "crm_lead_id": obj.crm_lead_id,
            "request_form_id": obj.request_form_id,
            "request_form_version": obj.request_form_version,
            "pricing_config_id": obj.pricing_config_id,
            "pricing_config_version": obj.pricing_config_version,
            "workflow_id": obj.workflow_id,
            "workflow_version": obj.workflow_version,
            "answers_snapshot": obj.answers_snapshot,
            "form_snapshot": obj.form_snapshot,
            "answers": [_serialize_answer(answer) for answer in obj.answers.all()],
            "attachments": [_serialize_attachment(attachment) for attachment in obj.attachments.all()],
            "activities": [_serialize_activity(activity) for activity in obj.activities.all()],
        })
    return row


def _serialize_request_field(field):
    return {
        "id": field.id,
        "form_id": field.form_id,
        "key": field.key,
        "label": field.label,
        "field_type": field.field_type,
        "required": field.required,
        "options": field.options,
        "validation": field.validation,
        "help_text": field.help_text,
        "placeholder": field.placeholder,
        "sort_order": field.sort_order,
    }


def _serialize_request_form(form):
    return {
        "id": form.id,
        "service_id": form.service_id,
        "name": form.name,
        "version": form.version,
        "status": form.status,
        "is_active": form.is_active,
        "fields": [_serialize_request_field(field) for field in form.fields.all()],
    }


def _create_answer_rows(service_request):
    field_rows = service_request.form_snapshot.get("fields", [])
    rows = [
        ServiceRequestAnswer(
            request=service_request,
            field_id=field.get("id"),
            field_key=field["key"],
            label=field["label"],
            field_type=field["field_type"],
            value=service_request.answers_snapshot.get(field["key"]),
            sort_order=field.get("sort_order", 0),
        )
        for field in field_rows
    ]
    ServiceRequestAnswer.objects.bulk_create(rows)


def _log_activity(service_request, activity_type, note, created_by=None, outcome="not_applicable", next_action=""):
    _ensure_choice(activity_type, ServiceRequestActivity.ACTIVITY_TYPE_CHOICES, "activity_type")
    _ensure_choice(outcome, ServiceRequestActivity.OUTCOME_CHOICES, "outcome")
    activity = ServiceRequestActivity.objects.create(
        request=service_request,
        activity_type=activity_type,
        outcome=outcome,
        note=note,
        next_action=next_action or "",
        created_by=created_by,
    )
    return activity


def _quote_queryset():
    return Quote.objects.select_related(
        "client",
        "client__user",
        "service",
        "service__category",
        "service_request",
        "previous_quote",
        "required_approver_role",
        "approved_by",
        "created_by",
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
    ).prefetch_related("items", "payments", "submissions")


def _latest_rejected_quote(service_request):
    return (
        service_request.quotes
        .filter(status="rejected")
        .order_by("-version", "-created_at", "-id")
        .first()
    )


def _ensure_no_active_quote(service_request):
    if service_request.quotes.exclude(status__in=["rejected", "expired"]).exists():
        raise ValidationError("This service request already has an active quote.")


def _quote_payload_data(payload, service_request):
    data = payload.dict(exclude_unset=True)
    if not data.get("required_approver_role_id"):
        raise ValidationError({"required_approver_role_id": "Required approver role is required."})
    service_fee = data.get("service_fee")
    amount = data.get("amount")
    if service_fee is None:
        data["service_fee"] = amount if amount is not None else service_request.estimated_value
    data["amount"] = Decimal("0.00")
    data["description"] = data.get("description") or service_request.scope_summary or service_request.service.name
    data["scope_summary"] = data.get("scope_summary") or service_request.scope_summary
    data["terms"] = data.get("terms") or "Work begins after the required mobilisation payment and approved documents are received."
    data["valid_until"] = data.get("valid_until") or (timezone.localdate() + timedelta(days=14))
    data["status"] = "awaiting_approval"
    return data


def _get_client_profile(user):
    try:
        return user.client_profile
    except Exception:
        raise HttpError(400, "Client profile not found for this user.")


def _get_staff_object_or_404(request, request_id):
    obj = get_object_or_404(_request_queryset(), id=request_id)
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if branch_ids and obj.branch_id not in branch_ids:
        raise HttpError(403, "You do not have permission to access this service request.")
    return obj


def _apply_filters(qs, status=None, priority=None, service_id=None, branch_id=None,
                   owner_id=None, client_id=None, source=None, date_from=None,
                   date_to=None, due_from=None, due_to=None, search=None):
    if status:
        qs = qs.filter(status=status)
    if priority:
        qs = qs.filter(priority=priority)
    if service_id:
        qs = qs.filter(service_id=service_id)
    if branch_id:
        qs = qs.filter(branch_id=branch_id)
    if owner_id:
        qs = qs.filter(owner_id=owner_id)
    if client_id:
        qs = qs.filter(client_id=client_id)
    if source:
        qs = qs.filter(source=source)
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)
    if due_from:
        qs = qs.filter(due_date__gte=due_from)
    if due_to:
        qs = qs.filter(due_date__lte=due_to)
    if search:
        qs = qs.filter(
            Q(request_number__icontains=search)
            | Q(client__user__first_name__icontains=search)
            | Q(client__user__last_name__icontains=search)
            | Q(client__user__email__icontains=search)
            | Q(client__company_name__icontains=search)
            | Q(service__name__icontains=search)
            | Q(contact_name__icontains=search)
            | Q(contact_phone__icontains=search)
            | Q(contact_email__icontains=search)
            | Q(source_reference__icontains=search)
        )
    return qs


def _create_service_request(payload, client, created_by, submitted_by=None, staff=False):
    data = payload.dict()
    answers = data.pop("answers")
    relation_ids = {
        "subservice_id": data.pop("subservice_id", None),
        "branch_id": data.pop("branch_id", None),
        "service_lead_id": data.pop("service_lead_id", None) if staff else None,
        "crm_lead_id": data.pop("crm_lead_id", None) if staff else None,
        "owner_id": data.pop("owner_id", None) if staff else None,
    }
    data.pop("client_id", None)
    service_id = data.pop("service_id")
    service = get_object_or_404(Service, id=service_id)
    subservice = None
    if relation_ids["subservice_id"]:
        subservice = get_object_or_404(ServiceSubService, id=relation_ids["subservice_id"], service=service)

    with transaction.atomic():
        obj = ServiceRequest.objects.create(
            client=client,
            service=service,
            subservice=subservice,
            answers_snapshot=answers,
            created_by=created_by,
            submitted_by=submitted_by,
            **{key: value for key, value in relation_ids.items() if key != "subservice_id"},
            **data,
        )
        _create_answer_rows(obj)
        _log_activity(
            obj,
            "request_created",
            "Service request submitted and consent recorded.",
            created_by=created_by,
        )
    return _request_queryset().get(id=obj.id)


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


# Deprecated compatibility endpoints. These remain until payment submission
# moves under the invoice/payment routers.
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
        client = _get_client_profile(request.user)
        invoice = get_object_or_404(
            _invoice_queryset(),
            id=invoice_id,
            client=client,
            status__in=CLIENT_VISIBLE_INVOICE_STATUSES,
        )
        if payload.invoice_id != invoice.id:
            return 400, {"detail": "Payload invoice_id must match the invoice path."}
        if payload.amount > invoice.balance:
            return 400, {"detail": "Amount exceeds outstanding balance."}
        if PaymentSubmission.objects.filter(invoice=invoice, client=client, status=PaymentSubmission.STATUS.PENDING).exists():
            return 400, {"detail": "You already have a pending submission for this invoice."}
        submission = PaymentSubmission.objects.create(
            invoice=invoice,
            client=client,
            submitted_by=request.user,
            submitted_by_type=PaymentSubmission.SUBMITTED_BY_TYPE.CLIENT,
            **payload.dict(exclude={"invoice_id"}),
        )
        _log_activity(
            invoice.service_request,
            "payment_submitted",
            f"Payment proof {submission.reference} submitted for invoice {invoice.invoice_number}.",
            created_by=request.user,
            next_action="Review payment submission",
        )
        return 201, submission
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


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
        client = _get_client_profile(request.user)
        with transaction.atomic():
            quote = get_object_or_404(
                _quote_queryset().select_for_update(),
                id=quote_id,
                client=client,
                status__in=CLIENT_VISIBLE_QUOTE_STATUSES,
            )
            if quote.status != "sent":
                return 400, {"detail": "Only sent quotes can be accepted."}
            quote.status = "accepted"
            quote.client_responded_at = timezone.now()
            quote.save(update_fields=["status", "client_responded_at", "updated_at"])
            if quote.service_request:
                quote.service_request.next_action = "Create invoice for accepted quotation"
                quote.service_request.save(update_fields=["next_action", "updated_at"])
                _log_activity(
                    quote.service_request,
                    "quote_accepted",
                    f"Client accepted quotation {quote.quote_number}.",
                    created_by=request.user,
                    next_action="Create invoice",
                )
        return 200, _quote_queryset().get(id=quote.id)
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


@router.post("/quotes/{quote_id}/reject", response={200: QuoteOut, 400: MessageSchema, 404: MessageSchema})
def reject_my_quote(request, quote_id: int, payload: QuoteClientActionIn):
    try:
        client = _get_client_profile(request.user)
        with transaction.atomic():
            quote = get_object_or_404(
                _quote_queryset().select_for_update(),
                id=quote_id,
                client=client,
                status__in=CLIENT_VISIBLE_QUOTE_STATUSES,
            )
            if quote.status != "sent":
                return 400, {"detail": "Only sent quotes can be rejected."}
            quote.status = "rejected"
            quote.client_rejection_reason = payload.reason or ""
            quote.client_responded_at = timezone.now()
            quote.save(update_fields=["status", "client_rejection_reason", "client_responded_at", "updated_at"])
            if quote.service_request:
                quote.service_request.status = "under_review"
                quote.service_request.next_action = "Prepare revised quotation"
                quote.service_request.save(update_fields=["status", "next_action", "updated_at"])
                _log_activity(
                    quote.service_request,
                    "quote_rejected",
                    f"Client rejected quotation {quote.quote_number}.",
                    created_by=request.user,
                    next_action="Prepare revised quote",
                )
        return 200, _quote_queryset().get(id=quote.id)
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


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
