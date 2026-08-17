"""Read/query layer for campaigns, marketing operations, content and media."""

from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Q, Sum
from django.utils import timezone

from domains.marketing_sales.constants import (
    MARKETING_MEETING_STATUS_ALIASES,
    TERMINAL_CALENDAR_STATUSES,
    TRADITIONAL_MEDIA_EXPIRY_WINDOW_DAYS,
)
from domains.marketing_sales.models.content import (
    Content,
    ContentCalendarItem,
    MediaLibraryAsset,
)
from domains.marketing_sales.models.marketing import (
    CampaignAsset,
    MarketingCampaign,
    MarketingMeetingContext,
    TraditionalMediaPlacement,
)
from domains.marketing_sales.models.sales import (
    FUNNEL_STAGE_ORDER,
    Lead,
    LeadActivity,
    LeadFunnelEvent,
)
from domains.marketing_sales.presenters import _campaign_campaign_base as _campaign_base
from domains.marketing_sales.presenters import _campaign_lead_row as _lead_row
from domains.marketing_sales.presenters import _campaign_money_ratio as _money_ratio
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
    _campaign_serialize_workspace_meeting as _serialize_workspace_meeting,
)
from domains.marketing_sales.presenters import _content_format_bytes as _format_bytes
from domains.marketing_sales.presenters import (
    _content_serialize_content_only as _serialize_content_only,
)
from domains.marketing_sales.presenters import (
    _marketing_employee_name as _employee_name,
)
from domains.marketing_sales.presenters import _marketing_pct as _pct
from user.models.branch import Branch
from user.models.employee import Employee
from user.models.role_targets import EmployeeTarget, with_target_progress
from user.utils.perm import scope_queryset


def _period_bounds(period_start=None, period_end=None):
    today = timezone.localdate()
    start = period_start or today.replace(day=1)
    end = period_end or today
    if start > end:
        start, end = (end, start)
    return (start, end)


def _decimal_sum(qs, field):
    return qs.aggregate(total=Sum(field))["total"] or Decimal("0.00")


def _meeting_status(status):
    if not status:
        return status
    return MARKETING_MEETING_STATUS_ALIASES.get(status.lower(), status.lower())


def _marketing_meeting_queryset():
    return MarketingMeetingContext.objects.select_related(
        "meeting", "meeting__organizer", "campaign"
    ).prefetch_related("meeting__attendees", "actions", "campaign_decisions")


def _filter_marketing_meetings(
    contexts,
    status=None,
    campaign_id=None,
    meeting_type=None,
    date_from=None,
    date_to=None,
    search=None,
    my_meetings=None,
    request=None,
):
    if status:
        contexts = contexts.filter(meeting__status=_meeting_status(status))
    if campaign_id:
        contexts = contexts.filter(campaign_id=campaign_id)
    if meeting_type:
        contexts = contexts.filter(meeting_type=meeting_type)
    if date_from:
        contexts = contexts.filter(meeting__meeting_date__gte=date_from)
    if date_to:
        contexts = contexts.filter(meeting__meeting_date__lte=date_to)
    if my_meetings and request:
        contexts = contexts.filter(
            Q(meeting__organizer=request.user) | Q(meeting__attendees=request.user)
        )
    if search:
        contexts = contexts.filter(
            Q(meeting__title__icontains=search)
            | Q(meeting__agenda__icontains=search)
            | Q(meeting__notes__icontains=search)
            | Q(meeting__meeting_id__icontains=search)
            | Q(campaign__name__icontains=search)
            | Q(campaign_decisions__decision__icontains=search)
            | Q(actions__title__icontains=search)
        )
    return contexts.distinct()


def _traditional_media_queryset(request):
    return scope_queryset(
        request,
        TraditionalMediaPlacement.objects.select_related(
            "campaign", "branch", "created_by"
        ),
        branch_field="branch_id",
    )


def _apply_expiry_filter(placements, expiry_filter):
    today = timezone.localdate()
    window_end = today + timedelta(days=TRADITIONAL_MEDIA_EXPIRY_WINDOW_DAYS)
    open_placements = placements.exclude(status__in=["archived", "cancelled"])
    if expiry_filter == "active":
        return open_placements.filter(end_date__gt=window_end)
    if expiry_filter == "expiring_soon":
        return open_placements.filter(end_date__gte=today, end_date__lte=window_end)
    if expiry_filter == "expired":
        return open_placements.filter(end_date__lt=today)
    return placements


def _filter_traditional_media_placements(
    placements,
    placement_type=None,
    ownership=None,
    status=None,
    expiry_filter=None,
    campaign_id=None,
    branch_id=None,
    division=None,
    date_from=None,
    date_to=None,
    search=None,
):
    if placement_type:
        placements = placements.filter(placement_type=placement_type)
    if ownership:
        placements = placements.filter(ownership=ownership)
    if status:
        placements = placements.filter(status=status)
    if campaign_id:
        placements = placements.filter(campaign_id=campaign_id)
    if branch_id:
        placements = placements.filter(branch_id=branch_id)
    if division:
        placements = placements.filter(division=division)
    if date_from:
        placements = placements.filter(end_date__gte=date_from)
    if date_to:
        placements = placements.filter(end_date__lte=date_to)
    if search:
        placements = placements.filter(
            Q(name__icontains=search)
            | Q(vendor__icontains=search)
            | Q(location__icontains=search)
            | Q(notes__icontains=search)
            | Q(campaign__name__icontains=search)
        )
    return _apply_expiry_filter(placements, expiry_filter).distinct()


def _traditional_media_dashboard(placements):
    today = timezone.localdate()
    window_end = today + timedelta(days=TRADITIONAL_MEDIA_EXPIRY_WINDOW_DAYS)
    open_placements = placements.exclude(status__in=["archived", "cancelled"])
    active_count = open_placements.filter(end_date__gte=today).count()
    expiring_count = open_placements.filter(
        end_date__gte=today, end_date__lte=window_end
    ).count()
    expired_count = open_placements.filter(end_date__lt=today).count()
    non_cancelled = placements.exclude(status="cancelled")
    by_type = [
        {
            "placement_type": value,
            "label": label,
            "count": placements.filter(placement_type=value).count(),
            "amount_paid": _decimal_sum(
                placements.filter(placement_type=value).exclude(status="cancelled"),
                "amount_paid",
            ),
        }
        for value, label in TraditionalMediaPlacement.PLACEMENT_TYPE_CHOICES
        if placements.filter(placement_type=value).exists()
    ]
    by_ownership = [
        {
            "ownership": value,
            "label": label,
            "count": placements.filter(ownership=value).count(),
            "amount_paid": _decimal_sum(
                placements.filter(ownership=value).exclude(status="cancelled"),
                "amount_paid",
            ),
        }
        for value, label in TraditionalMediaPlacement.OWNERSHIP_CHOICES
        if placements.filter(ownership=value).exists()
    ]
    by_status = [
        {
            "status": value,
            "label": label,
            "count": placements.filter(status=value).count(),
        }
        for value, label in TraditionalMediaPlacement.STATUS_CHOICES
        if placements.filter(status=value).exists()
    ]
    return {
        "kpis": {
            "total_placements": placements.count(),
            "active_placements": active_count,
            "total_spend": _decimal_sum(non_cancelled, "amount_paid"),
            "expiring_soon": expiring_count,
            "expired": expired_count,
        },
        "breakdowns": {
            "by_type": by_type,
            "by_ownership": by_ownership,
            "by_status": by_status,
        },
        "metadata": {
            "expiry_window_days": TRADITIONAL_MEDIA_EXPIRY_WINDOW_DAYS,
            "expiry_state_source": "end_date",
            "renew_action_supported": False,
        },
    }


def _resolve_traditional_media_relations(data):
    relations = {}
    campaign_provided = "campaign_id" in data
    branch_provided = "branch_id" in data
    campaign_id = data.pop("campaign_id", None)
    branch_id = data.pop("branch_id", None)
    if campaign_provided:
        relations["campaign"] = (
            MarketingCampaign.objects.filter(id=campaign_id).first()
            if campaign_id
            else None
        )
        if campaign_id and (not relations["campaign"]):
            raise ValidationError("Campaign not found")
    if branch_provided:
        relations["branch"] = (
            Branch.objects.filter(id=branch_id).first() if branch_id else None
        )
        if branch_id and (not relations["branch"]):
            raise ValidationError("Branch not found")
    return (data, relations)


def _email_filters(payload):
    return payload.filters or {}


def _lead_queryset(request):
    return scope_queryset(
        request,
        Lead.objects.select_related(
            "campaign", "referral_partner", "branch", "assigned_to", "assigned_to__user"
        ),
        branch_field="branch_id",
    )


def _calendar_queryset(request):
    return scope_queryset(
        request,
        ContentCalendarItem.objects.select_related(
            "content", "campaign", "branch", "owner", "owner__user"
        ),
        branch_field="branch_id",
    )


def _target_queryset(request):
    return scope_queryset(
        request,
        with_target_progress(
            EmployeeTarget.objects.select_related(
                "employee", "employee__branch", "role"
            ).filter(is_active=True)
        ),
        branch_field="employee__branch_id",
    )


def _apply_common_filters(leads, branch_id=None, division=None, campaign_id=None):
    if branch_id:
        leads = leads.filter(branch_id=branch_id)
    if division:
        leads = leads.filter(division=division)
    if campaign_id:
        leads = leads.filter(campaign_id=campaign_id)
    return leads


def _period_leads(request, start, end, branch_id=None, division=None, campaign_id=None):
    leads = _apply_common_filters(
        _lead_queryset(request), branch_id, division, campaign_id
    )
    return leads.filter(created_at__date__gte=start, created_at__date__lte=end)


def _period_calendar_items(
    request, start, end, branch_id=None, division=None, campaign_id=None
):
    items = _calendar_queryset(request).filter(
        Q(due_date__gte=start, due_date__lte=end)
        | Q(scheduled_at__date__gte=start, scheduled_at__date__lte=end)
        | Q(published_at__date__gte=start, published_at__date__lte=end)
    )
    if branch_id:
        items = items.filter(branch_id=branch_id)
    if division:
        items = items.filter(division=division)
    if campaign_id:
        items = items.filter(campaign_id=campaign_id)
    return items.distinct()


def _target_rows(request, start, end, branch_id=None):
    targets = _target_queryset(request).filter(
        period_start__lte=end, period_end__gte=start
    )
    if branch_id:
        targets = targets.filter(employee__branch_id=branch_id)
    rows = []
    for target in targets.order_by("sequence", "id")[:20]:
        actual = target.get_approved_progress_value()
        target_value = target.target_value or Decimal("0.00")
        progress_pct = (
            Decimal("100.00")
            if target_value == 0
            else min(
                actual / target_value * Decimal("100"), Decimal("100.00")
            ).quantize(Decimal("0.01"))
        )
        rows.append(
            {
                "id": target.id,
                "label": target.title,
                "target": target_value,
                "actual": actual,
                "unit": target.unit,
                "period": target.period,
                "progress_pct": progress_pct,
                "status": (
                    "on_track"
                    if progress_pct >= 90
                    else "at_risk" if progress_pct >= 70 else "off_track"
                ),
            }
        )
    return rows


def _lead_breakdown(leads, field, choices):
    total = leads.count()
    rows = []
    for value, label in choices:
        count = leads.filter(**{field: value}).count()
        if count:
            rows.append(
                {
                    field: value,
                    "label": label,
                    "count": count,
                    "percentage": _pct(count, total),
                }
            )
    return rows


def _weekly_content_output(items, start, end):
    weeks = []
    cursor = start - timedelta(days=start.weekday())
    while cursor <= end:
        week_end = min(cursor + timedelta(days=6), end)
        week_items = items.filter(
            Q(due_date__gte=cursor, due_date__lte=week_end)
            | Q(scheduled_at__date__gte=cursor, scheduled_at__date__lte=week_end)
            | Q(published_at__date__gte=cursor, published_at__date__lte=week_end)
        )
        weeks.append(
            {
                "week_start": cursor,
                "week_end": week_end,
                "planned": week_items.count(),
                "published": week_items.filter(status="published").count(),
            }
        )
        cursor += timedelta(days=7)
    return weeks


def _content_by_format(items):
    rows = []
    for value, label in ContentCalendarItem.FORMAT_CHOICES:
        format_items = items.filter(format=value)
        planned = format_items.count()
        if not planned:
            continue
        published_items = format_items.filter(status="published")
        views = [
            item.content.views
            for item in published_items
            if item.content_id and item.content.views is not None
        ]
        rows.append(
            {
                "format": value,
                "label": label,
                "planned": planned,
                "published": published_items.count(),
                "avg_reach": round(sum(views) / len(views), 1) if views else None,
            }
        )
    return rows


def _lead_source_rows(leads, campaigns, campaign_id=None):
    rows = []
    for value, label in Lead.SOURCE_CHOICES:
        source_leads = leads.filter(source=value)
        lead_count = source_leads.count()
        if not lead_count:
            continue
        contacted = source_leads.filter(
            Q(first_response_at__isnull=False)
            | Q(first_contact_at__isnull=False)
            | ~Q(status="new")
        ).count()
        won = source_leads.filter(status="won").count()
        estimated_cpl = None
        if campaign_id:
            spend = _decimal_sum(campaigns.filter(id=campaign_id), "budget_spent")
            estimated_cpl = (
                (spend / Decimal(lead_count)).quantize(Decimal("0.01"))
                if lead_count
                else None
            )
        rows.append(
            {
                "source": value,
                "label": label,
                "leads": lead_count,
                "contacted_pct": _pct(contacted, lead_count),
                "converted": won,
                "estimated_cpl": estimated_cpl,
            }
        )
    return rows


def _team_scorecard(leads, start, end):
    rows = []
    owner_ids = list(
        leads.exclude(assigned_to__isnull=True)
        .values_list("assigned_to_id", flat=True)
        .distinct()
    )
    for owner_id in owner_ids:
        owner_leads = leads.filter(assigned_to_id=owner_id)
        employee = owner_leads.first().assigned_to
        total = owner_leads.count()
        contacted = owner_leads.filter(
            Q(first_response_at__isnull=False)
            | Q(first_contact_at__isnull=False)
            | ~Q(status="new")
        ).count()
        activities = LeadActivity.objects.filter(
            lead_id__in=owner_leads.values("id"),
            created_at__date__gte=start,
            created_at__date__lte=end,
        ).count()
        won = owner_leads.filter(status="won").count()
        score = (
            round(
                (_pct(contacted, total) + min(100, activities * 10) + _pct(won, total))
                / 3
            )
            if total
            else 0
        )
        rows.append(
            {
                "employee_id": owner_id,
                "employee_name": _employee_name(employee),
                "role": employee.role.name if employee and employee.role else "",
                "leads": total,
                "contacted_pct": _pct(contacted, total),
                "activities": activities,
                "won": won,
                "score": score,
                "status": (
                    "on_track"
                    if score >= 80
                    else "at_risk" if score >= 60 else "off_track"
                ),
            }
        )
    return sorted(rows, key=lambda row: (-row["score"], row["employee_name"]))


def _partner_portal_token(request):
    token = request.GET.get("token") or request.headers.get("X-Partner-Token", "")
    auth_header = request.headers.get("Authorization", "")
    if not token and auth_header.lower().startswith("bearer "):
        token = auth_header[7:]
    return (token or "").strip()


def _partner_row(partner, leads=None):
    partner_leads = (
        leads.filter(referral_partner=partner)
        if leads is not None
        else Lead.objects.filter(referral_partner=partner)
    )
    won_leads = partner_leads.filter(status="won")
    commissions = partner.marketing_commissions.all()
    tasks = partner.marketing_tasks.all()
    reports = partner.marketing_reports.all()
    latest_report = reports.order_by("-created_at").first()
    return {
        "id": partner.id,
        "name": partner.name,
        "email": partner.email,
        "phone": partner.phone,
        "category": partner.category,
        "category_display": partner.get_category_display(),
        "status": partner.status,
        "status_display": partner.get_status_display(),
        "referred_leads": partner_leads.count(),
        "closed_leads": won_leads.count(),
        "closed_revenue": _decimal_sum(won_leads, "estimated_value"),
        "commission_due": _decimal_sum(
            commissions.filter(status__in=["pending_verification", "approved"]),
            "commission_due",
        ),
        "commission_paid": _decimal_sum(
            commissions.filter(status="paid"), "commission_due"
        ),
        "active_tasks": tasks.exclude(status__in=["approved", "cancelled"]).count(),
        "pending_reports": reports.filter(status="submitted").count(),
        "latest_report_status": latest_report.status if latest_report else "",
        "created_at": partner.created_at,
        "updated_at": partner.updated_at,
    }


def _campaign_period_bounds(period_start=None, period_end=None):
    today = timezone.localdate()
    start = period_start or today.replace(day=1)
    end = period_end or today
    if start > end:
        start, end = (end, start)
    return (start, end)


def _campaign_decimal_sum(qs, field):
    return qs.aggregate(total=Sum(field))["total"] or Decimal("0.00")


def _campaign_campaign_queryset(request):
    return scope_queryset(request, MarketingCampaign.objects.all())


def _campaign_lead_queryset(request):
    return scope_queryset(
        request,
        Lead.objects.select_related(
            "campaign", "branch", "assigned_to", "assigned_to__user"
        ),
        branch_field="branch_id",
    )


def _campaign_campaign_metrics(campaign, leads, period_start, period_end):
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
    pipeline_value = _campaign_decimal_sum(pipeline_leads, "estimated_value")
    won_revenue = _campaign_decimal_sum(won_leads, "estimated_value")
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
        "estimated_roas": (
            _money_ratio(won_revenue, total_spend) if total_spend else Decimal("0.00")
        ),
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


def _campaign_filter_campaigns(
    campaigns,
    leads,
    status=None,
    channel=None,
    search=None,
    branch_id=None,
    division=None,
):
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
        campaigns = campaigns.filter(
            id__in=leads.exclude(campaign_id=None).values("campaign_id")
        )
    return (campaigns.distinct(), leads)


def _campaign_budget_summary(campaign):
    expenses = campaign.workspace_expenses.all()
    committed = expenses.exclude(status="rejected").aggregate(total=Sum("amount"))[
        "total"
    ] or Decimal("0.00")
    paid = expenses.filter(status="paid").aggregate(total=Sum("amount"))[
        "total"
    ] or Decimal("0.00")
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


def _campaign_workspace_snapshot(request, campaign):
    start, end = _campaign_period_bounds()
    leads = _campaign_lead_queryset(request)
    campaign_leads = leads.filter(campaign_id=campaign.id)
    lead_statuses = [
        {"status": status, "count": campaign_leads.filter(status=status).count()}
        for status, _label in Lead.STATUS_CHOICES
    ]
    funnel_events = LeadFunnelEvent.objects.filter(campaign_id=campaign.id)
    funnel_stages = [
        {
            "stage": stage,
            "count": funnel_events.filter(to_stage=stage)
            .values("lead_id")
            .distinct()
            .count(),
        }
        for stage in FUNNEL_STAGE_ORDER
    ]
    tasks = campaign.workspace_tasks.select_related("owner", "owner__user").all()
    assets = campaign.workspace_assets.select_related("owner", "owner__user").all()
    risks = campaign.workspace_risks.select_related("owner", "owner__user").all()
    expenses = campaign.workspace_expenses.all()
    updates = campaign.workspace_updates.select_related("author").all()
    decisions = campaign.workspace_decisions.select_related(
        "source_meeting_context", "source_meeting_context__meeting"
    ).all()
    meeting_contexts = (
        campaign.marketing_meeting_contexts.select_related(
            "meeting", "meeting__organizer"
        )
        .prefetch_related("meeting__attendees", "actions", "campaign_decisions")
        .all()
    )
    today = timezone.localdate()
    next_meeting = (
        meeting_contexts.filter(
            meeting__status="scheduled", meeting__meeting_date__gte=today
        )
        .order_by("meeting__meeting_date", "meeting__meeting_time")
        .first()
    )
    source_request = campaign.source_requests.select_related(
        "requester", "branch"
    ).first()
    return {
        "campaign": _campaign_base(campaign),
        "performance": {
            **_campaign_campaign_metrics(campaign, leads, start, end),
            "lead_status_breakdown": lead_statuses,
            "funnel_stage_breakdown": funnel_stages,
            "recent_leads": [_lead_row(lead) for lead in campaign_leads[:10]],
        },
        "budget": {
            **_campaign_budget_summary(campaign),
            "expenses": [_serialize_expense(expense) for expense in expenses],
        },
        "source_request": (
            _serialize_request(source_request) if source_request else None
        ),
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
                "critical": risks.filter(severity="critical")
                .exclude(status="closed")
                .count(),
            },
            "items": [_serialize_risk(risk) for risk in risks],
        },
        "meetings": {
            "summary": {
                "total": meeting_contexts.count(),
                "upcoming": meeting_contexts.filter(
                    meeting__status="scheduled", meeting__meeting_date__gte=today
                ).count(),
                "completed": meeting_contexts.filter(
                    meeting__status="completed"
                ).count(),
                "open_actions": sum(
                    (
                        context.actions.exclude(
                            status__in=["done", "cancelled"]
                        ).count()
                        for context in meeting_contexts
                    )
                ),
            },
            "next_meeting": (
                _serialize_workspace_meeting(next_meeting) if next_meeting else None
            ),
            "items": [
                _serialize_workspace_meeting(context) for context in meeting_contexts
            ],
        },
        "decisions": [_serialize_decision(decision) for decision in decisions],
        "post_analysis": _serialize_post_analysis(
            getattr(campaign, "post_analysis", None)
        ),
        "activity_feed": _campaign_activity_feed(campaign),
    }


def _campaign_activity_feed(campaign):
    items = []
    for update in campaign.workspace_updates.select_related("author")[:20]:
        items.append(
            {
                "type": "update",
                "text": f"{update.update_type}: {update.text}",
                "actor": update.author.get_full_name() if update.author else "",
                "time": update.update_date,
            }
        )
    for decision in campaign.workspace_decisions.all()[:20]:
        items.append(
            {
                "type": "decision",
                "text": decision.decision,
                "actor": decision.owner,
                "time": decision.decision_date,
            }
        )
    for expense in campaign.workspace_expenses.all()[:20]:
        items.append(
            {
                "type": "budget",
                "text": f"{expense.vendor}: {expense.amount}",
                "actor": "Marketing / Finance",
                "time": expense.expense_date,
            }
        )
    return sorted(items, key=lambda item: str(item["time"]), reverse=True)[:30]


def _content_week_bounds(week_start=None, date_from=None, date_to=None):
    today = timezone.localdate()
    if date_from or date_to:
        start = date_from or date_to
        end = date_to or date_from
        if start > end:
            start, end = (end, start)
        return (start, end)
    start = week_start or today - timedelta(days=today.weekday())
    return (start, start + timedelta(days=6))


def _content_calendar_queryset(request):
    return scope_queryset(
        request,
        ContentCalendarItem.objects.select_related(
            "branch",
            "owner",
            "owner__user",
            "campaign",
            "campaign_asset",
            "content",
            "created_by",
        ),
        branch_field="branch_id",
    )


def _content_media_queryset(request):
    return scope_queryset(
        request,
        MediaLibraryAsset.objects.select_related(
            "branch",
            "owner",
            "owner__user",
            "campaign",
            "campaign_asset",
            "calendar_item",
            "content",
            "uploaded_by",
        ),
        branch_field="branch_id",
    )


def _content_filter_media_assets(
    assets,
    asset_type=None,
    division=None,
    campaign_id=None,
    content_id=None,
    calendar_item_id=None,
    branch_id=None,
    owner_id=None,
    status=None,
    search=None,
):
    if asset_type:
        assets = assets.filter(asset_type=asset_type)
    if division:
        assets = assets.filter(division=division)
    if campaign_id:
        assets = assets.filter(campaign_id=campaign_id)
    if content_id:
        assets = assets.filter(content_id=content_id)
    if calendar_item_id:
        assets = assets.filter(calendar_item_id=calendar_item_id)
    if branch_id:
        assets = assets.filter(branch_id=branch_id)
    if owner_id:
        assets = assets.filter(owner_id=owner_id)
    if status:
        assets = assets.filter(status=status)
    if search:
        assets = assets.filter(
            Q(title__icontains=search)
            | Q(description__icontains=search)
            | Q(tags__icontains=search)
            | Q(file_url__icontains=search)
            | Q(owner_name__icontains=search)
            | Q(campaign__name__icontains=search)
            | Q(content__title__icontains=search)
        )
    return assets.distinct()


def _content_media_summary(assets):
    total_size = assets.aggregate(total=Sum("file_size_bytes"))["total"] or 0
    type_counts = [
        {
            "asset_type": value,
            "label": label,
            "count": assets.filter(asset_type=value).count(),
        }
        for value, label in MediaLibraryAsset.ASSET_TYPE_CHOICES
    ]
    return {
        "total_assets": assets.count(),
        "active_assets": assets.filter(status="active").count(),
        "archived_assets": assets.filter(status="archived").count(),
        "total_size_bytes": total_size,
        "total_size_display": _format_bytes(total_size),
        "type_counts": type_counts,
    }


def _content_resolve_media_relations(data):
    missing = object()
    branch_id = data.pop("branch_id", missing)
    owner_id = data.pop("owner_id", missing)
    campaign_id = data.pop("campaign_id", missing)
    campaign_asset_id = data.pop("campaign_asset_id", missing)
    calendar_item_id = data.pop("calendar_item_id", missing)
    content_id = data.pop("content_id", missing)
    relations = {}
    if branch_id is not missing:
        relations["branch"] = (
            Branch.objects.filter(id=branch_id).first() if branch_id else None
        )
    if owner_id is not missing:
        relations["owner"] = (
            Employee.objects.filter(id=owner_id).first() if owner_id else None
        )
    if campaign_id is not missing:
        relations["campaign"] = (
            MarketingCampaign.objects.filter(id=campaign_id).first()
            if campaign_id
            else None
        )
    if campaign_asset_id is not missing:
        relations["campaign_asset"] = (
            CampaignAsset.objects.select_related("campaign", "content")
            .filter(id=campaign_asset_id)
            .first()
            if campaign_asset_id
            else None
        )
    if calendar_item_id is not missing:
        relations["calendar_item"] = (
            ContentCalendarItem.objects.select_related(
                "campaign", "campaign_asset", "content"
            )
            .filter(id=calendar_item_id)
            .first()
            if calendar_item_id
            else None
        )
    if content_id is not missing:
        relations["content"] = (
            Content.objects.filter(id=content_id).first() if content_id else None
        )
    campaign_asset = relations.get("campaign_asset")
    calendar_item = relations.get("calendar_item")
    if calendar_item:
        if not relations.get("campaign"):
            relations["campaign"] = calendar_item.campaign
        if not relations.get("campaign_asset"):
            relations["campaign_asset"] = calendar_item.campaign_asset
        if not relations.get("content"):
            relations["content"] = calendar_item.content
    campaign_asset = relations.get("campaign_asset")
    if campaign_asset:
        campaign = relations.get("campaign")
        if campaign and campaign.id != campaign_asset.campaign_id:
            raise ValidationError(
                {
                    "campaign_asset_id": "Campaign asset does not belong to the selected campaign."
                }
            )
        relations["campaign"] = campaign_asset.campaign
        if not relations.get("content"):
            relations["content"] = campaign_asset.content
    return (data, relations)


def _content_filter_calendar_items(
    items,
    start,
    end,
    status=None,
    platform=None,
    division=None,
    owner_id=None,
    campaign_id=None,
    branch_id=None,
    search=None,
):
    items = items.filter(
        Q(due_date__gte=start, due_date__lte=end)
        | Q(scheduled_at__date__gte=start, scheduled_at__date__lte=end)
        | Q(published_at__date__gte=start, published_at__date__lte=end)
    )
    if status:
        if status == "overdue":
            items = items.exclude(status__in=TERMINAL_CALENDAR_STATUSES).filter(
                due_date__lt=timezone.localdate()
            )
        else:
            items = items.filter(status=status)
    if platform:
        items = items.filter(platform=platform)
    if division:
        items = items.filter(division=division)
    if owner_id:
        items = items.filter(owner_id=owner_id)
    if campaign_id:
        items = items.filter(campaign_id=campaign_id)
    if branch_id:
        items = items.filter(branch_id=branch_id)
    if search:
        items = items.filter(
            Q(title__icontains=search)
            | Q(description__icontains=search)
            | Q(specifications__icontains=search)
            | Q(owner_name__icontains=search)
            | Q(campaign__name__icontains=search)
        )
    return items.distinct()


def _content_content_only_rows(start, end, status=None, platform=None, search=None):
    contents = (
        Content.objects.select_related("author")
        .filter(calendar_items__isnull=True)
        .filter(
            Q(scheduled_date__date__gte=start, scheduled_date__date__lte=end)
            | Q(published_date__date__gte=start, published_date__date__lte=end)
        )
    )
    if status:
        if status == "overdue":
            return []
        contents = contents.filter(status=status)
    if platform:
        contents = contents.filter(platform=platform)
    if search:
        contents = contents.filter(
            Q(title__icontains=search)
            | Q(body__icontains=search)
            | Q(excerpt__icontains=search)
            | Q(tags__icontains=search)
        )
    return [_serialize_content_only(content) for content in contents.distinct()]


def _content_apply_calendar_relations(data):
    missing = object()
    branch_id = data.pop("branch_id", missing)
    owner_id = data.pop("owner_id", missing)
    campaign_id = data.pop("campaign_id", missing)
    content_id = data.pop("content_id", missing)
    relations = {}
    if branch_id is not missing:
        relations["branch"] = (
            Branch.objects.filter(id=branch_id).first() if branch_id else None
        )
    if owner_id is not missing:
        relations["owner"] = (
            Employee.objects.filter(id=owner_id).first() if owner_id else None
        )
    if campaign_id is not missing:
        relations["campaign"] = (
            MarketingCampaign.objects.filter(id=campaign_id).first()
            if campaign_id
            else None
        )
    if content_id is not missing:
        relations["content"] = (
            Content.objects.filter(id=content_id).first() if content_id else None
        )
    return (data, relations)
