import csv
from datetime import date
from decimal import Decimal
from io import StringIO
from typing import List

from django.core.exceptions import ValidationError
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router
from ninja.pagination import LimitOffsetPagination, paginate

from services.api.schema.marketing_campaign_schemas import (
    CampaignAssetIn,
    CampaignAssetUpdate,
    CampaignDecisionIn,
    CampaignExpenseIn,
    CampaignPostAnalysisIn,
    CampaignRequestConvertIn,
    CampaignRequestIn,
    CampaignRequestUpdate,
    CampaignRiskIn,
    CampaignRiskUpdate,
    CampaignTaskIn,
    CampaignTaskUpdate,
    CampaignUpdateIn,
    MarketingCampaignIn,
    MarketingCampaignOut,
    MarketingCampaignUpdate,
)
from services.api.schema.others import MessageSchema
from services.models.crm import FUNNEL_STAGE_ORDER, Lead, LeadFunnelEvent
from services.models.marketing_campaign import (
    CampaignAsset,
    CampaignDecision,
    CampaignExpense,
    CampaignPostAnalysis,
    CampaignRequest,
    CampaignRisk,
    CampaignTask,
    CampaignUpdate,
    MarketingCampaign,
)
from user.models.branch import Branch
from user.models.employee import Employee
from user.utils.perm import require_permission, scope_queryset


router = Router(tags=["Marketing Campaigns"])


def _validation_detail(exc):
    if hasattr(exc, "message_dict"):
        return "; ".join(
            f"{field}: {', '.join(messages)}"
            for field, messages in exc.message_dict.items()
        )
    return exc.messages[0] if getattr(exc, "messages", None) else str(exc)


def _period_bounds(period_start=None, period_end=None):
    today = timezone.localdate()
    start = period_start or today.replace(day=1)
    end = period_end or today
    if start > end:
        start, end = end, start
    return start, end


def _decimal_sum(qs, field):
    return qs.aggregate(total=Sum(field))["total"] or Decimal("0.00")


def _pct(numerator, denominator):
    if not denominator:
        return 0.0
    return round((float(numerator) / float(denominator)) * 100, 1)


def _money_ratio(numerator, denominator):
    if not denominator:
        return Decimal("0.00")
    return (Decimal(numerator) / Decimal(denominator)).quantize(Decimal("0.01"))


def _campaign_queryset(request):
    return scope_queryset(
        request,
        MarketingCampaign.objects.all(),
    )


def _lead_queryset(request):
    return scope_queryset(
        request,
        Lead.objects.select_related("campaign", "branch", "assigned_to", "assigned_to__user"),
        branch_field="branch_id",
    )


def _employee_name(employee):
    if not employee:
        return ""
    full_name = employee.user.get_full_name()
    return full_name or employee.user.email or employee.user.username


def _campaign_base(campaign):
    return {
        "id": campaign.id,
        "name": campaign.name,
        "description": campaign.description,
        "status": campaign.status,
        "channel": campaign.channel,
        "impressions": campaign.impressions,
        "ctr": campaign.ctr,
        "roi": campaign.roi,
        "clicks": campaign.clicks,
        "budget_allocated": campaign.budget_allocated,
        "budget_spent": campaign.budget_spent,
        "budget_remaining": campaign.budget_remaining,
        "budget_utilization_percentage": float(campaign.budget_utilization_percentage),
        "is_over_budget": campaign.is_over_budget,
        "start_date": campaign.start_date,
        "end_date": campaign.end_date,
        "created_at": campaign.created_at,
        "updated_at": campaign.updated_at,
    }


def _campaign_metrics(campaign, leads, period_start, period_end):
    period_leads = leads.filter(
        campaign_id=campaign.id,
        created_at__date__gte=period_start,
        created_at__date__lte=period_end,
    )
    all_period_count = period_leads.count()
    qualified_count = period_leads.filter(
        status__in=["qualified", "proposal_sent", "negotiation", "won"]
    ).count()
    won_leads = period_leads.filter(status="won")
    won_count = won_leads.count()
    pipeline_leads = period_leads.filter(status__in=Lead.ACTIVE_STATUSES)
    pipeline_value = _decimal_sum(pipeline_leads, "estimated_value")
    won_revenue = _decimal_sum(won_leads, "estimated_value")
    total_spend = campaign.budget_spent
    days_left = None
    today = timezone.localdate()
    if campaign.end_date:
        days_left = max((campaign.end_date - today).days, 0)

    return {
        "lead_count": all_period_count,
        "qualified_count": qualified_count,
        "won_count": won_count,
        "pipeline_value": pipeline_value,
        "estimated_won_revenue": won_revenue,
        "cpl": _money_ratio(total_spend, all_period_count),
        "qualified_rate": _pct(qualified_count, all_period_count),
        "conversion_rate": _pct(won_count, all_period_count),
        "estimated_roas": _money_ratio(won_revenue, total_spend) if total_spend else Decimal("0.00"),
        "days_left": days_left,
        "data_quality": {
            "has_campaign_linked_leads": all_period_count > 0,
            "has_spend": total_spend > 0,
            "has_dates": bool(campaign.start_date and campaign.end_date),
            "notes": [
                "Lead attribution uses Lead.campaign_id.",
                "Revenue and ROAS are estimated from won linked leads, not payment attribution.",
            ],
        },
    }


def _filter_campaigns(campaigns, leads, status=None, channel=None, search=None, branch_id=None, division=None):
    if status:
        campaigns = campaigns.filter(status=status)
    if channel:
        campaigns = campaigns.filter(channel=channel)
    if search:
        campaigns = campaigns.filter(
            Q(name__icontains=search) | Q(description__icontains=search)
        )
    if branch_id:
        leads = leads.filter(branch_id=branch_id)
    if division:
        leads = leads.filter(division=division)
    if branch_id or division:
        campaigns = campaigns.filter(id__in=leads.exclude(campaign_id=None).values("campaign_id"))
    return campaigns.distinct(), leads


def _serialize_request(obj):
    return {
        "id": obj.id,
        "title": obj.title,
        "requester_id": obj.requester_id,
        "requester_name": obj.requester.get_full_name() if obj.requester else "",
        "department": obj.department,
        "division": obj.division,
        "branch_id": obj.branch_id,
        "branch_name": obj.branch.branch_name if obj.branch else "",
        "needed_by": obj.needed_by,
        "priority": obj.priority,
        "proposed_budget": obj.proposed_budget,
        "problem": obj.problem,
        "audience": obj.audience,
        "product": obj.product,
        "expected_outcome": obj.expected_outcome,
        "context": obj.context,
        "status": obj.status,
        "review_note": obj.review_note,
        "converted_campaign_id": obj.converted_campaign_id,
        "created_at": obj.created_at,
        "updated_at": obj.updated_at,
    }


def _serialize_task(obj):
    return {
        "id": obj.id,
        "campaign_id": obj.campaign_id,
        "title": obj.title,
        "description": obj.description,
        "owner_id": obj.owner_id,
        "owner_name": obj.owner_name or _employee_name(obj.owner),
        "due_date": obj.due_date,
        "status": obj.status,
        "priority": obj.priority,
        "completed_at": obj.completed_at,
        "created_at": obj.created_at,
        "updated_at": obj.updated_at,
    }


def _serialize_update(obj):
    return {
        "id": obj.id,
        "campaign_id": obj.campaign_id,
        "update_type": obj.update_type,
        "update_date": obj.update_date,
        "text": obj.text,
        "blocker": obj.blocker,
        "next_action": obj.next_action,
        "author_id": obj.author_id,
        "author_name": obj.author.get_full_name() if obj.author else "",
        "created_at": obj.created_at,
        "updated_at": obj.updated_at,
    }


def _serialize_expense(obj):
    return {
        "id": obj.id,
        "campaign_id": obj.campaign_id,
        "expense_date": obj.expense_date,
        "category": obj.category,
        "vendor": obj.vendor,
        "amount": obj.amount,
        "description": obj.description,
        "status": obj.status,
        "reference": obj.reference,
        "created_at": obj.created_at,
        "updated_at": obj.updated_at,
    }


def _serialize_asset(obj):
    media_assets = []
    if hasattr(obj, "media_library_assets"):
        media_assets = [
            {
                "id": media.id,
                "title": media.title,
                "asset_type": media.asset_type,
                "file_url": media.file_url,
                "thumbnail_url": media.thumbnail_url,
                "status": media.status,
            }
            for media in obj.media_library_assets.all()[:10]
        ]
    return {
        "id": obj.id,
        "campaign_id": obj.campaign_id,
        "name": obj.name,
        "asset_type": obj.asset_type,
        "owner_id": obj.owner_id,
        "owner_name": obj.owner_name or _employee_name(obj.owner),
        "due_date": obj.due_date,
        "status": obj.status,
        "description": obj.description,
        "specifications": obj.specifications,
        "approval_notes": obj.approval_notes,
        "content_id": obj.content_id,
        "media_assets": media_assets,
        "created_at": obj.created_at,
        "updated_at": obj.updated_at,
    }


def _serialize_risk(obj):
    return {
        "id": obj.id,
        "campaign_id": obj.campaign_id,
        "record_type": obj.record_type,
        "severity": obj.severity,
        "title": obj.title,
        "owner_id": obj.owner_id,
        "owner_name": obj.owner_name or _employee_name(obj.owner),
        "due_date": obj.due_date,
        "mitigation": obj.mitigation,
        "impact": obj.impact,
        "approver": obj.approver,
        "status": obj.status,
        "created_at": obj.created_at,
        "updated_at": obj.updated_at,
    }


def _serialize_decision(obj):
    return {
        "id": obj.id,
        "campaign_id": obj.campaign_id,
        "decision_date": obj.decision_date,
        "decision": obj.decision,
        "owner": obj.owner,
        "approver": obj.approver,
        "reason": obj.reason,
        "source_meeting_id": obj.source_meeting_context.meeting_id if obj.source_meeting_context else None,
        "source_meeting_context_id": obj.source_meeting_context_id,
        "created_at": obj.created_at,
        "updated_at": obj.updated_at,
    }


def _serialize_workspace_meeting(context):
    meeting = context.meeting
    return {
        "id": meeting.id,
        "meeting_context_id": context.id,
        "meeting_id": meeting.meeting_id,
        "title": meeting.title,
        "meeting_type": context.meeting_type,
        "meeting_date": meeting.meeting_date,
        "meeting_time": meeting.meeting_time.strftime("%H:%M"),
        "duration_minutes": meeting.duration_minutes,
        "status": meeting.status,
        "location_type": meeting.location_type,
        "location": meeting.location,
        "facilitator": context.facilitator,
        "recorder": context.recorder,
        "attendee_count": meeting.attendees.count(),
        "open_action_count": context.actions.exclude(status__in=["done", "cancelled"]).count(),
        "decision_count": context.campaign_decisions.count(),
        "latest_decisions": [
            _serialize_decision(decision)
            for decision in context.campaign_decisions.all()[:5]
        ],
    }


def _serialize_post_analysis(obj):
    if not obj:
        return None
    return {
        "id": obj.id,
        "campaign_id": obj.campaign_id,
        "conclusion": obj.conclusion,
        "worked": obj.worked,
        "failed": obj.failed,
        "lessons": obj.lessons,
        "next_actions": obj.next_actions,
        "reusable_assets": obj.reusable_assets,
        "analysis_date": obj.analysis_date,
        "approver": obj.approver,
        "author_id": obj.author_id,
        "author_name": obj.author.get_full_name() if obj.author else "",
        "created_at": obj.created_at,
        "updated_at": obj.updated_at,
    }


def _lead_row(lead):
    return {
        "id": lead.id,
        "full_name": lead.full_name,
        "phone": lead.phone,
        "division": lead.division,
        "source": lead.source,
        "status": lead.status,
        "estimated_value": lead.estimated_value,
        "score": lead.score,
        "assigned_to_id": lead.assigned_to_id,
        "assigned_to_name": _employee_name(lead.assigned_to),
        "created_at": lead.created_at,
    }


def _budget_summary(campaign):
    expenses = campaign.workspace_expenses.all()
    committed = expenses.exclude(status="rejected").aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    paid = expenses.filter(status="paid").aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    source_spend = max(campaign.budget_spent, paid)
    return {
        "budget_allocated": campaign.budget_allocated,
        "stored_campaign_spend": campaign.budget_spent,
        "workspace_committed": committed,
        "workspace_paid": paid,
        "effective_spend": source_spend,
        "remaining_against_committed": campaign.budget_allocated - committed,
        "variance_against_committed": committed - campaign.budget_allocated,
        "utilization_pct": _pct(committed, campaign.budget_allocated),
    }


def _workspace_snapshot(request, campaign):
    start, end = _period_bounds()
    leads = _lead_queryset(request)
    campaign_leads = leads.filter(campaign_id=campaign.id)
    lead_statuses = [
        {"status": status, "count": campaign_leads.filter(status=status).count()}
        for status, _label in Lead.STATUS_CHOICES
    ]
    funnel_events = LeadFunnelEvent.objects.filter(campaign_id=campaign.id)
    funnel_stages = [
        {"stage": stage, "count": funnel_events.filter(to_stage=stage).values("lead_id").distinct().count()}
        for stage in FUNNEL_STAGE_ORDER
    ]
    tasks = campaign.workspace_tasks.select_related("owner", "owner__user").all()
    assets = campaign.workspace_assets.select_related("owner", "owner__user").all()
    risks = campaign.workspace_risks.select_related("owner", "owner__user").all()
    expenses = campaign.workspace_expenses.all()
    updates = campaign.workspace_updates.select_related("author").all()
    decisions = campaign.workspace_decisions.select_related("source_meeting_context", "source_meeting_context__meeting").all()
    meeting_contexts = campaign.marketing_meeting_contexts.select_related(
        "meeting",
        "meeting__organizer",
    ).prefetch_related(
        "meeting__attendees",
        "actions",
        "campaign_decisions",
    ).all()
    today = timezone.localdate()
    next_meeting = meeting_contexts.filter(
        meeting__status="scheduled",
        meeting__meeting_date__gte=today,
    ).order_by("meeting__meeting_date", "meeting__meeting_time").first()
    source_request = campaign.source_requests.select_related("requester", "branch").first()

    return {
        "campaign": _campaign_base(campaign),
        "performance": {
            **_campaign_metrics(campaign, leads, start, end),
            "lead_status_breakdown": lead_statuses,
            "funnel_stage_breakdown": funnel_stages,
            "recent_leads": [_lead_row(lead) for lead in campaign_leads[:10]],
        },
        "budget": {
            **_budget_summary(campaign),
            "expenses": [_serialize_expense(expense) for expense in expenses],
        },
        "source_request": _serialize_request(source_request) if source_request else None,
        "tasks": {
            "summary": {
                "total": tasks.count(),
                "open": tasks.exclude(status="done").count(),
                "done": tasks.filter(status="done").count(),
            },
            "items": [_serialize_task(task) for task in tasks],
        },
        "updates": [_serialize_update(update) for update in updates],
        "assets": {
            "summary": {
                "total": assets.count(),
                "pending": assets.exclude(status__in=["approved", "live"]).count(),
            },
            "items": [_serialize_asset(asset) for asset in assets],
        },
        "risks": {
            "summary": {
                "total": risks.count(),
                "open": risks.exclude(status="closed").count(),
                "critical": risks.filter(severity="critical").exclude(status="closed").count(),
            },
            "items": [_serialize_risk(risk) for risk in risks],
        },
        "meetings": {
            "summary": {
                "total": meeting_contexts.count(),
                "upcoming": meeting_contexts.filter(meeting__status="scheduled", meeting__meeting_date__gte=today).count(),
                "completed": meeting_contexts.filter(meeting__status="completed").count(),
                "open_actions": sum(
                    context.actions.exclude(status__in=["done", "cancelled"]).count()
                    for context in meeting_contexts
                ),
            },
            "next_meeting": _serialize_workspace_meeting(next_meeting) if next_meeting else None,
            "items": [_serialize_workspace_meeting(context) for context in meeting_contexts],
        },
        "decisions": [_serialize_decision(decision) for decision in decisions],
        "post_analysis": _serialize_post_analysis(getattr(campaign, "post_analysis", None)),
        "activity_feed": _activity_feed(campaign),
    }


def _activity_feed(campaign):
    items = []
    for update in campaign.workspace_updates.select_related("author")[:20]:
        items.append({
            "type": "update",
            "text": f"{update.update_type}: {update.text}",
            "actor": update.author.get_full_name() if update.author else "",
            "time": update.update_date,
        })
    for decision in campaign.workspace_decisions.all()[:20]:
        items.append({
            "type": "decision",
            "text": decision.decision,
            "actor": decision.owner,
            "time": decision.decision_date,
        })
    for expense in campaign.workspace_expenses.all()[:20]:
        items.append({
            "type": "budget",
            "text": f"{expense.vendor}: {expense.amount}",
            "actor": "Marketing / Finance",
            "time": expense.expense_date,
        })
    return sorted(items, key=lambda item: str(item["time"]), reverse=True)[:30]


def _apply_payload(instance, payload_data, owner_model_fields=None):
    owner_model_fields = owner_model_fields or {}
    for attr, value in payload_data.items():
        model_attr = owner_model_fields.get(attr, attr)
        setattr(instance, model_attr, value)
    instance.full_clean()
    instance.save()
    return instance


@router.get("/panel")
@require_permission("marketing_campaigns", "list")
def get_campaign_panel(
    request,
    period_start: date = None,
    period_end: date = None,
    status: str = None,
    channel: str = None,
    division: str = None,
    branch_id: int = None,
    search: str = None,
    limit: int = 25,
):
    start, end = _period_bounds(period_start, period_end)
    leads = _lead_queryset(request)
    campaigns, metric_leads = _filter_campaigns(
        _campaign_queryset(request),
        leads,
        status=status,
        channel=channel,
        search=search,
        branch_id=branch_id,
        division=division,
    )

    rows = []
    for campaign in campaigns[: max(min(limit, 100), 1)]:
        rows.append({
            **_campaign_base(campaign),
            "metrics": _campaign_metrics(campaign, metric_leads, start, end),
            "budget": _budget_summary(campaign),
        })

    active_count = campaigns.filter(status="active").count()
    total_budget = campaigns.aggregate(total=Sum("budget_allocated"))["total"] or Decimal("0.00")
    total_spend = campaigns.aggregate(total=Sum("budget_spent"))["total"] or Decimal("0.00")
    attributed_leads = metric_leads.filter(
        campaign_id__in=campaigns.values("id"),
        created_at__date__gte=start,
        created_at__date__lte=end,
    )
    won_leads = attributed_leads.filter(status="won")

    return {
        "period": {"start": start, "end": end},
        "filters": {
            "status": status,
            "channel": channel,
            "division": division,
            "branch_id": branch_id,
            "search": search,
        },
        "kpis": {
            "total_campaigns": campaigns.count(),
            "active_campaigns": active_count,
            "total_budget": total_budget,
            "total_spend": total_spend,
            "attributed_leads": attributed_leads.count(),
            "qualified_leads": attributed_leads.filter(
                status__in=["qualified", "proposal_sent", "negotiation", "won"]
            ).count(),
            "won_leads": won_leads.count(),
            "estimated_won_revenue": _decimal_sum(won_leads, "estimated_value"),
            "avg_budget_utilization_pct": _pct(total_spend, total_budget),
        },
        "campaigns": rows,
        "data_notes": [
            "Campaign portfolio metrics use stored Campaign, Lead, and LeadFunnelEvent data.",
            "Spend comes from MarketingCampaign.budget_spent and workspace expense records; external ad platform spend is not integrated.",
            "Revenue and ROAS are estimated from won linked leads, not payment attribution.",
        ],
    }


@router.get("/panel/export")
@require_permission("marketing_campaigns", "list")
def export_campaign_panel(
    request,
    period_start: date = None,
    period_end: date = None,
    status: str = None,
    channel: str = None,
    division: str = None,
    branch_id: int = None,
    search: str = None,
):
    panel = get_campaign_panel(
        request,
        period_start=period_start,
        period_end=period_end,
        status=status,
        channel=channel,
        division=division,
        branch_id=branch_id,
        search=search,
        limit=100,
    )
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "Campaign",
        "Status",
        "Channel",
        "Budget",
        "Spend",
        "Leads",
        "Qualified",
        "Won",
        "Pipeline Value",
        "Estimated Won Revenue",
        "CPL",
        "Conversion %",
    ])
    for row in panel["campaigns"]:
        metrics = row["metrics"]
        writer.writerow([
            row["name"],
            row["status"],
            row["channel"],
            row["budget_allocated"],
            row["budget_spent"],
            metrics["lead_count"],
            metrics["qualified_count"],
            metrics["won_count"],
            metrics["pipeline_value"],
            metrics["estimated_won_revenue"],
            metrics["cpl"],
            metrics["conversion_rate"],
        ])
    response = HttpResponse(buffer.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="campaign-panel.csv"'
    return response


@router.get("/requests")
@require_permission("marketing_campaigns", "list")
def list_campaign_requests(request, status: str = None, search: str = None):
    requests = CampaignRequest.objects.select_related("requester", "branch").all()
    if status:
        requests = requests.filter(status=status)
    if search:
        requests = requests.filter(
            Q(title__icontains=search)
            | Q(problem__icontains=search)
            | Q(audience__icontains=search)
            | Q(product__icontains=search)
        )
    return {"results": [_serialize_request(obj) for obj in requests[:100]]}


@router.post("/requests", response={201: dict, 400: MessageSchema})
@require_permission("marketing_campaigns", "create")
def create_campaign_request(request, payload: CampaignRequestIn):
    try:
        data = payload.dict()
        branch_id = data.pop("branch_id", None)
        obj = CampaignRequest.objects.create(
            requester=request.user,
            branch=Branch.objects.filter(id=branch_id).first() if branch_id else None,
            **data,
        )
        return 201, _serialize_request(obj)
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.patch("/requests/{request_id}", response={200: dict, 400: MessageSchema, 404: MessageSchema})
@require_permission("marketing_campaigns", "update")
def update_campaign_request(request, request_id: int, payload: CampaignRequestUpdate):
    try:
        obj = get_object_or_404(CampaignRequest, id=request_id)
        data = payload.dict(exclude_unset=True)
        branch_id = data.pop("branch_id", None)
        if branch_id is not None:
            data["branch"] = Branch.objects.filter(id=branch_id).first()
        _apply_payload(obj, data)
        return 200, _serialize_request(obj)
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.post("/requests/{request_id}/convert", response={201: dict, 400: MessageSchema, 404: MessageSchema})
@require_permission("marketing_campaigns", "create")
def convert_campaign_request(request, request_id: int, payload: CampaignRequestConvertIn):
    try:
        obj = get_object_or_404(CampaignRequest, id=request_id)
        if obj.converted_campaign_id:
            return 400, {"detail": "Campaign request has already been converted."}
        campaign = MarketingCampaign.objects.create(
            name=obj.title,
            description=obj.problem,
            status=payload.status,
            channel=payload.channel,
            budget_allocated=obj.proposed_budget,
            start_date=payload.start_date,
            end_date=payload.end_date,
        )
        obj.status = "converted"
        obj.converted_campaign = campaign
        obj.save(update_fields=["status", "converted_campaign", "updated_at"])
        return 201, {"request": _serialize_request(obj), "campaign": _campaign_base(campaign)}
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.post("/{campaign_id}/tasks", response={201: dict, 400: MessageSchema, 404: MessageSchema})
@require_permission("marketing_campaigns", "create")
def create_campaign_task(request, campaign_id: int, payload: CampaignTaskIn):
    try:
        campaign = get_object_or_404(MarketingCampaign, id=campaign_id)
        data = payload.dict()
        owner_id = data.pop("owner_id", None)
        obj = CampaignTask.objects.create(
            campaign=campaign,
            owner=Employee.objects.filter(id=owner_id).first() if owner_id else None,
            created_by=request.user,
            **data,
        )
        return 201, _serialize_task(obj)
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.patch("/tasks/{task_id}", response={200: dict, 400: MessageSchema, 404: MessageSchema})
@require_permission("marketing_campaigns", "update")
def update_campaign_task(request, task_id: int, payload: CampaignTaskUpdate):
    try:
        obj = get_object_or_404(CampaignTask, id=task_id)
        data = payload.dict(exclude_unset=True)
        owner_id = data.pop("owner_id", None)
        if owner_id is not None:
            data["owner"] = Employee.objects.filter(id=owner_id).first()
        if data.get("status") == "done" and obj.status != "done":
            data["completed_at"] = timezone.now()
        elif data.get("status") and data.get("status") != "done":
            data["completed_at"] = None
        _apply_payload(obj, data)
        return 200, _serialize_task(obj)
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.post("/{campaign_id}/updates", response={201: dict, 400: MessageSchema, 404: MessageSchema})
@require_permission("marketing_campaigns", "create")
def create_campaign_update(request, campaign_id: int, payload: CampaignUpdateIn):
    try:
        campaign = get_object_or_404(MarketingCampaign, id=campaign_id)
        data = payload.dict()
        data["update_date"] = data["update_date"] or timezone.localdate()
        obj = CampaignUpdate.objects.create(campaign=campaign, author=request.user, **data)
        created_risk = None
        if obj.update_type == "blocker" and obj.blocker:
            created_risk = CampaignRisk.objects.create(
                campaign=campaign,
                record_type="blocker",
                severity="high",
                title=obj.blocker,
                owner_name=request.user.get_full_name() or request.user.email,
                mitigation=obj.next_action,
                created_by=request.user,
            )
        response = _serialize_update(obj)
        response["created_risk"] = _serialize_risk(created_risk) if created_risk else None
        return 201, response
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.post("/{campaign_id}/expenses", response={201: dict, 400: MessageSchema, 404: MessageSchema})
@require_permission("marketing_campaigns", "create")
def create_campaign_expense(request, campaign_id: int, payload: CampaignExpenseIn):
    try:
        campaign = get_object_or_404(MarketingCampaign, id=campaign_id)
        data = payload.dict()
        data["expense_date"] = data["expense_date"] or timezone.localdate()
        obj = CampaignExpense.objects.create(campaign=campaign, created_by=request.user, **data)
        return 201, _serialize_expense(obj)
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.post("/{campaign_id}/assets", response={201: dict, 400: MessageSchema, 404: MessageSchema})
@require_permission("marketing_campaigns", "create")
def create_campaign_asset(request, campaign_id: int, payload: CampaignAssetIn):
    try:
        campaign = get_object_or_404(MarketingCampaign, id=campaign_id)
        data = payload.dict()
        owner_id = data.pop("owner_id", None)
        content_id = data.pop("content_id", None)
        obj = CampaignAsset.objects.create(
            campaign=campaign,
            owner=Employee.objects.filter(id=owner_id).first() if owner_id else None,
            content_id=content_id,
            created_by=request.user,
            **data,
        )
        return 201, _serialize_asset(obj)
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.patch("/assets/{asset_id}", response={200: dict, 400: MessageSchema, 404: MessageSchema})
@require_permission("marketing_campaigns", "update")
def update_campaign_asset(request, asset_id: int, payload: CampaignAssetUpdate):
    try:
        obj = get_object_or_404(CampaignAsset, id=asset_id)
        data = payload.dict(exclude_unset=True)
        owner_id = data.pop("owner_id", None)
        if owner_id is not None:
            data["owner"] = Employee.objects.filter(id=owner_id).first()
        content_id = data.pop("content_id", None)
        if content_id is not None:
            data["content_id"] = content_id
        _apply_payload(obj, data)
        return 200, _serialize_asset(obj)
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.post("/{campaign_id}/risks", response={201: dict, 400: MessageSchema, 404: MessageSchema})
@require_permission("marketing_campaigns", "create")
def create_campaign_risk(request, campaign_id: int, payload: CampaignRiskIn):
    try:
        campaign = get_object_or_404(MarketingCampaign, id=campaign_id)
        data = payload.dict()
        owner_id = data.pop("owner_id", None)
        obj = CampaignRisk.objects.create(
            campaign=campaign,
            owner=Employee.objects.filter(id=owner_id).first() if owner_id else None,
            created_by=request.user,
            **data,
        )
        return 201, _serialize_risk(obj)
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.patch("/risks/{risk_id}", response={200: dict, 400: MessageSchema, 404: MessageSchema})
@require_permission("marketing_campaigns", "update")
def update_campaign_risk(request, risk_id: int, payload: CampaignRiskUpdate):
    try:
        obj = get_object_or_404(CampaignRisk, id=risk_id)
        data = payload.dict(exclude_unset=True)
        owner_id = data.pop("owner_id", None)
        if owner_id is not None:
            data["owner"] = Employee.objects.filter(id=owner_id).first()
        _apply_payload(obj, data)
        return 200, _serialize_risk(obj)
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.post("/{campaign_id}/decisions", response={201: dict, 400: MessageSchema, 404: MessageSchema})
@require_permission("marketing_campaigns", "create")
def create_campaign_decision(request, campaign_id: int, payload: CampaignDecisionIn):
    try:
        campaign = get_object_or_404(MarketingCampaign, id=campaign_id)
        data = payload.dict()
        data["decision_date"] = data["decision_date"] or timezone.localdate()
        obj = CampaignDecision.objects.create(campaign=campaign, created_by=request.user, **data)
        return 201, _serialize_decision(obj)
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.put("/{campaign_id}/post-analysis", response={200: dict, 400: MessageSchema, 404: MessageSchema})
@require_permission("marketing_campaigns", "update")
def save_campaign_post_analysis(request, campaign_id: int, payload: CampaignPostAnalysisIn):
    try:
        campaign = get_object_or_404(MarketingCampaign, id=campaign_id)
        data = payload.dict()
        mark_completed = data.pop("mark_campaign_completed", False)
        data["analysis_date"] = data["analysis_date"] or timezone.localdate()
        obj, _created = CampaignPostAnalysis.objects.update_or_create(
            campaign=campaign,
            defaults={**data, "author": request.user},
        )
        if mark_completed:
            campaign.status = "completed"
            campaign.save(update_fields=["status", "updated_at"])
        return 200, _serialize_post_analysis(obj)
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get("/{campaign_id}/workspace")
@require_permission("marketing_campaigns", "view")
def get_campaign_workspace(request, campaign_id: int):
    campaign = get_object_or_404(MarketingCampaign, id=campaign_id)
    return _workspace_snapshot(request, campaign)


@router.get("", response=List[MarketingCampaignOut])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("marketing_campaigns", "list")
def list_campaigns(
    request,
    status: str = None,
    channel: str = None,
    search: str = None
):
    """List all marketing campaigns with optional filtering."""
    campaigns = _campaign_queryset(request)

    if status:
        campaigns = campaigns.filter(status=status)
    if channel:
        campaigns = campaigns.filter(channel=channel)
    if search:
        campaigns = campaigns.filter(
            Q(name__icontains=search) | Q(description__icontains=search)
        )

    return campaigns


@router.post("", response={201: MarketingCampaignOut, 400: MessageSchema})
@require_permission("marketing_campaigns", "create")
def create_campaign(request, payload: MarketingCampaignIn):
    """Create a new marketing campaign."""
    try:
        campaign = MarketingCampaign.objects.create(**payload.dict())
        return 201, campaign
    except ValidationError as e:
        return 400, {'detail': _validation_detail(e)}
    except Exception as e:
        return 400, {'detail': str(e)}


@router.get("/{campaign_id}", response=MarketingCampaignOut)
@require_permission("marketing_campaigns", "view")
def get_campaign(request, campaign_id: int):
    """Get a specific marketing campaign by ID."""
    return get_object_or_404(MarketingCampaign, id=campaign_id)


@router.put("/{campaign_id}", response={200: MarketingCampaignOut, 400: MessageSchema, 404: MessageSchema})
@require_permission("marketing_campaigns", "update")
def update_campaign(request, campaign_id: int, payload: MarketingCampaignUpdate):
    """Update an existing marketing campaign."""
    try:
        campaign = get_object_or_404(MarketingCampaign, id=campaign_id)
        for attr, value in payload.dict(exclude_unset=True).items():
            setattr(campaign, attr, value)
        campaign.save()
        return 200, campaign
    except ValidationError as e:
        return 400, {'detail': _validation_detail(e)}
    except Exception as e:
        return 400, {'detail': str(e)}


@router.delete("/{campaign_id}", response={200: MessageSchema, 400: MessageSchema, 404: MessageSchema})
@require_permission("marketing_campaigns", "delete")
def delete_campaign(request, campaign_id: int):
    """Delete a marketing campaign."""
    try:
        campaign = get_object_or_404(MarketingCampaign, id=campaign_id)
        campaign.delete()
        return 200, {"detail": "Marketing campaign deleted successfully"}
    except ValidationError as e:
        return 400, {'detail': _validation_detail(e)}
    except Exception as e:
        return 400, {'detail': str(e)}


@router.get("/status/{status}/campaigns", response=List[MarketingCampaignOut])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("marketing_campaigns", "list")
def get_campaigns_by_status(request, status: str):
    """Get all campaigns with a specific status."""
    return _campaign_queryset(request).filter(status=status)


@router.get("/channel/{channel}/campaigns", response=List[MarketingCampaignOut])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("marketing_campaigns", "list")
def get_campaigns_by_channel(request, channel: str):
    """Get all campaigns for a specific channel."""
    return _campaign_queryset(request).filter(channel=channel)
