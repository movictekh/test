from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router

from services.api.schema.crm_schemas import (
    CreateDealSchema,
    DealListSchema,
    MoveDealStageSchema,
    PipelineReportSchema,
    PipelineReportsSchema,
    PipelineStageSchema,
    PipelineSummarySchema,
    UpdateDealSchema,
)
from services.models.crm import Deal, PipelineStage
from user.models.branch import Branch
from user.models.employee import Employee
from user.utils.perm import require_permission

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
        conversion_pct = round((closed_count / total_deals) * 100, 2)

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
            return 400, {"detail": "Default pipeline stage not found"}

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
        return 201, deal
    except Branch.DoesNotExist:
        return 400, {"detail": "Branch not found"}
    except Employee.DoesNotExist:
        return 400, {"detail": "Agent not found"}
    except Exception as e:
        return 400, {"detail": str(e)}


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
        conversion_rate = round((closed_deals.count() / total_created) * 100, 2)

    return PipelineReportsSchema(
        total_closed=closed_deals.count(),
        revenue=revenue,
        conversion_rate=conversion_rate,
        period_days=period,
    )
