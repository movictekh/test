"""State-changing helpers for Marketing & Sales leads."""

from django.utils import timezone

from domains.marketing_sales.services.funnel import record_status_funnel_event


def _apply_lead_payload(lead, payload_data, actor=None):
    previous_status = lead.status
    for attr, value in payload_data.items():
        setattr(lead, attr, value)

    if lead.status != "new" and not lead.first_contact_at:
        lead.first_contact_at = timezone.now()
    if lead.first_contact_at and not lead.first_response_at:
        lead.first_response_at = lead.first_contact_at

    lead.refresh_sla_status()
    lead.refresh_score()
    lead.full_clean()
    lead.save()
    if "status" in payload_data and previous_status != lead.status:
        record_status_funnel_event(
            lead,
            from_status=previous_status,
            to_status=lead.status,
            actor=actor,
        )
    return lead


def _apply_activity_effects(lead, payload_data):
    update_fields = []
    to_status = payload_data.get("to_status")

    if payload_data.get("next_action"):
        lead.next_action = payload_data["next_action"]
        update_fields.append("next_action")
    if payload_data.get("next_follow_up_at"):
        lead.next_follow_up_at = payload_data["next_follow_up_at"]
        update_fields.append("next_follow_up_at")
    if to_status:
        lead.status = to_status
        update_fields.append("status")

    is_contact_activity = payload_data.get("activity_type") != "internal_note"
    if (to_status and to_status != "new") or is_contact_activity:
        if not lead.first_contact_at:
            lead.first_contact_at = timezone.now()
            update_fields.append("first_contact_at")
        if not lead.first_response_at:
            lead.first_response_at = lead.first_contact_at or timezone.now()
            update_fields.append("first_response_at")

    if (
        to_status in ["contacted", "qualified", "proposal_sent", "negotiation"]
        or is_contact_activity
    ):
        lead.last_contact_at = timezone.now()
        update_fields.append("last_contact_at")

    if update_fields:
        lead.refresh_sla_status()
        lead.refresh_score()
        update_fields.extend(["sla_status", "score", "score_breakdown"])
        update_fields.append("updated_at")
        lead.full_clean()
        lead.save(update_fields=list(dict.fromkeys(update_fields)))
