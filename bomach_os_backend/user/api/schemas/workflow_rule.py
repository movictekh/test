from datetime import datetime
from typing import List, Optional

from ninja import Schema


class ConditionSchema(Schema):
    field: str
    operator: str
    value: str


class WorkflowRuleIn(Schema):
    name: str
    description: str = ""
    trigger_event: str
    conditions: List[ConditionSchema] = []
    action_type: str
    action_config: dict = {}
    is_active: bool = True


class WorkflowRuleUpdate(Schema):
    name: Optional[str] = None
    description: Optional[str] = None
    trigger_event: Optional[str] = None
    conditions: Optional[List[ConditionSchema]] = None
    action_type: Optional[str] = None
    action_config: Optional[dict] = None
    is_active: Optional[bool] = None


class WorkflowRuleOut(Schema):
    id: int
    name: str
    description: str
    trigger_event: str
    conditions: list
    action_type: str
    action_config: dict
    is_active: bool
    created_by_name: str = ""
    execution_count: int = 0
    created_at: datetime


class WorkflowRuleLogOut(Schema):
    id: int
    rule_name: str
    trigger_event: str
    trigger_object_id: int
    trigger_object_type: str
    conditions_met: bool
    action_executed: bool
    error_message: str
    created_at: datetime


class ChoiceSchema(Schema):
    value: str
    label: str
