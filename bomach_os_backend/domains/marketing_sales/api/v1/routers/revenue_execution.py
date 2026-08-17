from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import List

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router

from domains.marketing_sales.api.v1.schemas.sales import (
    ActivityScorecardRowSchema,
    DailyActionCompleteSchema,
    DailyActionInstanceOutSchema,
    DailyActionInstanceUpdateSchema,
    DailyActionTemplateCreateSchema,
    DailyActionTemplateOutSchema,
    DailyActionTemplateUpdateSchema,
    DailyExecutionDayOutSchema,
    DailyExecutionSummarySchema,
    MonthlyExecutionSummarySchema,
    OpenDailyExecutionDaySchema,
    RevenueKeyResultCreateSchema,
    RevenueKeyResultOutSchema,
    RevenueKeyResultUpdateSchema,
    RevenueObjectiveCreateSchema,
    RevenueObjectiveOutSchema,
    RevenueObjectiveUpdateSchema,
    SalesPlaybookCreateSchema,
    SalesPlaybookObjectionCreateSchema,
    SalesPlaybookObjectionUpdateSchema,
    SalesPlaybookUpdateSchema,
    SpeedToLeadQueueItemSchema,
    TurnaroundActionCompleteSchema,
    TurnaroundActionOutSchema,
    TurnaroundActionUpdateSchema,
    TurnaroundPlanCreateSchema,
    TurnaroundPlanDetailSchema,
    TurnaroundPlanOutSchema,
    TurnaroundPlanUpdateSchema,
)
from domains.marketing_sales.constants import (
    DIAGNOSIS_CARDS,
    FUNNEL_CORRECTIVE_ACTIONS,
    FUNNEL_STAGE_LABELS,
    LEAD_SCORING_MODEL,
    MANAGEMENT_RHYTHM,
    QUALIFICATION_CHECKLIST,
)
from domains.marketing_sales.models.revenue_execution import (
    DailyActionInstance,
    DailyActionTemplate,
    DailyExecutionDay,
    RevenueKeyResult,
    RevenueObjective,
    TurnaroundAction,
    TurnaroundPlan,
)
from domains.marketing_sales.models.sales import (
    FUNNEL_STAGE_ORDER,
    Lead,
    LeadActivity,
    LeadFunnelEvent,
    SalesPlaybook,
    SalesPlaybookObjection,
)
from domains.marketing_sales.presenters import _revenue_decimal_pct as _decimal_pct
from domains.marketing_sales.presenters import _revenue_employee_name as _employee_name
from domains.marketing_sales.presenters import (
    _revenue_lead_control_rows as _lead_control_rows,
)
from domains.marketing_sales.presenters import (
    _revenue_lead_sla_status as _lead_sla_status,
)
from domains.marketing_sales.presenters import _revenue_money_display as _money_display
from domains.marketing_sales.presenters import _revenue_pct as _pct
from domains.marketing_sales.presenters import (
    _revenue_playbook_objection_row as _playbook_objection_row,
)
from domains.marketing_sales.presenters import _revenue_playbook_row as _playbook_row
from domains.marketing_sales.presenters import (
    _revenue_progress_color as _progress_color,
)
from domains.marketing_sales.presenters import (
    _revenue_recommended_action as _recommended_action,
)
from domains.marketing_sales.presenters import _revenue_role_label as _role_label
from domains.marketing_sales.presenters import (
    _revenue_turnaround_end_date as _turnaround_end_date,
)
from domains.marketing_sales.presenters import (
    _revenue_validation_detail as _validation_detail,
)
from domains.marketing_sales.selectors.sales import (
    _revenue_action_queryset as _action_queryset,
)
from domains.marketing_sales.selectors.sales import (
    _revenue_activity_queryset as _activity_queryset,
)
from domains.marketing_sales.selectors.sales import (
    _revenue_cohort_lead_ids as _cohort_lead_ids,
)
from domains.marketing_sales.selectors.sales import (
    _revenue_completion_counts as _completion_counts,
)
from domains.marketing_sales.selectors.sales import _revenue_date_bounds as _date_bounds
from domains.marketing_sales.selectors.sales import (
    _revenue_day_queryset as _day_queryset,
)
from domains.marketing_sales.selectors.sales import _revenue_decimal_sum as _decimal_sum
from domains.marketing_sales.selectors.sales import (
    _revenue_eligible_revenue_employees as _eligible_revenue_employees,
)
from domains.marketing_sales.selectors.sales import (
    _revenue_forecast_payload as _forecast_payload,
)
from domains.marketing_sales.selectors.sales import (
    _revenue_funnel_data_quality as _funnel_data_quality,
)
from domains.marketing_sales.selectors.sales import (
    _revenue_funnel_event_queryset as _funnel_event_queryset,
)
from domains.marketing_sales.selectors.sales import (
    _revenue_key_result_queryset as _key_result_queryset,
)
from domains.marketing_sales.selectors.sales import (
    _revenue_lead_control_kpis as _lead_control_kpis,
)
from domains.marketing_sales.selectors.sales import (
    _revenue_lead_queryset as _lead_queryset,
)
from domains.marketing_sales.selectors.sales import (
    _revenue_lead_value_sum as _lead_value_sum,
)
from domains.marketing_sales.selectors.sales import (
    _revenue_objective_queryset as _objective_queryset,
)
from domains.marketing_sales.selectors.sales import _revenue_okr_counts as _okr_counts
from domains.marketing_sales.selectors.sales import (
    _revenue_period_bounds as _period_bounds,
)
from domains.marketing_sales.selectors.sales import (
    _revenue_playbook_objection_queryset as _playbook_objection_queryset,
)
from domains.marketing_sales.selectors.sales import (
    _revenue_playbook_queryset as _playbook_queryset,
)
from domains.marketing_sales.selectors.sales import (
    _revenue_revenue_target_value as _revenue_target_value,
)
from domains.marketing_sales.selectors.sales import (
    _revenue_stage_lead_sets as _stage_lead_sets,
)
from domains.marketing_sales.selectors.sales import (
    _revenue_template_queryset as _template_queryset,
)
from domains.marketing_sales.selectors.sales import (
    _revenue_transition_leaks as _transition_leaks,
)
from domains.marketing_sales.selectors.sales import (
    _revenue_turnaround_action_queryset as _turnaround_action_queryset,
)
from domains.marketing_sales.selectors.sales import (
    _revenue_turnaround_detail as _turnaround_detail,
)
from domains.marketing_sales.selectors.sales import (
    _revenue_turnaround_plan_queryset as _turnaround_plan_queryset,
)
from domains.marketing_sales.selectors.sales import (
    _revenue_weighted_forecast_value as _weighted_forecast_value,
)
from domains.marketing_sales.services.sales import (
    _revenue_activate_turnaround_plan as _activate_turnaround_plan,
)
from domains.marketing_sales.services.sales import (
    _revenue_apply_action_payload as _apply_action_payload,
)
from domains.marketing_sales.services.sales import (
    _revenue_apply_key_result_payload as _apply_key_result_payload,
)
from domains.marketing_sales.services.sales import (
    _revenue_apply_objective_payload as _apply_objective_payload,
)
from domains.marketing_sales.services.sales import (
    _revenue_apply_template_payload as _apply_template_payload,
)
from domains.marketing_sales.services.sales import (
    _revenue_apply_turnaround_action_payload as _apply_turnaround_action_payload,
)
from domains.marketing_sales.services.sales import (
    _revenue_apply_turnaround_plan_payload as _apply_turnaround_plan_payload,
)
from domains.marketing_sales.services.sales import _revenue_open_day as _open_day
from domains.marketing_sales.services.sales import (
    _revenue_seed_turnaround_actions as _seed_turnaround_actions,
)
from services.api.schema.others import MessageSchema
from user.models.branch import Branch
from user.models.employee import Employee
from user.models.role_targets import (
    EmployeeTarget,
    RoleTargetTemplate,
    with_target_progress,
)
from user.utils.perm import require_permission, scope_queryset

revenue_execution_router = Router(tags=["Revenue Execution"])


@revenue_execution_router.get("/funnel-audit")
@require_permission("revenue_execution", "view")
def get_funnel_audit(
    request,
    period_start: date = None,
    period_end: date = None,
    branch_id: int = None,
    division: str = None,
    source: str = None,
    campaign_id: int = None,
):
    start, end = _period_bounds(period_start, period_end)
    events = _funnel_event_queryset(request)
    leads = _lead_queryset(request)
    if branch_id:
        events = events.filter(branch_id=branch_id)
        leads = leads.filter(branch_id=branch_id)
    if division:
        events = events.filter(division=division)
        leads = leads.filter(division=division)
    if source:
        events = events.filter(source=source)
        leads = leads.filter(source=source)
    if campaign_id:
        events = events.filter(campaign_id=campaign_id)
        leads = leads.filter(campaign_id=campaign_id)
    cohort_ids = _cohort_lead_ids(events, start, end)
    cohort_events = events.filter(lead_id__in=cohort_ids)
    cohort_leads = leads.filter(id__in=cohort_ids)
    stage_sets = _stage_lead_sets(events, cohort_ids)
    leaks = _transition_leaks(stage_sets, cohort_leads)
    largest_leak = leaks[0]["to_stage"] if leaks else None
    funnel = []
    previous_stage = None
    for stage in FUNNEL_STAGE_ORDER:
        entered = len(stage_sets[stage])
        if previous_stage is None:
            conversion_pct = 100.0 if entered else 0.0
        else:
            previous_entered = len(stage_sets[previous_stage])
            conversion_pct = _pct(entered, previous_entered)
        funnel.append(
            {
                "stage": stage,
                "name": FUNNEL_STAGE_LABELS[stage],
                "entered": entered,
                "conversion_pct": conversion_pct,
                "drop_label": "Largest leak" if stage == largest_leak else "Monitor",
            }
        )
        previous_stage = stage
    division_conversion = []
    for division_key, division_label in Lead.DIVISION_CHOICES:
        division_lead_ids = set(
            cohort_leads.filter(division=division_key).values_list("id", flat=True)
        )
        if not division_lead_ids:
            continue
        division_stage_sets = _stage_lead_sets(events, division_lead_ids)
        division_leaks = _transition_leaks(
            division_stage_sets, cohort_leads.filter(division=division_key)
        )
        purchase_ids = division_stage_sets["purchase"]
        division_conversion.append(
            {
                "division": division_key,
                "division_label": division_label,
                "leads": len(division_lead_ids),
                "revenue": _lead_value_sum(cohort_leads, purchase_ids),
                "lead_to_win_pct": _pct(len(purchase_ids), len(division_lead_ids)),
                "biggest_leak": (
                    division_leaks[0]["transition"] if division_leaks else None
                ),
            }
        )
    return {
        "period": {"start": start, "end": end},
        "filters": {
            "branch_id": branch_id,
            "division": division,
            "source": source,
            "campaign_id": campaign_id,
        },
        "funnel": funnel,
        "leaks": leaks[:3],
        "division_conversion": division_conversion,
        "corrective_actions": FUNNEL_CORRECTIVE_ACTIONS,
        "data_quality": _funnel_data_quality(events, cohort_ids),
    }


@revenue_execution_router.get("/command-center")
@require_permission("revenue_execution", "view")
def get_command_center(
    request,
    date: date = None,
    period_start: date = None,
    period_end: date = None,
    branch_id: int = None,
):
    target_date = date or timezone.localdate()
    start, end = _period_bounds(period_start, period_end)
    now = timezone.now()
    leads = _lead_queryset(request)
    if branch_id:
        leads = leads.filter(branch_id=branch_id)
    period_leads = leads.filter(created_at__date__gte=start, created_at__date__lte=end)
    active_leads = leads.filter(status__in=Lead.ACTIVE_STATUSES)
    won_leads = leads.filter(
        status="won", updated_at__date__gte=start, updated_at__date__lte=end
    )
    revenue_closed = _decimal_sum(won_leads, "estimated_value")
    weighted_forecast = _weighted_forecast_value(active_leads)
    qualified_pipeline = _decimal_sum(
        active_leads.filter(status__in=["qualified", "proposal_sent", "negotiation"]),
        "estimated_value",
    )
    ninety_day_target = _revenue_target_value(start, end, branch_id=branch_id)
    target_achievement = _decimal_pct(revenue_closed, ninety_day_target)
    day = _day_queryset(request).filter(date=target_date, branch_id=branch_id).first()
    total_actions, completed_actions, open_actions, completion_pct = (
        _completion_counts(day) if day else (0, 0, 0, 0)
    )
    active_count = active_leads.count()
    leads_with_next_action = (
        active_leads.exclude(next_action="")
        .filter(next_follow_up_at__isnull=False)
        .count()
    )
    follow_up_compliance = (
        round(leads_with_next_action / active_count * 100, 2) if active_count else 0.0
    )
    sla_breaches = sum(
        (1 for lead in active_leads if _lead_sla_status(lead, now) == "breached")
    )
    health_score = round(
        (
            float(target_achievement)
            + min(float(_decimal_pct(weighted_forecast, ninety_day_target)), 100.0)
            + follow_up_compliance
            + float(completion_pct)
        )
        / 4
    )
    if sla_breaches or follow_up_compliance < 80:
        primary_constraint = "Follow-up discipline"
    elif qualified_pipeline < ninety_day_target:
        primary_constraint = "Qualified pipeline"
    elif open_actions:
        primary_constraint = "Daily execution"
    else:
        primary_constraint = "Forecast quality"
    priorities = []
    if day:
        for action in day.actions.select_related("owner", "owner__user").order_by(
            "sort_order", "id"
        )[:5]:
            priorities.append(
                {
                    "id": action.id,
                    "title": action.title,
                    "meta": action.description
                    or f"{_employee_name(action.owner) or 'Unassigned'} · Daily revenue action",
                    "severity": action.severity,
                    "done": action.status == "completed",
                }
            )
    qualified_count = period_leads.filter(
        status__in=["qualified", "proposal_sent", "negotiation", "won"]
    ).count()
    intent_count = period_leads.filter(
        status__in=["proposal_sent", "negotiation"]
    ).count()
    won_count = period_leads.filter(status="won").count()
    funnel = [
        {
            "stage": "awareness",
            "name": "Awareness",
            "number": period_leads.count(),
            "rate_label": "Reach",
            "drop_label": "Top of funnel",
        },
        {
            "stage": "discovery",
            "name": "Discovery",
            "number": period_leads.count(),
            "rate_label": "Leads",
            "drop_label": "Lead capture",
        },
        {
            "stage": "evaluation",
            "name": "Evaluation",
            "number": qualified_count,
            "rate_label": "Qualified",
            "drop_label": f"{(round(qualified_count / period_leads.count() * 100, 1) if period_leads.count() else 0)}% from prior",
        },
        {
            "stage": "intent",
            "name": "Intent",
            "number": intent_count,
            "rate_label": "Meetings",
            "drop_label": f"{(round(intent_count / qualified_count * 100, 1) if qualified_count else 0)}% from prior",
        },
        {
            "stage": "purchase",
            "name": "Purchase",
            "number": won_count,
            "rate_label": "Won",
            "drop_label": f"{(round(won_count / intent_count * 100, 1) if intent_count else 0)}% from prior",
        },
        {
            "stage": "loyalty",
            "name": "Loyalty",
            "number": 0,
            "rate_label": "Repeat/referral",
            "drop_label": "Not tracked in this slice",
        },
    ]
    team_snapshot = []
    for employee_id in (
        active_leads.exclude(assigned_to__isnull=True)
        .values_list("assigned_to_id", flat=True)
        .distinct()
    ):
        employee_leads = active_leads.filter(assigned_to_id=employee_id)
        employee = employee_leads.first().assigned_to
        total = employee_leads.count()
        owned_with_next_action = (
            employee_leads.exclude(next_action="")
            .filter(next_follow_up_at__isnull=False)
            .count()
        )
        score = round(owned_with_next_action / total * 100) if total else 0
        team_snapshot.append(
            {
                "role": _role_label(employee),
                "score": score,
                "revenue_indicator": (
                    "On pace"
                    if score >= 80
                    else "At risk" if score >= 60 else "Needs action"
                ),
                "priority_coaching": (
                    "Pipeline discipline" if score >= 80 else "Follow-up cadence"
                ),
            }
        )
    forecast_gap = max(ninety_day_target - weighted_forecast, Decimal("0.00"))
    executive_risks = [
        {
            "key": "forecast_gap",
            "title": f"{_money_display(forecast_gap)} forecast gap",
            "copy": "Current weighted pipeline is below the 90-day revenue target.",
            "route": "forecast",
            "severity": "red",
        },
        {
            "key": "overdue_lead_leakage",
            "title": "Overdue lead leakage",
            "copy": f"{sla_breaches} active leads are already outside follow-up expectation.",
            "route": "lead-control",
            "severity": "red",
        },
        {
            "key": "weak_evaluation_content",
            "title": "Weak content at evaluation/intent",
            "copy": "Most content creates awareness but not enough decision proof.",
            "route": "content-studio",
            "severity": "yellow",
        },
        {
            "key": "coaching_deficit",
            "title": "Coaching deficit",
            "copy": "Low performers need weekly evidence-based coaching, not only targets.",
            "route": "coaching",
            "severity": "yellow",
        },
    ]
    return {
        "date": target_date,
        "period": {"start": start, "end": end},
        "hero": {
            "commercial_health_score": health_score,
            "status": (
                "on_track"
                if health_score >= 80
                else "at_risk" if health_score >= 50 else "off_track"
            ),
            "ninety_day_target": ninety_day_target,
            "weighted_forecast": weighted_forecast,
            "primary_constraint": primary_constraint,
            "executive_review": "Every Friday · 4 PM",
        },
        "kpi_cards": [
            {
                "key": "revenue_closed",
                "label": "Revenue closed",
                "value": revenue_closed,
                "display_value": _money_display(revenue_closed),
                "foot": "Target pace: ₦37.5M per month",
                "icon": "ti-currency-naira",
                "bg": "#D1FAE5",
                "color": "#065F46",
            },
            {
                "key": "weighted_forecast",
                "label": "Weighted forecast",
                "value": weighted_forecast,
                "display_value": _money_display(weighted_forecast),
                "foot": f"{_decimal_pct(weighted_forecast, ninety_day_target)}% of 90-day target",
                "icon": "ti-chart-arrows-vertical",
                "bg": "#DBEAFE",
                "color": "#1E40AF",
            },
            {
                "key": "qualified_pipeline",
                "label": "Qualified pipeline",
                "value": qualified_count,
                "display_value": qualified_count,
                "foot": "Deals with verified need and timing",
                "icon": "ti-filter-check",
                "bg": "#EDE9FE",
                "color": "#5B21B6",
            },
            {
                "key": "follow_up_compliance",
                "label": "Follow-up compliance",
                "value": follow_up_compliance,
                "display_value": f"{follow_up_compliance}%",
                "foot": f"{sla_breaches} SLA breaches require action",
                "icon": "ti-clock-check",
                "bg": "#FEF3C7",
                "color": "#92400E",
            },
            {
                "key": "daily_execution",
                "label": "Daily execution",
                "value": completion_pct,
                "display_value": f"{completion_pct}%",
                "foot": f"{completed_actions} of {total_actions} non-negotiables complete",
                "icon": "ti-bolt",
                "bg": "#FCE7F3",
                "color": "#9D174D",
            },
        ],
        "priorities": priorities,
        "management_rhythm": MANAGEMENT_RHYTHM,
        "diagnosis": DIAGNOSIS_CARDS,
        "funnel": funnel,
        "team_snapshot": team_snapshot,
        "executive_risks": executive_risks,
    }


@revenue_execution_router.get("/forecast")
@require_permission("revenue_execution", "view")
def get_forecast(
    request,
    period_start: date = None,
    period_end: date = None,
    branch_id: int = None,
    division: str = None,
    scenario: str = "base",
):
    return _forecast_payload(
        request,
        period_start=period_start,
        period_end=period_end,
        branch_id=branch_id,
        division=division,
        scenario=scenario,
    )


@revenue_execution_router.get("/forecast/export")
@require_permission("revenue_execution", "view")
def export_forecast(
    request,
    period_start: date = None,
    period_end: date = None,
    branch_id: int = None,
    division: str = None,
    scenario: str = "base",
):
    forecast = _forecast_payload(
        request,
        period_start=period_start,
        period_end=period_end,
        branch_id=branch_id,
        division=division,
        scenario=scenario,
    )
    rows = [
        ["Scenario", forecast["hero"]["scenario_label"]],
        ["Target", forecast["hero"]["target"]],
        ["Weighted forecast", forecast["hero"]["weighted_forecast"]],
        ["Target gap", forecast["hero"]["target_gap"]],
        [],
        ["Division", "Opportunities", "Pipeline", "Weighted forecast", "Target gap"],
    ]
    for row in forecast["division_rows"]:
        rows.append(
            [
                row["division_label"],
                row["opportunities"],
                row["pipeline"],
                row["weighted_forecast"],
                row["display_target_gap"],
            ]
        )
    csv_body = "\n".join(
        (
            ",".join(
                (f'"{str(value).replace(chr(34), chr(34) + chr(34))}"' for value in row)
            )
            for row in rows
        )
    )
    response = HttpResponse(csv_body, content_type="text/csv")
    response["Content-Disposition"] = (
        'attachment; filename="bomach-revenue-forecast.csv"'
    )
    return response


@revenue_execution_router.get("/lead-control")
@require_permission("revenue_execution", "view")
def get_lead_control(
    request,
    filter: str = "all",
    search: str = None,
    branch_id: int = None,
    division: str = None,
    assigned_to_id: int = None,
    limit: int = 100,
):
    now = timezone.now()
    limit = min(max(limit, 1), 250)
    requested_filter = filter or "all"
    filter_aliases = {"sla_breaches": "breach", "reactivation": "reactivate"}
    normalized_filter = filter_aliases.get(requested_filter, requested_filter)
    base_leads = _lead_queryset(request)
    if branch_id:
        base_leads = base_leads.filter(branch_id=branch_id)
    if division:
        base_leads = base_leads.filter(division=division)
    if assigned_to_id:
        base_leads = base_leads.filter(assigned_to_id=assigned_to_id)
    if search:
        base_leads = base_leads.filter(
            Q(full_name__icontains=search)
            | Q(phone__icontains=search)
            | Q(email__icontains=search)
            | Q(source__icontains=search)
            | Q(division__icontains=search)
            | Q(notes__icontains=search)
        )
    filtered = base_leads
    if normalized_filter == "breach":
        ids = [
            lead.id
            for lead in base_leads.filter(status__in=Lead.ACTIVE_STATUSES)
            if _lead_sla_status(lead, now) == "breached"
        ]
        filtered = base_leads.filter(id__in=ids)
    elif normalized_filter == "hot":
        filtered = base_leads.filter(status__in=Lead.ACTIVE_STATUSES, score__gte=75)
    elif normalized_filter == "stale":
        ids = [
            lead.id
            for lead in base_leads.filter(status__in=Lead.ACTIVE_STATUSES)
            if lead.is_stale
        ]
        filtered = base_leads.filter(id__in=ids)
    elif normalized_filter == "reactivate":
        filtered = base_leads.filter(
            Q(status="lost") | Q(status="contacted") | Q(status="dormant")
        )
    filtered = filtered.order_by("-score", "next_follow_up_at", "-created_at")
    return {
        "kpi_cards": _lead_control_kpis(base_leads, now),
        "rows": _lead_control_rows(filtered, now, limit),
        "count": filtered.count(),
        "filter": normalized_filter,
        "scoring_model": LEAD_SCORING_MODEL,
        "qualification_checklist": QUALIFICATION_CHECKLIST,
    }


@revenue_execution_router.post("/lead-control/auto-assign")
@require_permission("revenue_execution", "update")
def auto_assign_leads(request, branch_id: int = None, limit: int = 250):
    leads = _lead_queryset(request).filter(
        assigned_to__isnull=True, status__in=Lead.ACTIVE_STATUSES
    )
    if branch_id:
        leads = leads.filter(branch_id=branch_id)
    leads = list(
        leads.order_by("branch_id", "created_at", "id")[: min(max(limit, 1), 500)]
    )
    assigned_count = 0
    eligible_by_branch = {}
    company_pool = list(
        _eligible_revenue_employees(request, branch_id=None).filter(branch__isnull=True)
    )
    for lead in leads:
        branch_key = lead.branch_id or "company"
        if branch_key not in eligible_by_branch:
            branch_pool = (
                list(_eligible_revenue_employees(request, branch_id=lead.branch_id))
                if lead.branch_id
                else company_pool
            )
            eligible_by_branch[branch_key] = branch_pool or company_pool
        pool = eligible_by_branch[branch_key]
        if not pool:
            continue
        assignee = pool[assigned_count % len(pool)]
        lead.assigned_to = assignee
        lead.full_clean()
        lead.save(update_fields=["assigned_to", "updated_at"])
        assigned_count += 1
    return {
        "assigned_count": assigned_count,
        "skipped_count": len(leads) - assigned_count,
    }


@revenue_execution_router.post("/lead-control/repair-next-actions")
@require_permission("revenue_execution", "update")
def repair_next_actions(request, branch_id: int = None, limit: int = 500):
    leads = (
        _lead_queryset(request)
        .filter(status__in=Lead.ACTIVE_STATUSES)
        .filter(Q(next_action="") | Q(next_follow_up_at__isnull=True))
    )
    if branch_id:
        leads = leads.filter(branch_id=branch_id)
    leads = list(
        leads.order_by("-score", "created_at", "id")[: min(max(limit, 1), 1000)]
    )
    follow_up_at = timezone.now() + timedelta(days=1)
    repaired_count = 0
    for lead in leads:
        update_fields = ["updated_at"]
        if not lead.next_action:
            lead.next_action = "Contact lead and confirm qualification status"
            update_fields.append("next_action")
        if not lead.next_follow_up_at:
            lead.next_follow_up_at = follow_up_at
            update_fields.append("next_follow_up_at")
        lead.full_clean()
        lead.save(update_fields=update_fields)
        repaired_count += 1
    return {"repaired_count": repaired_count, "skipped_count": 0}


@revenue_execution_router.get(
    "/playbooks/current", response={200: dict, 404: MessageSchema}
)
@require_permission("revenue_execution", "view")
def get_current_sales_playbook(
    request, division: str, stage: str, persona: str, branch_id: int = None
):
    playbooks = _playbook_queryset(request).filter(
        division=division, stage=stage, persona=persona, status="active"
    )
    playbook = None
    if branch_id:
        playbook = (
            playbooks.filter(branch_id=branch_id)
            .order_by("sort_order", "title", "id")
            .first()
        )
    if not playbook:
        playbook = (
            playbooks.filter(branch__isnull=True)
            .order_by("sort_order", "title", "id")
            .first()
        )
    if not playbook:
        return (
            404,
            {
                "detail": "No active sales playbook found for this division, stage and persona."
            },
        )
    return (200, _playbook_row(playbook, include_objections=True))


@revenue_execution_router.get("/playbooks")
@require_permission("revenue_execution", "view")
def list_sales_playbooks(
    request,
    division: str = None,
    stage: str = None,
    persona: str = None,
    status: str = None,
    branch_id: int = None,
    search: str = None,
    limit: int = 100,
):
    playbooks = _playbook_queryset(request)
    if division:
        playbooks = playbooks.filter(division=division)
    if stage:
        playbooks = playbooks.filter(stage=stage)
    if persona:
        playbooks = playbooks.filter(persona=persona)
    if status:
        playbooks = playbooks.filter(status=status)
    if branch_id:
        playbooks = playbooks.filter(branch_id=branch_id)
    if search:
        playbooks = playbooks.filter(
            Q(title__icontains=search)
            | Q(objective__icontains=search)
            | Q(opening_script__icontains=search)
            | Q(proof_to_use__icontains=search)
            | Q(primary_cta__icontains=search)
            | Q(exit_criteria__icontains=search)
        )
    limit = min(max(limit, 1), 250)
    return {
        "count": playbooks.count(),
        "filters": {
            "division": division,
            "stage": stage,
            "persona": persona,
            "status": status,
            "branch_id": branch_id,
            "search": search,
            "limit": limit,
        },
        "playbooks": [
            _playbook_row(playbook)
            for playbook in playbooks.order_by("sort_order", "title", "id")[:limit]
        ],
    }


@revenue_execution_router.post("/playbooks", response={201: dict, 400: MessageSchema})
@require_permission("revenue_execution", "create")
def create_sales_playbook(request, payload: SalesPlaybookCreateSchema):
    try:
        data = payload.dict()
        data["questions"] = data.get("questions") or []
        playbook = SalesPlaybook(created_by=request.user, **data)
        playbook.full_clean()
        playbook.save()
        return (201, _playbook_row(playbook, include_objections=True))
    except ValidationError as e:
        return (400, {"detail": _validation_detail(e)})
    except Exception as e:
        return (400, {"detail": str(e)})


@revenue_execution_router.get(
    "/playbooks/{playbook_id}", response={200: dict, 404: MessageSchema}
)
@require_permission("revenue_execution", "view")
def get_sales_playbook(request, playbook_id: int):
    playbook = get_object_or_404(_playbook_queryset(request), id=playbook_id)
    return (200, _playbook_row(playbook, include_objections=True))


@revenue_execution_router.patch(
    "/playbooks/{playbook_id}",
    response={200: dict, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("revenue_execution", "update")
def update_sales_playbook(
    request, playbook_id: int, payload: SalesPlaybookUpdateSchema
):
    try:
        playbook = get_object_or_404(_playbook_queryset(request), id=playbook_id)
        update_data = payload.dict(exclude_unset=True)
        if update_data.get("questions") is None and "questions" in update_data:
            update_data["questions"] = []
        for field, value in update_data.items():
            setattr(playbook, field, value)
        playbook.full_clean()
        playbook.save()
        return (200, _playbook_row(playbook, include_objections=True))
    except ValidationError as e:
        return (400, {"detail": _validation_detail(e)})
    except Exception as e:
        return (400, {"detail": str(e)})


@revenue_execution_router.delete(
    "/playbooks/{playbook_id}", response={200: MessageSchema, 404: MessageSchema}
)
@require_permission("revenue_execution", "update")
def archive_sales_playbook(request, playbook_id: int):
    playbook = get_object_or_404(_playbook_queryset(request), id=playbook_id)
    playbook.status = "archived"
    playbook.full_clean()
    playbook.save(update_fields=["status", "updated_at"])
    return (200, {"detail": "Sales playbook archived successfully."})


@revenue_execution_router.post(
    "/playbooks/{playbook_id}/objections",
    response={201: dict, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("revenue_execution", "create")
def create_sales_playbook_objection(
    request, playbook_id: int, payload: SalesPlaybookObjectionCreateSchema
):
    try:
        playbook = get_object_or_404(_playbook_queryset(request), id=playbook_id)
        objection = SalesPlaybookObjection(playbook=playbook, **payload.dict())
        objection.full_clean()
        objection.save()
        return (201, _playbook_objection_row(objection))
    except ValidationError as e:
        return (400, {"detail": _validation_detail(e)})
    except Exception as e:
        return (400, {"detail": str(e)})


@revenue_execution_router.patch(
    "/playbooks/objections/{objection_id}",
    response={200: dict, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("revenue_execution", "update")
def update_sales_playbook_objection(
    request, objection_id: int, payload: SalesPlaybookObjectionUpdateSchema
):
    try:
        objection = get_object_or_404(
            _playbook_objection_queryset(request), id=objection_id
        )
        for field, value in payload.dict(exclude_unset=True).items():
            setattr(objection, field, value)
        objection.full_clean()
        objection.save()
        return (200, _playbook_objection_row(objection))
    except ValidationError as e:
        return (400, {"detail": _validation_detail(e)})
    except Exception as e:
        return (400, {"detail": str(e)})


@revenue_execution_router.delete(
    "/playbooks/objections/{objection_id}",
    response={200: MessageSchema, 404: MessageSchema},
)
@require_permission("revenue_execution", "update")
def deactivate_sales_playbook_objection(request, objection_id: int):
    objection = get_object_or_404(
        _playbook_objection_queryset(request), id=objection_id
    )
    objection.is_active = False
    objection.full_clean()
    objection.save(update_fields=["is_active", "updated_at"])
    return (200, {"detail": "Sales playbook objection deactivated successfully."})


@revenue_execution_router.get("/okrs")
@require_permission("revenue_execution", "view")
def list_okrs(
    request,
    period_start: date = None,
    period_end: date = None,
    branch_id: int = None,
    status: str = None,
):
    start, end = _period_bounds(period_start, period_end)
    objectives = _objective_queryset(request).filter(
        period_start__lte=end, period_end__gte=start
    )
    if branch_id:
        objectives = objectives.filter(branch_id=branch_id)
    if status:
        objectives = objectives.filter(status=status)
    objective_list = list(objectives.order_by("period_start", "sort_order", "id"))
    return {
        "counts": _okr_counts(objective_list),
        "objectives": [
            {
                "id": objective.id,
                "label": objective.title,
                "status": objective.track_status,
                "progress_percentage": objective.progress_percentage,
                "key_results": [
                    {
                        "id": key_result.id,
                        "label": key_result.title,
                        "percent": key_result.progress_percentage,
                        "color": _progress_color(key_result.progress_percentage),
                        "status": key_result.track_status,
                    }
                    for key_result in objective.key_results.all()
                ],
            }
            for objective in objective_list
        ],
    }


@revenue_execution_router.post(
    "/okrs", response={201: RevenueObjectiveOutSchema, 400: MessageSchema}
)
@require_permission("revenue_execution", "create")
def create_okr(request, payload: RevenueObjectiveCreateSchema):
    try:
        objective = RevenueObjective(created_by=request.user, **payload.dict())
        objective.full_clean()
        objective.save()
        return (201, get_object_or_404(_objective_queryset(request), id=objective.id))
    except ValidationError as e:
        return (400, {"detail": _validation_detail(e)})
    except Exception as e:
        return (400, {"detail": str(e)})


@revenue_execution_router.post(
    "/okrs/{objective_id}/key-results",
    response={201: RevenueKeyResultOutSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("revenue_execution", "create")
def create_key_result(
    request, objective_id: int, payload: RevenueKeyResultCreateSchema
):
    try:
        objective = get_object_or_404(_objective_queryset(request), id=objective_id)
        key_result = RevenueKeyResult(objective=objective, **payload.dict())
        key_result.full_clean()
        key_result.save()
        return (201, get_object_or_404(_key_result_queryset(request), id=key_result.id))
    except ValidationError as e:
        return (400, {"detail": _validation_detail(e)})
    except Exception as e:
        return (400, {"detail": str(e)})


@revenue_execution_router.patch(
    "/okrs/key-results/{key_result_id}",
    response={200: RevenueKeyResultOutSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("revenue_execution", "update")
def update_key_result(
    request, key_result_id: int, payload: RevenueKeyResultUpdateSchema
):
    try:
        key_result = get_object_or_404(_key_result_queryset(request), id=key_result_id)
        return (
            200,
            _apply_key_result_payload(key_result, payload.dict(exclude_unset=True)),
        )
    except ValidationError as e:
        return (400, {"detail": _validation_detail(e)})
    except Exception as e:
        return (400, {"detail": str(e)})


@revenue_execution_router.patch(
    "/okrs/{objective_id}",
    response={200: RevenueObjectiveOutSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("revenue_execution", "update")
def update_okr(request, objective_id: int, payload: RevenueObjectiveUpdateSchema):
    try:
        objective = get_object_or_404(_objective_queryset(request), id=objective_id)
        return (
            200,
            _apply_objective_payload(objective, payload.dict(exclude_unset=True)),
        )
    except ValidationError as e:
        return (400, {"detail": _validation_detail(e)})
    except Exception as e:
        return (400, {"detail": str(e)})


@revenue_execution_router.get("/targets/summary")
@require_permission("revenue_execution", "view")
def get_targets_summary(
    request,
    period_start: date = None,
    period_end: date = None,
    period: str = None,
    role_id: int = None,
    branch_id: int = None,
):
    start, end = _period_bounds(period_start, period_end)
    templates = RoleTargetTemplate.objects.select_related("role").filter(is_active=True)
    targets = with_target_progress(
        EmployeeTarget.objects.select_related(
            "employee",
            "employee__user",
            "employee__branch",
            "role",
            "role_target_template",
        ).filter(period_start__lte=end, period_end__gte=start, is_active=True)
    )
    if period:
        templates = templates.filter(period=period)
        targets = targets.filter(period=period)
    if role_id:
        templates = templates.filter(role_id=role_id)
        targets = targets.filter(role_id=role_id)
    if branch_id:
        targets = targets.filter(employee__branch_id=branch_id)
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if branch_ids:
        targets = targets.filter(employee__branch_id__in=branch_ids)
    target_rows = []
    for target in targets.order_by("employee__employee_id", "sequence", "id"):
        progress_value = target.get_approved_progress_value()
        progress_percentage = target.get_progress_percentage()
        target_rows.append(
            {
                "id": target.id,
                "template_id": target.role_target_template_id,
                "label": target.title,
                "target": target.target_value,
                "actual": progress_value,
                "current_actual": progress_value,
                "progress_percentage": progress_percentage,
                "color": _progress_color(progress_percentage),
                "unit": target.unit,
                "period": target.period,
                "editable": True,
            }
        )
    existing_template_ids = {
        row["template_id"] for row in target_rows if row["template_id"]
    }
    for template in templates.exclude(id__in=existing_template_ids).order_by(
        "role__name", "sequence", "id"
    ):
        target_rows.append(
            {
                "id": None,
                "template_id": template.id,
                "label": template.title,
                "target": template.target_value,
                "actual": Decimal("0.00"),
                "current_actual": Decimal("0.00"),
                "progress_percentage": Decimal("0.00"),
                "color": "#DC2626",
                "unit": template.unit,
                "period": template.period,
                "editable": True,
            }
        )
    total_target_value = sum((row["target"] or Decimal("0.00") for row in target_rows))
    total_actual_value = sum((row["actual"] or Decimal("0.00") for row in target_rows))
    return {
        "period": {"start": start, "end": end, "period": period},
        "target_rows": target_rows,
        "summary": {
            "target_count": len(target_rows),
            "target_value": total_target_value,
            "actual_value": total_actual_value,
            "target_progress_percentage": _decimal_pct(
                total_actual_value, total_target_value
            ),
        },
    }


@revenue_execution_router.get(
    "/turnaround/plans", response=List[TurnaroundPlanOutSchema]
)
@require_permission("revenue_execution", "list")
def list_turnaround_plans(request, status: str = None, branch_id: int = None):
    plans = _turnaround_plan_queryset(request)
    if status:
        plans = plans.filter(status=status)
    if branch_id:
        plans = plans.filter(branch_id=branch_id)
    return plans


@revenue_execution_router.post(
    "/turnaround/plans", response={201: TurnaroundPlanOutSchema, 400: MessageSchema}
)
@require_permission("revenue_execution", "create")
def create_turnaround_plan(request, payload: TurnaroundPlanCreateSchema):
    try:
        data = payload.dict()
        if not data.get("end_date"):
            data["end_date"] = _turnaround_end_date(data["start_date"])
        with transaction.atomic():
            plan = TurnaroundPlan(created_by=request.user, **data)
            plan.full_clean()
            plan.save()
            _seed_turnaround_actions(plan)
        return (201, get_object_or_404(_turnaround_plan_queryset(request), id=plan.id))
    except ValidationError as e:
        return (400, {"detail": _validation_detail(e)})
    except Exception as e:
        return (400, {"detail": str(e)})


@revenue_execution_router.get(
    "/turnaround/plans/active",
    response={200: TurnaroundPlanDetailSchema, 404: MessageSchema},
)
@require_permission("revenue_execution", "view")
def get_active_turnaround_plan(request, branch_id: int = None):
    plans = _turnaround_plan_queryset(request).filter(status="active")
    if branch_id:
        plans = plans.filter(branch_id=branch_id)
    else:
        plans = plans.filter(branch__isnull=True)
    plan = plans.first()
    if not plan:
        return (404, {"detail": "No active turnaround plan found."})
    return (200, _turnaround_detail(plan))


@revenue_execution_router.get(
    "/turnaround/plans/{plan_id}",
    response={200: TurnaroundPlanDetailSchema, 404: MessageSchema},
)
@require_permission("revenue_execution", "view")
def get_turnaround_plan(request, plan_id: int):
    plan = get_object_or_404(_turnaround_plan_queryset(request), id=plan_id)
    return (200, _turnaround_detail(plan))


@revenue_execution_router.patch(
    "/turnaround/plans/{plan_id}",
    response={200: TurnaroundPlanOutSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("revenue_execution", "update")
def update_turnaround_plan(request, plan_id: int, payload: TurnaroundPlanUpdateSchema):
    try:
        plan = get_object_or_404(_turnaround_plan_queryset(request), id=plan_id)
        return (
            200,
            _apply_turnaround_plan_payload(plan, payload.dict(exclude_unset=True)),
        )
    except ValidationError as e:
        return (400, {"detail": _validation_detail(e)})
    except Exception as e:
        return (400, {"detail": str(e)})


@revenue_execution_router.post(
    "/turnaround/plans/{plan_id}/activate",
    response={200: TurnaroundPlanOutSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("revenue_execution", "update")
def activate_turnaround_plan(request, plan_id: int):
    try:
        plan = get_object_or_404(_turnaround_plan_queryset(request), id=plan_id)
        return (200, _activate_turnaround_plan(plan))
    except ValidationError as e:
        return (400, {"detail": _validation_detail(e)})
    except Exception as e:
        return (400, {"detail": str(e)})


@revenue_execution_router.post(
    "/turnaround/plans/{plan_id}/close",
    response={200: TurnaroundPlanOutSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("revenue_execution", "update")
def close_turnaround_plan(request, plan_id: int):
    try:
        plan = get_object_or_404(_turnaround_plan_queryset(request), id=plan_id)
        plan.status = "closed"
        plan.full_clean()
        plan.save()
        return (200, plan)
    except ValidationError as e:
        return (400, {"detail": _validation_detail(e)})
    except Exception as e:
        return (400, {"detail": str(e)})


@revenue_execution_router.patch(
    "/turnaround/actions/{action_id}",
    response={200: TurnaroundActionOutSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("revenue_execution", "update")
def update_turnaround_action(
    request, action_id: int, payload: TurnaroundActionUpdateSchema
):
    try:
        action = get_object_or_404(_turnaround_action_queryset(request), id=action_id)
        return (
            200,
            _apply_turnaround_action_payload(action, payload.dict(exclude_unset=True)),
        )
    except ValidationError as e:
        return (400, {"detail": _validation_detail(e)})
    except Exception as e:
        return (400, {"detail": str(e)})


@revenue_execution_router.post(
    "/turnaround/actions/{action_id}/complete",
    response={200: TurnaroundActionOutSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("revenue_execution", "complete")
def complete_turnaround_action(
    request, action_id: int, payload: TurnaroundActionCompleteSchema
):
    try:
        action = get_object_or_404(_turnaround_action_queryset(request), id=action_id)
        action.status = "completed"
        action.completed_at = timezone.now()
        action.completed_by = request.user
        action.completion_note = payload.completion_note or ""
        action.full_clean()
        action.save()
        return (200, action)
    except ValidationError as e:
        return (400, {"detail": _validation_detail(e)})
    except Exception as e:
        return (400, {"detail": str(e)})


@revenue_execution_router.post(
    "/turnaround/actions/{action_id}/reopen",
    response={200: TurnaroundActionOutSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("revenue_execution", "complete")
def reopen_turnaround_action(request, action_id: int):
    try:
        action = get_object_or_404(_turnaround_action_queryset(request), id=action_id)
        action.status = "open"
        action.completed_at = None
        action.completed_by = None
        action.completion_note = ""
        action.full_clean()
        action.save()
        return (200, action)
    except ValidationError as e:
        return (400, {"detail": _validation_detail(e)})
    except Exception as e:
        return (400, {"detail": str(e)})


@revenue_execution_router.get("/turnaround/plans/{plan_id}/export")
@require_permission("revenue_execution", "view")
def export_turnaround_plan(request, plan_id: int):
    plan = get_object_or_404(_turnaround_plan_queryset(request), id=plan_id)
    rows = [["Phase", "Action", "Owner", "Week", "Status"]]
    for action in plan.actions.order_by("sort_order", "week_start"):
        week = (
            f"Week {action.week_start}"
            if action.week_start == action.week_end
            else f"Week {action.week_start}-{action.week_end}"
        )
        rows.append(
            [
                action.get_phase_display(),
                action.title,
                action.owner_text or _employee_name(action.owner) or "",
                week,
                action.get_status_display(),
            ]
        )
    csv_body = "\n".join(
        (
            ",".join(
                (f'"{str(value).replace(chr(34), chr(34) + chr(34))}"' for value in row)
            )
            for row in rows
        )
    )
    response = HttpResponse(csv_body, content_type="text/csv")
    response["Content-Disposition"] = (
        'attachment; filename="bomach-13-week-turnaround.csv"'
    )
    return response


@revenue_execution_router.get(
    "/action-templates", response=List[DailyActionTemplateOutSchema]
)
@require_permission("revenue_execution", "list")
def list_action_templates(request, active: bool = None, branch_id: int = None):
    templates = _template_queryset(request)
    if active is not None:
        templates = templates.filter(is_active=active)
    if branch_id:
        templates = templates.filter(branch_id=branch_id)
    return templates


@revenue_execution_router.post(
    "/action-templates",
    response={201: DailyActionTemplateOutSchema, 400: MessageSchema},
)
@require_permission("revenue_execution", "create")
def create_action_template(request, payload: DailyActionTemplateCreateSchema):
    try:
        template = DailyActionTemplate(created_by=request.user, **payload.dict())
        template.full_clean()
        template.save()
        return (201, template)
    except ValidationError as e:
        return (400, {"detail": _validation_detail(e)})
    except Exception as e:
        return (400, {"detail": str(e)})


@revenue_execution_router.patch(
    "/action-templates/{template_id}",
    response={
        200: DailyActionTemplateOutSchema,
        400: MessageSchema,
        404: MessageSchema,
    },
)
@require_permission("revenue_execution", "update")
def update_action_template(
    request, template_id: int, payload: DailyActionTemplateUpdateSchema
):
    try:
        template = get_object_or_404(_template_queryset(request), id=template_id)
        return (
            200,
            _apply_template_payload(template, payload.dict(exclude_unset=True)),
        )
    except ValidationError as e:
        return (400, {"detail": _validation_detail(e)})
    except Exception as e:
        return (400, {"detail": str(e)})


@revenue_execution_router.delete(
    "/action-templates/{template_id}", response={200: MessageSchema, 404: MessageSchema}
)
@require_permission("revenue_execution", "delete")
def delete_action_template(request, template_id: int):
    template = get_object_or_404(_template_queryset(request), id=template_id)
    template.delete()
    return (200, {"detail": "Daily action template deleted successfully"})


@revenue_execution_router.get("/days/today", response=DailyExecutionDayOutSchema)
@require_permission("revenue_execution", "view")
def get_today(request, branch_id: int = None):
    today = timezone.localdate()
    return get_object_or_404(_day_queryset(request), date=today, branch_id=branch_id)


@revenue_execution_router.post(
    "/days/open", response={200: DailyExecutionDayOutSchema, 400: MessageSchema}
)
@require_permission("revenue_execution", "create")
def open_day(request, payload: OpenDailyExecutionDaySchema):
    try:
        target_date = payload.date or timezone.localdate()
        day = _open_day(
            request,
            target_date=target_date,
            branch_id=payload.branch_id,
            force_rebuild=payload.force_rebuild or False,
        )
        return (200, day)
    except ValidationError as e:
        return (400, {"detail": _validation_detail(e)})
    except Exception as e:
        return (400, {"detail": str(e)})


@revenue_execution_router.get("/days/{day_date}", response=DailyExecutionDayOutSchema)
@require_permission("revenue_execution", "view")
def get_day(request, day_date: date, branch_id: int = None):
    return get_object_or_404(_day_queryset(request), date=day_date, branch_id=branch_id)


@revenue_execution_router.patch(
    "/actions/{action_id}",
    response={
        200: DailyActionInstanceOutSchema,
        400: MessageSchema,
        404: MessageSchema,
    },
)
@require_permission("revenue_execution", "update")
def update_action(request, action_id: int, payload: DailyActionInstanceUpdateSchema):
    try:
        action = get_object_or_404(_action_queryset(request), id=action_id)
        return (200, _apply_action_payload(action, payload.dict(exclude_unset=True)))
    except ValidationError as e:
        return (400, {"detail": _validation_detail(e)})
    except Exception as e:
        return (400, {"detail": str(e)})


@revenue_execution_router.post(
    "/actions/{action_id}/complete",
    response={
        200: DailyActionInstanceOutSchema,
        400: MessageSchema,
        404: MessageSchema,
    },
)
@require_permission("revenue_execution", "complete")
def complete_action(request, action_id: int, payload: DailyActionCompleteSchema):
    try:
        action = get_object_or_404(_action_queryset(request), id=action_id)
        action.status = "completed"
        action.completed_at = timezone.now()
        action.completed_by = request.user
        action.completion_note = payload.completion_note or ""
        action.full_clean()
        action.save()
        return (200, action)
    except ValidationError as e:
        return (400, {"detail": _validation_detail(e)})
    except Exception as e:
        return (400, {"detail": str(e)})


@revenue_execution_router.post(
    "/actions/{action_id}/reopen",
    response={
        200: DailyActionInstanceOutSchema,
        400: MessageSchema,
        404: MessageSchema,
    },
)
@require_permission("revenue_execution", "complete")
def reopen_action(request, action_id: int):
    try:
        action = get_object_or_404(_action_queryset(request), id=action_id)
        action.status = "open"
        action.completed_at = None
        action.completed_by = None
        action.completion_note = ""
        action.full_clean()
        action.save()
        return (200, action)
    except ValidationError as e:
        return (400, {"detail": _validation_detail(e)})
    except Exception as e:
        return (400, {"detail": str(e)})


@revenue_execution_router.get("/summary", response=DailyExecutionSummarySchema)
@require_permission("revenue_execution", "view")
def get_summary(request, date: date = None, branch_id: int = None):
    target_date = date or timezone.localdate()
    day = _day_queryset(request).filter(date=target_date, branch_id=branch_id).first()
    total, completed, open_count, completion_pct = (
        _completion_counts(day) if day else (0, 0, 0, 0)
    )
    leads = _lead_queryset(request)
    if branch_id:
        leads = leads.filter(branch_id=branch_id)
    end_of_day = timezone.make_aware(datetime.combine(target_date, time.max))
    now = timezone.now()
    active_leads = leads.filter(status__in=Lead.ACTIVE_STATUSES)
    sla_breaches = sum(
        (1 for lead in active_leads if _lead_sla_status(lead, now) == "breached")
    )
    hot = active_leads.filter(score__gte=75).count()
    next_actions_due = active_leads.filter(
        next_follow_up_at__isnull=False, next_follow_up_at__lte=end_of_day
    ).count()
    return {
        "date": target_date,
        "completion_pct": completion_pct,
        "total_actions": total,
        "completed_actions": completed,
        "open_actions": open_count,
        "sla_breaches": sla_breaches,
        "hot_opportunities": hot,
        "next_actions_due": next_actions_due,
    }


@revenue_execution_router.get(
    "/monthly-summary", response=MonthlyExecutionSummarySchema
)
@require_permission("revenue_execution", "view")
def get_monthly_summary(request, month: str, branch_id: int = None):
    year, month_num = [int(part) for part in month.split("-")]
    start = date(year, month_num, 1)
    if month_num == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month_num + 1, 1)
    days = _day_queryset(request).filter(date__gte=start, date__lt=end)
    if branch_id:
        days = days.filter(branch_id=branch_id)
    total_days = days.count()
    completion_values = [_completion_counts(day)[3] for day in days]
    average_completion = (
        round(sum(completion_values) / total_days, 2) if total_days else 0.0
    )
    fully_completed = sum((1 for value in completion_values if value == 100))
    actions = _action_queryset(request).filter(day__date__gte=start, day__date__lt=end)
    if branch_id:
        actions = actions.filter(day__branch_id=branch_id)
    return {
        "month": month,
        "total_days": total_days,
        "fully_completed_days": fully_completed,
        "average_completion_pct": average_completion,
        "open_actions": actions.filter(status="open").count(),
        "completed_actions": actions.filter(status="completed").count(),
    }


@revenue_execution_router.get(
    "/speed-to-lead-queue", response=List[SpeedToLeadQueueItemSchema]
)
@require_permission("revenue_execution", "view")
def get_speed_to_lead_queue(request, branch_id: int = None, limit: int = 20):
    leads = _lead_queryset(request).filter(status__in=Lead.ACTIVE_STATUSES)
    if branch_id:
        leads = leads.filter(branch_id=branch_id)
    now = timezone.now()
    queue = []
    for lead in leads:
        sla_status = _lead_sla_status(lead, now)
        should_include = (
            sla_status in ["breached", "due_now"]
            or (
                lead.status == "new"
                and (not lead.first_response_at)
                and (not lead.first_contact_at)
            )
            or lead.score >= 75
            or lead.is_stale
        )
        if not should_include:
            continue
        queue.append(
            {
                "lead_id": lead.id,
                "full_name": lead.full_name,
                "source": lead.get_source_display(),
                "division": lead.get_division_display(),
                "score": lead.score,
                "priority": lead.priority,
                "sla_status": sla_status,
                "first_response_due_at": lead.first_response_due_at,
                "assigned_to_name": _employee_name(lead.assigned_to),
                "recommended_action": _recommended_action(lead, sla_status),
            }
        )
    return sorted(
        queue,
        key=lambda item: (
            item["sla_status"] != "breached",
            item["sla_status"] != "due_now",
            -item["score"],
        ),
    )[:limit]


@revenue_execution_router.get(
    "/activity-scorecard", response=List[ActivityScorecardRowSchema]
)
@require_permission("revenue_execution", "view")
def get_activity_scorecard(request, date: date = None, branch_id: int = None):
    target_date = date or timezone.localdate()
    start, end = _date_bounds(target_date)
    activities = _activity_queryset(request).filter(
        created_at__gte=start, created_at__lte=end
    )
    actions = _action_queryset(request).filter(day__date=target_date)
    leads = _lead_queryset(request)
    if branch_id:
        activities = activities.filter(lead__branch_id=branch_id)
        actions = actions.filter(day__branch_id=branch_id)
        leads = leads.filter(branch_id=branch_id)
    employees = {}
    for activity in activities:
        employee = None
        if activity.created_by:
            employee = getattr(activity.created_by, "employee_profile", None)
        employee = employee or activity.lead.assigned_to
        label = _role_label(employee)
        employees.setdefault(
            label,
            {
                "activities": 0,
                "completed": 0,
                "assigned": 0,
                "sla_total": 0,
                "sla_done": 0,
            },
        )
        employees[label]["activities"] += 1
    for action in actions:
        label = _role_label(action.owner)
        employees.setdefault(
            label,
            {
                "activities": 0,
                "completed": 0,
                "assigned": 0,
                "sla_total": 0,
                "sla_done": 0,
            },
        )
        employees[label]["assigned"] += 1
        if action.status == "completed":
            employees[label]["completed"] += 1
    for lead in leads.filter(created_at__date=target_date):
        label = _role_label(lead.assigned_to)
        employees.setdefault(
            label,
            {
                "activities": 0,
                "completed": 0,
                "assigned": 0,
                "sla_total": 0,
                "sla_done": 0,
            },
        )
        employees[label]["sla_total"] += 1
        if _lead_sla_status(lead) == "completed":
            employees[label]["sla_done"] += 1
    rows = []
    for label, metrics in sorted(employees.items()):
        action_score = (
            round(metrics["completed"] / metrics["assigned"] * 100)
            if metrics["assigned"]
            else 0
        )
        activity_score = min(100, metrics["activities"] * 10)
        sla_score = (
            round(metrics["sla_done"] / metrics["sla_total"] * 100)
            if metrics["sla_total"]
            else 0
        )
        score_parts = [
            value for value in [action_score, activity_score, sla_score] if value
        ]
        score = round(sum(score_parts) / len(score_parts)) if score_parts else 0
        if metrics["assigned"] and metrics["completed"] < metrics["assigned"]:
            focus = "Close open non-negotiable actions"
        elif metrics["sla_total"] and metrics["sla_done"] < metrics["sla_total"]:
            focus = "Improve first-response SLA"
        elif metrics["activities"] == 0:
            focus = "Log customer-facing activity"
        else:
            focus = "Maintain execution pace"
        rows.append(
            {
                "role": label,
                "daily_standard": "Complete assigned actions and log lead activity",
                "actual": f"{metrics['activities']} activities · {metrics['completed']}/{metrics['assigned']} actions · {metrics['sla_done']}/{metrics['sla_total']} SLA",
                "score": score,
                "manager_focus": focus,
            }
        )
    return rows
