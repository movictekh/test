"""Private support for Service Request v1 HTTP routers.

Shared API-layer query, validation and serialization helpers.
This module defines no HTTP endpoints.
"""

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
