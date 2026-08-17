"""State-changing workflows for Sales and revenue execution."""

from django.shortcuts import get_object_or_404
from django.utils import timezone

from domains.marketing_sales.constants import TURNAROUND_DEFAULT_ACTIONS
from domains.marketing_sales.models.revenue_execution import (
    DailyActionInstance,
    DailyActionTemplate,
    DailyExecutionDay,
    RevenueKeyResult,
    RevenueObjective,
    TurnaroundAction,
    TurnaroundPlan,
)
from domains.marketing_sales.presenters import (
    _revenue_turnaround_end_date as _turnaround_end_date,
)
from domains.marketing_sales.selectors.sales import (
    _revenue_day_queryset as _day_queryset,
)
from domains.marketing_sales.selectors.sales import (
    _revenue_templates_for_day as _templates_for_day,
)
from domains.marketing_sales.services.funnel import (
    record_initial_funnel_event,
    record_status_funnel_event,
)
from user.models.branch import Branch


def _apply_lead_payload(lead, payload_data, actor=None):
    previous_status = lead.status
    for attr, value in payload_data.items():
        setattr(lead, attr, value)
    if lead.status != "new" and (not lead.first_contact_at):
        lead.first_contact_at = timezone.now()
    if lead.first_contact_at and (not lead.first_response_at):
        lead.first_response_at = lead.first_contact_at
    lead.refresh_sla_status()
    lead.refresh_score()
    lead.full_clean()
    lead.save()
    if "status" in payload_data and previous_status != lead.status:
        record_status_funnel_event(
            lead, from_status=previous_status, to_status=lead.status, actor=actor
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
    if to_status and to_status != "new" or is_contact_activity:
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


def _revenue_apply_template_payload(template, payload_data):
    for attr, value in payload_data.items():
        setattr(template, attr, value)
    template.full_clean()
    template.save()
    return template


def _revenue_apply_action_payload(action, payload_data):
    for attr, value in payload_data.items():
        setattr(action, attr, value)
    action.full_clean()
    action.save()
    return action


def _revenue_ensure_action_instances(day, templates):
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


def _revenue_open_day(request, target_date, branch_id=None, force_rebuild=False):
    branch = None
    if branch_id:
        branch = get_object_or_404(Branch, id=branch_id)
    day, _ = DailyExecutionDay.objects.get_or_create(
        date=target_date, branch=branch, defaults={"opened_by": request.user}
    )
    templates = _templates_for_day(request, branch_id)
    if force_rebuild or not day.actions.exists():
        _revenue_ensure_action_instances(day, templates)
    return get_object_or_404(_day_queryset(request), id=day.id)


def _revenue_apply_objective_payload(objective, payload_data):
    for attr, value in payload_data.items():
        setattr(objective, attr, value)
    objective.full_clean()
    objective.save()
    return objective


def _revenue_apply_key_result_payload(key_result, payload_data):
    for attr, value in payload_data.items():
        setattr(key_result, attr, value)
    key_result.full_clean()
    key_result.save()
    return key_result


def _revenue_seed_turnaround_actions(plan):
    actions = [
        TurnaroundAction(plan=plan, sort_order=index + 1, **action)
        for index, action in enumerate(TURNAROUND_DEFAULT_ACTIONS)
    ]
    TurnaroundAction.objects.bulk_create(actions)


def _revenue_activate_turnaround_plan(plan):
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


def _revenue_apply_turnaround_plan_payload(plan, payload_data):
    activate = payload_data.get("status") == "active"
    for attr, value in payload_data.items():
        setattr(plan, attr, value)
    if plan.start_date and (not plan.end_date):
        plan.end_date = _turnaround_end_date(plan.start_date)
    plan.full_clean()
    plan.save()
    if activate:
        plan = _revenue_activate_turnaround_plan(plan)
    return plan


def _revenue_apply_turnaround_action_payload(action, payload_data):
    for attr, value in payload_data.items():
        setattr(action, attr, value)
    if "status" in payload_data:
        if action.status == "completed" and (not action.completed_at):
            action.completed_at = timezone.now()
        elif action.status == "open":
            action.completed_at = None
            action.completed_by = None
            action.completion_note = ""
    action.full_clean()
    action.save()
    return action
