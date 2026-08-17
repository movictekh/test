import csv
import hashlib
import html
import logging
import secrets
from datetime import date, timedelta
from decimal import Decimal
from io import StringIO

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.utils import timezone
from ninja import Router

from domains.marketing_sales.api.v1.schemas.sales import (
    BranchPerformanceSchema,
    ChannelMetricsSchema,
    MarketingOverviewSchema,
)
from domains.marketing_sales.api.v1.schemas.marketing import (
    EmailMarketingAudienceRequest,
    EmailMarketingSendRequest,
    MarketingMeetingActionIn,
    MarketingMeetingActionUpdate,
    MarketingMeetingDecisionIn,
    MarketingMeetingIn,
    MarketingMeetingUpdate,
    PartnerCommissionIn,
    PartnerCommissionUpdate,
    PartnerInvitationIn,
    PartnerReferredLeadIn,
    PartnerReportIn,
    PartnerReportReviewIn,
    PartnerTaskIn,
    PartnerTaskUpdate,
    TraditionalMediaPlacementIn,
    TraditionalMediaPlacementUpdate,
)
from domains.marketing_sales.services.funnel import record_initial_funnel_event
from services.models.content import ContentCalendarItem
from services.models.crm import FunnelLead, Lead, LeadActivity
from services.models.marketing_campaign import (
    CampaignDecision,
    EmailMarketingCampaign,
    EmailMarketingRecipient,
    MarketingCampaign,
    MarketingMeetingAction,
    MarketingMeetingContext,
    PartnerCommission,
    PartnerInvitation,
    PartnerReport,
    PartnerTask,
    TraditionalMediaPlacement,
)
from user.models.branch import Branch
from user.models.client import Client as CustomerClient
from user.models.employee import Employee
from user.models.meeting import Meeting
from user.models.partner import Partner
from user.models.role_targets import EmployeeTarget, with_target_progress
from user.models.user import User
from user.utils.perm import require_permission, scope_queryset
from user.utils.send_email import send_marketing_email

marketing_router = Router(tags=["Marketing Command Center"])
logger = logging.getLogger(__name__)

EMAIL_AUDIENCE_GROUPS = {
    "marketing_leads": "Marketing leads",
    "clients": "Clients",
    "partners": "Partners / realtors",
    "employees": "Employees",
    "manual": "Manual recipients",
}

MARKETING_MEETING_STATUS_ALIASES = {
    "upcoming": "scheduled",
}

MEETING_BASE_FIELDS = {
    "title",
    "agenda",
    "meeting_date",
    "meeting_time",
    "duration_minutes",
    "status",
    "location_type",
    "location",
    "notes",
    "file_url",
}

MEETING_CONTEXT_FIELDS = {
    "meeting_type",
    "facilitator",
    "recorder",
    "pre_read",
    "expected_outcome",
}

TRADITIONAL_MEDIA_EXPIRY_WINDOW_DAYS = 14


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


def _employee_name(employee):
    if not employee:
        return "Unassigned"
    full_name = employee.user.get_full_name()
    return full_name or employee.user.email or employee.user.username


def _user_name(user):
    if not user:
        return ""
    return user.get_full_name() or user.email or user.username


def _valid_email_or_none(email):
    email = (email or "").strip()
    if not email:
        return None
    try:
        validate_email(email)
    except ValidationError:
        return None
    return email


def _email_body_to_html(body):
    body = body or ""
    if "<" in body and ">" in body:
        return body
    return "<div>" + html.escape(body).replace("\n", "<br>") + "</div>"


def _email_campaign_row(campaign, include_recipients=False):
    row = {
        "id": campaign.id,
        "subject": campaign.subject,
        "body": campaign.body,
        "audience_groups": campaign.audience_groups,
        "filters": campaign.filters,
        "status": campaign.status,
        "recipient_count": campaign.recipient_count,
        "sent_count": campaign.sent_count,
        "failed_count": campaign.failed_count,
        "created_by_id": campaign.created_by_id,
        "sent_at": campaign.sent_at,
        "created_at": campaign.created_at,
        "updated_at": campaign.updated_at,
    }
    if include_recipients:
        row["recipients"] = [
            {
                "id": recipient.id,
                "email": recipient.email,
                "name": recipient.name,
                "source_group": recipient.source_group,
                "source_object_type": recipient.source_object_type,
                "source_object_id": recipient.source_object_id,
                "status": recipient.status,
                "provider_status_code": recipient.provider_status_code,
                "error": recipient.error,
                "created_at": recipient.created_at,
                "updated_at": recipient.updated_at,
            }
            for recipient in campaign.recipients.all()
        ]
    return row


def _validation_detail(exc):
    if hasattr(exc, "message_dict"):
        return "; ".join(
            f"{field}: {', '.join(messages)}"
            for field, messages in exc.message_dict.items()
        )
    return exc.messages[0] if getattr(exc, "messages", None) else str(exc)


def _meeting_status(status):
    if not status:
        return status
    return MARKETING_MEETING_STATUS_ALIASES.get(status.lower(), status.lower())


def _attendee_row(user):
    return {
        "user_id": user.id,
        "full_name": _user_name(user),
        "email": user.email,
    }


def _serialize_marketing_meeting_action(action):
    return {
        "id": action.id,
        "meeting_id": action.meeting_context.meeting_id,
        "meeting_context_id": action.meeting_context_id,
        "meeting_title": action.meeting_context.meeting.title,
        "campaign_id": action.meeting_context.campaign_id,
        "campaign_name": (
            action.meeting_context.campaign.name
            if action.meeting_context.campaign
            else ""
        ),
        "title": action.title,
        "description": action.description,
        "owner_id": action.owner_id,
        "owner_name": action.owner_name or _employee_name(action.owner),
        "due_date": action.due_date,
        "status": action.status,
        "priority": action.priority,
        "completed_at": action.completed_at,
        "created_at": action.created_at,
        "updated_at": action.updated_at,
    }


def _serialize_marketing_meeting_decision(decision):
    context = decision.source_meeting_context
    return {
        "id": decision.id,
        "campaign_id": decision.campaign_id,
        "campaign_name": decision.campaign.name if decision.campaign else "",
        "meeting_id": context.meeting_id if context else None,
        "source_meeting_id": context.meeting_id if context else None,
        "meeting_context_id": context.id if context else None,
        "source_meeting_context_id": context.id if context else None,
        "meeting_title": context.meeting.title if context else "",
        "decision_date": decision.decision_date,
        "decision": decision.decision,
        "owner": decision.owner,
        "approver": decision.approver,
        "reason": decision.reason,
        "created_at": decision.created_at,
        "updated_at": decision.updated_at,
    }


def _serialize_marketing_meeting_context(context, include_detail=False):
    meeting = context.meeting
    row = {
        "id": meeting.id,
        "meeting_context_id": context.id,
        "meeting_id": meeting.meeting_id,
        "title": meeting.title,
        "agenda": meeting.agenda,
        "meeting_date": meeting.meeting_date,
        "meeting_time": meeting.meeting_time.strftime("%H:%M"),
        "duration_minutes": meeting.duration_minutes,
        "duration_display": meeting.duration_display,
        "status": meeting.status,
        "location_type": meeting.location_type,
        "location": meeting.location,
        "organizer_id": meeting.organizer_id,
        "organizer_name": _user_name(meeting.organizer),
        "attendee_count": meeting.attendees.count(),
        "notes": meeting.notes,
        "file_url": meeting.file_url,
        "campaign_id": context.campaign_id,
        "campaign_name": context.campaign.name if context.campaign else "",
        "meeting_type": context.meeting_type,
        "facilitator": context.facilitator,
        "recorder": context.recorder,
        "pre_read": context.pre_read,
        "expected_outcome": context.expected_outcome,
        "open_action_count": context.actions.exclude(
            status__in=["done", "cancelled"]
        ).count(),
        "decision_count": context.campaign_decisions.count(),
        "created_at": meeting.created_at,
        "updated_at": meeting.updated_at,
    }
    if include_detail:
        row["attendees"] = [_attendee_row(user) for user in meeting.attendees.all()]
        row["actions"] = [
            _serialize_marketing_meeting_action(action)
            for action in context.actions.select_related(
                "owner",
                "owner__user",
                "meeting_context__meeting",
                "meeting_context__campaign",
            ).all()
        ]
        row["decisions"] = [
            _serialize_marketing_meeting_decision(decision)
            for decision in context.campaign_decisions.select_related(
                "campaign", "source_meeting_context__meeting"
            ).all()
        ]
    return row


def _marketing_meeting_queryset():
    return MarketingMeetingContext.objects.select_related(
        "meeting",
        "meeting__organizer",
        "campaign",
    ).prefetch_related(
        "meeting__attendees",
        "actions",
        "campaign_decisions",
    )


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


def _meeting_payload_data(payload, exclude_unset=False):
    data = payload.dict(exclude_unset=exclude_unset)
    attendee_ids = data.pop("attendee_ids", None)
    campaign_id = data.pop("campaign_id", None)
    base_data = {
        key: value for key, value in data.items() if key in MEETING_BASE_FIELDS
    }
    context_data = {
        key: value for key, value in data.items() if key in MEETING_CONTEXT_FIELDS
    }
    return base_data, context_data, attendee_ids, campaign_id


def _set_meeting_attendees(meeting, attendee_ids):
    if attendee_ids is None:
        return None
    attendees = User.objects.filter(id__in=attendee_ids)
    if attendees.count() != len(attendee_ids):
        raise ValidationError("One or more attendee user IDs are invalid")
    meeting.attendees.set(attendees)
    return attendees


def _traditional_media_queryset(request):
    return scope_queryset(
        request,
        TraditionalMediaPlacement.objects.select_related(
            "campaign", "branch", "created_by"
        ),
        branch_field="branch_id",
    )


def _placement_days_remaining(placement, today=None):
    today = today or timezone.localdate()
    return (placement.end_date - today).days


def _placement_expiry_state(placement, today=None):
    if placement.status in ["archived", "cancelled"]:
        return placement.status
    days_remaining = _placement_days_remaining(placement, today)
    if days_remaining < 0:
        return "expired"
    if days_remaining <= TRADITIONAL_MEDIA_EXPIRY_WINDOW_DAYS:
        return "expiring_soon"
    return "active"


def _placement_code(placement):
    return f"TM-{placement.id:04d}"


def _serialize_traditional_media_placement(placement, detail=False):
    today = timezone.localdate()
    days_remaining = _placement_days_remaining(placement, today)
    row = {
        "id": placement.id,
        "placement_code": _placement_code(placement),
        "placement_type": placement.placement_type,
        "placement_type_display": placement.get_placement_type_display(),
        "name": placement.name,
        "vendor": placement.vendor,
        "location": placement.location,
        "ownership": placement.ownership,
        "ownership_display": placement.get_ownership_display(),
        "amount_paid": placement.amount_paid,
        "start_date": placement.start_date,
        "end_date": placement.end_date,
        "days_remaining": days_remaining,
        "expiry_state": _placement_expiry_state(placement, today),
        "status": placement.status,
        "status_display": placement.get_status_display(),
        "proof_url": placement.proof_url,
        "campaign_id": placement.campaign_id,
        "campaign_name": placement.campaign.name if placement.campaign else "",
        "branch_id": placement.branch_id,
        "branch_name": placement.branch.branch_name if placement.branch else "",
        "division": placement.division,
        "notes": placement.notes,
        "created_by_id": placement.created_by_id,
        "created_by_name": _user_name(placement.created_by),
        "created_at": placement.created_at,
        "updated_at": placement.updated_at,
    }
    if detail:
        row["metadata"] = {
            "expiry_window_days": TRADITIONAL_MEDIA_EXPIRY_WINDOW_DAYS,
            "expiry_is_derived_from_end_date": True,
            "renew_action_supported": False,
        }
    return row


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


def _traditional_media_metadata():
    return {
        "placement_types": [
            {"value": value, "label": label}
            for value, label in TraditionalMediaPlacement.PLACEMENT_TYPE_CHOICES
        ],
        "ownerships": [
            {"value": value, "label": label}
            for value, label in TraditionalMediaPlacement.OWNERSHIP_CHOICES
        ],
        "statuses": [
            {"value": value, "label": label}
            for value, label in TraditionalMediaPlacement.STATUS_CHOICES
        ],
        "expiry_filters": [
            {"value": "active", "label": "Active"},
            {"value": "expiring_soon", "label": "Expiring soon"},
            {"value": "expired", "label": "Expired"},
        ],
        "divisions": [
            {"value": value, "label": label}
            for value, label in TraditionalMediaPlacement.DIVISION_CHOICES
        ],
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
        if campaign_id and not relations["campaign"]:
            raise ValidationError("Campaign not found")
    if branch_provided:
        relations["branch"] = (
            Branch.objects.filter(id=branch_id).first() if branch_id else None
        )
        if branch_id and not relations["branch"]:
            raise ValidationError("Branch not found")
    return data, relations


def _add_email_recipient(
    recipients_by_email,
    email,
    name,
    source_group,
    source_object_type="",
    source_object_id=None,
):
    valid_email = _valid_email_or_none(email)
    if not valid_email:
        return False
    key = valid_email.lower()
    if key in recipients_by_email:
        return False
    recipients_by_email[key] = {
        "email": valid_email,
        "name": name or valid_email.split("@")[0],
        "source_group": source_group,
        "source_object_type": source_object_type,
        "source_object_id": source_object_id,
    }
    return True


def _email_filters(payload):
    return payload.filters or {}


def _validate_email_audience_groups(groups):
    groups = groups or []
    invalid = [group for group in groups if group not in EMAIL_AUDIENCE_GROUPS]
    if invalid:
        raise ValidationError(
            {"audience_groups": f"Unsupported audience groups: {', '.join(invalid)}"}
        )
    return groups


def _resolve_email_recipients(request, payload):
    groups = _validate_email_audience_groups(payload.audience_groups)
    filters = _email_filters(payload)
    recipients_by_email = {}
    skipped_count = 0

    if "marketing_leads" in groups:
        leads = _lead_queryset(request).exclude(email="")
        if filters.get("division"):
            leads = leads.filter(division=filters["division"])
        if filters.get("status"):
            leads = leads.filter(status=filters["status"])
        if filters.get("source"):
            leads = leads.filter(source=filters["source"])
        if filters.get("campaign_id"):
            leads = leads.filter(campaign_id=filters["campaign_id"])
        if filters.get("branch_id"):
            leads = leads.filter(branch_id=filters["branch_id"])
        for lead in leads.order_by("full_name", "id"):
            if not _add_email_recipient(
                recipients_by_email,
                lead.email,
                lead.full_name,
                "marketing_leads",
                "services.Lead",
                lead.id,
            ):
                skipped_count += 1

    if "clients" in groups:
        clients = (
            CustomerClient.objects.select_related("user")
            .filter(is_active=True)
            .exclude(user__email="")
        )
        for client in clients.order_by("user__first_name", "user__last_name", "id"):
            if not _add_email_recipient(
                recipients_by_email,
                client.user.email,
                _user_name(client.user),
                "clients",
                "user.Client",
                client.id,
            ):
                skipped_count += 1

    if "partners" in groups:
        partners = Partner.objects.filter(status="active").exclude(email="")
        for partner in partners.order_by("name", "id"):
            if not _add_email_recipient(
                recipients_by_email,
                partner.email,
                partner.name,
                "partners",
                "user.Partner",
                partner.id,
            ):
                skipped_count += 1

    if "employees" in groups:
        employees = scope_queryset(
            request,
            Employee.objects.select_related("user", "branch")
            .filter(is_active=True)
            .exclude(user__email=""),
            branch_field="branch_id",
        )
        if filters.get("branch_id"):
            employees = employees.filter(branch_id=filters["branch_id"])
        for employee in employees.order_by("user__first_name", "user__last_name", "id"):
            if not _add_email_recipient(
                recipients_by_email,
                employee.user.email,
                _employee_name(employee),
                "employees",
                "user.Employee",
                employee.id,
            ):
                skipped_count += 1

    if "manual" in groups or payload.manual_recipients:
        for recipient in payload.manual_recipients or []:
            if not _add_email_recipient(
                recipients_by_email, recipient.email, recipient.name, "manual", "", None
            ):
                skipped_count += 1

    return list(recipients_by_email.values()), skipped_count


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
                (actual / target_value) * Decimal("100"),
                Decimal("100.00"),
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


def _revenue_target_totals(target_rows):
    revenue_rows = [
        row
        for row in target_rows
        if "revenue" in row["label"].lower()
        or "sales" in row["label"].lower()
        or row["unit"].lower() in ["ngn", "naira", "₦"]
    ]
    return {
        "target": sum((row["target"] for row in revenue_rows), Decimal("0.00")),
        "actual": sum((row["actual"] for row in revenue_rows), Decimal("0.00")),
    }


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


@marketing_router.get("/marketing/overview", response=MarketingOverviewSchema)
@require_permission("dashboard", "view")
def get_marketing_overview(request):
    today = timezone.now()
    last_month_start = (today - timedelta(days=30)).replace(day=1)

    current_leads = FunnelLead.objects.filter(created_at__gte=last_month_start).count()

    last_month_leads = FunnelLead.objects.filter(
        created_at__gte=last_month_start - timedelta(days=30),
        created_at__lt=last_month_start,
    ).count()

    converted = FunnelLead.objects.filter(
        status="converted", created_at__gte=last_month_start
    ).count()

    current_revenue = FunnelLead.objects.filter(
        status="converted", converted_at__gte=last_month_start
    ).aggregate(total=Sum("value"))["total"] or Decimal("0")

    conversion_rate = 0.0
    if current_leads > 0:
        conversion_rate = round((converted / current_leads) * 100, 2)

    roi = 0.0

    bonus_growth = 0.0
    if last_month_leads > 0:
        bonus_growth = round(
            ((current_leads - last_month_leads) / last_month_leads) * 100, 2
        )

    return {
        "leads_generated": current_leads,
        "conversion_rate": conversion_rate,
        "roi": roi,
        "revenue": current_revenue,
        "bonus_growth": bonus_growth,
        "delta_vs_last_month": {
            "leads": current_leads - last_month_leads,
            "leads_pct": bonus_growth,
        },
    }


@marketing_router.get(
    "/marketing/branches/performance", response=list[BranchPerformanceSchema]
)
@require_permission("dashboard", "view")
def get_branch_performance(request):
    branches = Branch.objects.filter(is_active=True)
    result = []

    for branch in branches:
        leads = FunnelLead.objects.filter(branch=branch).count()
        revenue = FunnelLead.objects.filter(
            branch=branch, status="converted"
        ).aggregate(total=Sum("value"))["total"] or Decimal("0")

        status_val = "green"
        if revenue < 100000:
            status_val = "yellow"
        if revenue < 50000:
            status_val = "red"

        result.append(
            BranchPerformanceSchema(
                id=branch.id,
                name=branch.branch_name,
                leads=leads,
                revenue=revenue,
                status=status_val,
                target=Decimal("100000"),
                achieved_pct=min(100, round((revenue / Decimal("100000")) * 100, 2)),
            )
        )

    return result


@marketing_router.get("/marketing/channels", response=ChannelMetricsSchema)
@require_permission("dashboard", "view")
def get_channel_metrics(request):
    return {
        "content_produced": 0,
        "content_traffic": 0,
        "digital_traffic": 0,
        "digital_spend": Decimal("0"),
        "csrc_avg_response_time": 0.0,
    }


@marketing_router.get("/marketing/email/audiences")
@require_permission("marketing_campaigns", "list")
def get_email_audiences(request, branch_id: int = None):
    lead_filters = {}
    employee_filters = {}
    if branch_id:
        lead_filters["branch_id"] = branch_id
        employee_filters["branch_id"] = branch_id

    leads = _lead_queryset(request).exclude(email="").filter(**lead_filters)
    clients = (
        CustomerClient.objects.select_related("user")
        .filter(is_active=True)
        .exclude(user__email="")
    )
    partners = Partner.objects.filter(status="active").exclude(email="")
    employees = scope_queryset(
        request,
        Employee.objects.select_related("user", "branch")
        .filter(is_active=True)
        .exclude(user__email=""),
        branch_field="branch_id",
    ).filter(**employee_filters)

    return {
        "audiences": [
            {
                "key": "marketing_leads",
                "label": EMAIL_AUDIENCE_GROUPS["marketing_leads"],
                "count": leads.count(),
            },
            {
                "key": "clients",
                "label": EMAIL_AUDIENCE_GROUPS["clients"],
                "count": clients.count(),
            },
            {
                "key": "partners",
                "label": EMAIL_AUDIENCE_GROUPS["partners"],
                "count": partners.count(),
            },
            {
                "key": "employees",
                "label": EMAIL_AUDIENCE_GROUPS["employees"],
                "count": employees.count(),
            },
            {"key": "manual", "label": EMAIL_AUDIENCE_GROUPS["manual"], "count": 0},
        ],
        "filters": {"branch_id": branch_id},
        "data_notes": [
            "Audience counts use records with valid-looking email addresses.",
            "Consent and unsubscribe enforcement are not modeled in this slice.",
        ],
    }


@marketing_router.post("/marketing/email/preview", response={200: dict, 400: dict})
@require_permission("marketing_campaigns", "list")
def preview_email_campaign(request, payload: EmailMarketingAudienceRequest):
    try:
        recipients, skipped_count = _resolve_email_recipients(request, payload)
        return 200, {
            "count": len(recipients),
            "skipped_count": skipped_count,
            "audience_groups": payload.audience_groups,
            "filters": payload.filters or {},
            "recipients": recipients,
        }
    except ValidationError as e:
        return 400, {"detail": str(e)}


@marketing_router.post("/marketing/email/send", response={200: dict, 400: dict})
@require_permission("marketing_campaigns", "create")
def send_email_campaign(request, payload: EmailMarketingSendRequest):
    subject = (payload.subject or "").strip()
    body = (payload.body or "").strip()
    if not subject or not body:
        return 400, {"detail": "Subject and body are required."}

    try:
        recipients, skipped_count = _resolve_email_recipients(request, payload)
    except ValidationError as e:
        return 400, {"detail": str(e)}
    if not recipients:
        return 400, {"detail": "No valid recipients resolved for this email campaign."}

    html_body = _email_body_to_html(body)
    with transaction.atomic():
        campaign = EmailMarketingCampaign.objects.create(
            subject=subject,
            body=body,
            audience_groups=payload.audience_groups,
            filters=payload.filters or {},
            status="draft",
            recipient_count=len(recipients),
            created_by=request.user,
        )

        sent_count = 0
        failed_count = 0
        for recipient in recipients:
            status = "failed"
            provider_status_code = None
            error = ""
            try:
                response = send_marketing_email(
                    recipient=recipient["email"],
                    name=recipient["name"],
                    subject=subject,
                    html_content=html_body,
                )
                provider_status_code = getattr(response, "status_code", None)
                if getattr(response, "ok", False):
                    status = "sent"
                    sent_count += 1
                else:
                    failed_count += 1
                    error = (
                        getattr(response, "text", "")
                        or "Email provider rejected the message."
                    )
            except Exception as exc:
                failed_count += 1
                error = str(exc)

            EmailMarketingRecipient.objects.create(
                campaign=campaign,
                email=recipient["email"],
                name=recipient["name"],
                source_group=recipient["source_group"],
                source_object_type=recipient["source_object_type"],
                source_object_id=recipient["source_object_id"],
                status=status,
                provider_status_code=provider_status_code,
                error=error,
            )

        campaign.sent_count = sent_count
        campaign.failed_count = failed_count
        campaign.status = (
            "sent"
            if sent_count and not failed_count
            else "failed" if failed_count else "draft"
        )
        campaign.sent_at = timezone.now()
        campaign.save(
            update_fields=[
                "sent_count",
                "failed_count",
                "status",
                "sent_at",
                "updated_at",
            ]
        )

    return 200, {
        "campaign": _email_campaign_row(campaign, include_recipients=True),
        "skipped_count": skipped_count,
    }


@marketing_router.get("/marketing/email/campaigns")
@require_permission("marketing_campaigns", "list")
def list_email_campaigns(
    request, status: str = None, search: str = None, limit: int = 50
):
    campaigns = EmailMarketingCampaign.objects.select_related("created_by").all()
    if status:
        campaigns = campaigns.filter(status=status)
    if search:
        campaigns = campaigns.filter(
            Q(subject__icontains=search) | Q(body__icontains=search)
        )
    limit = min(max(limit, 1), 200)
    return {
        "count": campaigns.count(),
        "campaigns": [
            _email_campaign_row(campaign)
            for campaign in campaigns.order_by("-created_at")[:limit]
        ],
    }


@marketing_router.get(
    "/marketing/email/campaigns/{campaign_id}", response={200: dict, 404: dict}
)
@require_permission("marketing_campaigns", "list")
def get_email_campaign(request, campaign_id: int):
    campaign = (
        EmailMarketingCampaign.objects.prefetch_related("recipients")
        .filter(id=campaign_id)
        .first()
    )
    if not campaign:
        return 404, {"detail": "Email campaign not found."}
    return 200, _email_campaign_row(campaign, include_recipients=True)


def _partner_token_hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _partner_portal_token(request):
    token = request.GET.get("token") or request.headers.get("X-Partner-Token", "")
    auth_header = request.headers.get("Authorization", "")
    if not token and auth_header.lower().startswith("bearer "):
        token = auth_header[7:]
    return (token or "").strip()


def _resolve_partner_invitation(request):
    token = _partner_portal_token(request)
    if not token:
        return None, {"detail": "Partner portal token is required."}

    invitation = (
        PartnerInvitation.objects.select_related("partner")
        .filter(token_hash=_partner_token_hash(token), status__in=["sent", "accepted"])
        .first()
    )
    if not invitation:
        return None, {"detail": "Invalid partner portal token."}
    if invitation.is_expired:
        invitation.status = "expired"
        invitation.save(update_fields=["status", "updated_at"])
        return None, {"detail": "Partner portal token has expired."}
    if invitation.partner.status in ["inactive", "suspended"]:
        return None, {"detail": "Partner is not currently allowed to use the portal."}
    if invitation.status == "sent":
        invitation.status = "accepted"
        invitation.accepted_at = timezone.now()
        invitation.partner.status = "active"
        invitation.partner.save(update_fields=["status", "updated_at"])
        invitation.save(update_fields=["status", "accepted_at", "updated_at"])
    return invitation, None


def _partner_invite_url(base_url, token):
    base_url = (base_url or "").strip()
    if not base_url:
        domain = getattr(settings, "DOMAIN", "")
        base_url = (
            domain
            if domain.startswith(("http://", "https://"))
            else f"https://{domain}"
        )
        base_url = base_url.rstrip("/") + "/partner-portal"
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}token={token}"


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


def _partner_task_row(task, include_reports=False):
    row = {
        "id": task.id,
        "partner_id": task.partner_id,
        "partner_name": task.partner.name,
        "campaign_id": task.campaign_id,
        "campaign_name": task.campaign.name if task.campaign else "",
        "partner_type": task.partner_type,
        "partner_type_display": task.get_partner_type_display(),
        "title": task.title,
        "objective": task.objective,
        "due_date": task.due_date,
        "fee": task.fee,
        "proof_requirement": task.proof_requirement,
        "tracking_url": task.tracking_url,
        "status": task.status,
        "status_display": task.get_status_display(),
        "report_count": task.reports.count(),
        "created_at": task.created_at,
        "updated_at": task.updated_at,
    }
    if include_reports:
        row["reports"] = [
            _partner_report_row(report)
            for report in task.reports.select_related("reviewed_by").all()
        ]
    return row


def _partner_report_row(report):
    return {
        "id": report.id,
        "task_id": report.task_id,
        "task_title": report.task.title,
        "partner_id": report.partner_id,
        "partner_name": report.partner.name,
        "reach": report.reach,
        "lead_count": report.lead_count,
        "proof_url": report.proof_url,
        "note": report.note,
        "status": report.status,
        "status_display": report.get_status_display(),
        "reviewed_by_id": report.reviewed_by_id,
        "reviewed_by_name": _user_name(report.reviewed_by),
        "reviewed_at": report.reviewed_at,
        "review_note": report.review_note,
        "created_at": report.created_at,
        "updated_at": report.updated_at,
    }


def _partner_commission_row(commission):
    return {
        "id": commission.id,
        "partner_id": commission.partner_id,
        "partner_name": commission.partner.name,
        "lead_id": commission.lead_id,
        "lead_name": commission.lead.full_name if commission.lead else "",
        "amount_basis": commission.amount_basis,
        "commission_rate": commission.commission_rate,
        "commission_due": commission.commission_due,
        "status": commission.status,
        "status_display": commission.get_status_display(),
        "approved_by_id": commission.approved_by_id,
        "approved_by_name": _user_name(commission.approved_by),
        "approved_at": commission.approved_at,
        "paid_at": commission.paid_at,
        "payment_reference": commission.payment_reference,
        "note": commission.note,
        "created_at": commission.created_at,
        "updated_at": commission.updated_at,
    }


def _create_partner_referral_lead(payload_data, partner, actor=None):
    payload_data["tags"] = payload_data.get("tags") or ["partner_referral"]
    payload_data["source"] = "referral"
    payload_data["referral_partner"] = partner
    lead = Lead(created_by=actor, **payload_data)
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
    record_initial_funnel_event(lead, actor=actor)
    return lead


@marketing_router.get("/marketing/partners/dashboard")
@require_permission("marketing_campaigns", "list")
def get_partner_operations_dashboard(
    request,
    period_start: date = None,
    period_end: date = None,
    branch_id: int = None,
    campaign_id: int = None,
):
    start, end = _period_bounds(period_start, period_end)
    leads = _lead_queryset(request).filter(
        referral_partner__isnull=False,
        created_at__date__gte=start,
        created_at__date__lte=end,
    )
    if branch_id:
        leads = leads.filter(branch_id=branch_id)
    if campaign_id:
        leads = leads.filter(campaign_id=campaign_id)

    partners = Partner.objects.prefetch_related(
        "marketing_tasks", "marketing_reports", "marketing_commissions"
    ).all()
    referred_partner_ids = list(
        leads.values_list("referral_partner_id", flat=True).distinct()
    )
    commissions = PartnerCommission.objects.select_related("partner", "lead").filter(
        partner_id__in=referred_partner_ids or partners.values("id"),
        created_at__date__gte=start,
        created_at__date__lte=end,
    )
    tasks = PartnerTask.objects.select_related("partner", "campaign").filter(
        partner_id__in=partners.values("id")
    )
    reports = PartnerReport.objects.select_related("task", "partner").filter(
        partner_id__in=partners.values("id"),
        created_at__date__gte=start,
        created_at__date__lte=end,
    )
    won_leads = leads.filter(status="won")

    return {
        "filters": {
            "period_start": start,
            "period_end": end,
            "branch_id": branch_id,
            "campaign_id": campaign_id,
        },
        "kpis": {
            "active_partners": partners.filter(status="active").count(),
            "referred_leads": leads.count(),
            "closed_referred_leads": won_leads.count(),
            "closed_referred_revenue": _decimal_sum(won_leads, "estimated_value"),
            "commission_due": _decimal_sum(
                commissions.filter(status__in=["pending_verification", "approved"]),
                "commission_due",
            ),
            "commission_paid": _decimal_sum(
                commissions.filter(status="paid"), "commission_due"
            ),
            "assigned_tasks": tasks.exclude(
                status__in=["approved", "cancelled"]
            ).count(),
            "pending_reports": reports.filter(status="submitted").count(),
            "pending_payment_approvals": commissions.filter(
                status="pending_verification"
            ).count(),
        },
        "top_partners": sorted(
            [_partner_row(partner, leads=leads) for partner in partners],
            key=lambda row: (row["closed_revenue"], row["referred_leads"]),
            reverse=True,
        )[:10],
        "data_notes": [
            "Partners reuse user.Partner records; this panel adds performance operations only.",
            "No KYC workflow is implemented in this slice.",
            "Lead attribution comes from Lead.referral_partner with source='referral'.",
        ],
    }


@marketing_router.get("/marketing/partners/directory")
@require_permission("marketing_campaigns", "list")
def list_partner_operations_directory(
    request,
    status: str = None,
    category: str = None,
    search: str = None,
    branch_id: int = None,
    campaign_id: int = None,
    limit: int = 50,
):
    partners = Partner.objects.prefetch_related(
        "marketing_tasks", "marketing_reports", "marketing_commissions"
    ).all()
    if status:
        partners = partners.filter(status=status)
    if category:
        partners = partners.filter(category=category)
    if search:
        partners = partners.filter(
            Q(name__icontains=search)
            | Q(email__icontains=search)
            | Q(phone__icontains=search)
        )
    leads = _lead_queryset(request).filter(referral_partner__isnull=False)
    if branch_id:
        leads = leads.filter(branch_id=branch_id)
    if campaign_id:
        leads = leads.filter(campaign_id=campaign_id)
    return {
        "filters": {
            "status": status,
            "category": category,
            "search": search,
            "branch_id": branch_id,
            "campaign_id": campaign_id,
        },
        "count": partners.count(),
        "partners": [
            _partner_row(partner, leads=leads)
            for partner in partners.order_by("name", "id")[: max(min(limit, 100), 1)]
        ],
    }


@marketing_router.post(
    "/marketing/partners/invitations", response={201: dict, 400: dict}
)
@require_permission("marketing_campaigns", "create")
def invite_marketing_partner(request, payload: PartnerInvitationIn):
    valid_email = _valid_email_or_none(payload.email)
    if not valid_email:
        return 400, {"detail": "A valid partner email is required."}

    try:
        with transaction.atomic():
            if payload.partner_id:
                partner = Partner.objects.get(id=payload.partner_id)
                partner.email = valid_email
                if payload.name:
                    partner.name = payload.name
                if payload.phone is not None:
                    partner.phone = payload.phone
                if payload.category:
                    partner.category = payload.category
                if payload.status:
                    partner.status = payload.status
                partner.full_clean()
                partner.save()
            else:
                partner = Partner(
                    name=payload.name or valid_email.split("@")[0],
                    email=valid_email,
                    phone=payload.phone or "",
                    category=payload.category or "real_estate",
                    status=payload.status or "pending",
                )
                partner.full_clean()
                partner.save()

            raw_token = secrets.token_urlsafe(32)
            invite_url = _partner_invite_url(payload.invite_url_base, raw_token)
            invitation = PartnerInvitation(
                partner=partner,
                email=valid_email,
                token_hash=_partner_token_hash(raw_token),
                invited_by=request.user,
                expires_at=timezone.now() + timedelta(days=14),
                last_sent_at=timezone.now(),
                invite_url=invite_url,
            )
            invitation.full_clean()
            invitation.save()

        def send_invite():
            try:
                send_marketing_email(
                    recipient=valid_email,
                    name=partner.name,
                    subject="Bomach partner portal invitation",
                    html_content=_email_body_to_html(
                        f"Hello {partner.name},\n\nUse this secure link to access your Bomach partner work portal:\n{invite_url}\n\nThis link expires in 14 days."
                    ),
                )
            except Exception:
                logger.exception(
                    "Failed to send partner portal invitation to %s", valid_email
                )

        transaction.on_commit(send_invite)
        return 201, {
            "partner": _partner_row(partner),
            "invitation": {
                "id": invitation.id,
                "email": invitation.email,
                "status": invitation.status,
                "expires_at": invitation.expires_at,
                "invite_url": invitation.invite_url,
                "portal_token": raw_token,
            },
        }
    except Partner.DoesNotExist:
        return 400, {"detail": "Partner not found."}
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@marketing_router.get("/marketing/partners/tasks")
@require_permission("marketing_campaigns", "list")
def list_partner_tasks(
    request,
    partner_id: int = None,
    status: str = None,
    partner_type: str = None,
    campaign_id: int = None,
    limit: int = 50,
):
    tasks = (
        PartnerTask.objects.select_related("partner", "campaign")
        .prefetch_related("reports")
        .all()
    )
    if partner_id:
        tasks = tasks.filter(partner_id=partner_id)
    if status:
        tasks = tasks.filter(status=status)
    if partner_type:
        tasks = tasks.filter(partner_type=partner_type)
    if campaign_id:
        tasks = tasks.filter(campaign_id=campaign_id)
    return {
        "count": tasks.count(),
        "tasks": [
            _partner_task_row(task)
            for task in tasks.order_by("status", "due_date", "-created_at")[
                : max(min(limit, 100), 1)
            ]
        ],
    }


@marketing_router.post("/marketing/partners/tasks", response={201: dict, 400: dict})
@require_permission("marketing_campaigns", "create")
def create_partner_task(request, payload: PartnerTaskIn):
    try:
        data = payload.dict()
        data["assigned_by"] = request.user
        task = PartnerTask(**data)
        task.full_clean()
        task.save()
        return 201, _partner_task_row(
            PartnerTask.objects.select_related("partner", "campaign").get(id=task.id)
        )
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@marketing_router.patch(
    "/marketing/partners/tasks/{task_id}", response={200: dict, 400: dict, 404: dict}
)
@require_permission("marketing_campaigns", "update")
def update_partner_task(request, task_id: int, payload: PartnerTaskUpdate):
    task = (
        PartnerTask.objects.select_related("partner", "campaign")
        .filter(id=task_id)
        .first()
    )
    if not task:
        return 404, {"detail": "Partner task not found."}
    try:
        for field, value in payload.dict(exclude_unset=True).items():
            setattr(task, field, value)
        task.full_clean()
        task.save()
        return 200, _partner_task_row(task)
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@marketing_router.get("/marketing/partners/reports")
@require_permission("marketing_campaigns", "list")
def list_partner_reports(
    request,
    partner_id: int = None,
    task_id: int = None,
    status: str = None,
    limit: int = 50,
):
    reports = PartnerReport.objects.select_related(
        "task", "partner", "reviewed_by"
    ).all()
    if partner_id:
        reports = reports.filter(partner_id=partner_id)
    if task_id:
        reports = reports.filter(task_id=task_id)
    if status:
        reports = reports.filter(status=status)
    return {
        "count": reports.count(),
        "reports": [
            _partner_report_row(report)
            for report in reports.order_by("-created_at")[: max(min(limit, 100), 1)]
        ],
    }


@marketing_router.patch(
    "/marketing/partners/reports/{report_id}/review",
    response={200: dict, 400: dict, 404: dict},
)
@require_permission("marketing_campaigns", "update")
def review_partner_report(request, report_id: int, payload: PartnerReportReviewIn):
    report = (
        PartnerReport.objects.select_related("task", "partner")
        .filter(id=report_id)
        .first()
    )
    if not report:
        return 404, {"detail": "Partner report not found."}
    if payload.status not in ["approved", "rejected"]:
        return 400, {"detail": "Report review status must be approved or rejected."}
    report.status = payload.status
    report.review_note = payload.review_note or ""
    report.reviewed_by = request.user
    report.reviewed_at = timezone.now()
    report.save(
        update_fields=[
            "status",
            "review_note",
            "reviewed_by",
            "reviewed_at",
            "updated_at",
        ]
    )
    report.task.status = "approved" if payload.status == "approved" else "in_progress"
    report.task.save(update_fields=["status", "updated_at"])
    return 200, _partner_report_row(report)


@marketing_router.get("/marketing/partners/commissions")
@require_permission("marketing_campaigns", "list")
def list_partner_commissions(
    request, partner_id: int = None, status: str = None, limit: int = 50
):
    commissions = PartnerCommission.objects.select_related(
        "partner", "lead", "approved_by"
    ).all()
    if partner_id:
        commissions = commissions.filter(partner_id=partner_id)
    if status:
        commissions = commissions.filter(status=status)
    return {
        "count": commissions.count(),
        "commissions": [
            _partner_commission_row(commission)
            for commission in commissions.order_by("status", "-created_at")[
                : max(min(limit, 100), 1)
            ]
        ],
    }


@marketing_router.post(
    "/marketing/partners/commissions", response={201: dict, 400: dict}
)
@require_permission("marketing_campaigns", "create")
def create_partner_commission(request, payload: PartnerCommissionIn):
    try:
        data = payload.dict()
        commission = PartnerCommission(**data)
        if data.get("commission_due") is None:
            commission.calculate_due()
        commission.full_clean()
        commission.save()
        return 201, _partner_commission_row(
            PartnerCommission.objects.select_related(
                "partner", "lead", "approved_by"
            ).get(id=commission.id)
        )
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@marketing_router.patch(
    "/marketing/partners/commissions/{commission_id}/approve",
    response={200: dict, 400: dict, 404: dict},
)
@require_permission("marketing_campaigns", "update")
def approve_partner_commission(
    request, commission_id: int, payload: PartnerCommissionUpdate
):
    commission = (
        PartnerCommission.objects.select_related("partner", "lead", "approved_by")
        .filter(id=commission_id)
        .first()
    )
    if not commission:
        return 404, {"detail": "Partner commission not found."}
    if commission.status == "paid":
        return 400, {"detail": "Paid commissions cannot be re-approved."}
    commission.status = "approved"
    commission.approved_by = request.user
    commission.approved_at = timezone.now()
    if payload.note is not None:
        commission.note = payload.note
    commission.save(
        update_fields=["status", "approved_by", "approved_at", "note", "updated_at"]
    )
    return 200, _partner_commission_row(commission)


@marketing_router.patch(
    "/marketing/partners/commissions/{commission_id}/mark-paid",
    response={200: dict, 400: dict, 404: dict},
)
@require_permission("marketing_campaigns", "update")
def mark_partner_commission_paid(
    request, commission_id: int, payload: PartnerCommissionUpdate
):
    commission = (
        PartnerCommission.objects.select_related("partner", "lead", "approved_by")
        .filter(id=commission_id)
        .first()
    )
    if not commission:
        return 404, {"detail": "Partner commission not found."}
    if commission.status != "approved":
        return 400, {
            "detail": "Commission must be approved before it can be marked paid."
        }
    commission.status = "paid"
    commission.paid_at = timezone.now()
    if payload.payment_reference is not None:
        commission.payment_reference = payload.payment_reference
    if payload.note is not None:
        commission.note = payload.note
    commission.save(
        update_fields=["status", "paid_at", "payment_reference", "note", "updated_at"]
    )
    return 200, _partner_commission_row(commission)


@marketing_router.post(
    "/marketing/partners/referred-leads", response={201: dict, 400: dict}
)
@require_permission("marketing_campaigns", "create")
def create_internal_partner_referred_lead(request, payload: PartnerReferredLeadIn):
    if not payload.partner_id:
        return 400, {"detail": "partner_id is required."}
    try:
        partner = Partner.objects.get(id=payload.partner_id)
        payload_data = payload.dict(exclude={"partner_id"})
        lead = _create_partner_referral_lead(payload_data, partner, actor=request.user)
        return 201, {
            "id": lead.id,
            "full_name": lead.full_name,
            "source": lead.source,
            "referral_partner_id": lead.referral_partner_id,
            "referral_partner_name": partner.name,
            "status": lead.status,
            "created_at": lead.created_at,
        }
    except Partner.DoesNotExist:
        return 400, {"detail": "Partner not found."}
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@marketing_router.get(
    "/marketing/partner-portal/session", auth=None, response={200: dict, 401: dict}
)
def get_partner_portal_session(request):
    invitation, error = _resolve_partner_invitation(request)
    if error:
        return 401, error
    partner = invitation.partner
    tasks = (
        PartnerTask.objects.select_related("partner", "campaign")
        .prefetch_related("reports")
        .filter(partner=partner)
    )
    return 200, {
        "partner": _partner_row(partner),
        "invitation": {
            "id": invitation.id,
            "email": invitation.email,
            "status": invitation.status,
            "expires_at": invitation.expires_at,
            "accepted_at": invitation.accepted_at,
        },
        "tasks": [
            _partner_task_row(task, include_reports=True)
            for task in tasks.order_by("status", "due_date", "-created_at")
        ],
        "rules": [
            "Every referred lead must be registered before inspection or negotiation.",
            "Commission is tracked only after Bomach verifies company receipt.",
            "Use approved price lists, claims and marketing materials.",
        ],
    }


@marketing_router.post(
    "/marketing/partner-portal/leads",
    auth=None,
    response={201: dict, 400: dict, 401: dict},
)
def create_partner_portal_lead(request, payload: PartnerReferredLeadIn):
    invitation, error = _resolve_partner_invitation(request)
    if error:
        return 401, error
    try:
        payload_data = payload.dict(exclude={"partner_id"})
        lead = _create_partner_referral_lead(
            payload_data, invitation.partner, actor=None
        )
        return 201, {
            "id": lead.id,
            "full_name": lead.full_name,
            "source": lead.source,
            "referral_partner_id": lead.referral_partner_id,
            "referral_partner_name": invitation.partner.name,
            "status": lead.status,
            "created_at": lead.created_at,
        }
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@marketing_router.post(
    "/marketing/partner-portal/reports",
    auth=None,
    response={201: dict, 400: dict, 401: dict, 404: dict},
)
def submit_partner_portal_report(request, payload: PartnerReportIn):
    invitation, error = _resolve_partner_invitation(request)
    if error:
        return 401, error
    task = (
        PartnerTask.objects.select_related("partner", "campaign")
        .filter(id=payload.task_id, partner=invitation.partner)
        .first()
    )
    if not task:
        return 404, {"detail": "Partner task not found for this portal session."}
    try:
        report = PartnerReport(
            task=task,
            partner=invitation.partner,
            reach=payload.reach,
            lead_count=payload.lead_count,
            proof_url=payload.proof_url or "",
            note=payload.note or "",
        )
        report.full_clean()
        report.save()
        task.status = "report_submitted"
        task.save(update_fields=["status", "updated_at"])
        return 201, _partner_report_row(report)
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@marketing_router.get("/marketing/traditional-media/dashboard")
@require_permission("marketing_campaigns", "list")
def get_traditional_media_dashboard(
    request,
    placement_type: str = None,
    ownership: str = None,
    status: str = None,
    expiry_filter: str = None,
    campaign_id: int = None,
    branch_id: int = None,
    division: str = None,
    date_from: date = None,
    date_to: date = None,
    search: str = None,
):
    placements = _filter_traditional_media_placements(
        _traditional_media_queryset(request),
        placement_type=placement_type,
        ownership=ownership,
        status=status,
        expiry_filter=expiry_filter,
        campaign_id=campaign_id,
        branch_id=branch_id,
        division=division,
        date_from=date_from,
        date_to=date_to,
        search=search,
    )
    return {
        "filters": {
            "placement_type": placement_type,
            "ownership": ownership,
            "status": status,
            "expiry_filter": expiry_filter,
            "campaign_id": campaign_id,
            "branch_id": branch_id,
            "division": division,
            "date_from": date_from,
            "date_to": date_to,
            "search": search,
        },
        **_traditional_media_dashboard(placements),
    }


@marketing_router.get("/marketing/traditional-media/placements")
@require_permission("marketing_campaigns", "list")
def list_traditional_media_placements(
    request,
    placement_type: str = None,
    ownership: str = None,
    status: str = None,
    expiry_filter: str = None,
    campaign_id: int = None,
    branch_id: int = None,
    division: str = None,
    date_from: date = None,
    date_to: date = None,
    search: str = None,
    limit: int = 50,
):
    placements = _filter_traditional_media_placements(
        _traditional_media_queryset(request),
        placement_type=placement_type,
        ownership=ownership,
        status=status,
        expiry_filter=expiry_filter,
        campaign_id=campaign_id,
        branch_id=branch_id,
        division=division,
        date_from=date_from,
        date_to=date_to,
        search=search,
    )
    limit = max(min(limit, 200), 1)
    return {
        "filters": {
            "placement_type": placement_type,
            "ownership": ownership,
            "status": status,
            "expiry_filter": expiry_filter,
            "campaign_id": campaign_id,
            "branch_id": branch_id,
            "division": division,
            "date_from": date_from,
            "date_to": date_to,
            "search": search,
            "limit": limit,
        },
        "dashboard": _traditional_media_dashboard(placements)["kpis"],
        "placements": [
            _serialize_traditional_media_placement(placement)
            for placement in placements[:limit]
        ],
        "metadata": _traditional_media_metadata(),
        "data_notes": [
            "Expiry state is derived from end_date.",
            "There is no renew action; update expiry dates through PATCH /marketing/traditional-media/placements/{id}.",
        ],
    }


@marketing_router.get("/marketing/traditional-media/placements/export")
@require_permission("marketing_campaigns", "list")
def export_traditional_media_placements(
    request,
    placement_type: str = None,
    ownership: str = None,
    status: str = None,
    expiry_filter: str = None,
    campaign_id: int = None,
    branch_id: int = None,
    division: str = None,
    date_from: date = None,
    date_to: date = None,
    search: str = None,
):
    placements = _filter_traditional_media_placements(
        _traditional_media_queryset(request),
        placement_type=placement_type,
        ownership=ownership,
        status=status,
        expiry_filter=expiry_filter,
        campaign_id=campaign_id,
        branch_id=branch_id,
        division=division,
        date_from=date_from,
        date_to=date_to,
        search=search,
    )
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "ID",
            "Type",
            "Placement",
            "Vendor",
            "Location",
            "Ownership",
            "Amount",
            "Start",
            "Expiry",
            "Days",
            "Expiry State",
            "Status",
            "Proof",
        ]
    )
    for placement in placements[:500]:
        row = _serialize_traditional_media_placement(placement)
        writer.writerow(
            [
                row["placement_code"],
                row["placement_type_display"],
                row["name"],
                row["vendor"],
                row["location"],
                row["ownership_display"],
                row["amount_paid"],
                row["start_date"],
                row["end_date"],
                row["days_remaining"],
                row["expiry_state"],
                row["status"],
                row["proof_url"],
            ]
        )
    response = HttpResponse(buffer.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = (
        'attachment; filename="traditional-media-placements.csv"'
    )
    return response


@marketing_router.post(
    "/marketing/traditional-media/placements", response={201: dict, 400: dict}
)
@require_permission("marketing_campaigns", "create")
def create_traditional_media_placement(request, payload: TraditionalMediaPlacementIn):
    try:
        data, relations = _resolve_traditional_media_relations(payload.dict())
        placement = TraditionalMediaPlacement.objects.create(
            created_by=request.user,
            **relations,
            **data,
        )
        return 201, _serialize_traditional_media_placement(placement, detail=True)
    except ValidationError as exc:
        return 400, {"detail": _validation_detail(exc)}
    except Exception as exc:
        return 400, {"detail": str(exc)}


@marketing_router.get(
    "/marketing/traditional-media/placements/{placement_id}",
    response={200: dict, 404: dict},
)
@require_permission("marketing_campaigns", "view")
def get_traditional_media_placement(request, placement_id: int):
    placement = _traditional_media_queryset(request).filter(id=placement_id).first()
    if not placement:
        return 404, {"detail": "Traditional media placement not found"}
    return 200, _serialize_traditional_media_placement(placement, detail=True)


@marketing_router.patch(
    "/marketing/traditional-media/placements/{placement_id}",
    response={200: dict, 400: dict, 404: dict},
)
@require_permission("marketing_campaigns", "update")
def update_traditional_media_placement(
    request, placement_id: int, payload: TraditionalMediaPlacementUpdate
):
    try:
        placement = _traditional_media_queryset(request).filter(id=placement_id).first()
        if not placement:
            return 404, {"detail": "Traditional media placement not found"}
        data, relations = _resolve_traditional_media_relations(
            payload.dict(exclude_unset=True)
        )
        for field, value in {**relations, **data}.items():
            setattr(placement, field, value)
        placement.full_clean()
        placement.save()
        placement.refresh_from_db()
        return 200, _serialize_traditional_media_placement(placement, detail=True)
    except ValidationError as exc:
        return 400, {"detail": _validation_detail(exc)}
    except Exception as exc:
        return 400, {"detail": str(exc)}


@marketing_router.get("/marketing/meetings")
@require_permission("marketing_campaigns", "list")
def list_marketing_meetings(
    request,
    status: str = None,
    campaign_id: int = None,
    meeting_type: str = None,
    date_from: date = None,
    date_to: date = None,
    search: str = None,
    my_meetings: bool = None,
    limit: int = 50,
):
    contexts = _filter_marketing_meetings(
        _marketing_meeting_queryset(),
        status=status,
        campaign_id=campaign_id,
        meeting_type=meeting_type,
        date_from=date_from,
        date_to=date_to,
        search=search,
        my_meetings=my_meetings,
        request=request,
    )
    limit = max(min(limit, 100), 1)
    today = timezone.localdate()
    actions = MarketingMeetingAction.objects.select_related(
        "owner",
        "owner__user",
        "meeting_context",
        "meeting_context__meeting",
        "meeting_context__campaign",
    ).filter(meeting_context__in=contexts)
    decisions = CampaignDecision.objects.select_related(
        "campaign",
        "source_meeting_context",
        "source_meeting_context__meeting",
    ).filter(source_meeting_context__in=contexts)

    return {
        "filters": {
            "status": status,
            "campaign_id": campaign_id,
            "meeting_type": meeting_type,
            "date_from": date_from,
            "date_to": date_to,
            "search": search,
            "my_meetings": my_meetings,
        },
        "kpis": {
            "total_meetings": contexts.count(),
            "upcoming_meetings": contexts.filter(
                meeting__status="scheduled", meeting__meeting_date__gte=today
            ).count(),
            "completed_meetings": contexts.filter(meeting__status="completed").count(),
            "open_action_items": actions.exclude(
                status__in=["done", "cancelled"]
            ).count(),
            "decisions_recorded": decisions.count(),
        },
        "meetings": [
            _serialize_marketing_meeting_context(context)
            for context in contexts[:limit]
        ],
        "open_actions": [
            _serialize_marketing_meeting_action(action)
            for action in actions.exclude(status__in=["done", "cancelled"]).order_by(
                "due_date", "-created_at"
            )[:limit]
        ],
        "decision_register": [
            _serialize_marketing_meeting_decision(decision)
            for decision in decisions[:limit]
        ],
        "meeting_types": [
            {"value": value, "label": label}
            for value, label in MarketingMeetingContext.MEETING_TYPE_CHOICES
        ],
        "status_choices": [
            {"value": value, "label": label} for value, label in Meeting.STATUS_CHOICES
        ],
    }


@marketing_router.get("/marketing/meetings/export")
@require_permission("marketing_campaigns", "list")
def export_marketing_meetings(
    request,
    status: str = None,
    campaign_id: int = None,
    meeting_type: str = None,
    date_from: date = None,
    date_to: date = None,
    search: str = None,
    my_meetings: bool = None,
):
    contexts = _filter_marketing_meetings(
        _marketing_meeting_queryset(),
        status=status,
        campaign_id=campaign_id,
        meeting_type=meeting_type,
        date_from=date_from,
        date_to=date_to,
        search=search,
        my_meetings=my_meetings,
        request=request,
    )
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "Meeting",
            "Type",
            "Campaign",
            "Date",
            "Time",
            "Duration",
            "Status",
            "Location",
            "Facilitator",
            "Recorder",
            "Attendees",
            "Open Actions",
            "Decisions",
        ]
    )
    for context in contexts[:500]:
        meeting = context.meeting
        writer.writerow(
            [
                meeting.title,
                context.meeting_type,
                context.campaign.name if context.campaign else "",
                meeting.meeting_date,
                meeting.meeting_time.strftime("%H:%M"),
                meeting.duration_minutes,
                meeting.status,
                meeting.location,
                context.facilitator,
                context.recorder,
                meeting.attendees.count(),
                context.actions.exclude(status__in=["done", "cancelled"]).count(),
                context.campaign_decisions.count(),
            ]
        )
    response = HttpResponse(buffer.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="marketing-meetings.csv"'
    return response


@marketing_router.post("/marketing/meetings", response={201: dict, 400: dict})
@require_permission("meetings", "create")
def create_marketing_meeting(request, payload: MarketingMeetingIn):
    try:
        base_data, context_data, attendee_ids, campaign_id = _meeting_payload_data(
            payload
        )
        campaign = None
        if campaign_id:
            campaign = MarketingCampaign.objects.filter(id=campaign_id).first()
            if not campaign:
                return 400, {"detail": "Campaign not found"}
        with transaction.atomic():
            meeting = Meeting.objects.create(
                organizer=request.user,
                **base_data,
            )
            _set_meeting_attendees(meeting, attendee_ids or [])
            context = MarketingMeetingContext.objects.create(
                meeting=meeting,
                campaign=campaign,
                **context_data,
            )
        return 201, _serialize_marketing_meeting_context(context, include_detail=True)
    except ValidationError as exc:
        return 400, {"detail": _validation_detail(exc)}
    except Exception as exc:
        return 400, {"detail": str(exc)}


@marketing_router.patch(
    "/marketing/meetings/actions/{action_id}",
    response={200: dict, 400: dict, 404: dict},
)
@require_permission("meetings", "update")
def update_marketing_meeting_action(
    request, action_id: int, payload: MarketingMeetingActionUpdate
):
    try:
        action = (
            MarketingMeetingAction.objects.select_related(
                "owner",
                "owner__user",
                "meeting_context",
                "meeting_context__meeting",
                "meeting_context__campaign",
            )
            .filter(id=action_id)
            .first()
        )
        if not action:
            return 404, {"detail": "Marketing meeting action not found"}
        data = payload.dict(exclude_unset=True)
        owner_id = data.pop("owner_id", None)
        if owner_id is not None:
            data["owner"] = Employee.objects.filter(id=owner_id).first()
        if data.get("status") == "done" and action.status != "done":
            data["completed_at"] = timezone.now()
        elif data.get("status") and data.get("status") != "done":
            data["completed_at"] = None
        for field, value in data.items():
            setattr(action, field, value)
        action.full_clean()
        action.save()
        return 200, _serialize_marketing_meeting_action(action)
    except ValidationError as exc:
        return 400, {"detail": _validation_detail(exc)}
    except Exception as exc:
        return 400, {"detail": str(exc)}


@marketing_router.get(
    "/marketing/meetings/{meeting_id}", response={200: dict, 404: dict}
)
@require_permission("marketing_campaigns", "view")
def get_marketing_meeting(request, meeting_id: int):
    context = (
        MarketingMeetingContext.objects.select_related(
            "meeting",
            "meeting__organizer",
            "campaign",
        )
        .prefetch_related("meeting__attendees", "actions", "campaign_decisions")
        .filter(meeting_id=meeting_id)
        .first()
    )
    if not context:
        return 404, {"detail": "Marketing meeting not found"}
    return 200, _serialize_marketing_meeting_context(context, include_detail=True)


@marketing_router.patch(
    "/marketing/meetings/{meeting_id}", response={200: dict, 400: dict, 404: dict}
)
@require_permission("meetings", "update")
def update_marketing_meeting(request, meeting_id: int, payload: MarketingMeetingUpdate):
    try:
        context = (
            MarketingMeetingContext.objects.select_related("meeting", "campaign")
            .filter(meeting_id=meeting_id)
            .first()
        )
        if not context:
            return 404, {"detail": "Marketing meeting not found"}
        base_data, context_data, attendee_ids, campaign_id = _meeting_payload_data(
            payload, exclude_unset=True
        )
        if campaign_id is not None:
            context.campaign = (
                MarketingCampaign.objects.filter(id=campaign_id).first()
                if campaign_id
                else None
            )
            if campaign_id and not context.campaign:
                return 400, {"detail": "Campaign not found"}
        with transaction.atomic():
            for field, value in base_data.items():
                setattr(context.meeting, field, value)
            context.meeting.full_clean()
            context.meeting.save()
            _set_meeting_attendees(context.meeting, attendee_ids)
            for field, value in context_data.items():
                setattr(context, field, value)
            context.full_clean()
            context.save()
        context = (
            MarketingMeetingContext.objects.select_related(
                "meeting",
                "meeting__organizer",
                "campaign",
            )
            .prefetch_related("meeting__attendees", "actions", "campaign_decisions")
            .get(id=context.id)
        )
        return 200, _serialize_marketing_meeting_context(context, include_detail=True)
    except ValidationError as exc:
        return 400, {"detail": _validation_detail(exc)}
    except Exception as exc:
        return 400, {"detail": str(exc)}


@marketing_router.post(
    "/marketing/meetings/{meeting_id}/actions",
    response={201: dict, 400: dict, 404: dict},
)
@require_permission("meetings", "update")
def create_marketing_meeting_action(
    request, meeting_id: int, payload: MarketingMeetingActionIn
):
    try:
        context = (
            MarketingMeetingContext.objects.select_related("meeting", "campaign")
            .filter(meeting_id=meeting_id)
            .first()
        )
        if not context:
            return 404, {"detail": "Marketing meeting not found"}
        data = payload.dict()
        owner_id = data.pop("owner_id", None)
        action = MarketingMeetingAction.objects.create(
            meeting_context=context,
            owner=Employee.objects.filter(id=owner_id).first() if owner_id else None,
            created_by=request.user,
            **data,
        )
        action = MarketingMeetingAction.objects.select_related(
            "owner",
            "owner__user",
            "meeting_context",
            "meeting_context__meeting",
            "meeting_context__campaign",
        ).get(id=action.id)
        return 201, _serialize_marketing_meeting_action(action)
    except ValidationError as exc:
        return 400, {"detail": _validation_detail(exc)}
    except Exception as exc:
        return 400, {"detail": str(exc)}


@marketing_router.post(
    "/marketing/meetings/{meeting_id}/decisions",
    response={201: dict, 400: dict, 404: dict},
)
@require_permission("marketing_campaigns", "update")
def create_marketing_meeting_decision(
    request, meeting_id: int, payload: MarketingMeetingDecisionIn
):
    try:
        context = (
            MarketingMeetingContext.objects.select_related("meeting", "campaign")
            .filter(meeting_id=meeting_id)
            .first()
        )
        if not context:
            return 404, {"detail": "Marketing meeting not found"}
        data = payload.dict()
        campaign_id = data.pop("campaign_id", None)
        campaign = context.campaign
        if campaign_id:
            campaign = MarketingCampaign.objects.filter(id=campaign_id).first()
            if not campaign:
                return 400, {"detail": "Campaign not found"}
        if not campaign:
            return 400, {
                "detail": "A campaign is required to record a campaign decision from a marketing meeting."
            }
        data["decision_date"] = data["decision_date"] or timezone.localdate()
        decision = CampaignDecision.objects.create(
            campaign=campaign,
            source_meeting_context=context,
            created_by=request.user,
            **data,
        )
        decision = CampaignDecision.objects.select_related(
            "campaign",
            "source_meeting_context",
            "source_meeting_context__meeting",
        ).get(id=decision.id)
        return 201, _serialize_marketing_meeting_decision(decision)
    except ValidationError as exc:
        return 400, {"detail": _validation_detail(exc)}
    except Exception as exc:
        return 400, {"detail": str(exc)}


@marketing_router.get("/marketing/analytics")
@require_permission("marketing_dashboard", "view")
def get_marketing_analytics(
    request,
    period_start: date = None,
    period_end: date = None,
    branch_id: int = None,
    division: str = None,
    campaign_id: int = None,
):
    start, end = _period_bounds(period_start, period_end)
    leads = _period_leads(request, start, end, branch_id, division, campaign_id)
    calendar_items = _period_calendar_items(
        request, start, end, branch_id, division, campaign_id
    )
    target_rows = _target_rows(request, start, end, branch_id)
    revenue_targets = _revenue_target_totals(target_rows)

    campaigns = MarketingCampaign.objects.filter(
        Q(start_date__isnull=True) | Q(start_date__lte=end),
        Q(end_date__isnull=True) | Q(end_date__gte=start),
    )
    if campaign_id:
        campaigns = campaigns.filter(id=campaign_id)
    if branch_id or division:
        linked_campaign_ids = set(
            leads.exclude(campaign_id=None).values_list("campaign_id", flat=True)
        ) | set(
            calendar_items.exclude(campaign_id=None).values_list(
                "campaign_id", flat=True
            )
        )
        campaigns = campaigns.filter(id__in=linked_campaign_ids)

    total_leads = leads.count()
    contacted_count = leads.filter(
        Q(first_response_at__isnull=False)
        | Q(first_contact_at__isnull=False)
        | ~Q(status="new")
    ).count()
    won_leads = leads.filter(status="won")
    won_count = won_leads.count()
    revenue_closed = _decimal_sum(won_leads, "estimated_value")
    avg_deal_value = (
        (revenue_closed / Decimal(won_count)).quantize(Decimal("0.01"))
        if won_count
        else Decimal("0.00")
    )
    sla_overdue = leads.filter(
        Q(sla_status="breached")
        | Q(
            first_response_at__isnull=True,
            first_contact_at__isnull=True,
            first_response_due_at__lt=timezone.now(),
        )
    ).count()

    planned_content = calendar_items.count()
    published_content = calendar_items.filter(status="published").count()
    platform_rows = [
        {
            "platform": value,
            "label": label,
            "planned": calendar_items.filter(platform=value).count(),
            "published": calendar_items.filter(
                platform=value, status="published"
            ).count(),
        }
        for value, label in ContentCalendarItem.PLATFORM_CHOICES
        if calendar_items.filter(platform=value).exists()
    ]
    top_platform = (
        max(platform_rows, key=lambda row: row["published"]) if platform_rows else None
    )

    total_spend = _decimal_sum(campaigns, "budget_spent")
    attributed_leads = leads.exclude(campaign_id=None)
    campaign_won_revenue = _decimal_sum(
        attributed_leads.filter(status="won"), "estimated_value"
    )

    revenue_by_division = []
    for value, label in Lead.DIVISION_CHOICES:
        division_leads = leads.filter(division=value)
        actual = _decimal_sum(division_leads.filter(status="won"), "estimated_value")
        deals = division_leads.filter(status="won").count()
        if not division_leads.exists() and not actual:
            continue
        revenue_by_division.append(
            {
                "division": value,
                "label": label,
                "target": None,
                "actual": actual,
                "gap": None,
                "achievement_pct": None,
                "deals_closed": deals,
            }
        )

    return {
        "period": {
            "start": start,
            "end": end,
            "filters": {
                "branch_id": branch_id,
                "division": division,
                "campaign_id": campaign_id,
            },
        },
        "overview": {
            "leads_this_period": total_leads,
            "revenue_closed": revenue_closed,
            "avg_deal_value": avg_deal_value,
            "won_deal_count": won_count,
            "client_score": None,
            "client_score_status": "unavailable",
            "leads_by_source": _lead_breakdown(leads, "source", Lead.SOURCE_CHOICES),
            "leads_by_division": _lead_breakdown(
                leads, "division", Lead.DIVISION_CHOICES
            ),
            "weekly_content_output": _weekly_content_output(calendar_items, start, end),
            "target_vs_actual": target_rows,
        },
        "lead_analytics": {
            "new_leads": leads.filter(status="new").count(),
            "contacted": contacted_count,
            "contacted_pct": _pct(contacted_count, total_leads),
            "sla_overdue": sla_overdue,
            "won": won_count,
            "source_breakdown": _lead_source_rows(
                leads, campaigns, campaign_id=campaign_id
            ),
        },
        "content_analytics": {
            "planned": planned_content,
            "published": published_content,
            "compliance_pct": _pct(published_content, planned_content),
            "top_platform": top_platform,
            "platforms": platform_rows,
            "by_format": _content_by_format(calendar_items),
        },
        "revenue": {
            "total_closed": revenue_closed,
            "target": revenue_targets["target"],
            "target_actual_from_reports": revenue_targets["actual"],
            "achievement_pct": _pct(revenue_closed, revenue_targets["target"]),
            "deals_closed": won_count,
            "by_division": revenue_by_division,
        },
        "team_scorecard": _team_scorecard(leads, start, end),
        "campaign_summary": {
            "total_campaigns": campaigns.count(),
            "active_campaigns": campaigns.filter(status="active").count(),
            "total_budget": _decimal_sum(campaigns, "budget_allocated"),
            "total_spend": total_spend,
            "attributed_leads": attributed_leads.count(),
            "won_revenue": campaign_won_revenue,
            "estimated_cpl": (
                (total_spend / Decimal(attributed_leads.count())).quantize(
                    Decimal("0.01")
                )
                if attributed_leads.count()
                else None
            ),
            "stored_impressions": campaigns.aggregate(total=Sum("impressions"))["total"]
            or 0,
        },
        "data_notes": [
            "Ad metrics are stored campaign fields, not live Meta, Google, TikTok, or analytics-platform integrations.",
            "Campaign attribution uses Lead.campaign_id and won lead estimated_value.",
            "Revenue is estimated from won leads unless a payment attribution layer is added.",
            "Revenue by division does not allocate target values because existing targets are role/employee-period records, not division target records.",
            "Client score is unavailable until customer rating data is connected to this panel.",
        ],
    }
