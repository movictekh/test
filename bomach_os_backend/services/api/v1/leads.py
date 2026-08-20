from datetime import date, timedelta
from decimal import Decimal
from typing import List

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router
from ninja.pagination import LimitOffsetPagination, paginate

from services.api.schema.crm_schemas import (
    LeadActivityCreateSchema,
    LeadActivityOutSchema,
    LeadActivityUpdateSchema,
    LeadAssignSchema,
    LeadCreateSchema,
    LeadOutSchema,
    LeadStatusSchema,
    LeadSummarySchema,
    LeadUpdateSchema,
)
from services.api.schema.others import MessageSchema
from services.funnel_events import (
    record_initial_funnel_event,
    record_status_funnel_event,
)
from services.models.crm import Lead, LeadActivity
from user.utils.perm import require_permission, scope_queryset

router = Router(tags=["Marketing Leads"])


def _validation_detail(exc):
    if hasattr(exc, "message_dict"):
        return "; ".join(
            f"{field}: {', '.join(messages)}"
            for field, messages in exc.message_dict.items()
        )
    return exc.messages[0] if getattr(exc, "messages", None) else str(exc)


def _lead_queryset(request):
    leads = Lead.objects.select_related(
        "campaign",
        "referral_partner",
        "branch",
        "assigned_to",
        "assigned_to__user",
        "created_by",
    )
    return scope_queryset(request, leads, branch_field="branch_id")


def _apply_lead_payload(lead, payload_data, actor=None):
    previous_status = lead.status
    for attr, value in payload_data.items():
        setattr(lead, attr, value)

    if lead.status != "new" and not lead.first_contact_at:
        lead.first_contact_at = timezone.now()
    if lead.first_contact_at and not lead.first_response_at:
        lead.first_response_at = lead.first_contact_at

    lead.refresh_sla_status()
    lead.refresh_score()
    lead.full_clean()
    lead.save()
    if "status" in payload_data and previous_status != lead.status:
        record_status_funnel_event(
            lead,
            from_status=previous_status,
            to_status=lead.status,
            actor=actor,
        )
    return lead


def _activity_queryset(lead):
    return lead.activities.select_related("created_by")


def _apply_lead_filters(
    leads,
    status=None,
    division=None,
    source=None,
    campaign_id=None,
    assigned_to_id=None,
    branch_id=None,
    priority=None,
    sla=None,
    search=None,
    date_from=None,
    date_to=None,
):
    now = timezone.now()

    if status:
        leads = leads.filter(status=status)
    if division:
        leads = leads.filter(division=division)
    if source:
        leads = leads.filter(source=source)
    if campaign_id:
        leads = leads.filter(campaign_id=campaign_id)
    if assigned_to_id:
        leads = leads.filter(assigned_to_id=assigned_to_id)
    if branch_id:
        leads = leads.filter(branch_id=branch_id)
    if priority == "hot":
        leads = leads.filter(score__gte=75)
    elif priority == "warm":
        leads = leads.filter(score__gte=50, score__lt=75)
    elif priority == "nurture":
        leads = leads.filter(score__lt=50)
    if sla == "breach":
        leads = leads.filter(
            status="new",
            first_contact_at__isnull=True,
            created_at__lt=now - timedelta(minutes=30),
        )
    elif sla == "safe":
        leads = leads.exclude(
            status="new",
            first_contact_at__isnull=True,
            created_at__lt=now - timedelta(minutes=30),
        )
    if search:
        leads = leads.filter(
            Q(full_name__icontains=search)
            | Q(phone__icontains=search)
            | Q(email__icontains=search)
            | Q(source__icontains=search)
            | Q(division__icontains=search)
            | Q(notes__icontains=search)
        )
    if date_from:
        leads = leads.filter(created_at__date__gte=date_from)
    if date_to:
        leads = leads.filter(created_at__date__lte=date_to)
    return leads


def _lead_value_sum(leads):
    total = leads.aggregate(total=Sum("estimated_value"))["total"] or Decimal("0.00")
    return total.quantize(Decimal("0.01"))


def _pipeline_card(lead):
    return {
        "id": lead.id,
        "lead": lead.full_name,
        "division": lead.division,
        "division_label": lead.get_division_display(),
        "source": lead.source,
        "source_label": lead.get_source_display(),
        "referral_partner_id": lead.referral_partner_id,
        "referral_partner_name": (
            lead.referral_partner.name if lead.referral_partner else None
        ),
        "status": lead.status,
        "status_label": lead.get_status_display(),
        "estimated_value": lead.estimated_value,
        "priority": lead.priority,
        "sla_status": lead.sla_status,
        "is_sla_breached": lead.is_sla_breached,
        "is_stale": lead.is_stale,
        "owner": (
            lead.assigned_to.user.get_full_name() if lead.assigned_to else "Unassigned"
        ),
        "next_action": lead.next_action,
        "next_follow_up_at": lead.next_follow_up_at,
        "created_at": lead.created_at,
        "updated_at": lead.updated_at,
    }


def _activity_timeline_item(activity):
    return {
        "id": activity.id,
        "sequence": activity.sequence,
        "activity_type": activity.activity_type,
        "activity_type_display": activity.get_activity_type_display(),
        "outcome": activity.outcome,
        "outcome_display": activity.get_outcome_display(),
        "note": activity.note,
        "from_status": activity.from_status,
        "to_status": activity.to_status,
        "next_action": activity.next_action,
        "next_follow_up_at": activity.next_follow_up_at,
        "created_by": (
            activity.created_by.get_full_name() if activity.created_by else None
        ),
        "created_at": activity.created_at,
    }


def _apply_activity_effects(lead, payload_data):
    update_fields = []
    to_status = payload_data.get("to_status")

    if payload_data.get("next_action"):
        lead.next_action = payload_data["next_action"]
        update_fields.append("next_action")
    if payload_data.get("next_follow_up_at"):
        lead.next_follow_up_at = payload_data["next_follow_up_at"]
        update_fields.append("next_follow_up_at")
    if to_status:
        lead.status = to_status
        update_fields.append("status")

    is_contact_activity = payload_data.get("activity_type") != "internal_note"
    if (to_status and to_status != "new") or is_contact_activity:
        if not lead.first_contact_at:
            lead.first_contact_at = timezone.now()
            update_fields.append("first_contact_at")
        if not lead.first_response_at:
            lead.first_response_at = lead.first_contact_at or timezone.now()
            update_fields.append("first_response_at")

    if (
        to_status in ["contacted", "qualified", "proposal_sent", "negotiation"]
        or is_contact_activity
    ):
        lead.last_contact_at = timezone.now()
        update_fields.append("last_contact_at")

    if update_fields:
        lead.refresh_sla_status()
        lead.refresh_score()
        update_fields.extend(["sla_status", "score", "score_breakdown"])
        update_fields.append("updated_at")
        lead.full_clean()
        lead.save(update_fields=list(dict.fromkeys(update_fields)))


@router.get("/summary", response=LeadSummarySchema)
@require_permission("leads", "view")
def get_lead_summary(request):
    leads = _lead_queryset(request)
    now = timezone.now()
    active = leads.filter(status__in=Lead.ACTIVE_STATUSES)
    sla_threshold = now - timedelta(minutes=30)

    return {
        "total": leads.count(),
        "active": active.count(),
        "new_uncontacted": leads.filter(
            status="new", first_contact_at__isnull=True
        ).count(),
        "sla_breaches": leads.filter(
            status="new",
            first_contact_at__isnull=True,
            created_at__lt=sla_threshold,
        ).count(),
        "hot_leads": active.filter(score__gte=75).count(),
        "stale_leads": active.filter(
            Q(last_contact_at__lt=now - timedelta(days=12))
            | Q(last_contact_at__isnull=True, created_at__lt=now - timedelta(days=12))
        ).count(),
        "upcoming_followups": active.filter(
            next_follow_up_at__gte=now,
            next_follow_up_at__lte=now + timedelta(days=1),
        ).count(),
    }


@router.get("", response=List[LeadOutSchema])
@paginate(LimitOffsetPagination, page_size=20)
@require_permission("leads", "list")
def list_leads(
    request,
    status: str = None,
    division: str = None,
    source: str = None,
    campaign_id: int = None,
    assigned_to_id: int = None,
    branch_id: int = None,
    priority: str = None,
    sla: str = None,
    search: str = None,
    date_from: date = None,
    date_to: date = None,
):
    leads = _lead_queryset(request)
    leads = _apply_lead_filters(
        leads,
        status=status,
        division=division,
        source=source,
        campaign_id=campaign_id,
        assigned_to_id=assigned_to_id,
        branch_id=branch_id,
        priority=priority,
        sla=sla,
        search=search,
        date_from=date_from,
        date_to=date_to,
    )

    return leads.order_by("-created_at")


@router.post("", response={201: LeadOutSchema, 400: MessageSchema})
@require_permission("leads", "create")
def create_lead(request, payload: LeadCreateSchema):
    try:
        payload_data = payload.dict()
        payload_data["tags"] = payload_data.get("tags") or []
        lead = Lead(created_by=request.user, **payload_data)
        lead.full_clean()
        lead.save()
        lead.set_default_first_response_due()
        lead.refresh_sla_status()
        lead.refresh_score()
        lead.full_clean()
        lead.save(
            update_fields=[
                "first_response_due_at",
                "sla_status",
                "score",
                "score_breakdown",
                "updated_at",
            ]
        )
        record_initial_funnel_event(lead, actor=request.user)
        if lead.status not in ["new", "contacted"]:
            record_status_funnel_event(
                lead,
                from_status="new",
                to_status=lead.status,
                actor=request.user,
            )
        return 201, lead
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get("/pipeline")
@require_permission("leads", "list")
def get_pipeline(
    request,
    division: str = None,
    assigned_to_id: int = None,
    branch_id: int = None,
    search: str = None,
    priority: str = None,
    sla: str = None,
    date_from: date = None,
    date_to: date = None,
):
    leads = _apply_lead_filters(
        _lead_queryset(request),
        division=division,
        assigned_to_id=assigned_to_id,
        branch_id=branch_id,
        search=search,
        priority=priority,
        sla=sla,
        date_from=date_from,
        date_to=date_to,
    )
    stage_order = [
        "new",
        "contacted",
        "qualified",
        "proposal_sent",
        "negotiation",
        "won",
        "lost",
    ]
    stage_labels = dict(Lead.STATUS_CHOICES)

    columns = []
    for status in stage_order:
        stage_leads = leads.filter(status=status)
        cards = [
            _pipeline_card(lead)
            for lead in stage_leads.order_by(
                "-score", "next_follow_up_at", "-created_at"
            )
        ]
        columns.append(
            {
                "status": status,
                "label": stage_labels.get(status, status),
                "count": stage_leads.count(),
                "total_estimated_value": _lead_value_sum(stage_leads),
                "cards": cards,
            }
        )

    total_leads = leads.count()
    won_count = leads.filter(status="won").count()
    active_leads = leads.filter(status__in=Lead.ACTIVE_STATUSES)
    sla_breach_count = sum(1 for lead in leads if lead.is_sla_breached)
    stale_count = sum(1 for lead in leads if lead.is_stale)
    conversion_rate = round((won_count / total_leads) * 100, 2) if total_leads else 0.0

    return {
        "filters": {
            "division": division,
            "assigned_to_id": assigned_to_id,
            "branch_id": branch_id,
            "search": search,
            "priority": priority,
            "sla": sla,
            "date_from": date_from,
            "date_to": date_to,
        },
        "summary": {
            "total_leads": total_leads,
            "overdue_count": sla_breach_count,
            "sla_breach_count": sla_breach_count,
            "stale_count": stale_count,
            "active_pipeline_value": _lead_value_sum(active_leads),
            "won_count": won_count,
            "conversion_rate": conversion_rate,
        },
        "columns": columns,
    }


@router.get("/pipeline/{lead_id}")
@require_permission("leads", "view")
def get_pipeline_lead_detail(request, lead_id: int):
    lead = get_object_or_404(_lead_queryset(request), id=lead_id)
    return {
        "lead": {
            "id": lead.id,
            "full_name": lead.full_name,
            "phone": lead.phone,
            "email": lead.email,
            "division": lead.division,
            "division_label": lead.get_division_display(),
            "source": lead.source,
            "source_label": lead.get_source_display(),
            "campaign_id": lead.campaign_id,
            "campaign_name": lead.campaign.name if lead.campaign else None,
            "referral_partner_id": lead.referral_partner_id,
            "referral_partner_name": (
                lead.referral_partner.name if lead.referral_partner else None
            ),
            "branch_id": lead.branch_id,
            "branch_name": lead.branch.branch_name if lead.branch else None,
            "assigned_to_id": lead.assigned_to_id,
            "assigned_to_name": (
                lead.assigned_to.user.get_full_name() if lead.assigned_to else None
            ),
            "budget_range": lead.budget_range,
            "estimated_value": lead.estimated_value,
            "notes": lead.notes,
            "tags": lead.tags,
            "status": lead.status,
            "status_label": lead.get_status_display(),
            "score": lead.score,
            "priority": lead.priority,
            "sla_status": lead.sla_status,
            "is_sla_breached": lead.is_sla_breached,
            "is_stale": lead.is_stale,
            "first_contact_at": lead.first_contact_at,
            "last_contact_at": lead.last_contact_at,
            "first_response_due_at": lead.first_response_due_at,
            "first_response_at": lead.first_response_at,
            "next_follow_up_at": lead.next_follow_up_at,
            "next_action": lead.next_action,
            "created_at": lead.created_at,
            "updated_at": lead.updated_at,
        },
        "activity_timeline": [
            _activity_timeline_item(activity)
            for activity in _activity_queryset(lead).order_by("-sequence")
        ],
    }


@router.get("/{lead_id}/activities", response=List[LeadActivityOutSchema])
@paginate(LimitOffsetPagination, page_size=20)
@require_permission("leads", "view")
def list_lead_activities(
    request,
    lead_id: int,
    activity_type: str = None,
    outcome: str = None,
    created_by_id: int = None,
    date_from: date = None,
    date_to: date = None,
):
    lead = get_object_or_404(_lead_queryset(request), id=lead_id)
    activities = _activity_queryset(lead)

    if activity_type:
        activities = activities.filter(activity_type=activity_type)
    if outcome:
        activities = activities.filter(outcome=outcome)
    if created_by_id:
        activities = activities.filter(created_by_id=created_by_id)
    if date_from:
        activities = activities.filter(created_at__date__gte=date_from)
    if date_to:
        activities = activities.filter(created_at__date__lte=date_to)

    return activities.order_by("-sequence")


@router.post(
    "/{lead_id}/activities",
    response={201: LeadActivityOutSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("leads", "create")
def create_lead_activity(request, lead_id: int, payload: LeadActivityCreateSchema):
    try:
        lead = get_object_or_404(_lead_queryset(request), id=lead_id)
        payload_data = payload.dict()
        payload_data["outcome"] = payload_data.get("outcome") or ""
        payload_data["next_action"] = payload_data.get("next_action") or ""
        payload_data["to_status"] = payload_data.get("to_status") or ""
        from_status = lead.status if payload_data["to_status"] else ""

        with transaction.atomic():
            activity = LeadActivity.create_for_lead(
                lead_id=lead.id,
                created_by=request.user,
                from_status=from_status,
                **payload_data,
            )
            _apply_activity_effects(lead, payload_data)
            if payload_data["to_status"]:
                record_status_funnel_event(
                    lead,
                    from_status=from_status,
                    to_status=payload_data["to_status"],
                    actor=request.user,
                    occurred_at=activity.created_at,
                    metadata={"activity_id": activity.id},
                )
        return 201, activity
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get("/{lead_id}/activities/{activity_id}", response=LeadActivityOutSchema)
@require_permission("leads", "view")
def get_lead_activity(request, lead_id: int, activity_id: int):
    lead = get_object_or_404(_lead_queryset(request), id=lead_id)
    return get_object_or_404(_activity_queryset(lead), id=activity_id)


@router.patch(
    "/{lead_id}/activities/{activity_id}",
    response={200: LeadActivityOutSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("leads", "update")
def update_lead_activity(
    request,
    lead_id: int,
    activity_id: int,
    payload: LeadActivityUpdateSchema,
):
    try:
        lead = get_object_or_404(_lead_queryset(request), id=lead_id)
        activity = get_object_or_404(_activity_queryset(lead), id=activity_id)

        for attr, value in payload.dict(exclude_unset=True).items():
            if attr in ["outcome", "next_action", "from_status", "to_status"]:
                value = value or ""
            setattr(activity, attr, value)

        activity.full_clean()
        activity.save()
        return 200, activity
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.delete(
    "/{lead_id}/activities/{activity_id}",
    response={200: MessageSchema, 404: MessageSchema},
)
@require_permission("leads", "delete")
def delete_lead_activity(request, lead_id: int, activity_id: int):
    lead = get_object_or_404(_lead_queryset(request), id=lead_id)
    activity = get_object_or_404(_activity_queryset(lead), id=activity_id)
    activity.delete()
    return 200, {"detail": "Lead activity deleted successfully"}


@router.get("/{lead_id}", response=LeadOutSchema)
@require_permission("leads", "view")
def get_lead(request, lead_id: int):
    return get_object_or_404(_lead_queryset(request), id=lead_id)


@router.patch(
    "/{lead_id}", response={200: LeadOutSchema, 400: MessageSchema, 404: MessageSchema}
)
@require_permission("leads", "update")
def update_lead(request, lead_id: int, payload: LeadUpdateSchema):
    try:
        lead = get_object_or_404(_lead_queryset(request), id=lead_id)
        return 200, _apply_lead_payload(
            lead, payload.dict(exclude_unset=True), actor=request.user
        )
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.patch(
    "/{lead_id}/assign",
    response={200: LeadOutSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("leads", "update")
def assign_lead(request, lead_id: int, payload: LeadAssignSchema):
    try:
        lead = get_object_or_404(_lead_queryset(request), id=lead_id)
        lead.assigned_to_id = payload.assigned_to_id
        lead.full_clean()
        lead.save(update_fields=["assigned_to", "updated_at"])
        return 200, lead
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.patch(
    "/{lead_id}/status",
    response={200: LeadOutSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("leads", "update")
def update_lead_status(request, lead_id: int, payload: LeadStatusSchema):
    try:
        lead = get_object_or_404(_lead_queryset(request), id=lead_id)
        previous_status = lead.status
        lead.status = payload.status

        if payload.status != "new" and not lead.first_contact_at:
            lead.first_contact_at = timezone.now()
        if lead.first_contact_at and not lead.first_response_at:
            lead.first_response_at = lead.first_contact_at
        if payload.status in ["contacted", "qualified", "proposal_sent", "negotiation"]:
            lead.last_contact_at = timezone.now()

        lead.refresh_sla_status()
        lead.refresh_score()
        lead.full_clean()
        lead.save()
        if previous_status != lead.status:
            record_status_funnel_event(
                lead,
                from_status=previous_status,
                to_status=lead.status,
                actor=request.user,
            )
        return 200, lead
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.delete("/{lead_id}", response={200: MessageSchema, 404: MessageSchema})
@require_permission("leads", "delete")
def delete_lead(request, lead_id: int):
    lead = get_object_or_404(_lead_queryset(request), id=lead_id)
    lead.delete()
    return 200, {"detail": "Lead deleted successfully"}
