"""State-changing workflows for campaigns, marketing operations, content and media."""

from django.core.exceptions import ValidationError
from django.utils import timezone

from domains.marketing_sales.constants import (
    CAMPAIGN_ASSET_STATUS_BY_CALENDAR_STATUS,
    CAMPAIGN_ASSET_TYPE_BY_FORMAT,
    EMAIL_AUDIENCE_GROUPS,
)
from domains.marketing_sales.models.marketing import (
    CampaignAsset,
    PartnerInvitation,
)
from domains.marketing_sales.models.sales import Lead
from domains.marketing_sales.presenters import (
    _content_effective_status as _effective_status,
)
from domains.marketing_sales.presenters import (
    _marketing_add_email_recipient as _add_email_recipient,
)
from domains.marketing_sales.presenters import (
    _marketing_employee_name as _employee_name,
)
from domains.marketing_sales.presenters import (
    _marketing_partner_token_hash as _partner_token_hash,
)
from domains.marketing_sales.presenters import _marketing_user_name as _user_name
from domains.marketing_sales.selectors.marketing import (
    _email_filters,
    _lead_queryset,
    _partner_portal_token,
)
from domains.marketing_sales.services.funnel import record_initial_funnel_event
from domains.crm.models.client import Client as CustomerClient
from domains.people.models.employee import Employee
from domains.crm.models.partner import Partner
from user.models.user import User
from system.authorization import scope_queryset


def _set_meeting_attendees(meeting, attendee_ids):
    if attendee_ids is None:
        return None
    attendees = User.objects.filter(id__in=attendee_ids)
    if attendees.count() != len(attendee_ids):
        raise ValidationError("One or more attendee user IDs are invalid")
    meeting.attendees.set(attendees)
    return attendees


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
    return (list(recipients_by_email.values()), skipped_count)


def _resolve_partner_invitation(request):
    token = _partner_portal_token(request)
    if not token:
        return (None, {"detail": "Partner portal token is required."})
    invitation = (
        PartnerInvitation.objects.select_related("partner")
        .filter(token_hash=_partner_token_hash(token), status__in=["sent", "accepted"])
        .first()
    )
    if not invitation:
        return (None, {"detail": "Invalid partner portal token."})
    if invitation.is_expired:
        invitation.status = "expired"
        invitation.save(update_fields=["status", "updated_at"])
        return (None, {"detail": "Partner portal token has expired."})
    if invitation.partner.status in ["inactive", "suspended"]:
        return (None, {"detail": "Partner is not currently allowed to use the portal."})
    if invitation.status == "sent":
        invitation.status = "accepted"
        invitation.accepted_at = timezone.now()
        invitation.partner.status = "active"
        invitation.partner.save(update_fields=["status", "updated_at"])
        invitation.save(update_fields=["status", "accepted_at", "updated_at"])
    return (invitation, None)


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


def _campaign_apply_payload(instance, payload_data, owner_model_fields=None):
    owner_model_fields = owner_model_fields or {}
    for attr, value in payload_data.items():
        model_attr = owner_model_fields.get(attr, attr)
        setattr(instance, model_attr, value)
    instance.full_clean()
    instance.save()
    return instance


def _content_sync_media_to_campaign_asset(asset):
    if not asset.campaign_asset:
        return
    campaign_asset = asset.campaign_asset
    if asset.content_id:
        campaign_asset.content_id = asset.content_id
    if asset.description and (not campaign_asset.description):
        campaign_asset.description = asset.description
    if asset.thumbnail_url and (not campaign_asset.specifications):
        campaign_asset.specifications = asset.thumbnail_url
    campaign_asset.full_clean()
    campaign_asset.save()


def _content_sync_campaign_asset(item, actor=None):
    if not item.campaign:
        if item.campaign_asset_id:
            item.campaign_asset = None
            item.save(update_fields=["campaign_asset", "updated_at"])
        return None
    defaults = {
        "name": item.title,
        "asset_type": CAMPAIGN_ASSET_TYPE_BY_FORMAT.get(item.format, "other"),
        "owner": item.owner,
        "owner_name": item.owner_name,
        "due_date": item.due_date,
        "status": CAMPAIGN_ASSET_STATUS_BY_CALENDAR_STATUS.get(
            _effective_status(item), "briefed"
        ),
        "description": item.description,
        "specifications": item.specifications,
        "approval_notes": item.approval_notes,
        "content": item.content,
        "created_by": actor or item.created_by,
    }
    if item.campaign_asset_id:
        asset = item.campaign_asset
        for attr, value in defaults.items():
            setattr(asset, attr, value)
        asset.full_clean()
        asset.save()
        return asset
    asset = CampaignAsset.objects.create(campaign=item.campaign, **defaults)
    item.campaign_asset = asset
    item.save(update_fields=["campaign_asset", "updated_at"])
    return asset
