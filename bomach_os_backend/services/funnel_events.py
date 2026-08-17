from django.utils import timezone

from services.models.crm import (
    TERMINAL_LEAD_STATUSES,
    Lead,
    LeadFunnelEvent,
    funnel_stage_for_lead_status,
)


def _event_snapshot(lead):
    return {
        "source": lead.source or "",
        "division": lead.division or "",
        "campaign_id": lead.campaign_id,
        "branch_id": lead.branch_id,
    }


def _create_event(
    lead,
    *,
    from_stage="",
    to_stage="",
    event_type="transition",
    occurred_at=None,
    actor=None,
    metadata=None,
):
    metadata = metadata or {}
    snapshot = _event_snapshot(lead)
    occurred_at = occurred_at or timezone.now()
    existing = LeadFunnelEvent.objects.filter(
        lead=lead,
        from_stage=from_stage or "",
        to_stage=to_stage or "",
        event_type=event_type,
        metadata=metadata,
    ).first()
    if existing:
        return existing

    return LeadFunnelEvent.objects.create(
        lead=lead,
        from_stage=from_stage or "",
        to_stage=to_stage or "",
        event_type=event_type,
        occurred_at=occurred_at,
        source=snapshot["source"],
        division=snapshot["division"],
        campaign_id=snapshot["campaign_id"],
        branch_id=snapshot["branch_id"],
        actor=actor,
        metadata=metadata,
    )


def record_initial_funnel_event(
    lead, *, actor=None, occurred_at=None, backfilled=False, metadata=None
):
    event_metadata = {"backfilled": backfilled, "current_status": lead.status}
    event_metadata.update(metadata or {})
    return _create_event(
        lead,
        to_stage="discovery",
        event_type="initial",
        occurred_at=occurred_at or lead.created_at or timezone.now(),
        actor=actor,
        metadata=event_metadata,
    )


def record_status_funnel_event(
    lead,
    *,
    from_status,
    to_status,
    actor=None,
    occurred_at=None,
    backfilled=False,
    metadata=None,
):
    if not to_status:
        return None

    from_stage = funnel_stage_for_lead_status(from_status) if from_status else ""
    to_stage = funnel_stage_for_lead_status(to_status)
    event_metadata = {
        "from_status": from_status or "",
        "to_status": to_status,
        "backfilled": backfilled,
    }
    event_metadata.update(metadata or {})

    if to_status in TERMINAL_LEAD_STATUSES:
        event_metadata["terminal_status"] = to_status
        return _create_event(
            lead,
            from_stage=from_stage,
            event_type="terminal",
            occurred_at=occurred_at,
            actor=actor,
            metadata=event_metadata,
        )

    if not to_stage:
        return None
    if (
        from_stage == to_stage
        and LeadFunnelEvent.objects.filter(lead=lead, to_stage=to_stage).exists()
    ):
        return None

    return _create_event(
        lead,
        from_stage=from_stage,
        to_stage=to_stage,
        event_type="transition",
        occurred_at=occurred_at,
        actor=actor,
        metadata=event_metadata,
    )


def backfill_lead_funnel_events(queryset=None):
    leads = queryset or Lead.objects.all()
    created = 0
    skipped = 0

    for lead in leads.prefetch_related("activities", "funnel_events"):
        if not lead.funnel_events.filter(event_type="initial").exists():
            record_initial_funnel_event(
                lead, occurred_at=lead.created_at, backfilled=True
            )
            created += 1

        for activity in lead.activities.order_by("sequence", "created_at", "id"):
            if not activity.to_status:
                continue
            if LeadFunnelEvent.objects.filter(
                lead=lead,
                metadata__activity_id=activity.id,
            ).exists():
                skipped += 1
                continue
            event = record_status_funnel_event(
                lead,
                from_status=activity.from_status,
                to_status=activity.to_status,
                actor=activity.created_by,
                occurred_at=activity.created_at,
                backfilled=True,
                metadata={"activity_id": activity.id},
            )
            created += 1 if event else 0

        current_stage = funnel_stage_for_lead_status(lead.status)
        if (
            current_stage
            and not lead.funnel_events.filter(to_stage=current_stage).exists()
        ):
            event = record_status_funnel_event(
                lead,
                from_status="",
                to_status=lead.status,
                actor=lead.created_by,
                occurred_at=lead.updated_at or lead.created_at,
                backfilled=True,
                metadata={"inferred_current": True},
            )
            created += 1 if event else 0
        else:
            skipped += 1

    return {"created": created, "skipped": skipped}
