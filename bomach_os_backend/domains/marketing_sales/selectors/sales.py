"""Read/query layer for Sales, funnel, pipeline and revenue execution."""

from datetime import (
    datetime,
    time,
    timedelta,
)
from decimal import Decimal

from django.db.models import Q, Sum
from django.utils import timezone

from domains.marketing_sales.constants import (
    FORECAST_DEFAULT_TARGET,
    FORECAST_SCENARIOS,
    FORECAST_STAGE_AGE_LIMIT_DAYS,
    FUNNEL_LEAK_FIXES,
    FUNNEL_STAGE_LABELS,
    LEAD_STATUS_FORECAST_WEIGHTS,
    TURNAROUND_EVIDENCE,
    TURNAROUND_GOVERNANCE_RULES,
    TURNAROUND_PERFORMANCE_CONTRACTS,
    TURNAROUND_PHASES,
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
from domains.marketing_sales.presenters import (
    _revenue_lead_sla_status as _lead_sla_status,
)
from domains.marketing_sales.presenters import _revenue_money_display as _money_display
from domains.marketing_sales.presenters import (
    _revenue_normalized_scenario as _normalized_scenario,
)
from domains.marketing_sales.presenters import _revenue_pct as _pct
from domains.marketing_sales.presenters import (
    _revenue_quality_control_status as _quality_control_status,
)
from domains.marketing_sales.presenters import (
    _revenue_turnaround_kpis as _turnaround_kpis,
)
from user.models.employee import Employee
from user.models.role_targets import EmployeeTarget
from user.utils.perm import scope_queryset


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


def _revenue_day_queryset(request):
    qs = DailyExecutionDay.objects.select_related(
        "branch", "opened_by"
    ).prefetch_related(
        "actions",
        "actions__owner",
        "actions__owner__user",
        "actions__completed_by",
        "actions__template",
    )
    return scope_queryset(request, qs, branch_field="branch_id")


def _revenue_template_queryset(request):
    qs = DailyActionTemplate.objects.select_related(
        "branch", "default_owner", "default_owner__user", "created_by"
    )
    return scope_queryset(request, qs, branch_field="branch_id")


def _revenue_action_queryset(request):
    qs = DailyActionInstance.objects.select_related(
        "day", "day__branch", "template", "owner", "owner__user", "completed_by"
    )
    return scope_queryset(request, qs, branch_field="day__branch_id")


def _revenue_lead_queryset(request):
    qs = Lead.objects.select_related(
        "assigned_to", "assigned_to__user", "assigned_to__role", "branch"
    )
    return scope_queryset(request, qs, branch_field="branch_id")


def _revenue_activity_queryset(request):
    qs = LeadActivity.objects.select_related(
        "lead",
        "lead__assigned_to",
        "lead__assigned_to__user",
        "lead__assigned_to__role",
        "created_by",
    )
    return scope_queryset(request, qs, branch_field="lead__branch_id")


def _revenue_turnaround_plan_queryset(request):
    qs = TurnaroundPlan.objects.select_related(
        "branch", "primary_owner", "primary_owner__user", "created_by"
    ).prefetch_related(
        "actions", "actions__owner", "actions__owner__user", "actions__completed_by"
    )
    return scope_queryset(request, qs, branch_field="branch_id")


def _revenue_turnaround_action_queryset(request):
    qs = TurnaroundAction.objects.select_related(
        "plan", "plan__branch", "owner", "owner__user", "completed_by"
    )
    return scope_queryset(request, qs, branch_field="plan__branch_id")


def _revenue_objective_queryset(request):
    qs = RevenueObjective.objects.select_related(
        "branch", "owner", "owner__user", "created_by"
    ).prefetch_related(
        "key_results",
        "key_results__linked_employee_target",
        "key_results__linked_kpi_record",
    )
    return scope_queryset(request, qs, branch_field="branch_id")


def _revenue_key_result_queryset(request):
    qs = RevenueKeyResult.objects.select_related(
        "objective", "objective__branch", "linked_employee_target", "linked_kpi_record"
    )
    return scope_queryset(request, qs, branch_field="objective__branch_id")


def _revenue_playbook_queryset(request):
    qs = SalesPlaybook.objects.select_related("branch", "created_by").prefetch_related(
        "objections"
    )
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if branch_ids:
        return qs.filter(Q(branch_id__in=branch_ids) | Q(branch__isnull=True))
    return qs


def _revenue_playbook_objection_queryset(request):
    qs = SalesPlaybookObjection.objects.select_related("playbook", "playbook__branch")
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if branch_ids:
        return qs.filter(
            Q(playbook__branch_id__in=branch_ids) | Q(playbook__branch__isnull=True)
        )
    return qs


def _revenue_funnel_event_queryset(request):
    qs = LeadFunnelEvent.objects.select_related("lead", "branch", "campaign", "actor")
    return scope_queryset(request, qs, branch_field="branch_id")


def _revenue_date_bounds(day):
    start = timezone.make_aware(datetime.combine(day, time.min))
    end = timezone.make_aware(datetime.combine(day, time.max))
    return (start, end)


def _revenue_period_bounds(period_start=None, period_end=None):
    today = timezone.localdate()
    start = period_start or today.replace(day=1)
    end = period_end or today
    return (start, end)


def _revenue_decimal_sum(queryset, field_name):
    total = queryset.aggregate(total=Sum(field_name))["total"] or Decimal("0.00")
    return (
        total.quantize(Decimal("0.01"))
        if isinstance(total, Decimal)
        else Decimal(total).quantize(Decimal("0.01"))
    )


def _revenue_scenario_factor(scenario):
    return FORECAST_SCENARIOS.get(scenario or "base", FORECAST_SCENARIOS["base"])[
        "factor"
    ]


def _revenue_weighted_forecast_value(leads, factor=Decimal("1.00")):
    weighted = Decimal("0.00")
    for row in leads.values("status").annotate(total=Sum("estimated_value")):
        weighted += (
            row["total"] or Decimal("0.00")
        ) * LEAD_STATUS_FORECAST_WEIGHTS.get(row["status"], Decimal("0.00"))
    return (weighted * factor).quantize(Decimal("0.01"))


def _revenue_revenue_target_value(start, end, branch_id=None):
    revenue_targets = EmployeeTarget.objects.filter(
        period_start__lte=end,
        period_end__gte=start,
        title__icontains="revenue",
        is_active=True,
    )
    if branch_id:
        revenue_targets = revenue_targets.filter(employee__branch_id=branch_id)
    return (
        _revenue_decimal_sum(revenue_targets, "target_value") or FORECAST_DEFAULT_TARGET
    )


def _revenue_forecast_quality_controls(active_leads, now=None):
    now = now or timezone.now()
    total = active_leads.count()
    value_pct = _decimal_pct(
        active_leads.filter(estimated_value__gt=Decimal("0.00")).count(), total
    )
    next_action_pct = _decimal_pct(
        active_leads.exclude(next_action="")
        .filter(next_follow_up_at__isnull=False)
        .count(),
        total,
    )
    stage_age_pct = _decimal_pct(
        active_leads.filter(
            updated_at__gte=now - timedelta(days=FORECAST_STAGE_AGE_LIMIT_DAYS)
        ).count(),
        total,
    )
    supported_values = [value_pct, next_action_pct, stage_age_pct]
    confidence = (
        sum(supported_values, Decimal("0.00")) / Decimal(len(supported_values))
        if supported_values
        else Decimal("0.00")
    ).quantize(Decimal("0.01"))
    controls = [
        {
            "key": "value_present",
            "label": "All opportunities have value",
            "supported": True,
            "value": value_pct,
            "display_value": f"{value_pct}%",
            "status": _quality_control_status(value_pct),
        },
        {
            "key": "next_action_scheduled",
            "label": "Next action scheduled",
            "supported": True,
            "value": next_action_pct,
            "display_value": f"{next_action_pct}%",
            "status": _quality_control_status(next_action_pct),
        },
        {
            "key": "stage_age_within_limit",
            "label": "Stage-age within limit",
            "supported": True,
            "value": stage_age_pct,
            "display_value": f"{stage_age_pct}%",
            "status": _quality_control_status(stage_age_pct),
            "limit_days": FORECAST_STAGE_AGE_LIMIT_DAYS,
        },
        {
            "key": "close_date_verified",
            "label": "Close date verified",
            "supported": False,
            "value": None,
            "display_value": "Not tracked",
            "status": "unsupported",
            "reason": "Revenue execution leads do not have expected close dates yet.",
        },
        {
            "key": "decision_maker_recorded",
            "label": "Decision-maker recorded",
            "supported": False,
            "value": None,
            "display_value": "Not tracked",
            "status": "unsupported",
            "reason": "Lead 360 does not have a structured decision-maker field yet.",
        },
    ]
    return (controls, confidence)


def _revenue_forecast_division_rows(active_leads, factor):
    rows = []
    for division_key, division_label in Lead.DIVISION_CHOICES:
        division_leads = active_leads.filter(division=division_key)
        opportunity_count = division_leads.count()
        if not opportunity_count:
            continue
        pipeline_value = _revenue_decimal_sum(division_leads, "estimated_value")
        weighted_forecast = _revenue_weighted_forecast_value(
            division_leads, factor=factor
        )
        rows.append(
            {
                "division": division_key,
                "division_label": division_label,
                "opportunities": opportunity_count,
                "pipeline": pipeline_value,
                "display_pipeline": _money_display(pipeline_value),
                "weighted_forecast": weighted_forecast,
                "display_weighted_forecast": _money_display(weighted_forecast),
                "target": None,
                "target_gap": None,
                "display_target_gap": "Not allocated",
            }
        )
    return rows


def _revenue_forecast_methodology():
    return {
        "source": "lead",
        "source_label": "Lead-derived forecast",
        "status_weights": [
            {
                "status": status,
                "label": label,
                "weight": LEAD_STATUS_FORECAST_WEIGHTS.get(status, Decimal("0.00")),
            }
            for status, label in Lead.STATUS_CHOICES
        ],
        "limitations": [
            "This slice does not use the legacy Deal pipeline module.",
            "Expected close dates are not tracked on revenue execution leads.",
            "Decision-maker and close-date confidence controls are reported as unsupported.",
            "Division-level target gaps are not calculated until targets are allocated by division.",
        ],
    }


def _revenue_forecast_payload(
    request,
    period_start=None,
    period_end=None,
    branch_id=None,
    division=None,
    scenario="base",
):
    start, end = _revenue_period_bounds(period_start, period_end)
    scenario_key = _normalized_scenario(scenario)
    factor = _revenue_scenario_factor(scenario_key)
    leads = _revenue_lead_queryset(request)
    if branch_id:
        leads = leads.filter(branch_id=branch_id)
    if division:
        leads = leads.filter(division=division)
    active_leads = leads.filter(status__in=Lead.ACTIVE_STATUSES)
    target = _revenue_revenue_target_value(start, end, branch_id=branch_id)
    unweighted_pipeline = _revenue_decimal_sum(active_leads, "estimated_value")
    weighted_forecast = _revenue_weighted_forecast_value(active_leads, factor=factor)
    base_weighted_forecast = _revenue_weighted_forecast_value(active_leads)
    target_gap = max(target - weighted_forecast, Decimal("0.00"))
    pipeline_coverage = (
        (unweighted_pipeline / target).quantize(Decimal("0.01"))
        if target
        else Decimal("0.00")
    )
    quality_controls, forecast_confidence = _revenue_forecast_quality_controls(
        active_leads
    )
    return {
        "period": {"start": start, "end": end},
        "filters": {
            "branch_id": branch_id,
            "division": division,
            "scenario": scenario_key,
        },
        "hero": {
            "weighted_forecast": weighted_forecast,
            "display_weighted_forecast": _money_display(weighted_forecast),
            "base_weighted_forecast": base_weighted_forecast,
            "target": target,
            "display_target": _money_display(target),
            "progress_percentage": _decimal_pct(weighted_forecast, target),
            "target_gap": target_gap,
            "display_target_gap": _money_display(target_gap),
            "scenario": scenario_key,
            "scenario_label": FORECAST_SCENARIOS[scenario_key]["label"],
            "target_scope": "overall",
        },
        "kpi_cards": [
            {
                "key": "unweighted_pipeline",
                "label": "Unweighted pipeline",
                "value": unweighted_pipeline,
                "display_value": _money_display(unweighted_pipeline),
                "foot": "All active opportunity values",
            },
            {
                "key": "pipeline_coverage",
                "label": "Pipeline coverage",
                "value": pipeline_coverage,
                "display_value": f"{pipeline_coverage}×",
                "foot": "Target operating range: 3×–4×",
            },
            {
                "key": "forecast_confidence",
                "label": "Forecast confidence",
                "value": forecast_confidence,
                "display_value": f"{forecast_confidence}%",
                "foot": "Based only on supported data-quality controls",
            },
            {
                "key": "target_gap",
                "label": "Target gap",
                "value": target_gap,
                "display_value": _money_display(target_gap),
                "foot": "Additional weighted forecast required",
            },
        ],
        "quality_controls": quality_controls,
        "division_rows": _revenue_forecast_division_rows(active_leads, factor),
        "scenario_options": [
            {
                "key": key,
                "label": option["label"],
                "factor": option["factor"],
                "description": option["description"],
                "active": key == scenario_key,
            }
            for key, option in FORECAST_SCENARIOS.items()
        ],
        "methodology": _revenue_forecast_methodology(),
    }


def _revenue_templates_for_day(request, branch_id):
    templates = _revenue_template_queryset(request).filter(is_active=True)
    if branch_id:
        return templates.filter(Q(branch_id=branch_id) | Q(branch__isnull=True))
    return templates.filter(branch__isnull=True)


def _revenue_completion_counts(day):
    total = day.actions.count()
    completed = day.actions.filter(status="completed").count()
    open_count = total - completed
    completion_pct = round(completed / total * 100) if total else 0
    return (total, completed, open_count, completion_pct)


def _revenue_lead_control_kpis(leads, now):
    active_leads = list(leads.filter(status__in=Lead.ACTIVE_STATUSES))
    return [
        {
            "key": "new_uncontacted",
            "label": "New & uncontacted",
            "value": len(
                [
                    lead
                    for lead in active_leads
                    if lead.status == "new"
                    and (not lead.first_contact_at)
                    and (not lead.first_response_at)
                ]
            ),
            "foot": "Require immediate acknowledgement",
            "icon": "ti-user-exclamation",
            "bg": "#FEE2E2",
            "color": "#991B1B",
        },
        {
            "key": "sla_breaches",
            "label": "SLA breaches",
            "value": len(
                [
                    lead
                    for lead in active_leads
                    if _lead_sla_status(lead, now) == "breached"
                ]
            ),
            "foot": "Escalate to manager",
            "icon": "ti-alarm",
            "bg": "#FEF3C7",
            "color": "#92400E",
        },
        {
            "key": "hot_leads",
            "label": "Hot leads",
            "value": len([lead for lead in active_leads if lead.score >= 75]),
            "foot": "Score 75+",
            "icon": "ti-flame",
            "bg": "#FCE7F3",
            "color": "#9D174D",
        },
        {
            "key": "stale_opportunities",
            "label": "Stale opportunities",
            "value": len([lead for lead in active_leads if lead.is_stale]),
            "foot": "12+ days without meaningful progress",
            "icon": "ti-hourglass-empty",
            "bg": "#DBEAFE",
            "color": "#1E40AF",
        },
    ]


def _revenue_eligible_revenue_employees(request, branch_id=None):
    role_filter = (
        Q(role__name__icontains="revenue")
        | Q(role__name__icontains="sales")
        | Q(role__name__icontains="marketing")
        | Q(role__name__icontains="business development")
        | Q(designation__icontains="revenue")
        | Q(designation__icontains="sales")
        | Q(designation__icontains="marketing")
        | Q(designation__icontains="business development")
        | Q(designation__icontains="customer relations")
    )
    employees = (
        Employee.objects.select_related("user", "role", "branch")
        .filter(is_active=True, employment_status="active")
        .filter(role_filter)
    )
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if branch_ids:
        employees = employees.filter(branch_id__in=branch_ids)
    if branch_id:
        employees = employees.filter(Q(branch_id=branch_id) | Q(branch__isnull=True))
    return employees.order_by("branch_id", "employee_id", "id")


def _revenue_okr_counts(objectives):
    counts = {"on_track": 0, "at_risk": 0, "off_track": 0}
    for objective in objectives:
        status = objective.track_status
        counts[status] = counts.get(status, 0) + 1
    return counts


def _revenue_first_events_by_lead(events):
    first_events = {}
    for event in events.order_by("lead_id", "occurred_at", "id"):
        first_events.setdefault(event.lead_id, event)
    return first_events


def _revenue_cohort_lead_ids(events, start, end):
    first_events = _revenue_first_events_by_lead(events)
    return {
        lead_id
        for lead_id, event in first_events.items()
        if start <= event.occurred_at.date() <= end
    }


def _revenue_stage_lead_sets(events, cohort_ids):
    return {
        stage: set(
            events.filter(lead_id__in=cohort_ids, to_stage=stage)
            .values_list("lead_id", flat=True)
            .distinct()
        )
        for stage in FUNNEL_STAGE_ORDER
    }


def _revenue_funnel_data_quality(events, cohort_ids):
    cohort_events = events.filter(lead_id__in=cohort_ids)
    total = cohort_events.count()
    backfilled = sum((1 for event in cohort_events if event.metadata.get("backfilled")))
    event_based = total - backfilled
    missing_transition_count = 0
    for lead_id in cohort_ids:
        reached = set(
            cohort_events.filter(lead_id=lead_id)
            .exclude(to_stage="")
            .values_list("to_stage", flat=True)
        )
        if len(reached) <= 1:
            missing_transition_count += 1
    real_ratio = event_based / total if total else 0
    if total == 0 or real_ratio < 0.5:
        confidence = "partial"
    elif real_ratio < 0.8:
        confidence = "medium"
    else:
        confidence = "high"
    return {
        "event_based_count": event_based,
        "backfilled_count": backfilled,
        "missing_transition_count": missing_transition_count,
        "confidence": confidence,
    }


def _revenue_lead_value_sum(leads, lead_ids):
    return leads.filter(id__in=lead_ids).aggregate(total=Sum("estimated_value"))[
        "total"
    ] or Decimal("0.00")


def _revenue_transition_leaks(stage_sets, leads):
    leaks = []
    for index, from_stage in enumerate(FUNNEL_STAGE_ORDER[:-1]):
        to_stage = FUNNEL_STAGE_ORDER[index + 1]
        current = stage_sets[from_stage]
        progressed = stage_sets[to_stage]
        lost_ids = current - progressed
        entered = len(current)
        progressed_count = len(progressed & current)
        loss_pct = round(100 - _pct(progressed_count, entered), 2) if entered else 0.0
        copy = FUNNEL_LEAK_FIXES[from_stage, to_stage]["copy"]
        fix = FUNNEL_LEAK_FIXES[from_stage, to_stage]["fix"]
        leaks.append(
            {
                "transition": f"{FUNNEL_STAGE_LABELS[from_stage]} → {FUNNEL_STAGE_LABELS[to_stage]}",
                "from_stage": from_stage,
                "to_stage": to_stage,
                "entered": entered,
                "progressed": progressed_count,
                "lost": len(lost_ids),
                "loss_pct": loss_pct,
                "revenue_impact": _revenue_lead_value_sum(leads, lost_ids),
                "copy": copy,
                "fix": fix,
            }
        )
    return sorted(
        leaks, key=lambda row: (row["loss_pct"], row["revenue_impact"]), reverse=True
    )


def _revenue_phase_summary(plan):
    actions = list(
        plan.actions.select_related("owner", "owner__user", "completed_by").order_by(
            "sort_order", "week_start", "created_at"
        )
    )
    grouped = []
    for phase, title, period in TURNAROUND_PHASES:
        phase_actions = [action for action in actions if action.phase == phase]
        total = len(phase_actions)
        completed = len(
            [action for action in phase_actions if action.status == "completed"]
        )
        grouped.append(
            {
                "phase": phase,
                "title": title,
                "period": period,
                "total_actions": total,
                "completed_actions": completed,
                "completion_pct": round(completed / total * 100) if total else 0,
                "actions": phase_actions,
            }
        )
    return grouped


def _revenue_turnaround_detail(plan):
    return {
        "plan": plan,
        "kpis": _turnaround_kpis(plan),
        "roadmap": _revenue_phase_summary(plan),
        "performance_contracts": TURNAROUND_PERFORMANCE_CONTRACTS,
        "governance_rules": [
            {"sequence": index + 1, "rule": rule}
            for index, rule in enumerate(TURNAROUND_GOVERNANCE_RULES)
        ],
        "evidence": TURNAROUND_EVIDENCE,
    }
