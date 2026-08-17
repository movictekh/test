"""
Workflow engine: evaluates rules against trigger events and executes actions.
"""

from decimal import Decimal

from user.models.workflow_rule import WorkflowRule, WorkflowRuleLog

OPERATORS = {
    "eq": lambda a, b: str(a) == str(b),
    "neq": lambda a, b: str(a) != str(b),
    "gt": lambda a, b: float(a) > float(b),
    "gte": lambda a, b: float(a) >= float(b),
    "lt": lambda a, b: float(a) < float(b),
    "lte": lambda a, b: float(a) <= float(b),
    "in": lambda a, b: str(a) in [str(v) for v in b],
    "contains": lambda a, b: str(b) in str(a),
}


def _evaluate_conditions(conditions, instance):
    """Check if all conditions match the instance. AND logic."""
    for condition in conditions:
        field = condition.get("field", "")
        operator = condition.get("operator", "eq")
        expected = condition.get("value", "")

        actual = getattr(instance, field, None)
        if actual is None:
            return False

        op_func = OPERATORS.get(operator)
        if op_func is None:
            return False

        if not op_func(actual, expected):
            return False

    return True


def _execute_notification(action_config, trigger_event, instance):
    """Create Notification records for specified recipients."""
    from user.models.notification import Notification

    recipient_ids = action_config.get("recipient_ids", [])
    title = action_config.get("title", f"Workflow: {trigger_event}")
    message = action_config.get(
        "message", f"An automated action was triggered by {trigger_event}."
    )

    for user_id in recipient_ids:
        Notification.objects.create(
            user_id=user_id,
            title=title,
            message=message,
            notification_type="system",
            link=action_config.get("link", ""),
            metadata={
                "trigger_event": trigger_event,
                "object_type": type(instance).__name__,
                "object_id": instance.pk,
            },
        )


def evaluate_workflow_rules(trigger_event, instance):
    """
    Called from domain endpoints after a status change.

    1. Query active WorkflowRule objects matching trigger_event
    2. Evaluate conditions against instance
    3. If conditions match, execute action
    4. Log execution to WorkflowRuleLog
    """
    rules = WorkflowRule.objects.filter(
        trigger_event=trigger_event,
        is_active=True,
    )

    for rule in rules:
        conditions_met = _evaluate_conditions(rule.conditions, instance)
        action_executed = False
        error_message = ""

        if conditions_met:
            try:
                if rule.action_type == "send_notification":
                    _execute_notification(rule.action_config, trigger_event, instance)
                action_executed = True
            except Exception as e:
                error_message = str(e)

        WorkflowRuleLog.objects.create(
            rule=rule,
            trigger_event=trigger_event,
            trigger_object_id=instance.pk,
            trigger_object_type=type(instance).__name__,
            conditions_met=conditions_met,
            action_executed=action_executed,
            error_message=error_message,
        )
