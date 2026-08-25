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

from domains.marketing_sales.api.v1.schemas.marketing import (
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
from domains.marketing_sales.models.marketing import (
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
from domains.marketing_sales.presenters import _campaign_campaign_base as _campaign_base
from domains.marketing_sales.presenters import _campaign_pct as _pct
from domains.marketing_sales.presenters import (
    _campaign_serialize_asset as _serialize_asset,
)
from domains.marketing_sales.presenters import (
    _campaign_serialize_decision as _serialize_decision,
)
from domains.marketing_sales.presenters import (
    _campaign_serialize_expense as _serialize_expense,
)
from domains.marketing_sales.presenters import (
    _campaign_serialize_post_analysis as _serialize_post_analysis,
)
from domains.marketing_sales.presenters import (
    _campaign_serialize_request as _serialize_request,
)
from domains.marketing_sales.presenters import (
    _campaign_serialize_risk as _serialize_risk,
)
from domains.marketing_sales.presenters import (
    _campaign_serialize_task as _serialize_task,
)
from domains.marketing_sales.presenters import (
    _campaign_serialize_update as _serialize_update,
)
from domains.marketing_sales.presenters import (
    _campaign_validation_detail as _validation_detail,
)
from domains.marketing_sales.selectors.marketing import (
    _campaign_budget_summary as _budget_summary,
)
from domains.marketing_sales.selectors.marketing import (
    _campaign_campaign_metrics as _campaign_metrics,
)
from domains.marketing_sales.selectors.marketing import (
    _campaign_campaign_queryset as _campaign_queryset,
)
from domains.marketing_sales.selectors.marketing import (
    _campaign_decimal_sum as _decimal_sum,
)
from domains.marketing_sales.selectors.marketing import (
    _campaign_filter_campaigns as _filter_campaigns,
)
from domains.marketing_sales.selectors.marketing import (
    _campaign_lead_queryset as _lead_queryset,
)
from domains.marketing_sales.selectors.marketing import (
    _campaign_period_bounds as _period_bounds,
)
from domains.marketing_sales.selectors.marketing import (
    _campaign_workspace_snapshot as _workspace_snapshot,
)
from domains.marketing_sales.services.marketing import (
    _campaign_apply_payload as _apply_payload,
)
from shared.api.schema.others import MessageSchema
from domains.organization.models.branch import Branch
from domains.people.models.employee import Employee
from system.authorization import require_permission

campaigns_router = Router(tags=["Marketing Campaigns"])


@campaigns_router.get("/panel")
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
        rows.append(
            {
                **_campaign_base(campaign),
                "metrics": _campaign_metrics(campaign, metric_leads, start, end),
                "budget": _budget_summary(campaign),
            }
        )
    active_count = campaigns.filter(status="active").count()
    total_budget = campaigns.aggregate(total=Sum("budget_allocated"))[
        "total"
    ] or Decimal("0.00")
    total_spend = campaigns.aggregate(total=Sum("budget_spent"))["total"] or Decimal(
        "0.00"
    )
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


@campaigns_router.get("/panel/export")
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
    writer.writerow(
        [
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
        ]
    )
    for row in panel["campaigns"]:
        metrics = row["metrics"]
        writer.writerow(
            [
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
            ]
        )
    response = HttpResponse(buffer.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="campaign-panel.csv"'
    return response


@campaigns_router.get("/requests")
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


@campaigns_router.post("/requests", response={201: dict, 400: MessageSchema})
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
        return (201, _serialize_request(obj))
    except ValidationError as e:
        return (400, {"detail": _validation_detail(e)})
    except Exception as e:
        return (400, {"detail": str(e)})


@campaigns_router.patch(
    "/requests/{request_id}",
    response={200: dict, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("marketing_campaigns", "update")
def update_campaign_request(request, request_id: int, payload: CampaignRequestUpdate):
    try:
        obj = get_object_or_404(CampaignRequest, id=request_id)
        data = payload.dict(exclude_unset=True)
        branch_id = data.pop("branch_id", None)
        if branch_id is not None:
            data["branch"] = Branch.objects.filter(id=branch_id).first()
        _apply_payload(obj, data)
        return (200, _serialize_request(obj))
    except ValidationError as e:
        return (400, {"detail": _validation_detail(e)})
    except Exception as e:
        return (400, {"detail": str(e)})


@campaigns_router.post(
    "/requests/{request_id}/convert",
    response={201: dict, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("marketing_campaigns", "create")
def convert_campaign_request(
    request, request_id: int, payload: CampaignRequestConvertIn
):
    try:
        obj = get_object_or_404(CampaignRequest, id=request_id)
        if obj.converted_campaign_id:
            return (400, {"detail": "Campaign request has already been converted."})
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
        return (
            201,
            {"request": _serialize_request(obj), "campaign": _campaign_base(campaign)},
        )
    except ValidationError as e:
        return (400, {"detail": _validation_detail(e)})
    except Exception as e:
        return (400, {"detail": str(e)})


@campaigns_router.post(
    "/{campaign_id}/tasks", response={201: dict, 400: MessageSchema, 404: MessageSchema}
)
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
        return (201, _serialize_task(obj))
    except ValidationError as e:
        return (400, {"detail": _validation_detail(e)})
    except Exception as e:
        return (400, {"detail": str(e)})


@campaigns_router.patch(
    "/tasks/{task_id}", response={200: dict, 400: MessageSchema, 404: MessageSchema}
)
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
        return (200, _serialize_task(obj))
    except ValidationError as e:
        return (400, {"detail": _validation_detail(e)})
    except Exception as e:
        return (400, {"detail": str(e)})


@campaigns_router.post(
    "/{campaign_id}/updates",
    response={201: dict, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("marketing_campaigns", "create")
def create_campaign_update(request, campaign_id: int, payload: CampaignUpdateIn):
    try:
        campaign = get_object_or_404(MarketingCampaign, id=campaign_id)
        data = payload.dict()
        data["update_date"] = data["update_date"] or timezone.localdate()
        obj = CampaignUpdate.objects.create(
            campaign=campaign, author=request.user, **data
        )
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
        response["created_risk"] = (
            _serialize_risk(created_risk) if created_risk else None
        )
        return (201, response)
    except ValidationError as e:
        return (400, {"detail": _validation_detail(e)})
    except Exception as e:
        return (400, {"detail": str(e)})


@campaigns_router.post(
    "/{campaign_id}/expenses",
    response={201: dict, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("marketing_campaigns", "create")
def create_campaign_expense(request, campaign_id: int, payload: CampaignExpenseIn):
    try:
        campaign = get_object_or_404(MarketingCampaign, id=campaign_id)
        data = payload.dict()
        data["expense_date"] = data["expense_date"] or timezone.localdate()
        obj = CampaignExpense.objects.create(
            campaign=campaign, created_by=request.user, **data
        )
        return (201, _serialize_expense(obj))
    except ValidationError as e:
        return (400, {"detail": _validation_detail(e)})
    except Exception as e:
        return (400, {"detail": str(e)})


@campaigns_router.post(
    "/{campaign_id}/assets",
    response={201: dict, 400: MessageSchema, 404: MessageSchema},
)
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
        return (201, _serialize_asset(obj))
    except ValidationError as e:
        return (400, {"detail": _validation_detail(e)})
    except Exception as e:
        return (400, {"detail": str(e)})


@campaigns_router.patch(
    "/assets/{asset_id}", response={200: dict, 400: MessageSchema, 404: MessageSchema}
)
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
        return (200, _serialize_asset(obj))
    except ValidationError as e:
        return (400, {"detail": _validation_detail(e)})
    except Exception as e:
        return (400, {"detail": str(e)})


@campaigns_router.post(
    "/{campaign_id}/risks", response={201: dict, 400: MessageSchema, 404: MessageSchema}
)
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
        return (201, _serialize_risk(obj))
    except ValidationError as e:
        return (400, {"detail": _validation_detail(e)})
    except Exception as e:
        return (400, {"detail": str(e)})


@campaigns_router.patch(
    "/risks/{risk_id}", response={200: dict, 400: MessageSchema, 404: MessageSchema}
)
@require_permission("marketing_campaigns", "update")
def update_campaign_risk(request, risk_id: int, payload: CampaignRiskUpdate):
    try:
        obj = get_object_or_404(CampaignRisk, id=risk_id)
        data = payload.dict(exclude_unset=True)
        owner_id = data.pop("owner_id", None)
        if owner_id is not None:
            data["owner"] = Employee.objects.filter(id=owner_id).first()
        _apply_payload(obj, data)
        return (200, _serialize_risk(obj))
    except ValidationError as e:
        return (400, {"detail": _validation_detail(e)})
    except Exception as e:
        return (400, {"detail": str(e)})


@campaigns_router.post(
    "/{campaign_id}/decisions",
    response={201: dict, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("marketing_campaigns", "create")
def create_campaign_decision(request, campaign_id: int, payload: CampaignDecisionIn):
    try:
        campaign = get_object_or_404(MarketingCampaign, id=campaign_id)
        data = payload.dict()
        data["decision_date"] = data["decision_date"] or timezone.localdate()
        obj = CampaignDecision.objects.create(
            campaign=campaign, created_by=request.user, **data
        )
        return (201, _serialize_decision(obj))
    except ValidationError as e:
        return (400, {"detail": _validation_detail(e)})
    except Exception as e:
        return (400, {"detail": str(e)})


@campaigns_router.put(
    "/{campaign_id}/post-analysis",
    response={200: dict, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("marketing_campaigns", "update")
def save_campaign_post_analysis(
    request, campaign_id: int, payload: CampaignPostAnalysisIn
):
    try:
        campaign = get_object_or_404(MarketingCampaign, id=campaign_id)
        data = payload.dict()
        mark_completed = data.pop("mark_campaign_completed", False)
        data["analysis_date"] = data["analysis_date"] or timezone.localdate()
        obj, _created = CampaignPostAnalysis.objects.update_or_create(
            campaign=campaign, defaults={**data, "author": request.user}
        )
        if mark_completed:
            campaign.status = "completed"
            campaign.save(update_fields=["status", "updated_at"])
        return (200, _serialize_post_analysis(obj))
    except ValidationError as e:
        return (400, {"detail": _validation_detail(e)})
    except Exception as e:
        return (400, {"detail": str(e)})


@campaigns_router.get("/{campaign_id}/workspace")
@require_permission("marketing_campaigns", "view")
def get_campaign_workspace(request, campaign_id: int):
    campaign = get_object_or_404(MarketingCampaign, id=campaign_id)
    return _workspace_snapshot(request, campaign)


@campaigns_router.get("", response=List[MarketingCampaignOut])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("marketing_campaigns", "list")
def list_campaigns(
    request, status: str = None, channel: str = None, search: str = None
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


@campaigns_router.post("", response={201: MarketingCampaignOut, 400: MessageSchema})
@require_permission("marketing_campaigns", "create")
def create_campaign(request, payload: MarketingCampaignIn):
    """Create a new marketing campaign."""
    try:
        campaign = MarketingCampaign.objects.create(**payload.dict())
        return (201, campaign)
    except ValidationError as e:
        return (400, {"detail": _validation_detail(e)})
    except Exception as e:
        return (400, {"detail": str(e)})


@campaigns_router.get("/{campaign_id}", response=MarketingCampaignOut)
@require_permission("marketing_campaigns", "view")
def get_campaign(request, campaign_id: int):
    """Get a specific marketing campaign by ID."""
    return get_object_or_404(MarketingCampaign, id=campaign_id)


@campaigns_router.put(
    "/{campaign_id}",
    response={200: MarketingCampaignOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("marketing_campaigns", "update")
def update_campaign(request, campaign_id: int, payload: MarketingCampaignUpdate):
    """Update an existing marketing campaign."""
    try:
        campaign = get_object_or_404(MarketingCampaign, id=campaign_id)
        for attr, value in payload.dict(exclude_unset=True).items():
            setattr(campaign, attr, value)
        campaign.save()
        return (200, campaign)
    except ValidationError as e:
        return (400, {"detail": _validation_detail(e)})
    except Exception as e:
        return (400, {"detail": str(e)})


@campaigns_router.delete(
    "/{campaign_id}",
    response={200: MessageSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("marketing_campaigns", "delete")
def delete_campaign(request, campaign_id: int):
    """Delete a marketing campaign."""
    try:
        campaign = get_object_or_404(MarketingCampaign, id=campaign_id)
        campaign.delete()
        return (200, {"detail": "Marketing campaign deleted successfully"})
    except ValidationError as e:
        return (400, {"detail": _validation_detail(e)})
    except Exception as e:
        return (400, {"detail": str(e)})


@campaigns_router.get("/status/{status}/campaigns", response=List[MarketingCampaignOut])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("marketing_campaigns", "list")
def get_campaigns_by_status(request, status: str):
    """Get all campaigns with a specific status."""
    return _campaign_queryset(request).filter(status=status)


@campaigns_router.get(
    "/channel/{channel}/campaigns", response=List[MarketingCampaignOut]
)
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("marketing_campaigns", "list")
def get_campaigns_by_channel(request, channel: str):
    """Get all campaigns for a specific channel."""
    return _campaign_queryset(request).filter(channel=channel)
