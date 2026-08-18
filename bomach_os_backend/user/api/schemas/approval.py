from ninja import Schema
from typing import Optional, List, Any, Dict
from datetime import datetime


# Human-readable labels for each employee level value
_LEVEL_DISPLAY = {
    'intern':           'Intern',
    'junior':           'Junior',
    'mid_level':        'Mid Level',
    'senior':           'Senior',
    'high':             'High',
    'head_hr':          'Head of Human Resources',
    'head_operations':  'Head of Operations',
    'head_marketing':   'Head of Marketing',
    'head_finance':     'Head of Finance',
    'head_legal':       'Head of Legal',
    'head_it':          'Head of IT',
    'manager':          'Manager',
    'cto':              'Chief Technology Officer',
    'cfo':              'Chief Financial Officer',
    'clo':              'Chief Legal Officer',
    'chro':             'Chief Human Resources Officer',
    'cmo':              'Chief Marketing Officer',
    'board_member':     'Board Member',
    'ceo':              'Chief Executive Officer',
}


# ── Flow schemas ──────────────────────────────────────────────────────────────

class ApprovalFlowStepInputSchema(Schema):
    """One step definition when creating / updating a flow."""
    step_order: int
    step_name: str
    required_level: str


class ApprovalFlowCreateSchema(Schema):
    name: str
    description: Optional[str] = None
    action_type: str
    steps: List[ApprovalFlowStepInputSchema]


class ApprovalFlowUpdateSchema(Schema):
    name: Optional[str] = None
    description: Optional[str] = None
    action_type: Optional[str] = None
    is_active: Optional[bool] = None
    # When provided, fully replaces all existing steps
    steps: Optional[List[ApprovalFlowStepInputSchema]] = None


class ApprovalFlowStepSchema(Schema):
    id: int
    step_order: int
    step_name: str
    required_level: str
    required_level_display: str

    @staticmethod
    def resolve_required_level_display(obj):
        return _LEVEL_DISPLAY.get(obj.required_level, obj.required_level)


class ApprovalFlowSchema(Schema):
    id: int
    name: str
    description: Optional[str] = None
    action_type: str
    action_type_display: str
    is_active: bool
    steps: List[ApprovalFlowStepSchema]
    created_by_id: Optional[int] = None
    created_by_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_action_type_display(obj):
        return obj.get_action_type_display()

    @staticmethod
    def resolve_steps(obj):
        return list(obj.steps.all())

    @staticmethod
    def resolve_created_by_name(obj):
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}".strip() or obj.created_by.email
        return None


# ── Request schemas ───────────────────────────────────────────────────────────

class ApprovalRequestCreateSchema(Schema):
    flow_id: int
    title: str
    description: str
    metadata: Optional[Dict[str, Any]] = None


class ApprovalActionSchema(Schema):
    """Payload for approve / reject endpoints."""
    comment: Optional[str] = None


class ApprovalDecisionSchema(Schema):
    id: int
    step_order: int
    step_name: str
    decision: str
    decision_display: str
    comment: Optional[str] = None
    approver_id: Optional[int] = None
    approver_name: Optional[str] = None
    created_at: datetime

    @staticmethod
    def resolve_decision_display(obj):
        return obj.get_decision_display()

    @staticmethod
    def resolve_approver_name(obj):
        if obj.approver:
            return f"{obj.approver.first_name} {obj.approver.last_name}".strip() or obj.approver.email
        return None


class ApprovalRequestSchema(Schema):
    id: int
    approval_request_id: str
    flow_id: int
    flow_name: str
    action_type: str
    action_type_display: str
    title: str
    description: str
    status: str
    status_display: str
    current_step: int
    total_steps: int
    # The label of the step currently awaiting a decision (None if done)
    pending_step_name: Optional[str] = None
    pending_step_required_level: Optional[str] = None
    pending_step_required_level_display: Optional[str] = None
    decisions: List[ApprovalDecisionSchema]
    metadata: Optional[Dict[str, Any]] = None
    created_by_id: Optional[int] = None
    created_by_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_flow_name(obj):
        return obj.flow.name

    @staticmethod
    def resolve_action_type(obj):
        return obj.flow.action_type

    @staticmethod
    def resolve_action_type_display(obj):
        return obj.flow.get_action_type_display()

    @staticmethod
    def resolve_status_display(obj):
        return obj.get_status_display()

    @staticmethod
    def resolve_total_steps(obj):
        return obj.total_steps

    @staticmethod
    def resolve_pending_step_name(obj):
        if obj.status != 'pending':
            return None
        step = obj.flow.steps.filter(step_order=obj.current_step).first()
        return step.step_name if step else None

    @staticmethod
    def resolve_pending_step_required_level(obj):
        if obj.status != 'pending':
            return None
        step = obj.flow.steps.filter(step_order=obj.current_step).first()
        return step.required_level if step else None

    @staticmethod
    def resolve_pending_step_required_level_display(obj):
        if obj.status != 'pending':
            return None
        step = obj.flow.steps.filter(step_order=obj.current_step).first()
        return _LEVEL_DISPLAY.get(step.required_level, step.required_level) if step else None

    @staticmethod
    def resolve_decisions(obj):
        return list(obj.decisions.all())

    @staticmethod
    def resolve_created_by_name(obj):
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}".strip() or obj.created_by.email
        return None


class ApprovalFlowChoicesSchema(Schema):
    action_types: List[dict]
