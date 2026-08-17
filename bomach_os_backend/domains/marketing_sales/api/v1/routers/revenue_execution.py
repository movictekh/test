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
from services.api.schema.others import MessageSchema
from services.models.crm import (
    FUNNEL_STAGE_ORDER,
    DailyActionInstance,
    DailyActionTemplate,
    DailyExecutionDay,
    Lead,
    LeadActivity,
    LeadFunnelEvent,
    RevenueKeyResult,
    RevenueObjective,
    SalesPlaybook,
    SalesPlaybookObjection,
    TurnaroundAction,
    TurnaroundPlan,
)
from user.models.branch import Branch
from user.models.employee import Employee
from user.models.role_targets import (
    EmployeeTarget,
    RoleTargetTemplate,
    with_target_progress,
)
from user.utils.perm import require_permission, scope_queryset

revenue_execution_router = Router(tags=["Revenue Execution"])


TURNAROUND_DEFAULT_ACTIONS = [
    {
        "phase": "stabilise",
        "title": "Clean CRM: owners, stages, sources, values and next actions",
        "owner_text": "Analytics + Sales",
        "week_start": 1,
        "week_end": 1,
    },
    {
        "phase": "stabilise",
        "title": "Launch lead-response SLA dashboard and escalation",
        "owner_text": "CSRC Lead",
        "week_start": 1,
        "week_end": 1,
    },
    {
        "phase": "stabilise",
        "title": "Define MQL, SQL, opportunity, won and lost criteria",
        "owner_text": "Marketing Manager",
        "week_start": 2,
        "week_end": 2,
    },
    {
        "phase": "stabilise",
        "title": "Stop campaigns with no traceable leads or revenue signal",
        "owner_text": "Digital Marketer",
        "week_start": 2,
        "week_end": 2,
    },
    {
        "phase": "standardise",
        "title": "Roll out division-specific discovery and objection playbooks",
        "owner_text": "Sales Lead",
        "week_start": 3,
        "week_end": 3,
    },
    {
        "phase": "standardise",
        "title": "Introduce 7-touch follow-up cadence with next-action automation",
        "owner_text": "CRM Admin",
        "week_start": 3,
        "week_end": 4,
    },
    {
        "phase": "standardise",
        "title": "Start weekly call review, role-play and coaching scorecard",
        "owner_text": "Marketing Manager",
        "week_start": 4,
        "week_end": 4,
    },
    {
        "phase": "standardise",
        "title": "Link every content brief to funnel stage and CTA",
        "owner_text": "Content Director",
        "week_start": 5,
        "week_end": 5,
    },
    {
        "phase": "standardise",
        "title": "Implement multi-touch campaign attribution and cost controls",
        "owner_text": "Analytics Officer",
        "week_start": 6,
        "week_end": 6,
    },
    {
        "phase": "scale",
        "title": "Scale top two channels and stop bottom-quartile spend",
        "owner_text": "CEO + Digital",
        "week_start": 7,
        "week_end": 8,
    },
    {
        "phase": "scale",
        "title": "Launch referral, loyalty and dormant-lead reactivation engine",
        "owner_text": "CSRC + Partnerships",
        "week_start": 8,
        "week_end": 9,
    },
    {
        "phase": "scale",
        "title": "Automate reports, reminders, summaries and approvals",
        "owner_text": "Bomach OS Team",
        "week_start": 10,
        "week_end": 10,
    },
    {
        "phase": "scale",
        "title": "Quarterly performance review, role reset and incentive calibration",
        "owner_text": "CEO + HR",
        "week_start": 13,
        "week_end": 13,
    },
]

TURNAROUND_PHASES = [
    ("stabilise", "Stabilise", "Weeks 1-2"),
    ("standardise", "Standardise", "Weeks 3-6"),
    ("scale", "Scale", "Weeks 7-13"),
]

TURNAROUND_PERFORMANCE_CONTRACTS = [
    {
        "role": "Marketing Manager",
        "outcome_metrics": "Qualified pipeline, conversion, revenue forecast, ROI",
        "minimum_operating_standard": "Weekly forecast accuracy >=80%; zero unowned red actions",
    },
    {
        "role": "CSRC",
        "outcome_metrics": "Response speed, qualification quality, handoff completeness",
        "minimum_operating_standard": "95% within SLA; 100% required fields before handoff",
    },
    {
        "role": "Sales Representative",
        "outcome_metrics": "Quality conversations, meetings, proposals, wins, revenue",
        "minimum_operating_standard": "100% active leads with next action; weekly coaching participation",
    },
    {
        "role": "Digital Marketer",
        "outcome_metrics": "Qualified leads, cost per qualified lead, influenced pipeline",
        "minimum_operating_standard": "No channel scaled without source and conversion evidence",
    },
    {
        "role": "Content & Media",
        "outcome_metrics": "On-time content, funnel coverage, leads/revenue influenced",
        "minimum_operating_standard": "At least 40% of output supports evaluation, intent or loyalty",
    },
    {
        "role": "Business Development",
        "outcome_metrics": "Target accounts, partner pipeline, meetings, revenue",
        "minimum_operating_standard": "Named-account plan and partner-sourced opportunity target",
    },
]

TURNAROUND_GOVERNANCE_RULES = [
    "No lead without source, owner, stage and next action.",
    "No campaign without objective, audience, budget, tracking and stop/scale rule.",
    "No content brief without funnel stage, CTA and accountable owner.",
    "No weekly report without decisions, owners and deadlines.",
    "No incentive based only on activity; reward verified revenue contribution and customer outcome.",
    "Underperformance triggers diagnosis, coaching plan and review date, not endless verbal warnings.",
]

TURNAROUND_EVIDENCE = [
    {
        "source": "Salesforce - State of Sales",
        "title": "Automate non-selling work",
        "description": "Sales teams lose time to administration, data entry and prospecting. Bomach OS should automate summaries, assignments, reminders and approvals.",
        "url": "https://www.salesforce.com/sales/state-of-sales/",
    },
    {
        "source": "Harvard Business Review",
        "title": "Speed-to-lead matters",
        "description": "Faster response to online leads is associated with a much greater chance of qualification, so response time must be visible and escalated.",
        "url": "https://hbr.org/2011/03/the-short-life-of-online-sales-leads",
    },
    {
        "source": "HubSpot Knowledge Base",
        "title": "Separate lifecycle, status and deal stages",
        "description": "Lifecycle stage, lead status and deal stages answer different operational questions and should not be collapsed into one field.",
        "url": "https://knowledge.hubspot.com/records/use-lifecycle-stages",
    },
    {
        "source": "HubSpot Playbooks",
        "title": "Standardise conversations and notes",
        "description": "Interactive playbooks help teams ask consistent questions and keep structured notes during customer conversations.",
        "url": "https://knowledge.hubspot.com/playbooks/use-playbooks",
    },
    {
        "source": "Google Analytics",
        "title": "Use attribution paths",
        "description": "Attribution paths preserve conversion credit across touchpoints instead of treating every sale as a single-source outcome.",
        "url": "https://support.google.com/analytics/answer/10596866",
    },
    {
        "source": "WhatsApp Business",
        "title": "Build permission-based conversational commerce",
        "description": "Use rapid response, useful templates, segmentation and opt-out controls rather than indiscriminate broadcasts.",
        "url": "https://whatsappbusiness.com/products/create-ads-that-click-to-whatsapp/",
    },
    {
        "source": "DataReportal - Digital Nigeria",
        "title": "Operate mobile-first",
        "description": "Nigeria's large social-media audience reinforces the need for mobile-first creative, messaging and measurement.",
        "url": "https://datareportal.com/reports/digital-2026-nigeria",
    },
    {
        "source": "NDPC + ARCON",
        "title": "Make compliance part of workflow",
        "description": "Consent, withdrawal rights, claims evidence and advertising approval should be captured before campaigns go live.",
        "url": "https://ndpc.gov.ng/",
    },
]

MANAGEMENT_RHYTHM = [
    {
        "time": "9:00 AM",
        "name": "Revenue huddle",
        "focus": "Red metrics, top deals, blockers and commitments",
    },
    {
        "time": "1:00 PM",
        "name": "Pipeline control",
        "focus": "SLA breaches, next actions and campaign quality",
    },
    {
        "time": "5:00 PM",
        "name": "Close-out",
        "focus": "Results, misses, learning and tomorrow’s first actions",
    },
    {
        "time": "Friday 4 PM",
        "name": "Executive review",
        "focus": "Forecast, ROI, people decisions and resource shifts",
    },
]

DIAGNOSIS_CARDS = [
    {
        "key": "lead_response",
        "title": "Lead response",
        "copy": "Inbound leads wait too long or are not acknowledged consistently.",
        "route": "lead-control",
        "status": "bad",
        "action": "Install SLA queue, auto-assignment and escalation.",
    },
    {
        "key": "crm_discipline",
        "title": "CRM discipline",
        "copy": "Stages, values and next actions are not consistently updated.",
        "route": "lead-control",
        "status": "bad",
        "action": "Make required fields and daily pipeline hygiene mandatory.",
    },
    {
        "key": "qualification",
        "title": "Qualification",
        "copy": "Activity is mistaken for sales readiness.",
        "route": "playbooks",
        "status": "warn",
        "action": "Use agreed MQL/SQL criteria and discovery questions.",
    },
    {
        "key": "sales_capability",
        "title": "Sales capability",
        "copy": "Staff need structured practice, feedback and deal coaching.",
        "route": "coaching",
        "status": "bad",
        "action": "Weekly call review, role-play and individual skill plans.",
    },
    {
        "key": "content_to_revenue",
        "title": "Content-to-revenue",
        "copy": "Content is measured by posts and reach rather than influenced revenue.",
        "route": "content-studio",
        "status": "warn",
        "action": "Brief by funnel stage, CTA and revenue signal.",
    },
    {
        "key": "management_cadence",
        "title": "Management cadence",
        "copy": "Reports arrive after problems are already old.",
        "route": "daily-execution",
        "status": "warn",
        "action": "Use daily leading indicators and weekly outcome review.",
    },
]

LEAD_SCORING_MODEL = [
    {
        "points": 40,
        "name": "Customer fit",
        "copy": "Division match, location, budget, authority and service suitability.",
    },
    {
        "points": 30,
        "name": "Purchase intent",
        "copy": "Inspection request, proposal request, payment question or decision deadline.",
    },
    {
        "points": 20,
        "name": "Engagement",
        "copy": "Replies, calls, brochure views, event attendance and repeat visits.",
    },
    {
        "points": 10,
        "name": "Timing",
        "copy": "Ready now, within 30 days, 90 days, or long-term nurture.",
    },
]

QUALIFICATION_CHECKLIST = [
    {"label": "Problem / need recorded", "status": "required"},
    {"label": "Budget or ability to pay verified", "status": "required"},
    {"label": "Decision-maker / authority identified", "status": "before_sql"},
    {"label": "Purchase timeline recorded", "status": "before_sql"},
    {"label": "Required service / product fit confirmed", "status": "before_sql"},
    {"label": "Next decision event and date scheduled", "status": "before_sql"},
]

LEAD_STATUS_FORECAST_WEIGHTS = {
    "new": Decimal("0.05"),
    "contacted": Decimal("0.10"),
    "qualified": Decimal("0.30"),
    "proposal_sent": Decimal("0.50"),
    "negotiation": Decimal("0.70"),
    "won": Decimal("1.00"),
    "dormant": Decimal("0.05"),
}

FORECAST_SCENARIOS = {
    "conservative": {
        "label": "Conservative",
        "factor": Decimal("0.72"),
        "description": "Discounts weighted pipeline for execution risk.",
    },
    "base": {
        "label": "Base",
        "factor": Decimal("1.00"),
        "description": "Uses current lead status weights without adjustment.",
    },
    "stretch": {
        "label": "Stretch",
        "factor": Decimal("1.28"),
        "description": "Assumes improved follow-up discipline and conversion.",
    },
}
FORECAST_DEFAULT_TARGET = Decimal("150000000.00")
FORECAST_STAGE_AGE_LIMIT_DAYS = 14

FUNNEL_STAGE_LABELS = {
    "discovery": "Discovery",
    "evaluation": "Evaluation",
    "intent": "Intent",
    "purchase": "Purchase",
    "loyalty": "Loyalty",
}

FUNNEL_LEAK_FIXES = {
    ("discovery", "evaluation"): {
        "copy": "Leads are not becoming qualified opportunities.",
        "fix": "Tighten response quality, qualification fields, and handoff criteria.",
    },
    ("evaluation", "intent"): {
        "copy": "Qualified leads are not booking inspections, meetings or demos.",
        "fix": "Add proof, urgency and an agreed next event before ending qualification.",
    },
    ("intent", "purchase"): {
        "copy": "Meetings happen but proposals and decisions stall.",
        "fix": "Use proposal follow-up cadence, decision map and manager deal reviews.",
    },
    ("purchase", "loyalty"): {
        "copy": "Closed clients are not consistently producing referrals or repeat business.",
        "fix": "Trigger onboarding, satisfaction check and referral ask at defined milestones.",
    },
}

FUNNEL_CORRECTIVE_ACTIONS = [
    {
        "id": "l1",
        "title": "Enforce 15-minute human-response target for paid leads",
        "owner": "CSRC Lead",
        "due": "Today",
        "done": False,
    },
    {
        "id": "l2",
        "title": "Require qualification fields before sales handoff",
        "owner": "Marketing Manager",
        "due": "16 Jul",
        "done": False,
    },
    {
        "id": "l3",
        "title": "Create inspection/proposal follow-up cadence",
        "owner": "Sales Lead",
        "due": "17 Jul",
        "done": False,
    },
    {
        "id": "l4",
        "title": "Build proof content for evaluation and intent stages",
        "owner": "Content Director",
        "due": "20 Jul",
        "done": False,
    },
]


def _validation_detail(exc):
    if hasattr(exc, "message_dict"):
        return "; ".join(
            f"{field}: {', '.join(messages)}"
            for field, messages in exc.message_dict.items()
        )
    return exc.messages[0] if getattr(exc, "messages", None) else str(exc)


def _employee_name(employee):
    return employee.user.get_full_name() if employee else None


def _role_label(employee):
    if not employee:
        return "Unassigned"
    if employee.role:
        return employee.role.name
    if employee.designation:
        return employee.designation
    return employee.user.get_full_name() or employee.employee_id


def _day_queryset(request):
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


def _template_queryset(request):
    qs = DailyActionTemplate.objects.select_related(
        "branch", "default_owner", "default_owner__user", "created_by"
    )
    return scope_queryset(request, qs, branch_field="branch_id")


def _action_queryset(request):
    qs = DailyActionInstance.objects.select_related(
        "day",
        "day__branch",
        "template",
        "owner",
        "owner__user",
        "completed_by",
    )
    return scope_queryset(request, qs, branch_field="day__branch_id")


def _lead_queryset(request):
    qs = Lead.objects.select_related(
        "assigned_to", "assigned_to__user", "assigned_to__role", "branch"
    )
    return scope_queryset(request, qs, branch_field="branch_id")


def _activity_queryset(request):
    qs = LeadActivity.objects.select_related(
        "lead",
        "lead__assigned_to",
        "lead__assigned_to__user",
        "lead__assigned_to__role",
        "created_by",
    )
    return scope_queryset(request, qs, branch_field="lead__branch_id")


def _turnaround_plan_queryset(request):
    qs = TurnaroundPlan.objects.select_related(
        "branch",
        "primary_owner",
        "primary_owner__user",
        "created_by",
    ).prefetch_related(
        "actions",
        "actions__owner",
        "actions__owner__user",
        "actions__completed_by",
    )
    return scope_queryset(request, qs, branch_field="branch_id")


def _turnaround_action_queryset(request):
    qs = TurnaroundAction.objects.select_related(
        "plan",
        "plan__branch",
        "owner",
        "owner__user",
        "completed_by",
    )
    return scope_queryset(request, qs, branch_field="plan__branch_id")


def _objective_queryset(request):
    qs = RevenueObjective.objects.select_related(
        "branch",
        "owner",
        "owner__user",
        "created_by",
    ).prefetch_related(
        "key_results",
        "key_results__linked_employee_target",
        "key_results__linked_kpi_record",
    )
    return scope_queryset(request, qs, branch_field="branch_id")


def _key_result_queryset(request):
    qs = RevenueKeyResult.objects.select_related(
        "objective",
        "objective__branch",
        "linked_employee_target",
        "linked_kpi_record",
    )
    return scope_queryset(request, qs, branch_field="objective__branch_id")


def _playbook_queryset(request):
    qs = SalesPlaybook.objects.select_related("branch", "created_by").prefetch_related(
        "objections"
    )
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if branch_ids:
        return qs.filter(Q(branch_id__in=branch_ids) | Q(branch__isnull=True))
    return qs


def _playbook_objection_queryset(request):
    qs = SalesPlaybookObjection.objects.select_related("playbook", "playbook__branch")
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if branch_ids:
        return qs.filter(
            Q(playbook__branch_id__in=branch_ids) | Q(playbook__branch__isnull=True)
        )
    return qs


def _funnel_event_queryset(request):
    qs = LeadFunnelEvent.objects.select_related(
        "lead",
        "branch",
        "campaign",
        "actor",
    )
    return scope_queryset(request, qs, branch_field="branch_id")


def _date_bounds(day):
    start = timezone.make_aware(datetime.combine(day, time.min))
    end = timezone.make_aware(datetime.combine(day, time.max))
    return start, end


def _period_bounds(period_start=None, period_end=None):
    today = timezone.localdate()
    start = period_start or today.replace(day=1)
    end = period_end or today
    return start, end


def _decimal_sum(queryset, field_name):
    total = queryset.aggregate(total=Sum(field_name))["total"] or Decimal("0.00")
    return (
        total.quantize(Decimal("0.01"))
        if isinstance(total, Decimal)
        else Decimal(total).quantize(Decimal("0.01"))
    )


def _decimal_pct(numerator, denominator):
    if not denominator:
        return Decimal("0.00")
    numerator = Decimal(str(numerator or "0.00"))
    denominator = Decimal(str(denominator))
    return min(
        (numerator / denominator) * Decimal("100.00"), Decimal("100.00")
    ).quantize(Decimal("0.01"))


def _playbook_objection_row(objection):
    return {
        "id": objection.id,
        "playbook_id": objection.playbook_id,
        "objection": objection.objection,
        "response": objection.response,
        "sort_order": objection.sort_order,
        "is_active": objection.is_active,
        "created_at": objection.created_at,
        "updated_at": objection.updated_at,
    }


def _playbook_row(playbook, include_objections=False):
    row = {
        "id": playbook.id,
        "title": playbook.title,
        "division": playbook.division,
        "division_display": playbook.get_division_display(),
        "stage": playbook.stage,
        "stage_display": playbook.get_stage_display(),
        "persona": playbook.persona,
        "persona_display": playbook.get_persona_display(),
        "objective": playbook.objective,
        "opening_script": playbook.opening_script,
        "questions": playbook.questions,
        "proof_to_use": playbook.proof_to_use,
        "primary_cta": playbook.primary_cta,
        "exit_criteria": playbook.exit_criteria,
        "status": playbook.status,
        "branch_id": playbook.branch_id,
        "branch_name": playbook.branch.branch_name if playbook.branch else None,
        "created_by_id": playbook.created_by_id,
        "sort_order": playbook.sort_order,
        "created_at": playbook.created_at,
        "updated_at": playbook.updated_at,
    }
    if include_objections:
        row["objections"] = [
            _playbook_objection_row(objection)
            for objection in playbook.objections.all()
            if objection.is_active
        ]
    return row


def _money_display(value):
    value = Decimal(value or "0.00")
    if value >= Decimal("1000000000"):
        return f"₦{(value / Decimal('1000000000')).quantize(Decimal('0.1'))}B"
    if value >= Decimal("1000000"):
        millions = value / Decimal("1000000")
        display = (
            millions.quantize(Decimal("0.1"))
            if value % Decimal("1000000")
            else millions.quantize(Decimal("1"))
        )
        return f"₦{display}M"
    if value >= Decimal("1000"):
        return f"₦{(value / Decimal('1000')).quantize(Decimal('1'))}K"
    return f"₦{value.quantize(Decimal('1'))}"


def _scenario_factor(scenario):
    return FORECAST_SCENARIOS.get(scenario or "base", FORECAST_SCENARIOS["base"])[
        "factor"
    ]


def _normalized_scenario(scenario):
    return scenario if scenario in FORECAST_SCENARIOS else "base"


def _weighted_forecast_value(leads, factor=Decimal("1.00")):
    weighted = Decimal("0.00")
    for row in leads.values("status").annotate(total=Sum("estimated_value")):
        weighted += (
            row["total"] or Decimal("0.00")
        ) * LEAD_STATUS_FORECAST_WEIGHTS.get(
            row["status"],
            Decimal("0.00"),
        )
    return (weighted * factor).quantize(Decimal("0.01"))


def _revenue_target_value(start, end, branch_id=None):
    revenue_targets = EmployeeTarget.objects.filter(
        period_start__lte=end,
        period_end__gte=start,
        title__icontains="revenue",
        is_active=True,
    )
    if branch_id:
        revenue_targets = revenue_targets.filter(employee__branch_id=branch_id)
    return _decimal_sum(revenue_targets, "target_value") or FORECAST_DEFAULT_TARGET


def _quality_control_status(value):
    if value is None:
        return "unsupported"
    if value >= Decimal("80.00"):
        return "ok"
    if value >= Decimal("60.00"):
        return "warn"
    return "red"


def _forecast_quality_controls(active_leads, now=None):
    now = now or timezone.now()
    total = active_leads.count()
    value_pct = _decimal_pct(
        active_leads.filter(estimated_value__gt=Decimal("0.00")).count(),
        total,
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
    return controls, confidence


def _forecast_division_rows(active_leads, factor):
    rows = []
    for division_key, division_label in Lead.DIVISION_CHOICES:
        division_leads = active_leads.filter(division=division_key)
        opportunity_count = division_leads.count()
        if not opportunity_count:
            continue
        pipeline_value = _decimal_sum(division_leads, "estimated_value")
        weighted_forecast = _weighted_forecast_value(division_leads, factor=factor)
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


def _forecast_methodology():
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


def _forecast_payload(
    request,
    period_start=None,
    period_end=None,
    branch_id=None,
    division=None,
    scenario="base",
):
    start, end = _period_bounds(period_start, period_end)
    scenario_key = _normalized_scenario(scenario)
    factor = _scenario_factor(scenario_key)

    leads = _lead_queryset(request)
    if branch_id:
        leads = leads.filter(branch_id=branch_id)
    if division:
        leads = leads.filter(division=division)
    active_leads = leads.filter(status__in=Lead.ACTIVE_STATUSES)

    target = _revenue_target_value(start, end, branch_id=branch_id)
    unweighted_pipeline = _decimal_sum(active_leads, "estimated_value")
    weighted_forecast = _weighted_forecast_value(active_leads, factor=factor)
    base_weighted_forecast = _weighted_forecast_value(active_leads)
    target_gap = max(target - weighted_forecast, Decimal("0.00"))
    pipeline_coverage = (
        (unweighted_pipeline / target).quantize(Decimal("0.01"))
        if target
        else Decimal("0.00")
    )
    quality_controls, forecast_confidence = _forecast_quality_controls(active_leads)

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
        "division_rows": _forecast_division_rows(active_leads, factor),
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
        "methodology": _forecast_methodology(),
    }


def _progress_color(progress):
    if progress >= Decimal("90.00"):
        return "#059669"
    if progress >= Decimal("60.00"):
        return "#D97706"
    return "#DC2626"


def _apply_template_payload(template, payload_data):
    for attr, value in payload_data.items():
        setattr(template, attr, value)
    template.full_clean()
    template.save()
    return template


def _apply_action_payload(action, payload_data):
    for attr, value in payload_data.items():
        setattr(action, attr, value)
    action.full_clean()
    action.save()
    return action


def _templates_for_day(request, branch_id):
    templates = _template_queryset(request).filter(is_active=True)
    if branch_id:
        return templates.filter(Q(branch_id=branch_id) | Q(branch__isnull=True))
    return templates.filter(branch__isnull=True)


def _ensure_action_instances(day, templates):
    existing_template_ids = set(
        day.actions.exclude(template__isnull=True).values_list("template_id", flat=True)
    )
    created = []

    for template in templates:
        if template.id in existing_template_ids:
            continue
        created.append(
            DailyActionInstance(
                day=day,
                template=template,
                title=template.title,
                description=template.description,
                owner=template.default_owner,
                severity=template.severity,
                sort_order=template.sort_order,
            )
        )

    if created:
        DailyActionInstance.objects.bulk_create(created)


def _open_day(request, target_date, branch_id=None, force_rebuild=False):
    branch = None
    if branch_id:
        branch = get_object_or_404(Branch, id=branch_id)

    day, _ = DailyExecutionDay.objects.get_or_create(
        date=target_date,
        branch=branch,
        defaults={"opened_by": request.user},
    )
    templates = _templates_for_day(request, branch_id)
    if force_rebuild or not day.actions.exists():
        _ensure_action_instances(day, templates)
    return get_object_or_404(_day_queryset(request), id=day.id)


def _completion_counts(day):
    total = day.actions.count()
    completed = day.actions.filter(status="completed").count()
    open_count = total - completed
    completion_pct = round((completed / total) * 100) if total else 0
    return total, completed, open_count, completion_pct


def _lead_sla_status(lead, now=None):
    now = now or timezone.now()
    if lead.first_response_at or lead.first_contact_at:
        return "completed"
    due_at = lead.first_response_due_at
    if not due_at and lead.created_at:
        due_at = lead.created_at + timezone.timedelta(
            minutes=Lead.DEFAULT_FIRST_RESPONSE_MINUTES
        )
    if due_at and now > due_at:
        return "breached"
    if due_at and now + timezone.timedelta(minutes=5) >= due_at:
        return "due_now"
    return "safe"


def _recommended_action(lead, sla_status):
    if sla_status == "breached":
        return "Contact immediately and log the first response"
    if sla_status == "due_now":
        return "Contact now before the SLA breaches"
    if lead.score >= 75:
        return "Manager review and next action required today"
    if not lead.next_action:
        return "Create a dated next action"
    return lead.next_action


def _lead_control_rows(leads, now, limit):
    rows = []
    for lead in leads[:limit]:
        sla_status = _lead_sla_status(lead, now)
        age_days = (now - lead.created_at).days if lead.created_at else 0
        rows.append(
            {
                "id": lead.id,
                "lead": lead.full_name,
                "lead_meta": f"{lead.get_source_display()} · {lead.get_division_display()} · {lead.estimated_value}",
                "source": lead.source,
                "source_display": lead.get_source_display(),
                "division": lead.division,
                "division_display": lead.get_division_display(),
                "status": lead.status,
                "status_display": lead.get_status_display(),
                "score": lead.score,
                "priority": lead.priority,
                "stage": lead.status,
                "stage_label": lead.get_status_display(),
                "age_days": age_days,
                "next_action": lead.next_action
                or _recommended_action(lead, sla_status),
                "sla_status": sla_status,
                "sla_label": (
                    "Breach"
                    if sla_status == "breached"
                    else "Due now" if sla_status == "due_now" else "Safe"
                ),
                "owner": _employee_name(lead.assigned_to) or "Unassigned",
                "actions": [
                    {"label": "Open", "action": "open"},
                    (
                        {"label": "Contact", "action": "contact"}
                        if sla_status in ["breached", "due_now"] or lead.status == "new"
                        else None
                    ),
                ],
            }
        )
        rows[-1]["actions"] = [action for action in rows[-1]["actions"] if action]
    return rows


def _lead_control_kpis(leads, now):
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
                    and not lead.first_contact_at
                    and not lead.first_response_at
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


def _eligible_revenue_employees(request, branch_id=None):
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
        .filter(
            is_active=True,
            employment_status="active",
        )
        .filter(role_filter)
    )

    branch_ids = getattr(request, "_perm_branch_ids", [])
    if branch_ids:
        employees = employees.filter(branch_id__in=branch_ids)
    if branch_id:
        employees = employees.filter(Q(branch_id=branch_id) | Q(branch__isnull=True))
    return employees.order_by("branch_id", "employee_id", "id")


def _okr_counts(objectives):
    counts = {"on_track": 0, "at_risk": 0, "off_track": 0}
    for objective in objectives:
        status = objective.track_status
        counts[status] = counts.get(status, 0) + 1
    return counts


def _apply_objective_payload(objective, payload_data):
    for attr, value in payload_data.items():
        setattr(objective, attr, value)
    objective.full_clean()
    objective.save()
    return objective


def _apply_key_result_payload(key_result, payload_data):
    for attr, value in payload_data.items():
        setattr(key_result, attr, value)
    key_result.full_clean()
    key_result.save()
    return key_result


def _pct(part, whole):
    if not whole:
        return 0.0
    return round((part / whole) * 100, 2)


def _first_events_by_lead(events):
    first_events = {}
    for event in events.order_by("lead_id", "occurred_at", "id"):
        first_events.setdefault(event.lead_id, event)
    return first_events


def _cohort_lead_ids(events, start, end):
    first_events = _first_events_by_lead(events)
    return {
        lead_id
        for lead_id, event in first_events.items()
        if start <= event.occurred_at.date() <= end
    }


def _stage_lead_sets(events, cohort_ids):
    return {
        stage: set(
            events.filter(lead_id__in=cohort_ids, to_stage=stage)
            .values_list("lead_id", flat=True)
            .distinct()
        )
        for stage in FUNNEL_STAGE_ORDER
    }


def _funnel_data_quality(events, cohort_ids):
    cohort_events = events.filter(lead_id__in=cohort_ids)
    total = cohort_events.count()
    backfilled = sum(1 for event in cohort_events if event.metadata.get("backfilled"))
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
    real_ratio = (event_based / total) if total else 0
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


def _lead_value_sum(leads, lead_ids):
    return leads.filter(id__in=lead_ids).aggregate(total=Sum("estimated_value"))[
        "total"
    ] or Decimal("0.00")


def _transition_leaks(stage_sets, leads):
    leaks = []
    for index, from_stage in enumerate(FUNNEL_STAGE_ORDER[:-1]):
        to_stage = FUNNEL_STAGE_ORDER[index + 1]
        current = stage_sets[from_stage]
        progressed = stage_sets[to_stage]
        lost_ids = current - progressed
        entered = len(current)
        progressed_count = len(progressed & current)
        loss_pct = round(100 - _pct(progressed_count, entered), 2) if entered else 0.0
        copy = FUNNEL_LEAK_FIXES[(from_stage, to_stage)]["copy"]
        fix = FUNNEL_LEAK_FIXES[(from_stage, to_stage)]["fix"]
        leaks.append(
            {
                "transition": f"{FUNNEL_STAGE_LABELS[from_stage]} → {FUNNEL_STAGE_LABELS[to_stage]}",
                "from_stage": from_stage,
                "to_stage": to_stage,
                "entered": entered,
                "progressed": progressed_count,
                "lost": len(lost_ids),
                "loss_pct": loss_pct,
                "revenue_impact": _lead_value_sum(leads, lost_ids),
                "copy": copy,
                "fix": fix,
            }
        )
    return sorted(
        leaks, key=lambda row: (row["loss_pct"], row["revenue_impact"]), reverse=True
    )


def _turnaround_end_date(start_date):
    return start_date + timedelta(weeks=13) - timedelta(days=1)


def _seed_turnaround_actions(plan):
    actions = [
        TurnaroundAction(
            plan=plan,
            sort_order=index + 1,
            **action,
        )
        for index, action in enumerate(TURNAROUND_DEFAULT_ACTIONS)
    ]
    TurnaroundAction.objects.bulk_create(actions)


def _phase_summary(plan):
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
                "completion_pct": round((completed / total) * 100) if total else 0,
                "actions": phase_actions,
            }
        )
    return grouped


def _turnaround_kpis(plan):
    total = plan.total_actions
    completed = plan.completed_actions
    current_phase = plan.current_phase.replace("_", " ").title()
    owner_name = _employee_name(plan.primary_owner) or "Marketing Manager"
    return [
        {
            "label": "Plan completion",
            "value": f"{plan.completion_pct}%",
            "foot": f"{completed} of {total} actions",
        },
        {
            "label": "Current phase",
            "value": current_phase,
            "foot": f"{plan.start_date} to {plan.end_date}",
        },
        {
            "label": "Primary owner",
            "value": owner_name,
            "foot": "CEO removes blockers",
        },
        {
            "label": "Success test",
            "value": "Revenue + discipline",
            "foot": "Not activity volume alone",
        },
    ]


def _turnaround_detail(plan):
    return {
        "plan": plan,
        "kpis": _turnaround_kpis(plan),
        "roadmap": _phase_summary(plan),
        "performance_contracts": TURNAROUND_PERFORMANCE_CONTRACTS,
        "governance_rules": [
            {"sequence": index + 1, "rule": rule}
            for index, rule in enumerate(TURNAROUND_GOVERNANCE_RULES)
        ],
        "evidence": TURNAROUND_EVIDENCE,
    }


def _activate_turnaround_plan(plan):
    active_qs = TurnaroundPlan.objects.filter(status="active")
    if plan.branch_id:
        active_qs = active_qs.filter(branch_id=plan.branch_id)
    else:
        active_qs = active_qs.filter(branch__isnull=True)
    active_qs.exclude(id=plan.id).update(status="archived")
    plan.status = "active"
    plan.full_clean()
    plan.save()
    return plan


def _apply_turnaround_plan_payload(plan, payload_data):
    activate = payload_data.get("status") == "active"
    for attr, value in payload_data.items():
        setattr(plan, attr, value)
    if plan.start_date and not plan.end_date:
        plan.end_date = _turnaround_end_date(plan.start_date)
    plan.full_clean()
    plan.save()
    if activate:
        plan = _activate_turnaround_plan(plan)
    return plan


def _apply_turnaround_action_payload(action, payload_data):
    for attr, value in payload_data.items():
        setattr(action, attr, value)
    if "status" in payload_data:
        if action.status == "completed" and not action.completed_at:
            action.completed_at = timezone.now()
        elif action.status == "open":
            action.completed_at = None
            action.completed_by = None
            action.completion_note = ""
    action.full_clean()
    action.save()
    return action


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
        round((leads_with_next_action / active_count) * 100, 2) if active_count else 0.0
    )
    sla_breaches = sum(
        1 for lead in active_leads if _lead_sla_status(lead, now) == "breached"
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
            "drop_label": f"{round((qualified_count / period_leads.count()) * 100, 1) if period_leads.count() else 0}% from prior",
        },
        {
            "stage": "intent",
            "name": "Intent",
            "number": intent_count,
            "rate_label": "Meetings",
            "drop_label": f"{round((intent_count / qualified_count) * 100, 1) if qualified_count else 0}% from prior",
        },
        {
            "stage": "purchase",
            "name": "Purchase",
            "number": won_count,
            "rate_label": "Won",
            "drop_label": f"{round((won_count / intent_count) * 100, 1) if intent_count else 0}% from prior",
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
        score = round((owned_with_next_action / total) * 100) if total else 0
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
        ",".join(f'"{str(value).replace(chr(34), chr(34) + chr(34))}"' for value in row)
        for row in rows
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
    filter_aliases = {
        "sla_breaches": "breach",
        "reactivation": "reactivate",
    }
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
        assigned_to__isnull=True,
        status__in=Lead.ACTIVE_STATUSES,
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


@revenue_execution_router.get("/playbooks/current", response={200: dict, 404: MessageSchema})
@require_permission("revenue_execution", "view")
def get_current_sales_playbook(
    request,
    division: str,
    stage: str,
    persona: str,
    branch_id: int = None,
):
    playbooks = _playbook_queryset(request).filter(
        division=division,
        stage=stage,
        persona=persona,
        status="active",
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
        return 404, {
            "detail": "No active sales playbook found for this division, stage and persona."
        }
    return 200, _playbook_row(playbook, include_objections=True)


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
        return 201, _playbook_row(playbook, include_objections=True)
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@revenue_execution_router.get("/playbooks/{playbook_id}", response={200: dict, 404: MessageSchema})
@require_permission("revenue_execution", "view")
def get_sales_playbook(request, playbook_id: int):
    playbook = get_object_or_404(_playbook_queryset(request), id=playbook_id)
    return 200, _playbook_row(playbook, include_objections=True)


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
        return 200, _playbook_row(playbook, include_objections=True)
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@revenue_execution_router.delete(
    "/playbooks/{playbook_id}", response={200: MessageSchema, 404: MessageSchema}
)
@require_permission("revenue_execution", "update")
def archive_sales_playbook(request, playbook_id: int):
    playbook = get_object_or_404(_playbook_queryset(request), id=playbook_id)
    playbook.status = "archived"
    playbook.full_clean()
    playbook.save(update_fields=["status", "updated_at"])
    return 200, {"detail": "Sales playbook archived successfully."}


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
        return 201, _playbook_objection_row(objection)
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


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
        return 200, _playbook_objection_row(objection)
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


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
    return 200, {"detail": "Sales playbook objection deactivated successfully."}


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


@revenue_execution_router.post("/okrs", response={201: RevenueObjectiveOutSchema, 400: MessageSchema})
@require_permission("revenue_execution", "create")
def create_okr(request, payload: RevenueObjectiveCreateSchema):
    try:
        objective = RevenueObjective(created_by=request.user, **payload.dict())
        objective.full_clean()
        objective.save()
        return 201, get_object_or_404(_objective_queryset(request), id=objective.id)
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


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
        return 201, get_object_or_404(_key_result_queryset(request), id=key_result.id)
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


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
        return 200, _apply_key_result_payload(
            key_result, payload.dict(exclude_unset=True)
        )
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@revenue_execution_router.patch(
    "/okrs/{objective_id}",
    response={200: RevenueObjectiveOutSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("revenue_execution", "update")
def update_okr(request, objective_id: int, payload: RevenueObjectiveUpdateSchema):
    try:
        objective = get_object_or_404(_objective_queryset(request), id=objective_id)
        return 200, _apply_objective_payload(
            objective, payload.dict(exclude_unset=True)
        )
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


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

    total_target_value = sum((row["target"] or Decimal("0.00")) for row in target_rows)
    total_actual_value = sum((row["actual"] or Decimal("0.00")) for row in target_rows)
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


@revenue_execution_router.get("/turnaround/plans", response=List[TurnaroundPlanOutSchema])
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
        return 201, get_object_or_404(_turnaround_plan_queryset(request), id=plan.id)
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


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
        return 404, {"detail": "No active turnaround plan found."}
    return 200, _turnaround_detail(plan)


@revenue_execution_router.get(
    "/turnaround/plans/{plan_id}",
    response={200: TurnaroundPlanDetailSchema, 404: MessageSchema},
)
@require_permission("revenue_execution", "view")
def get_turnaround_plan(request, plan_id: int):
    plan = get_object_or_404(_turnaround_plan_queryset(request), id=plan_id)
    return 200, _turnaround_detail(plan)


@revenue_execution_router.patch(
    "/turnaround/plans/{plan_id}",
    response={200: TurnaroundPlanOutSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("revenue_execution", "update")
def update_turnaround_plan(request, plan_id: int, payload: TurnaroundPlanUpdateSchema):
    try:
        plan = get_object_or_404(_turnaround_plan_queryset(request), id=plan_id)
        return 200, _apply_turnaround_plan_payload(
            plan, payload.dict(exclude_unset=True)
        )
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@revenue_execution_router.post(
    "/turnaround/plans/{plan_id}/activate",
    response={200: TurnaroundPlanOutSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("revenue_execution", "update")
def activate_turnaround_plan(request, plan_id: int):
    try:
        plan = get_object_or_404(_turnaround_plan_queryset(request), id=plan_id)
        return 200, _activate_turnaround_plan(plan)
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


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
        return 200, plan
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


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
        return 200, _apply_turnaround_action_payload(
            action, payload.dict(exclude_unset=True)
        )
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


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
        return 200, action
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


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
        return 200, action
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


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
        ",".join(f'"{str(value).replace(chr(34), chr(34) + chr(34))}"' for value in row)
        for row in rows
    )
    response = HttpResponse(csv_body, content_type="text/csv")
    response["Content-Disposition"] = (
        'attachment; filename="bomach-13-week-turnaround.csv"'
    )
    return response


@revenue_execution_router.get("/action-templates", response=List[DailyActionTemplateOutSchema])
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
        return 201, template
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


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
        return 200, _apply_template_payload(template, payload.dict(exclude_unset=True))
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@revenue_execution_router.delete(
    "/action-templates/{template_id}", response={200: MessageSchema, 404: MessageSchema}
)
@require_permission("revenue_execution", "delete")
def delete_action_template(request, template_id: int):
    template = get_object_or_404(_template_queryset(request), id=template_id)
    template.delete()
    return 200, {"detail": "Daily action template deleted successfully"}


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
        return 200, day
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


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
        return 200, _apply_action_payload(action, payload.dict(exclude_unset=True))
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


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
        return 200, action
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


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
        return 200, action
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


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
        1 for lead in active_leads if _lead_sla_status(lead, now) == "breached"
    )
    hot = active_leads.filter(score__gte=75).count()
    next_actions_due = active_leads.filter(
        next_follow_up_at__isnull=False,
        next_follow_up_at__lte=end_of_day,
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


@revenue_execution_router.get("/monthly-summary", response=MonthlyExecutionSummarySchema)
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
    fully_completed = sum(1 for value in completion_values if value == 100)
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


@revenue_execution_router.get("/speed-to-lead-queue", response=List[SpeedToLeadQueueItemSchema])
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
                and not lead.first_response_at
                and not lead.first_contact_at
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


@revenue_execution_router.get("/activity-scorecard", response=List[ActivityScorecardRowSchema])
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
            round((metrics["completed"] / metrics["assigned"]) * 100)
            if metrics["assigned"]
            else 0
        )
        activity_score = min(100, metrics["activities"] * 10)
        sla_score = (
            round((metrics["sla_done"] / metrics["sla_total"]) * 100)
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
                "actual": (
                    f"{metrics['activities']} activities · "
                    f"{metrics['completed']}/{metrics['assigned']} actions · "
                    f"{metrics['sla_done']}/{metrics['sla_total']} SLA"
                ),
                "score": score,
                "manager_focus": focus,
            }
        )

    return rows
