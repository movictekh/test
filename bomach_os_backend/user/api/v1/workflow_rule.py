from ninja import Router
from ninja.pagination import paginate, LimitOffsetPagination
from django.shortcuts import get_object_or_404

from user.api.schemas.workflow_rule import (
    WorkflowRuleIn, WorkflowRuleUpdate, WorkflowRuleOut,
    WorkflowRuleLogOut, ChoiceSchema,
)
from user.models.workflow_rule import WorkflowRule, WorkflowRuleLog
from user.utils.perm import require_permission

workflow_rule_router = Router(tags=["Workflow Rules"])


@workflow_rule_router.get("/choices/triggers", response=list[ChoiceSchema])
@require_permission("workflow_rules", "view")
def get_trigger_choices(request):
    return [
        ChoiceSchema(value=val, label=label)
        for val, label in WorkflowRule.TRIGGER_CHOICES
    ]


@workflow_rule_router.get("/choices/actions", response=list[ChoiceSchema])
@require_permission("workflow_rules", "view")
def get_action_choices(request):
    return [
        ChoiceSchema(value=val, label=label)
        for val, label in WorkflowRule.ACTION_CHOICES
    ]


@workflow_rule_router.get("/", response=list[WorkflowRuleOut])
@paginate(LimitOffsetPagination, page_size=20)
@require_permission("workflow_rules", "list")
def list_rules(request, trigger_event: str = None, is_active: bool = None):
    qs = WorkflowRule.objects.all()
    if trigger_event:
        qs = qs.filter(trigger_event=trigger_event)
    if is_active is not None:
        qs = qs.filter(is_active=is_active)
    return [
        WorkflowRuleOut(
            id=r.id,
            name=r.name,
            description=r.description,
            trigger_event=r.trigger_event,
            conditions=r.conditions,
            action_type=r.action_type,
            action_config=r.action_config,
            is_active=r.is_active,
            created_by_name=r.created_by.get_full_name() if r.created_by else '',
            execution_count=r.execution_logs.count(),
            created_at=r.created_at,
        )
        for r in qs
    ]


@workflow_rule_router.get("/{rule_id}", response=WorkflowRuleOut)
@require_permission("workflow_rules", "view")
def get_rule(request, rule_id: int):
    r = get_object_or_404(WorkflowRule, id=rule_id)
    return WorkflowRuleOut(
        id=r.id,
        name=r.name,
        description=r.description,
        trigger_event=r.trigger_event,
        conditions=r.conditions,
        action_type=r.action_type,
        action_config=r.action_config,
        is_active=r.is_active,
        created_by_name=r.created_by.get_full_name() if r.created_by else '',
        created_at=r.created_at,
    )


@workflow_rule_router.post("/", response={201: WorkflowRuleOut})
@require_permission("workflow_rules", "create")
def create_rule(request, payload: WorkflowRuleIn):
    rule = WorkflowRule.objects.create(
        name=payload.name,
        description=payload.description,
        trigger_event=payload.trigger_event,
        conditions=[c.dict() for c in payload.conditions],
        action_type=payload.action_type,
        action_config=payload.action_config,
        is_active=payload.is_active,
        created_by=request.user,
    )
    return 201, WorkflowRuleOut(
        id=rule.id,
        name=rule.name,
        description=rule.description,
        trigger_event=rule.trigger_event,
        conditions=rule.conditions,
        action_type=rule.action_type,
        action_config=rule.action_config,
        is_active=rule.is_active,
        created_by_name=request.user.get_full_name(),
        created_at=rule.created_at,
    )


@workflow_rule_router.put("/{rule_id}", response={200: WorkflowRuleOut})
@require_permission("workflow_rules", "update")
def update_rule(request, rule_id: int, payload: WorkflowRuleUpdate):
    rule = get_object_or_404(WorkflowRule, id=rule_id)
    data = payload.dict(exclude_unset=True)
    if 'conditions' in data and data['conditions'] is not None:
        data['conditions'] = [
            c.dict() if hasattr(c, 'dict') else c
            for c in data['conditions']
        ]
    for field, value in data.items():
        setattr(rule, field, value)
    rule.save()
    return WorkflowRuleOut(
        id=rule.id,
        name=rule.name,
        description=rule.description,
        trigger_event=rule.trigger_event,
        conditions=rule.conditions,
        action_type=rule.action_type,
        action_config=rule.action_config,
        is_active=rule.is_active,
        created_by_name=rule.created_by.get_full_name() if rule.created_by else '',
        created_at=rule.created_at,
    )


@workflow_rule_router.delete("/{rule_id}", response={200: dict})
@require_permission("workflow_rules", "delete")
def deactivate_rule(request, rule_id: int):
    rule = get_object_or_404(WorkflowRule, id=rule_id)
    rule.is_active = False
    rule.save(update_fields=['is_active', 'updated_at'])
    return {"detail": f"Rule '{rule.name}' deactivated"}
