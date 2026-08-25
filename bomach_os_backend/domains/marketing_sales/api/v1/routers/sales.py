"""Sales acquisition, inquiry, funnel and pipeline HTTP endpoints.

HTTP layer only: query, workflow and presentation helpers live in the domain application layers.
"""

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

from domains.marketing_sales.api.v1.schemas.sales import (
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
from domains.marketing_sales.models.sales import Lead, LeadActivity
from domains.marketing_sales.selectors.sales import (
    _activity_queryset,
    _apply_lead_filters,
    _lead_queryset,
    _lead_value_sum,
)
from domains.marketing_sales.services.funnel import (
    record_initial_funnel_event,
    record_status_funnel_event,
)
from domains.marketing_sales.services.sales import (
    _apply_activity_effects,
    _apply_lead_payload,
)
from shared.api.schema.others import MessageSchema
from system.authorization import require_permission

leads_router = Router(tags=["Marketing Leads"])


@leads_router.get("/summary", response=LeadSummarySchema)
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
            status="new", first_contact_at__isnull=True, created_at__lt=sla_threshold
        ).count(),
        "hot_leads": active.filter(score__gte=75).count(),
        "stale_leads": active.filter(
            Q(last_contact_at__lt=now - timedelta(days=12))
            | Q(last_contact_at__isnull=True, created_at__lt=now - timedelta(days=12))
        ).count(),
        "upcoming_followups": active.filter(
            next_follow_up_at__gte=now, next_follow_up_at__lte=now + timedelta(days=1)
        ).count(),
    }


@leads_router.get("", response=List[LeadOutSchema])
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


@leads_router.post("", response={201: LeadOutSchema, 400: MessageSchema})
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
                lead, from_status="new", to_status=lead.status, actor=request.user
            )
        return (201, lead)
    except ValidationError as e:
        return (400, {"detail": _validation_detail(e)})
    except Exception as e:
        return (400, {"detail": str(e)})


@leads_router.get("/pipeline")
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
    sla_breach_count = sum((1 for lead in leads if lead.is_sla_breached))
    stale_count = sum((1 for lead in leads if lead.is_stale))
    conversion_rate = round(won_count / total_leads * 100, 2) if total_leads else 0.0
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


@leads_router.get("/pipeline/{lead_id}")
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


@leads_router.get("/{lead_id}/activities", response=List[LeadActivityOutSchema])
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


@leads_router.post(
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
        return (201, activity)
    except ValidationError as e:
        return (400, {"detail": _validation_detail(e)})
    except Exception as e:
        return (400, {"detail": str(e)})


@leads_router.get("/{lead_id}/activities/{activity_id}", response=LeadActivityOutSchema)
@require_permission("leads", "view")
def get_lead_activity(request, lead_id: int, activity_id: int):
    lead = get_object_or_404(_lead_queryset(request), id=lead_id)
    return get_object_or_404(_activity_queryset(lead), id=activity_id)


@leads_router.patch(
    "/{lead_id}/activities/{activity_id}",
    response={200: LeadActivityOutSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("leads", "update")
def update_lead_activity(
    request, lead_id: int, activity_id: int, payload: LeadActivityUpdateSchema
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
        return (200, activity)
    except ValidationError as e:
        return (400, {"detail": _validation_detail(e)})
    except Exception as e:
        return (400, {"detail": str(e)})


@leads_router.delete(
    "/{lead_id}/activities/{activity_id}",
    response={200: MessageSchema, 404: MessageSchema},
)
@require_permission("leads", "delete")
def delete_lead_activity(request, lead_id: int, activity_id: int):
    lead = get_object_or_404(_lead_queryset(request), id=lead_id)
    activity = get_object_or_404(_activity_queryset(lead), id=activity_id)
    activity.delete()
    return (200, {"detail": "Lead activity deleted successfully"})


@leads_router.get("/{lead_id}", response=LeadOutSchema)
@require_permission("leads", "view")
def get_lead(request, lead_id: int):
    return get_object_or_404(_lead_queryset(request), id=lead_id)


@leads_router.patch(
    "/{lead_id}", response={200: LeadOutSchema, 400: MessageSchema, 404: MessageSchema}
)
@require_permission("leads", "update")
def update_lead(request, lead_id: int, payload: LeadUpdateSchema):
    try:
        lead = get_object_or_404(_lead_queryset(request), id=lead_id)
        return (
            200,
            _apply_lead_payload(
                lead, payload.dict(exclude_unset=True), actor=request.user
            ),
        )
    except ValidationError as e:
        return (400, {"detail": _validation_detail(e)})
    except Exception as e:
        return (400, {"detail": str(e)})


@leads_router.patch(
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
        return (200, lead)
    except ValidationError as e:
        return (400, {"detail": _validation_detail(e)})
    except Exception as e:
        return (400, {"detail": str(e)})


@leads_router.patch(
    "/{lead_id}/status",
    response={200: LeadOutSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("leads", "update")
def update_lead_status(request, lead_id: int, payload: LeadStatusSchema):
    try:
        lead = get_object_or_404(_lead_queryset(request), id=lead_id)
        previous_status = lead.status
        lead.status = payload.status
        if payload.status != "new" and (not lead.first_contact_at):
            lead.first_contact_at = timezone.now()
        if lead.first_contact_at and (not lead.first_response_at):
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
        return (200, lead)
    except ValidationError as e:
        return (400, {"detail": _validation_detail(e)})
    except Exception as e:
        return (400, {"detail": str(e)})


@leads_router.delete("/{lead_id}", response={200: MessageSchema, 404: MessageSchema})
@require_permission("leads", "delete")
def delete_lead(request, lead_id: int):
    lead = get_object_or_404(_lead_queryset(request), id=lead_id)
    lead.delete()
    return (200, {"detail": "Lead deleted successfully"})


from datetime import timedelta
from typing import List

from django.db.models import Sum
from django.utils import timezone
from ninja import Router
from ninja.pagination import LimitOffsetPagination, paginate

from domains.marketing_sales.api.v1.schemas.sales import (
    ConversionBreakdownSchema,
    DropOffAlertSchema,
    FunnelLeadListSchema,
    FunnelStageSummarySchema,
    FunnelSummarySchema,
)
from domains.marketing_sales.models.sales import FunnelLead, FunnelSnapshot, FunnelStage
from system.authorization import require_permission

funnel_router = Router(tags=["Funnel Engine"])


@funnel_router.get("/funnel/summary", response=FunnelSummarySchema)
@require_permission("leads", "view")
def get_funnel_summary(request):
    stages = FunnelStage.objects.all()
    last_month = timezone.now().date() - timedelta(days=30)
    result = []
    prev_count = None
    for stage in stages:
        current_count = FunnelLead.objects.filter(stage=stage, status="active").count()
        last_snapshot = FunnelSnapshot.objects.filter(
            stage=stage, date=last_month
        ).first()
        conversion_rate = 0.0
        if prev_count and prev_count > 0:
            conversion_rate = round(current_count / prev_count * 100, 2)
        change_pct = 0.0
        if last_snapshot and last_snapshot.count > 0:
            change_pct = round(
                (current_count - last_snapshot.count) / last_snapshot.count * 100, 2
            )
        result.append(
            FunnelStageSummarySchema(
                name=stage.name,
                display_name=stage.get_name_display(),
                reach=FunnelLead.objects.filter(stage__order__lte=stage.order).count(),
                leads=current_count,
                conversion_rate=conversion_rate,
                change_pct=change_pct,
            )
        )
        prev_count = current_count
    return {"stages": result}


@funnel_router.get("/funnel/conversion-breakdown", response=ConversionBreakdownSchema)
@require_permission("leads", "view")
def get_conversion_breakdown(request):
    stages = list(FunnelStage.objects.all().order_by("order"))
    transitions = []
    for i in range(len(stages) - 1):
        current_stage = stages[i]
        next_stage = stages[i + 1]
        current_count = FunnelLead.objects.filter(
            stage=current_stage, status__in=["active", "converted"]
        ).count()
        next_count = FunnelLead.objects.filter(
            stage=next_stage, status__in=["active", "converted"]
        ).count()
        rate = 0.0
        if current_count > 0:
            rate = round(next_count / current_count * 100, 2)
        transitions.append(
            {
                "from_stage": current_stage.get_name_display(),
                "to_stage": next_stage.get_name_display(),
                "rate": rate,
            }
        )
    return {"transitions": transitions}


@funnel_router.get("/funnel/drop-off-alerts", response=List[DropOffAlertSchema])
@require_permission("leads", "view")
def get_drop_off_alerts(request, threshold: float = 50.0):
    stages = list(FunnelStage.objects.all().order_by("order"))
    alerts = []
    for i in range(len(stages) - 1):
        current_stage = stages[i]
        next_stage = stages[i + 1]
        entered = FunnelLead.objects.filter(stage=current_stage).count()
        progressed = FunnelLead.objects.filter(stage=next_stage).count()
        if entered > 0:
            loss_pct = round((entered - progressed) / entered * 100, 2)
            if loss_pct >= threshold:
                suggestions = [
                    f"Review {current_stage.get_name_display()} touchpoints",
                    "Analyze why leads aren't progressing",
                    "Consider lead scoring improvements",
                ]
                alerts.append(
                    {
                        "stage": f"{current_stage.get_name_display()} → {next_stage.get_name_display()}",
                        "loss_pct": loss_pct,
                        "suggestions": suggestions,
                    }
                )
    return alerts


@funnel_router.get("/funnel/leads/activity-log", response=List[FunnelLeadListSchema])
@paginate(LimitOffsetPagination, page_size=20)
@require_permission("leads", "view")
def get_lead_activity_log(
    request, stage: str = None, status: str = None, search: str = None
):
    from django.db.models import Q

    leads = FunnelLead.objects.select_related(
        "stage", "assigned_role", "assigned_role__user", "branch"
    )
    if stage:
        leads = leads.filter(stage__name=stage)
    if status:
        leads = leads.filter(status=status)
    if search:
        leads = leads.filter(
            Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(email__icontains=search)
        )
    return leads.order_by("-last_activity")


from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router

from domains.marketing_sales.api.v1.schemas.sales import (
    CreateDealSchema,
    DealListSchema,
    MoveDealStageSchema,
    PipelineReportSchema,
    PipelineReportsSchema,
    PipelineStageSchema,
    PipelineSummarySchema,
    UpdateDealSchema,
)
from domains.marketing_sales.models.sales import Deal, PipelineStage
from user.models.branch import Branch
from user.models.employee import Employee
from system.authorization import require_permission

pipeline_router = Router(tags=["Sales Pipeline"])


@pipeline_router.get("/pipeline/deals", response=PipelineReportSchema)
@require_permission("leads", "view")
def get_deals(
    request,
    branch_id: int = None,
    agent_id: int = None,
    stage: str = None,
    period: int = None,
):
    deals = Deal.objects.select_related("stage", "agent", "agent__user", "branch")
    if branch_id:
        deals = deals.filter(branch_id=branch_id)
    if agent_id:
        deals = deals.filter(agent_id=agent_id)
    if stage:
        deals = deals.filter(stage__slug=stage)
    if period:
        deals = deals.filter(created_at__gte=timezone.now() - timedelta(days=period))
    total_value = deals.aggregate(total=Sum("value"))["total"] or Decimal("0")
    closed_count = deals.filter(stage__is_won=True).count()
    total_deals = deals.count()
    conversion_pct = 0.0
    if total_deals > 0:
        conversion_pct = round(closed_count / total_deals * 100, 2)
    stages_data = []
    for pipeline_stage in PipelineStage.objects.all().order_by("order"):
        stage_deals = deals.filter(stage=pipeline_stage)
        stage_value = stage_deals.aggregate(total=Sum("value"))["total"] or Decimal("0")
        stages_data.append(
            PipelineStageSchema(
                id=pipeline_stage.id,
                name=pipeline_stage.name,
                slug=pipeline_stage.slug,
                order=pipeline_stage.order,
                color=pipeline_stage.color,
                deal_count=stage_deals.count(),
                stage_value=stage_value,
                deals=list(stage_deals),
            )
        )
    return PipelineReportSchema(
        summary=PipelineSummarySchema(
            total_deals=total_deals,
            total_value=total_value,
            closed_count=closed_count,
            conversion_pct=conversion_pct,
            avg_days=14.0,
        ),
        stages=stages_data,
    )


@pipeline_router.post("/pipeline/deals", response={201: DealListSchema, 400: dict})
@require_permission("leads", "create")
def create_deal(request, payload: CreateDealSchema):
    try:
        stage = PipelineStage.objects.filter(slug="new_lead").first()
        if not stage:
            return (400, {"detail": "Default pipeline stage not found"})
        branch = None
        if payload.branch_id:
            branch = Branch.objects.get(id=payload.branch_id)
        agent = None
        if payload.agent_id:
            agent = Employee.objects.get(id=payload.agent_id)
        deal = Deal.objects.create(
            lead_name=payload.lead_name,
            property_name=payload.property_name,
            property_id=payload.property_id,
            branch=branch,
            agent=agent,
            value=payload.value,
            email=payload.email,
            phone=payload.phone,
            probability=payload.probability,
            tags=payload.tags or [],
            notes=payload.notes,
            stage=stage,
        )
        return (201, deal)
    except Branch.DoesNotExist:
        return (400, {"detail": "Branch not found"})
    except Employee.DoesNotExist:
        return (400, {"detail": "Agent not found"})
    except Exception as e:
        return (400, {"detail": str(e)})


@pipeline_router.patch(
    "/pipeline/deals/{deal_id}/stage",
    response={200: DealListSchema, 400: dict, 404: dict},
)
@require_permission("leads", "update")
def move_deal_stage(request, deal_id: int, payload: MoveDealStageSchema):
    deal = get_object_or_404(Deal, id=deal_id)
    new_stage = get_object_or_404(PipelineStage, slug=payload.stage)
    deal.stage = new_stage
    deal.save()
    if new_stage.is_won or new_stage.is_lost:
        deal.closed_at = timezone.now()
        deal.save()
    return deal


@pipeline_router.patch(
    "/pipeline/deals/{deal_id}", response={200: DealListSchema, 400: dict, 404: dict}
)
@require_permission("leads", "update")
def update_deal(request, deal_id: int, payload: UpdateDealSchema):
    deal = get_object_or_404(Deal, id=deal_id)
    update_data = payload.dict(exclude_unset=True)
    if "agent_id" in update_data:
        if update_data["agent_id"]:
            deal.agent = Employee.objects.get(id=update_data["agent_id"])
        else:
            deal.agent = None
        del update_data["agent_id"]
    for key, value in update_data.items():
        setattr(deal, key, value)
    deal.save()
    return deal


@pipeline_router.delete("/pipeline/deals/{deal_id}", response={200: dict, 404: dict})
@require_permission("leads", "delete")
def delete_deal(request, deal_id: int):
    deal = get_object_or_404(Deal, id=deal_id)
    deal.delete()
    return {"detail": "Deal deleted successfully"}


@pipeline_router.get("/pipeline/reports", response=PipelineReportsSchema)
@require_permission("dashboard", "view")
def get_pipeline_reports(request, period: int = 30):
    start_date = timezone.now() - timedelta(days=period)
    closed_deals = Deal.objects.filter(stage__is_won=True, closed_at__gte=start_date)
    total_created = Deal.objects.filter(created_at__gte=start_date).count()
    revenue = closed_deals.aggregate(total=Sum("value"))["total"] or Decimal("0")
    conversion_rate = 0.0
    if total_created > 0:
        conversion_rate = round(closed_deals.count() / total_created * 100, 2)
    return PipelineReportsSchema(
        total_closed=closed_deals.count(),
        revenue=revenue,
        conversion_rate=conversion_rate,
        period_days=period,
    )


from datetime import timedelta
from typing import List

from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router

from domains.marketing_sales.api.v1.schemas.sales import (
    AssignAgentSchema,
    CreateFollowUpSchema,
    CreateInquirySchema,
    FollowUpSchema,
    InquiryListSchema,
    InquirySummarySchema,
    UpdateFollowUpSchema,
    UpdateInquirySchema,
    UpdateInquiryStatusSchema,
)
from domains.marketing_sales.models.sales import FollowUp, Inquiry
from domains.marketing_sales.presenters import (
    _sales_activity_timeline_item as _activity_timeline_item,
)
from domains.marketing_sales.presenters import _sales_pipeline_card as _pipeline_card
from domains.marketing_sales.presenters import (
    _sales_validation_detail as _validation_detail,
)
from user.models.branch import Branch
from user.models.employee import Employee
from system.authorization import require_permission

csrc_router = Router(tags=["CSRC Dashboard"])


@csrc_router.get("/csrc/inquiries", response=InquirySummarySchema)
@require_permission("leads", "view")
def get_inquiries(
    request,
    branch_id: int = None,
    source: str = None,
    priority: str = None,
    status: str = None,
    date_from: str = None,
    date_to: str = None,
):
    inquiries = Inquiry.objects.select_related(
        "assigned_agent", "assigned_agent__user", "branch"
    )
    if branch_id:
        inquiries = inquiries.filter(branch_id=branch_id)
    if source:
        inquiries = inquiries.filter(source=source)
    if priority:
        inquiries = inquiries.filter(priority=priority)
    if status:
        inquiries = inquiries.filter(status=status)
    if date_from:
        inquiries = inquiries.filter(created_at__date__gte=date_from)
    if date_to:
        inquiries = inquiries.filter(created_at__date__lte=date_to)
    total = inquiries.count()
    new_count = inquiries.filter(status="new").count()
    pending_followups = FollowUp.objects.filter(status="pending").count()
    return InquirySummarySchema(
        total=total,
        new_count=new_count,
        pending_followups=pending_followups,
        avg_response_time=0.0,
        inquiries=inquiries[:20],
    )


@csrc_router.post("/csrc/inquiries", response={201: InquiryListSchema, 400: dict})
@require_permission("leads", "create")
def create_inquiry(request, payload: CreateInquirySchema):
    try:
        branch = None
        if payload.branch_id:
            branch = Branch.objects.get(id=payload.branch_id)
        assigned_agent = None
        if payload.assigned_agent_id:
            assigned_agent = Employee.objects.get(id=payload.assigned_agent_id)
        inquiry = Inquiry.objects.create(
            lead_name=payload.lead_name,
            email=payload.email or "",
            phone=payload.phone,
            source=payload.source,
            inquiry_type=payload.inquiry_type,
            priority=payload.priority,
            channel=payload.channel or "",
            branch=branch,
            assigned_agent=assigned_agent,
            notes=payload.notes or "",
        )
        return (201, inquiry)
    except Branch.DoesNotExist:
        return (400, {"detail": "Branch not found"})
    except Employee.DoesNotExist:
        return (400, {"detail": "Agent not found"})
    except Exception as e:
        return (400, {"detail": str(e)})


@csrc_router.patch(
    "/csrc/inquiries/{inquiry_id}",
    response={200: InquiryListSchema, 400: dict, 404: dict},
)
@require_permission("leads", "update")
def update_inquiry(request, inquiry_id: int, payload: UpdateInquirySchema):
    inquiry = get_object_or_404(Inquiry, id=inquiry_id)
    update_data = payload.dict(exclude_unset=True)
    if "assigned_agent_id" in update_data:
        if update_data["assigned_agent_id"]:
            inquiry.assigned_agent = Employee.objects.get(
                id=update_data["assigned_agent_id"]
            )
        else:
            inquiry.assigned_agent = None
        del update_data["assigned_agent_id"]
    for key, value in update_data.items():
        setattr(inquiry, key, value)
    inquiry.save()
    return inquiry


@csrc_router.post(
    "/csrc/inquiries/{inquiry_id}/assign",
    response={200: InquiryListSchema, 400: dict, 404: dict},
)
@require_permission("leads", "update")
def assign_inquiry_agent(request, inquiry_id: int, payload: AssignAgentSchema):
    inquiry = get_object_or_404(Inquiry, id=inquiry_id)
    try:
        agent = Employee.objects.get(id=payload.agent_id)
        inquiry.assigned_agent = agent
        inquiry.save()
        return inquiry
    except Employee.DoesNotExist:
        return (400, {"detail": "Agent not found"})


@csrc_router.patch(
    "/csrc/inquiries/{inquiry_id}/status",
    response={200: InquiryListSchema, 400: dict, 404: dict},
)
@require_permission("leads", "update")
def update_inquiry_status(request, inquiry_id: int, payload: UpdateInquiryStatusSchema):
    inquiry = get_object_or_404(Inquiry, id=inquiry_id)
    inquiry.status = payload.status
    if payload.status == "contacted" and (not inquiry.first_contact_at):
        inquiry.first_contact_at = timezone.now()
    if payload.status == "resolved":
        inquiry.resolved_at = timezone.now()
    inquiry.save()
    return inquiry


@csrc_router.get("/csrc/inquiries/missed", response=List[InquiryListSchema])
@require_permission("leads", "view")
def get_missed_inquiries(request):
    threshold = timezone.now() - timedelta(minutes=30)
    return Inquiry.objects.filter(
        status="new", created_at__lt=threshold, first_contact_at__isnull=True
    ).select_related("assigned_agent", "assigned_agent__user", "branch")


@csrc_router.get("/csrc/followups", response=List[FollowUpSchema])
@require_permission("leads", "view")
def get_followups(request, tab: str = "today"):
    today = timezone.now().date()
    if tab == "today":
        followups = FollowUp.objects.filter(
            schedule_type="today", scheduled_at__date=today
        )
    elif tab == "tomorrow":
        followups = FollowUp.objects.filter(
            schedule_type="tomorrow", scheduled_at__date=today + timedelta(days=1)
        )
    elif tab == "overdue":
        followups = FollowUp.objects.filter(
            status="pending", scheduled_at__lt=timezone.now()
        )
    else:
        followups = FollowUp.objects.none()
    return followups.select_related("inquiry", "agent", "agent__user")


@csrc_router.post("/csrc/followups", response={201: FollowUpSchema, 400: dict})
@require_permission("leads", "create")
def create_followup(request, payload: CreateFollowUpSchema):
    try:
        inquiry = Inquiry.objects.get(id=payload.inquiry_id)
        agent = None
        if payload.agent_id:
            agent = Employee.objects.get(id=payload.agent_id)
        followup = FollowUp.objects.create(
            inquiry=inquiry,
            agent=agent,
            action=payload.action,
            scheduled_at=payload.scheduled_at,
            schedule_type=payload.schedule_type,
            notes=payload.notes or "",
        )
        return (201, followup)
    except Inquiry.DoesNotExist:
        return (400, {"detail": "Inquiry not found"})
    except Employee.DoesNotExist:
        return (400, {"detail": "Agent not found"})
    except Exception as e:
        return (400, {"detail": str(e)})


@csrc_router.patch(
    "/csrc/followups/{followup_id}",
    response={200: FollowUpSchema, 400: dict, 404: dict},
)
@require_permission("leads", "update")
def update_followup(request, followup_id: int, payload: UpdateFollowUpSchema):
    followup = get_object_or_404(FollowUp, id=followup_id)
    update_data = payload.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(followup, key, value)
    if payload.status == "completed":
        followup.completed_at = timezone.now()
    followup.save()
    return followup
