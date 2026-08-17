from datetime import timedelta
from typing import List

from django.db.models import Sum
from django.utils import timezone
from ninja import Router
from ninja.pagination import LimitOffsetPagination, paginate

from services.api.schema.crm_schemas import (
    ConversionBreakdownSchema,
    DropOffAlertSchema,
    FunnelLeadListSchema,
    FunnelStageSummarySchema,
    FunnelSummarySchema,
)
from services.models.crm import FunnelLead, FunnelSnapshot, FunnelStage
from user.utils.perm import require_permission

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
            conversion_rate = round((current_count / prev_count) * 100, 2)

        change_pct = 0.0
        if last_snapshot and last_snapshot.count > 0:
            change_pct = round(
                ((current_count - last_snapshot.count) / last_snapshot.count) * 100, 2
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
            rate = round((next_count / current_count) * 100, 2)

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
            loss_pct = round(((entered - progressed) / entered) * 100, 2)

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
    request,
    stage: str = None,
    status: str = None,
    search: str = None,
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
