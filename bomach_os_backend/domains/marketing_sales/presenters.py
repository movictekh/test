"""API presentation helpers for the Marketing & Sales domain."""

import hashlib
import html
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.utils import timezone

from domains.marketing_sales.constants import (
    DIVISION_COLORS,
    FORECAST_SCENARIOS,
    MEDIA_ICONS,
    MEETING_BASE_FIELDS,
    MEETING_CONTEXT_FIELDS,
    TERMINAL_CALENDAR_STATUSES,
    TRADITIONAL_MEDIA_EXPIRY_WINDOW_DAYS,
)
from domains.marketing_sales.models.content import (
    ContentCalendarItem,
    MediaLibraryAsset,
)
from domains.marketing_sales.models.marketing import TraditionalMediaPlacement
from domains.marketing_sales.models.sales import Lead


def _sales_validation_detail(exc):
    if hasattr(exc, "message_dict"):
        return "; ".join(
            (
                f"{field}: {', '.join(messages)}"
                for field, messages in exc.message_dict.items()
            )
        )
    return exc.messages[0] if getattr(exc, "messages", None) else str(exc)


def _sales_pipeline_card(lead):
    return {
        "id": lead.id,
        "lead": lead.full_name,
        "division": lead.division,
        "division_label": lead.get_division_display(),
        "source": lead.source,
        "source_label": lead.get_source_display(),
        "referral_partner_id": lead.referral_partner_id,
        "referral_partner_name": (
            lead.referral_partner.name if lead.referral_partner else None
        ),
        "status": lead.status,
        "status_label": lead.get_status_display(),
        "estimated_value": lead.estimated_value,
        "priority": lead.priority,
        "sla_status": lead.sla_status,
        "is_sla_breached": lead.is_sla_breached,
        "is_stale": lead.is_stale,
        "owner": (
            lead.assigned_to.user.get_full_name() if lead.assigned_to else "Unassigned"
        ),
        "next_action": lead.next_action,
        "next_follow_up_at": lead.next_follow_up_at,
        "created_at": lead.created_at,
        "updated_at": lead.updated_at,
    }


def _sales_activity_timeline_item(activity):
    return {
        "id": activity.id,
        "sequence": activity.sequence,
        "activity_type": activity.activity_type,
        "activity_type_display": activity.get_activity_type_display(),
        "outcome": activity.outcome,
        "outcome_display": activity.get_outcome_display(),
        "note": activity.note,
        "from_status": activity.from_status,
        "to_status": activity.to_status,
        "next_action": activity.next_action,
        "next_follow_up_at": activity.next_follow_up_at,
        "created_by": (
            activity.created_by.get_full_name() if activity.created_by else None
        ),
        "created_at": activity.created_at,
    }


def _campaign_validation_detail(exc):
    if hasattr(exc, "message_dict"):
        return "; ".join(
            (
                f"{field}: {', '.join(messages)}"
                for field, messages in exc.message_dict.items()
            )
        )
    return exc.messages[0] if getattr(exc, "messages", None) else str(exc)


def _campaign_pct(numerator, denominator):
    if not denominator:
        return 0.0
    return round(float(numerator) / float(denominator) * 100, 1)


def _campaign_money_ratio(numerator, denominator):
    if not denominator:
        return Decimal("0.00")
    return (Decimal(numerator) / Decimal(denominator)).quantize(Decimal("0.01"))


def _campaign_employee_name(employee):
    if not employee:
        return ""
    full_name = employee.user.get_full_name()
    return full_name or employee.user.email or employee.user.username


def _campaign_campaign_base(campaign):
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


def _campaign_serialize_request(obj):
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


def _campaign_serialize_task(obj):
    return {
        "id": obj.id,
        "campaign_id": obj.campaign_id,
        "title": obj.title,
        "description": obj.description,
        "owner_id": obj.owner_id,
        "owner_name": obj.owner_name or _campaign_employee_name(obj.owner),
        "due_date": obj.due_date,
        "status": obj.status,
        "priority": obj.priority,
        "completed_at": obj.completed_at,
        "created_at": obj.created_at,
        "updated_at": obj.updated_at,
    }


def _campaign_serialize_update(obj):
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


def _campaign_serialize_expense(obj):
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


def _campaign_serialize_asset(obj):
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
        "owner_name": obj.owner_name or _campaign_employee_name(obj.owner),
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


def _campaign_serialize_risk(obj):
    return {
        "id": obj.id,
        "campaign_id": obj.campaign_id,
        "record_type": obj.record_type,
        "severity": obj.severity,
        "title": obj.title,
        "owner_id": obj.owner_id,
        "owner_name": obj.owner_name or _campaign_employee_name(obj.owner),
        "due_date": obj.due_date,
        "mitigation": obj.mitigation,
        "impact": obj.impact,
        "approver": obj.approver,
        "status": obj.status,
        "created_at": obj.created_at,
        "updated_at": obj.updated_at,
    }


def _campaign_serialize_decision(obj):
    return {
        "id": obj.id,
        "campaign_id": obj.campaign_id,
        "decision_date": obj.decision_date,
        "decision": obj.decision,
        "owner": obj.owner,
        "approver": obj.approver,
        "reason": obj.reason,
        "source_meeting_id": (
            obj.source_meeting_context.meeting_id
            if obj.source_meeting_context
            else None
        ),
        "source_meeting_context_id": obj.source_meeting_context_id,
        "created_at": obj.created_at,
        "updated_at": obj.updated_at,
    }


def _campaign_serialize_workspace_meeting(context):
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
        "open_action_count": context.actions.exclude(
            status__in=["done", "cancelled"]
        ).count(),
        "decision_count": context.campaign_decisions.count(),
        "latest_decisions": [
            _campaign_serialize_decision(decision)
            for decision in context.campaign_decisions.all()[:5]
        ],
    }


def _campaign_serialize_post_analysis(obj):
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


def _campaign_lead_row(lead):
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
        "assigned_to_name": _campaign_employee_name(lead.assigned_to),
        "created_at": lead.created_at,
    }


def _marketing_pct(numerator, denominator):
    if not denominator:
        return 0.0
    return round(float(numerator) / float(denominator) * 100, 1)


def _marketing_employee_name(employee):
    if not employee:
        return "Unassigned"
    full_name = employee.user.get_full_name()
    return full_name or employee.user.email or employee.user.username


def _marketing_user_name(user):
    if not user:
        return ""
    return user.get_full_name() or user.email or user.username


def _marketing_valid_email_or_none(email):
    email = (email or "").strip()
    if not email:
        return None
    try:
        validate_email(email)
    except ValidationError:
        return None
    return email


def _marketing_email_body_to_html(body):
    body = body or ""
    if "<" in body and ">" in body:
        return body
    return "<div>" + html.escape(body).replace("\n", "<br>") + "</div>"


def _marketing_email_campaign_row(campaign, include_recipients=False):
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


def _marketing_validation_detail(exc):
    if hasattr(exc, "message_dict"):
        return "; ".join(
            (
                f"{field}: {', '.join(messages)}"
                for field, messages in exc.message_dict.items()
            )
        )
    return exc.messages[0] if getattr(exc, "messages", None) else str(exc)


def _marketing_attendee_row(user):
    return {
        "user_id": user.id,
        "full_name": _marketing_user_name(user),
        "email": user.email,
    }


def _marketing_serialize_marketing_meeting_action(action):
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
        "owner_name": action.owner_name or _marketing_employee_name(action.owner),
        "due_date": action.due_date,
        "status": action.status,
        "priority": action.priority,
        "completed_at": action.completed_at,
        "created_at": action.created_at,
        "updated_at": action.updated_at,
    }


def _marketing_serialize_marketing_meeting_decision(decision):
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


def _marketing_serialize_marketing_meeting_context(context, include_detail=False):
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
        "organizer_name": _marketing_user_name(meeting.organizer),
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
        row["attendees"] = [
            _marketing_attendee_row(user) for user in meeting.attendees.all()
        ]
        row["actions"] = [
            _marketing_serialize_marketing_meeting_action(action)
            for action in context.actions.select_related(
                "owner",
                "owner__user",
                "meeting_context__meeting",
                "meeting_context__campaign",
            ).all()
        ]
        row["decisions"] = [
            _marketing_serialize_marketing_meeting_decision(decision)
            for decision in context.campaign_decisions.select_related(
                "campaign", "source_meeting_context__meeting"
            ).all()
        ]
    return row


def _marketing_meeting_payload_data(payload, exclude_unset=False):
    data = payload.dict(exclude_unset=exclude_unset)
    attendee_ids = data.pop("attendee_ids", None)
    campaign_id = data.pop("campaign_id", None)
    base_data = {
        key: value for key, value in data.items() if key in MEETING_BASE_FIELDS
    }
    context_data = {
        key: value for key, value in data.items() if key in MEETING_CONTEXT_FIELDS
    }
    return (base_data, context_data, attendee_ids, campaign_id)


def _marketing_placement_days_remaining(placement, today=None):
    today = today or timezone.localdate()
    return (placement.end_date - today).days


def _marketing_placement_expiry_state(placement, today=None):
    if placement.status in ["archived", "cancelled"]:
        return placement.status
    days_remaining = _marketing_placement_days_remaining(placement, today)
    if days_remaining < 0:
        return "expired"
    if days_remaining <= TRADITIONAL_MEDIA_EXPIRY_WINDOW_DAYS:
        return "expiring_soon"
    return "active"


def _marketing_placement_code(placement):
    return f"TM-{placement.id:04d}"


def _marketing_serialize_traditional_media_placement(placement, detail=False):
    today = timezone.localdate()
    days_remaining = _marketing_placement_days_remaining(placement, today)
    row = {
        "id": placement.id,
        "placement_code": _marketing_placement_code(placement),
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
        "expiry_state": _marketing_placement_expiry_state(placement, today),
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
        "created_by_name": _marketing_user_name(placement.created_by),
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


def _marketing_traditional_media_metadata():
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


def _marketing_add_email_recipient(
    recipients_by_email,
    email,
    name,
    source_group,
    source_object_type="",
    source_object_id=None,
):
    valid_email = _marketing_valid_email_or_none(email)
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


def _marketing_revenue_target_totals(target_rows):
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


def _marketing_partner_token_hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _marketing_partner_invite_url(base_url, token):
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


def _marketing_partner_task_row(task, include_reports=False):
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
            _marketing_partner_report_row(report)
            for report in task.reports.select_related("reviewed_by").all()
        ]
    return row


def _marketing_partner_report_row(report):
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
        "reviewed_by_name": _marketing_user_name(report.reviewed_by),
        "reviewed_at": report.reviewed_at,
        "review_note": report.review_note,
        "created_at": report.created_at,
        "updated_at": report.updated_at,
    }


def _marketing_partner_commission_row(commission):
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
        "approved_by_name": _marketing_user_name(commission.approved_by),
        "approved_at": commission.approved_at,
        "paid_at": commission.paid_at,
        "payment_reference": commission.payment_reference,
        "note": commission.note,
        "created_at": commission.created_at,
        "updated_at": commission.updated_at,
    }


def _revenue_validation_detail(exc):
    if hasattr(exc, "message_dict"):
        return "; ".join(
            (
                f"{field}: {', '.join(messages)}"
                for field, messages in exc.message_dict.items()
            )
        )
    return exc.messages[0] if getattr(exc, "messages", None) else str(exc)


def _revenue_employee_name(employee):
    return employee.user.get_full_name() if employee else None


def _revenue_role_label(employee):
    if not employee:
        return "Unassigned"
    if employee.role:
        return employee.role.name
    if employee.designation:
        return employee.designation
    return employee.user.get_full_name() or employee.employee_id


def _revenue_decimal_pct(numerator, denominator):
    if not denominator:
        return Decimal("0.00")
    numerator = Decimal(str(numerator or "0.00"))
    denominator = Decimal(str(denominator))
    return min(numerator / denominator * Decimal("100.00"), Decimal("100.00")).quantize(
        Decimal("0.01")
    )


def _revenue_playbook_objection_row(objection):
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


def _revenue_playbook_row(playbook, include_objections=False):
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
            _revenue_playbook_objection_row(objection)
            for objection in playbook.objections.all()
            if objection.is_active
        ]
    return row


def _revenue_money_display(value):
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


def _revenue_normalized_scenario(scenario):
    return scenario if scenario in FORECAST_SCENARIOS else "base"


def _revenue_quality_control_status(value):
    if value is None:
        return "unsupported"
    if value >= Decimal("80.00"):
        return "ok"
    if value >= Decimal("60.00"):
        return "warn"
    return "red"


def _revenue_progress_color(progress):
    if progress >= Decimal("90.00"):
        return "#059669"
    if progress >= Decimal("60.00"):
        return "#D97706"
    return "#DC2626"


def _revenue_lead_sla_status(lead, now=None):
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


def _revenue_recommended_action(lead, sla_status):
    if sla_status == "breached":
        return "Contact immediately and log the first response"
    if sla_status == "due_now":
        return "Contact now before the SLA breaches"
    if lead.score >= 75:
        return "Manager review and next action required today"
    if not lead.next_action:
        return "Create a dated next action"
    return lead.next_action


def _revenue_lead_control_rows(leads, now, limit):
    rows = []
    for lead in leads[:limit]:
        sla_status = _revenue_lead_sla_status(lead, now)
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
                or _revenue_recommended_action(lead, sla_status),
                "sla_status": sla_status,
                "sla_label": (
                    "Breach"
                    if sla_status == "breached"
                    else "Due now" if sla_status == "due_now" else "Safe"
                ),
                "owner": _revenue_employee_name(lead.assigned_to) or "Unassigned",
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


def _revenue_pct(part, whole):
    if not whole:
        return 0.0
    return round(part / whole * 100, 2)


def _revenue_turnaround_end_date(start_date):
    return start_date + timedelta(weeks=13) - timedelta(days=1)


def _revenue_turnaround_kpis(plan):
    total = plan.total_actions
    completed = plan.completed_actions
    current_phase = plan.current_phase.replace("_", " ").title()
    owner_name = _revenue_employee_name(plan.primary_owner) or "Marketing Manager"
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
        {"label": "Primary owner", "value": owner_name, "foot": "CEO removes blockers"},
        {
            "label": "Success test",
            "value": "Revenue + discipline",
            "foot": "Not activity volume alone",
        },
    ]


def _content_validation_detail(exc):
    if hasattr(exc, "message_dict"):
        return "; ".join(
            (
                f"{field}: {', '.join(messages)}"
                for field, messages in exc.message_dict.items()
            )
        )
    return exc.messages[0] if getattr(exc, "messages", None) else str(exc)


def _content_owner_name(employee):
    if not employee:
        return ""
    full_name = employee.user.get_full_name()
    return full_name or employee.user.email or employee.user.username


def _content_format_bytes(size):
    size = int(size or 0)
    if size <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(size)
    unit = units[0]
    for unit in units:
        if value < 1024 or unit == units[-1]:
            break
        value /= 1024
    if unit == "B":
        return f"{int(value)} {unit}"
    return f"{value:.1f} {unit}"


def _content_serialize_media_asset(asset, detail=False):
    row = {
        "id": asset.id,
        "title": asset.title,
        "asset_type": asset.asset_type,
        "file_url": asset.file_url,
        "thumbnail_url": asset.thumbnail_url,
        "mime_type": asset.mime_type,
        "file_size_bytes": asset.file_size_bytes,
        "display_size": _content_format_bytes(asset.file_size_bytes),
        "division": asset.division,
        "branch_id": asset.branch_id,
        "branch_name": asset.branch.branch_name if asset.branch else "",
        "owner_id": asset.owner_id,
        "owner_name": asset.owner_name or _content_owner_name(asset.owner),
        "campaign_id": asset.campaign_id,
        "campaign_name": asset.campaign.name if asset.campaign else "",
        "campaign_asset_id": asset.campaign_asset_id,
        "campaign_asset_name": (
            asset.campaign_asset.name if asset.campaign_asset else ""
        ),
        "calendar_item_id": asset.calendar_item_id,
        "calendar_item_title": asset.calendar_item.title if asset.calendar_item else "",
        "content_id": asset.content_id,
        "content_title": asset.content.title if asset.content else "",
        "tags": asset.tags,
        "description": asset.description,
        "status": asset.status,
        "icon": MEDIA_ICONS.get(asset.asset_type, MEDIA_ICONS["other"]),
        "color": DIVISION_COLORS.get(asset.division, "#6B7280"),
        "uploaded_by_id": asset.uploaded_by_id,
        "uploaded_by_name": (
            asset.uploaded_by.get_full_name() if asset.uploaded_by else ""
        ),
        "created_at": asset.created_at,
        "updated_at": asset.updated_at,
    }
    if detail:
        row["links"] = {
            "campaign": (
                {"id": asset.campaign_id, "name": row["campaign_name"]}
                if asset.campaign
                else None
            ),
            "campaign_asset": (
                {"id": asset.campaign_asset_id, "name": row["campaign_asset_name"]}
                if asset.campaign_asset
                else None
            ),
            "calendar_item": (
                {"id": asset.calendar_item_id, "title": row["calendar_item_title"]}
                if asset.calendar_item
                else None
            ),
            "content": (
                {"id": asset.content_id, "title": row["content_title"]}
                if asset.content
                else None
            ),
        }
    return row


def _content_media_metadata():
    return {
        "asset_types": [
            {"value": value, "label": label}
            for value, label in MediaLibraryAsset.ASSET_TYPE_CHOICES
        ],
        "statuses": [
            {"value": value, "label": label}
            for value, label in MediaLibraryAsset.STATUS_CHOICES
        ],
        "divisions": [
            {"value": value, "label": label}
            for value, label in MediaLibraryAsset.DIVISION_CHOICES
        ],
    }


def _content_effective_status(item, today=None):
    today = today or timezone.localdate()
    if (
        item.status not in TERMINAL_CALENDAR_STATUSES
        and item.due_date
        and (item.due_date < today)
    ):
        return "overdue"
    return item.status


def _content_item_display_date(item):
    if item.published_at:
        return item.published_at.date()
    if item.scheduled_at:
        return item.scheduled_at.date()
    return item.due_date


def _content_serialize_calendar_item(item):
    return {
        "id": item.id,
        "source": "calendar_item",
        "title": item.title,
        "format": item.format,
        "platform": item.platform,
        "division": item.division,
        "branch_id": item.branch_id,
        "branch_name": item.branch.branch_name if item.branch else "",
        "owner_id": item.owner_id,
        "owner_name": item.owner_name or _content_owner_name(item.owner),
        "status": item.status,
        "effective_status": _content_effective_status(item),
        "due_date": item.due_date,
        "scheduled_at": item.scheduled_at,
        "published_at": item.published_at,
        "calendar_date": _content_item_display_date(item),
        "campaign_id": item.campaign_id,
        "campaign_name": item.campaign.name if item.campaign else "",
        "campaign_asset_id": item.campaign_asset_id,
        "content_id": item.content_id,
        "funnel_stage": item.funnel_stage,
        "description": item.description,
        "call_to_action": item.call_to_action,
        "specifications": item.specifications,
        "approval_notes": item.approval_notes,
        "sort_order": item.sort_order,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def _content_serialize_content_only(content):
    calendar_date = None
    if content.published_date:
        calendar_date = content.published_date.date()
    elif content.scheduled_date:
        calendar_date = content.scheduled_date.date()
    return {
        "id": None,
        "source": "content",
        "title": content.title,
        "format": content.content_type,
        "platform": content.platform,
        "division": "",
        "branch_id": None,
        "branch_name": "",
        "owner_id": None,
        "owner_name": content.author.get_full_name() if content.author else "",
        "status": content.status,
        "effective_status": content.status,
        "due_date": None,
        "scheduled_at": content.scheduled_date,
        "published_at": content.published_date,
        "calendar_date": calendar_date,
        "campaign_id": None,
        "campaign_name": "",
        "campaign_asset_id": None,
        "content_id": content.id,
        "funnel_stage": "",
        "description": content.excerpt,
        "call_to_action": "",
        "specifications": content.external_url,
        "approval_notes": "",
        "sort_order": 0,
        "created_at": content.created_at,
        "updated_at": content.updated_at,
    }


def _content_calendar_response(rows, start, end, filters):
    rows = sorted(
        rows,
        key=lambda row: (
            str(row["calendar_date"] or ""),
            row["sort_order"],
            row["title"],
        ),
    )
    week_days = []
    current = start
    while current <= end:
        day_rows = [row for row in rows if row["calendar_date"] == current]
        week_days.append(
            {
                "date": current,
                "weekday": current.strftime("%a"),
                "is_today": current == timezone.localdate(),
                "items": day_rows,
            }
        )
        current += timedelta(days=1)
    total = len(rows)
    published = len([row for row in rows if row["effective_status"] == "published"])
    overdue = len([row for row in rows if row["effective_status"] == "overdue"])
    scheduled = len([row for row in rows if row["effective_status"] == "scheduled"])
    in_progress = len(
        [
            row
            for row in rows
            if row["effective_status"]
            in {"briefed", "in_progress", "in_review", "approved"}
        ]
    )
    return {
        "period": {"start": start, "end": end},
        "label": f"Week of {start.strftime('%b %-d')} - {end.strftime('%b %-d, %Y')}",
        "filters": filters,
        "kpis": {
            "total": total,
            "published": published,
            "scheduled": scheduled,
            "in_progress": in_progress,
            "overdue": overdue,
            "published_label": f"{published} / {total} published",
        },
        "days": week_days,
        "rows": rows,
        "metadata": {
            "statuses": [
                {"value": value, "label": label}
                for value, label in ContentCalendarItem.STATUS_CHOICES
            ],
            "formats": [
                {"value": value, "label": label}
                for value, label in ContentCalendarItem.FORMAT_CHOICES
            ],
            "platforms": [
                {"value": value, "label": label}
                for value, label in ContentCalendarItem.PLATFORM_CHOICES
            ],
            "divisions": [
                {"value": value, "label": label}
                for value, label in ContentCalendarItem.DIVISION_CHOICES
            ],
            "funnel_stages": [
                {"value": value, "label": label}
                for value, label in ContentCalendarItem.FUNNEL_STAGE_CHOICES
            ],
        },
    }
